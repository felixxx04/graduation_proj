"""Phase 1 对比实验脚本 — 预训练+DP微调 vs 从零DP训练

核心改动:
1. embed_dim: 8 → 16 (config.py已更新)
2. DP模式下dropout=0 (trainer.py已更新, 自动切换)
3. 预训练+DP微调策略 (本脚本实现)

5组对比实验:
  1. no_dp_baseline_v4  — embed_dim=16, 无DP训练 (v4 baseline)
  2. dp_from_scratch_eps1 — embed_dim=16, 从零DP-SGD ε=1.0 (对照组)
  3. dp_finetune_eps1    — embed_dim=16, 预训练→DP微调 ε=1.0 (实验组)
  4. dp_finetune_eps05   — 预训练→DP微调 ε=0.5
  5. dp_finetune_eps5    — 预训练→DP微调 ε=5.0

输出:
  experiments/results/phase1/ 下每组 metadata + train_history
  experiments/results/phase1/comparison_table.json 汇总表
  experiments/results/phase1/comparison_table.csv CSV格式(论文用)
"""

import json
import csv
import logging
import sys
import time
import copy
from pathlib import Path
from typing import Dict, Any, List

# 确保项目根目录在sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.pipeline.runner import PipelineRunner
from app.models.trainer import DeepFMTrainer
from app.models.deepfm import DeepFM
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results" / "phase1"


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
        else:
            metrics['auc_pr'] = 0.0
    except ImportError:
        metrics['auc_pr'] = 0.0

    # AUC-ROC
    try:
        from sklearn.metrics import roc_auc_score
        binary_labels = (labels >= 0.5).astype(int)
        if binary_labels.sum() > 0 and (1 - binary_labels).sum() > 0:
            metrics['auc_roc'] = float(roc_auc_score(binary_labels, preds))
        else:
            metrics['auc_roc'] = 0.0
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

    # 分离度
    if positive_mask.any() and negative_mask.any():
        metrics['separation'] = float(
            preds[positive_mask].mean() - preds[negative_mask].mean()
        )

    logger.info(
        f"Test metrics: loss={avg_loss:.4f}, auc_pr={metrics.get('auc_pr', 0):.4f}, "
        f"auc_roc={metrics.get('auc_roc', 0):.4f}, "
        f"separation={metrics.get('separation', 0):.4f}"
    )

    return metrics


def run_no_dp_baseline(
    name: str,
    pipeline_result: Dict[str, Any],
    epochs: int = 15,
) -> Dict[str, Any]:
    """运行无DP基线实验 (embed_dim=16)"""
    field_dims = pipeline_result['field_dims']
    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    test_dataset = pipeline_result['test_dataset']

    logger.info(f"Starting experiment: {name} (No-DP, embed_dim={settings.embed_dim})")

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

    # 保存encoder
    pipeline_result['encoder'].save(str(Path(save_dir) / "encoder.json"))

    # 添加元信息
    metadata['experiment_name'] = name
    metadata['strategy'] = 'no_dp_baseline'
    metadata['embed_dim'] = settings.embed_dim
    metadata['dp_training'] = False
    metadata['training_time_seconds'] = round(elapsed, 2)
    metadata['num_test_samples'] = len(test_dataset)

    # 测试集评估
    test_metrics = evaluate_on_test(
        trainer.model, test_dataset, trainer.device, trainer.criterion
    )
    metadata['test_metrics'] = test_metrics

    # 保存metadata
    with open(Path(save_dir) / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Experiment {name} completed in {elapsed:.1f}s: "
        f"best_val_loss={metadata['best_val_loss']:.4f}, "
        f"test_auc_pr={test_metrics.get('auc_pr', 0):.4f}, "
        f"separation={test_metrics.get('separation', 0):.4f}"
    )

    return metadata


def run_dp_from_scratch(
    name: str,
    pipeline_result: Dict[str, Any],
    dp_target_epsilon: float = 1.0,
    epochs: int = 15,
) -> Dict[str, Any]:
    """运行从零DP-SGD实验 (对照组: embed_dim=16, DP dropout=0)"""
    field_dims = pipeline_result['field_dims']
    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    test_dataset = pipeline_result['test_dataset']

    logger.info(
        f"Starting experiment: {name} (DP from scratch, "
        f"eps={dp_target_epsilon}, embed_dim={settings.embed_dim})"
    )

    trainer = DeepFMTrainer(
        field_dims=field_dims,
        embed_dim=settings.embed_dim,
        hidden_dims=settings.hidden_dims,
        # DP模式下dropout自动切换为dp_dropout/dp_embed_dropout
        focal_alpha=settings.focal_loss_alpha,
        focal_gamma=settings.focal_loss_gamma,
        dp_enabled=True,
        dp_target_epsilon=dp_target_epsilon,
        dp_max_grad_norm=settings.dp_max_grad_norm,
    )

    save_dir = str(RESULTS_DIR / name)
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.time()
    metadata = trainer.train(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        epochs=epochs,
        learning_rate=settings.default_learning_rate,
        batch_size=settings.dp_batch_size,
        patience=settings.early_stopping_patience,
        weight_decay=settings.weight_decay,
        save_dir=save_dir,
    )
    elapsed = time.time() - start_time

    pipeline_result['encoder'].save(str(Path(save_dir) / "encoder.json"))

    metadata['experiment_name'] = name
    metadata['strategy'] = 'dp_from_scratch'
    metadata['embed_dim'] = settings.embed_dim
    metadata['dp_target_epsilon'] = dp_target_epsilon
    metadata['dp_training'] = True
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
        f"eps_spent={metadata.get('dp_epsilon_spent')}, "
        f"test_auc_pr={test_metrics.get('auc_pr', 0):.4f}, "
        f"separation={test_metrics.get('separation', 0):.4f}"
    )

    return metadata


def run_dp_finetune(
    name: str,
    pipeline_result: Dict[str, Any],
    pretrained_model_path: str,
    dp_target_epsilon: float = 1.0,
    pretrain_epochs: int = 15,
    finetune_epochs: int = 8,
    finetune_lr: float = 1e-4,
) -> Dict[str, Any]:
    """预训练+DP微调实验 (实验组)

    策略:
    1. 加载无DP预训练好的模型权重
    2. 冻结FM组件(embedding + linear + 二阶交互)
    3. 仅对Deep MLP头施加DP-SGD微调
    4. 使用更小的学习率和更少的epoch

    冻结FM的理由: 药物-疾病关联是公共医学知识, 不需要隐私保护;
    Deep MLP头做个性化排序决策, 需要DP保护
    """
    import torch

    field_dims = pipeline_result['field_dims']
    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    test_dataset = pipeline_result['test_dataset']

    logger.info(
        f"Starting experiment: {name} (DP finetune, "
        f"eps={dp_target_epsilon}, finetune_epochs={finetune_epochs})"
    )

    # Step 1: 创建模型并加载预训练权重
    trainer = DeepFMTrainer(
        field_dims=field_dims,
        embed_dim=settings.embed_dim,
        hidden_dims=settings.hidden_dims,
        # DP模式下dropout自动切换
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

    # Step 2: 冻结FM组件 (仅微调Deep MLP)
    # 冻结 MultiFieldFM 的所有参数 (embedding + linear + embed_dropout)
    for param in trainer.model.fm.parameters():
        param.requires_grad = False
    logger.info(
        f"Frozen FM component: {sum(p.numel() for p in trainer.model.fm.parameters())} params frozen, "
        f"{sum(p.numel() for p in trainer.model.deep.parameters())} params trainable (Deep MLP only)"
    )

    trainable_params = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)
    logger.info(f"Total trainable parameters: {trainable_params}")

    # Step 3: DP-SGD微调 (仅对可训练参数)
    save_dir = str(RESULTS_DIR / name)
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    # 手动设置optimizer (仅对可训练参数)
    trainer.optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, trainer.model.parameters()),
        lr=finetune_lr,
        weight_decay=settings.weight_decay,
    )
    trainer.epochs = finetune_epochs

    # DataLoader
    from torch.utils.data import DataLoader
    train_loader = DataLoader(
        train_dataset, batch_size=settings.dp_batch_size, shuffle=True, drop_last=False
    )

    # 配置DP-SGD (仅对可训练参数生效)
    if trainer.dp_enabled:
        train_loader = trainer.setup_dp(train_loader)

    # 微调训练循环
    trainer.best_val_loss = float('inf')
    trainer.best_epoch = 0
    trainer.patience_counter = 0
    trainer.train_history = []

    logger.info(
        f"DP finetune started: {finetune_epochs} epochs, lr={finetune_lr}, "
        f"dp_eps={dp_target_epsilon}, trainable_params={trainable_params}"
    )

    for epoch in range(1, finetune_epochs + 1):
        # Train (微调, FM冻结)
        train_loss, train_metrics = trainer._train_epoch(train_loader, epoch)

        # Validate
        val_loader = DataLoader(
            val_dataset, batch_size=settings.dp_batch_size, shuffle=False, drop_last=False
        )
        val_loss, val_metrics = trainer._eval_epoch(val_loader, epoch)

        history_entry = {
            'epoch': epoch,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'phase': 'dp_finetune',
            **train_metrics,
            **val_metrics,
        }
        trainer.train_history.append(history_entry)

        # DP隐私报告
        if trainer.dp_enabled and trainer.privacy_engine:
            epsilon_spent = trainer.privacy_engine.get_epsilon(delta=settings.default_delta)
            history_entry['dp_epsilon_spent'] = epsilon_spent
            logger.info(f"Epoch {epoch}: DP epsilon spent = {epsilon_spent:.4f}")

        # 早停
        if val_loss < trainer.best_val_loss:
            trainer.best_val_loss = val_loss
            trainer.best_epoch = epoch
            trainer.patience_counter = 0
            trainer._save_model(Path(save_dir) / "best_model.pt")
        else:
            trainer.patience_counter += 1
            if trainer.patience_counter >= settings.early_stopping_patience:
                logger.info(
                    f"Early stopping at epoch {epoch}, best epoch={trainer.best_epoch}"
                )
                break

        logger.info(
            f"Epoch {epoch}/{finetune_epochs}: train_loss={train_loss:.4f}, "
            f"val_loss={val_loss:.4f}, "
            f"val_auc_pr={val_metrics.get('auc_pr', 0):.4f}"
        )

    elapsed = time.time() - start_time

    # 保存最终模型
    trainer._save_model(Path(save_dir) / "final_model.pt")

    # 保存encoder
    pipeline_result['encoder'].save(str(Path(save_dir) / "encoder.json"))

    # 构建metadata
    metadata = trainer._build_metadata(train_dataset, val_dataset)
    metadata['experiment_name'] = name
    metadata['strategy'] = 'dp_finetune'
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

    # 解冻FM用于测试评估 (模型需要完整前向传播)
    for param in trainer.model.fm.parameters():
        param.requires_grad = True

    test_metrics = evaluate_on_test(
        trainer.model, test_dataset, trainer.device, trainer.criterion
    )
    metadata['test_metrics'] = test_metrics

    # 保存metadata
    with open(Path(save_dir) / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Experiment {name} completed in {elapsed:.1f}s: "
        f"eps_spent={metadata.get('dp_epsilon_spent')}, "
        f"test_auc_pr={test_metrics.get('auc_pr', 0):.4f}, "
        f"separation={test_metrics.get('separation', 0):.4f}"
    )

    return metadata


def build_comparison_table(all_results: List[Dict[str, Any]]) -> None:
    """构建对比表并保存为JSON和CSV"""
    comparison = []
    for result in all_results:
        test_m = result.get('test_metrics', {})
        entry = {
            'experiment': result['experiment_name'],
            'strategy': result.get('strategy', ''),
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
    print("\n" + "=" * 110)
    print("Phase 1 对比实验结果 (Pretrain + DP Finetune vs From-Scratch DP)")
    print("=" * 110)
    header = (
        f"{'实验':<25} {'策略':<18} {'ε_spent':<10} "
        f"{'AUC-PR':<8} {'AUC-ROC':<8} {'HR@4':<6} {'HR@10':<6} "
        f"{'Sep.':<8} {'SVR@4':<7} {'时间(s)':<8}"
    )
    print(header)
    print("-" * 110)
    for e in comparison:
        dp_str = "Yes" if e['dp_training'] else "No"
        eps_str = f"{e['dp_epsilon_spent']:.2f}" if e['dp_epsilon_spent'] else "N/A"
        auc_pr_str = f"{e['auc_pr']:.4f}" if e['auc_pr'] else "N/A"
        auc_roc_str = f"{e['auc_roc']:.4f}" if e['auc_roc'] else "N/A"
        hr4_str = f"{e['hr@4']:.2f}" if e['hr@4'] else "N/A"
        hr10_str = f"{e['hr@10']:.2f}" if e['hr@10'] else "N/A"
        sep_str = f"{e['separation']:.4f}" if e['separation'] else "N/A"
        svr_str = f"{e['safety_violation@4']:.2f}" if e['safety_violation@4'] else "N/A"
        time_str = f"{e['training_time_s']:.1f}" if e['training_time_s'] else "N/A"

        print(
            f"{e['experiment']:<25} {e['strategy']:<18} {eps_str:<10} "
            f"{auc_pr_str:<8} {auc_roc_str:<8} {hr4_str:<6} {hr10_str:<6} "
            f"{sep_str:<8} {svr_str:<7} {time_str:<8}"
        )
    print("=" * 110)

    # 与旧版本对比 (如果旧数据存在)
    old_results_path = PROJECT_ROOT / "experiments" / "results" / "comparison_table.json"
    if old_results_path.exists():
        with open(old_results_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        print("\n旧版本对比 (embed_dim=8, DP dropout=0.1/0.2):")
        print("-" * 80)
        for e in old_data:
            eps_str = f"{e.get('dp_epsilon_spent', 'N/A'):.2f}" if e.get('dp_epsilon_spent') else "N/A"
            sep_str = f"{e.get('separation', 0):.4f}" if e.get('separation') else "N/A"
            auc_str = f"{e.get('auc_pr', 0):.4f}" if e.get('auc_pr') else "N/A"
            print(
                f"  {e['experiment']:<20} ε={eps_str:<10} "
                f"AUC-PR={auc_str:<8} Sep={sep_str:<8}"
            )


def main():
    """运行Phase 1对比实验"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 加载数据
    logger.info("Loading pipeline data...")
    pipeline_data = load_pipeline_data()

    logger.info("Running pipeline...")
    pipeline_result = run_pipeline(pipeline_data)

    logger.info(
        f"Pipeline ready: {len(pipeline_result['train_dataset'])} train + "
        f"{len(pipeline_result['val_dataset'])} val + "
        f"{len(pipeline_result['test_dataset'])} test, "
        f"field_dims={pipeline_result['field_dims']}"
    )

    all_results = []

    # ── 实验1: No-DP Baseline (embed_dim=16, v4) ──
    # 同时作为预训练模型, 保存best_model.pt供后续微调使用
    result1 = run_no_dp_baseline(
        name="no_dp_baseline_v4",
        pipeline_result=pipeline_result,
        epochs=15,
    )
    all_results.append(result1)

    # 获取预训练模型路径
    pretrained_model_path = str(RESULTS_DIR / "no_dp_baseline_v4" / "best_model.pt")
    logger.info(f"Pretrained model saved at: {pretrained_model_path}")

    # ── 实验2: DP from scratch (对照组: embed_dim=16, DP dropout=0, ε=1.0) ──
    result2 = run_dp_from_scratch(
        name="dp_from_scratch_eps1_v4",
        pipeline_result=pipeline_result,
        dp_target_epsilon=1.0,
        epochs=15,
    )
    all_results.append(result2)

    # ── 实验3: DP finetune ε=1.0 (实验组) ──
    result3 = run_dp_finetune(
        name="dp_finetune_eps1_v4",
        pipeline_result=pipeline_result,
        pretrained_model_path=pretrained_model_path,
        dp_target_epsilon=1.0,
        finetune_epochs=8,
        finetune_lr=1e-4,
    )
    all_results.append(result3)

    # ── 实验4: DP finetune ε=0.5 ──
    result4 = run_dp_finetune(
        name="dp_finetune_eps05_v4",
        pipeline_result=pipeline_result,
        pretrained_model_path=pretrained_model_path,
        dp_target_epsilon=0.5,
        finetune_epochs=8,
        finetune_lr=1e-4,
    )
    all_results.append(result4)

    # ── 实验5: DP finetune ε=5.0 ──
    result5 = run_dp_finetune(
        name="dp_finetune_eps5_v4",
        pipeline_result=pipeline_result,
        pretrained_model_path=pretrained_model_path,
        dp_target_epsilon=5.0,
        finetune_epochs=8,
        finetune_lr=1e-4,
    )
    all_results.append(result5)

    # 构建对比表
    build_comparison_table(all_results)

    logger.info("All Phase 1 experiments completed!")


if __name__ == "__main__":
    main()