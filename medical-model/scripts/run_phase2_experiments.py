"""Phase 2 对比实验脚本 — 16-field schema + 药物词汇裁剪 + 500患者

核心改动 (vs Phase 1):
1. Schema: 14→16 fields (新增 med_class_3, med_class_4)
2. FeatureEncoder: drug_candidate 频率裁剪 (min_freq=2, __RARE__ token)
3. 患者数据: 300→500 (pipeline_data.json已重新生成)
4. Labeler: 新增 efficacy_tier 字段 (不影响label值)

3组核心实验:
  1. no_dp_baseline_v5   — 16-field schema, 500患者, 无DP训练 (v5 baseline)
  2. dp_finetune_eps1_v5  — 预训练→DP微调 ε=1.0 (主要实验组)
  3. dp_finetune_eps05_v5 — 预训练→DP微调 ε=0.5 (严格隐私)

输出:
  experiments/results/phase2/ 下每组 metadata + train_history
  experiments/results/phase2/comparison_table.json 汇总表
"""

import json
import csv
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# 确保项目根目录在sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.runner import PipelineRunner
from app.models.trainer import DeepFMTrainer
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase2"


def load_pipeline_data() -> Dict[str, Any]:
    """加载pipeline_data.json"""
    pipeline_path = Path(settings.data_dir) / "pipeline_data.json"
    if not pipeline_path.exists():
        raise FileNotFoundError(f"pipeline_data.json not found at {pipeline_path}")
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_pipeline(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """运行数据管道"""
    runner = PipelineRunner()
    runner.load_safety_data(
        pipeline_data.get('contraindication_map', {}),
        pipeline_data.get('interaction_map', {}),
    )
    runner.load_indication_data(
        pipeline_data.get('indication_map', {}),
    )

    merged_drugs = pipeline_data.get('merged_drugs', {})
    drugs_list = list(merged_drugs.values())
    patient_records = pipeline_data.get('patient_records', [])

    if not patient_records:
        raise ValueError("No patient_records in pipeline_data.json")

    return runner.run(patient_records, drugs_list, seed=42)


def evaluate_on_test(model, test_dataset, device, criterion) -> Dict[str, float]:
    """在测试集上评估模型"""
    import torch
    import numpy as np
    from torch.utils.data import DataLoader

    model.eval()
    loader = DataLoader(test_dataset, batch_size=256, shuffle=False)

    total_loss = 0.0
    all_preds = []
    all_labels = []

    with torch.no_grad():
        for batch in loader:
            field_indices = batch['field_indices'].to(device)
            continuous_features = batch['continuous_features'].to(device)
            labels = batch['label'].to(device)

            logits, _ = model(field_indices, continuous_features)
            loss = criterion(logits, labels)

            total_loss += loss.item() * len(labels)
            probs = torch.sigmoid(logits).detach().cpu().numpy().flatten()
            all_preds.extend(probs)
            all_labels.extend(labels.detach().cpu().numpy().flatten())

    avg_loss = total_loss / len(all_labels)
    preds = np.array(all_preds)
    labels = np.array(all_labels)

    metrics = {'test_loss': avg_loss}

    # AUC-PR
    try:
        from sklearn.metrics import average_precision_score
        binary_labels = (labels >= 0.5).astype(int)
        if binary_labels.sum() > 0 and (1 - binary_labels).sum() > 0:
            metrics['auc_pr'] = float(average_precision_score(binary_labels, preds))
    except ImportError:
        metrics['auc_pr'] = 0.0

    # AUC-ROC
    try:
        from sklearn.metrics import roc_auc_score
        binary_labels = (labels >= 0.5).astype(int)
        if binary_labels.sum() > 0 and (1 - binary_labels).sum() > 0:
            metrics['auc_roc'] = float(roc_auc_score(binary_labels, preds))
    except (ImportError, ValueError):
        metrics['auc_roc'] = 0.0

    # HR@4, HR@10
    for k in [4, 10]:
        top_k_indices = np.argsort(preds)[::-1][:k]
        top_k_labels = labels[top_k_indices]
        metrics[f'hr@{k}'] = float(np.mean(top_k_labels >= 0.7))

    # SafetyViolationRate@4
    top_4_indices = np.argsort(preds)[::-1][:4]
    top_4_labels = labels[top_4_indices]
    metrics['safety_violation_rate@4'] = float(np.mean(top_4_labels == 0.0))

    # 预测分布
    positive_mask = labels >= 0.7
    negative_mask = labels <= 0.05
    if positive_mask.any():
        metrics['mean_pred_positive'] = float(preds[positive_mask].mean())
    if negative_mask.any():
        metrics['mean_pred_negative'] = float(preds[negative_mask].mean())

    if positive_mask.any() and negative_mask.any():
        metrics['separation'] = float(
            preds[positive_mask].mean() - preds[negative_mask].mean()
        )

    logger.info(
        f"Test metrics: loss={avg_loss:.4f}, auc_pr={metrics.get('auc_pr', 0):.4f}, "
        f"separation={metrics.get('separation', 0):.4f}"
    )
    return metrics


def run_no_dp_baseline(name, pipeline_result, epochs=15) -> Dict[str, Any]:
    """运行无DP基线实验 (16-field schema, 500患者)"""
    field_dims = pipeline_result['field_dims']
    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    test_dataset = pipeline_result['test_dataset']

    logger.info(f"Starting experiment: {name} (No-DP, field_dims={field_dims})")

    trainer = DeepFMTrainer(
        field_dims=field_dims,
        embed_dim=settings.embed_dim,
        hidden_dims=settings.hidden_dims,
        dropout=settings.dropout,
        embed_dropout=settings.embed_dropout,
        focal_alpha=settings.focal_loss_alpha,
        focal_gamma=settings.focal_loss_gamma,
        dp_enabled=False,
    )

    save_dir = str(RESULTS_DIR / name)
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    metadata = trainer.train(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        epochs=epochs,
        learning_rate=settings.default_learning_rate,
        batch_size=settings.default_batch_size,
        patience=settings.early_stopping_patience,
        weight_decay=settings.weight_decay,
        save_dir=save_dir,
    )
    elapsed = time.time() - start_time

    pipeline_result['encoder'].save(str(Path(save_dir) / "encoder.json"))

    metadata['experiment_name'] = name
    metadata['strategy'] = 'no_dp_baseline'
    metadata['schema_version'] = 'v5_16fields'
    metadata['field_dims'] = field_dims
    metadata['embed_dim'] = settings.embed_dim
    metadata['dp_training'] = False
    metadata['training_time_seconds'] = round(elapsed, 2)
    metadata['num_test_samples'] = len(test_dataset)

    test_metrics = evaluate_on_test(
        trainer.model, test_dataset, trainer.device, trainer.criterion
    )
    metadata['test_metrics'] = test_metrics

    with open(Path(save_dir) / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Experiment {name} completed in {elapsed:.1f}s: "
        f"best_val_loss={metadata['best_val_loss']:.4f}, "
        f"test_auc_pr={test_metrics.get('auc_pr', 0):.4f}, "
        f"separation={test_metrics.get('separation', 0):.4f}"
    )

    return metadata


def run_dp_finetune(
    name, pipeline_result, pretrained_model_path,
    dp_target_epsilon=1.0, finetune_epochs=8, finetune_lr=1e-4,
) -> Dict[str, Any]:
    """预训练+DP微调实验 (16-field schema)"""
    import torch

    field_dims = pipeline_result['field_dims']
    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    test_dataset = pipeline_result['test_dataset']

    logger.info(
        f"Starting experiment: {name} (DP finetune, "
        f"eps={dp_target_epsilon}, finetune_epochs={finetune_epochs})"
    )

    trainer = DeepFMTrainer(
        field_dims=field_dims,
        embed_dim=settings.embed_dim,
        hidden_dims=settings.hidden_dims,
        focal_alpha=settings.focal_loss_alpha,
        focal_gamma=settings.focal_loss_gamma,
        dp_enabled=True,
        dp_target_epsilon=dp_target_epsilon,
        dp_max_grad_norm=settings.dp_max_grad_norm,
    )

    # 加载预训练权重
    pretrained_state = torch.load(
        pretrained_model_path, map_location=trainer.device, weights_only=True
    )
    trainer.model.load_state_dict(pretrained_state)
    logger.info(f"Loaded pretrained weights from {pretrained_model_path}")

    # 冻结FM组件 (仅微调Deep MLP)
    for param in trainer.model.fm.parameters():
        param.requires_grad = False
    trainable_params = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    logger.info(f"Frozen FM, trainable Deep MLP: {trainable_params} params")

    save_dir = str(RESULTS_DIR / name)
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # 手动设置optimizer
    trainer.optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, trainer.model.parameters()),
        lr=finetune_lr, weight_decay=settings.weight_decay,
    )
    trainer.epochs = finetune_epochs

    from torch.utils.data import DataLoader
    train_loader = DataLoader(
        train_dataset, batch_size=settings.dp_batch_size, shuffle=True, drop_last=False
    )

    if trainer.dp_enabled:
        train_loader = trainer.setup_dp(train_loader)

    trainer.best_val_loss = float('inf')
    trainer.best_epoch = 0
    trainer.patience_counter = 0
    trainer.train_history = []

    for epoch in range(1, finetune_epochs + 1):
        train_loss, train_metrics = trainer._train_epoch(train_loader, epoch)
        val_loader = DataLoader(
            val_dataset, batch_size=settings.dp_batch_size, shuffle=False, drop_last=False
        )
        val_loss, val_metrics = trainer._eval_epoch(val_loader, epoch)

        history_entry = {
            'epoch': epoch, 'train_loss': train_loss, 'val_loss': val_loss,
            'phase': 'dp_finetune', **train_metrics, **val_metrics,
        }
        trainer.train_history.append(history_entry)

        if trainer.dp_enabled and trainer.privacy_engine:
            epsilon_spent = trainer.privacy_engine.get_epsilon(delta=settings.default_delta)
            history_entry['dp_epsilon_spent'] = epsilon_spent

        if val_loss < trainer.best_val_loss:
            trainer.best_val_loss = val_loss
            trainer.best_epoch = epoch
            trainer.patience_counter = 0
            trainer._save_model(Path(save_dir) / "best_model.pt")
        else:
            trainer.patience_counter += 1
            if trainer.patience_counter >= settings.early_stopping_patience:
                break

        logger.info(
            f"Epoch {epoch}/{finetune_epochs}: train_loss={train_loss:.4f}, "
            f"val_loss={val_loss:.4f}"
        )

    elapsed = time.time() - start_time
    trainer._save_model(Path(save_dir) / "final_model.pt")
    pipeline_result['encoder'].save(str(Path(save_dir) / "encoder.json"))

    metadata = trainer._build_metadata(train_dataset, val_dataset)
    metadata['experiment_name'] = name
    metadata['strategy'] = 'dp_finetune'
    metadata['schema_version'] = 'v5_16fields'
    metadata['field_dims'] = field_dims
    metadata['embed_dim'] = settings.embed_dim
    metadata['dp_target_epsilon'] = dp_target_epsilon
    metadata['dp_training'] = True
    metadata['pretrain_source'] = pretrained_model_path
    metadata['finetune_epochs'] = finetune_epochs
    metadata['finetune_lr'] = finetune_lr
    metadata['frozen_params'] = sum(p.numel() for p in trainer.model.fm.parameters())
    metadata['trainable_params'] = trainable_params
    metadata['training_time_seconds'] = round(elapsed, 2)
    metadata['num_test_samples'] = len(test_dataset)

    # 解冻用于测试
    for param in trainer.model.fm.parameters():
        param.requires_grad = True

    test_metrics = evaluate_on_test(
        trainer.model, test_dataset, trainer.device, trainer.criterion
    )
    metadata['test_metrics'] = test_metrics

    with open(Path(save_dir) / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Experiment {name} completed in {elapsed:.1f}s: "
        f"test_auc_pr={test_metrics.get('auc_pr', 0):.4f}, "
        f"separation={test_metrics.get('separation', 0):.4f}"
    )

    return metadata


def build_comparison_table(all_results: List[Dict[str, Any]]) -> None:
    """构建对比表并保存"""
    comparison = []
    for result in all_results:
        test_m = result.get('test_metrics', {})
        entry = {
            'experiment': result['experiment_name'],
            'strategy': result.get('strategy', ''),
            'schema_version': result.get('schema_version', ''),
            'field_dims': result.get('field_dims', []),
            'embed_dim': result.get('embed_dim', settings.embed_dim),
            'dp_training': result.get('dp_training', False),
            'dp_epsilon_spent': result.get('dp_epsilon_spent'),
            'dp_target_epsilon': result.get('dp_target_epsilon'),
            'best_epoch': result['best_epoch'],
            'best_val_loss': result['best_val_loss'],
            'test_loss': test_m.get('test_loss'),
            'auc_pr': test_m.get('auc_pr'),
            'auc_roc': test_m.get('auc_roc'),
            'hr@4': test_m.get('hr@4'),
            'hr@10': test_m.get('hr@10'),
            'safety_violation@4': test_m.get('safety_violation_rate@4'),
            'mean_pred_positive': test_m.get('mean_pred_positive'),
            'mean_pred_negative': test_m.get('mean_pred_negative'),
            'separation': test_m.get('separation'),
            'training_time_s': result.get('training_time_seconds'),
            'num_train': result.get('num_train_samples'),
            'num_val': result.get('num_val_samples'),
            'num_test': result.get('num_test_samples'),
        }
        comparison.append(entry)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "comparison_table.json", 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    if comparison:
        with open(RESULTS_DIR / "comparison_table.csv", 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=comparison[0].keys())
            writer.writeheader()
            writer.writerows(comparison)

    # 打印对比表
    print("\n" + "=" * 100)
    print("Phase 2 对比实验结果 (16-field schema + vocab pruning + 500 patients)")
    print("=" * 100)
    header = (
        f"{'实验':<25} {'策略':<18} {'ε_spent':<10} "
        f"{'AUC-PR':<8} {'Sep.':<8} {'HR@4':<6} {'时间(s)':<8}"
    )
    print(header)
    print("-" * 100)
    for e in comparison:
        eps_str = f"{e['dp_epsilon_spent']:.2f}" if e['dp_epsilon_spent'] else "N/A"
        auc_str = f"{e['auc_pr']:.4f}" if e['auc_pr'] else "N/A"
        sep_str = f"{e['separation']:.4f}" if e['separation'] else "N/A"
        hr_str = f"{e['hr@4']:.2f}" if e['hr@4'] else "N/A"
        time_str = f"{e['training_time_s']:.1f}" if e['training_time_s'] else "N/A"
        print(
            f"{e['experiment']:<25} {e['strategy']:<18} {eps_str:<10} "
            f"{auc_str:<8} {sep_str:<8} {hr_str:<6} {time_str:<8}"
        )
    print("=" * 100)


def main():
    """运行Phase 2对比实验"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Loading pipeline data...")
    pipeline_data = load_pipeline_data()

    logger.info("Running pipeline (16-field schema, 500 patients)...")
    pipeline_result = run_pipeline(pipeline_data)

    field_dims = pipeline_result['field_dims']
    logger.info(
        f"Pipeline ready: field_dims={field_dims}, "
        f"{len(pipeline_result['train_dataset'])} train + "
        f"{len(pipeline_result['val_dataset'])} val + "
        f"{len(pipeline_result['test_dataset'])} test"
    )

    all_results = []

    # ── 实验1: No-DP Baseline (v5, 16-field) ──
    result1 = run_no_dp_baseline(
        name="no_dp_baseline_v5",
        pipeline_result=pipeline_result,
        epochs=15,
    )
    all_results.append(result1)

    pretrained_model_path = str(RESULTS_DIR / "no_dp_baseline_v5" / "best_model.pt")

    # ── 实验2: DP finetune ε=1.0 (v5) ──
    result2 = run_dp_finetune(
        name="dp_finetune_eps1_v5",
        pipeline_result=pipeline_result,
        pretrained_model_path=pretrained_model_path,
        dp_target_epsilon=1.0,
        finetune_epochs=8,
        finetune_lr=1e-4,
    )
    all_results.append(result2)

    # ── 实验3: DP finetune ε=0.5 (v5) ──
    result3 = run_dp_finetune(
        name="dp_finetune_eps05_v5",
        pipeline_result=pipeline_result,
        pretrained_model_path=pretrained_model_path,
        dp_target_epsilon=0.5,
        finetune_epochs=8,
        finetune_lr=1e-4,
    )
    all_results.append(result3)

    build_comparison_table(all_results)

    logger.info("All Phase 2 experiments completed!")


if __name__ == "__main__":
    main()