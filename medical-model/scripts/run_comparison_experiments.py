"""对比实验脚本 — 毕业论文核心数据

4组对比实验:
  1. No-DP Baseline  — 无差分隐私训练 + 无DP推理
  2. DP-Inference    — 无差分隐私训练 + Laplace噪声推理
  3. DP-SGD          — Opacus DP-SGD训练 (epsilon=1.0)
  4. DP-SGD+Infer    — Opacus DP-SGD训练 + Laplace噪声推理

输出:
  - experiments/results/ 下每组实验的 metadata + train_history
  - experiments/results/comparison_table.json  汇总对比表
  - experiments/results/comparison_table.csv   CSV格式(论文用)
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

RESULTS_DIR = PROJECT_ROOT / "experiments" / "results"


def load_pipeline_data() -> Dict[str, Any]:
    """加载pipeline_data.json"""
    pipeline_path = Path(settings.data_dir) / "pipeline_data.json"
    if not pipeline_path.exists():
        raise FileNotFoundError(f"pipeline_data.json not found at {pipeline_path}")

    with open(pipeline_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_pipeline(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    """运行数据管道，生成训练数据"""
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


def run_experiment(
    name: str,
    pipeline_result: Dict[str, Any],
    dp_training: bool = False,
    dp_target_epsilon: float = 1.0,
    epochs: int = 15,
    batch_size: int = 256,
) -> Dict[str, Any]:
    """运行单组实验

    Args:
        name: 实验名称
        pipeline_result: 数据管道输出
        dp_training: 是否启用DP-SGD训练
        dp_target_epsilon: DP-SGD目标epsilon
        epochs: 训练轮数
        batch_size: 批次大小
    Returns:
        实验结果metadata
    """
    logger.info(f"{'='*60}")
    logger.info(f"Starting experiment: {name}")
    logger.info(f"  dp_training={dp_training}, dp_target_epsilon={dp_target_epsilon}")
    logger.info(f"{'='*60}")

    field_dims = pipeline_result['field_dims']
    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    test_dataset = pipeline_result['test_dataset']

    logger.info(
        f"Data: {len(train_dataset)} train + {len(val_dataset)} val + "
        f"{len(test_dataset)} test, field_dims={field_dims}"
    )

    trainer = DeepFMTrainer(
        field_dims=field_dims,
        embed_dim=settings.embed_dim,
        hidden_dims=settings.hidden_dims,
        dropout=settings.dropout,
        embed_dropout=settings.embed_dropout,
        focal_alpha=settings.focal_loss_alpha,
        focal_gamma=settings.focal_loss_gamma,
        dp_enabled=dp_training,
        dp_target_epsilon=dp_target_epsilon,
        dp_max_grad_norm=settings.dp_max_grad_norm,
    )

    start_time = time.time()

    # 保存到实验专属目录
    save_dir = str(RESULTS_DIR / name)
    Path(save_dir).mkdir(parents=True, exist_ok=True)

    metadata = trainer.train(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        epochs=epochs,
        learning_rate=settings.default_learning_rate,
        batch_size=batch_size,
        patience=settings.early_stopping_patience,
        weight_decay=settings.weight_decay,
        save_dir=save_dir,
    )

    elapsed = time.time() - start_time

    # 保存encoder
    pipeline_result['encoder'].save(str(Path(save_dir) / "encoder.json"))

    # 添加实验元信息
    metadata['experiment_name'] = name
    metadata['dp_training'] = dp_training
    metadata['training_time_seconds'] = round(elapsed, 2)
    metadata['num_test_samples'] = len(test_dataset)

    # 保存完整metadata
    with open(Path(save_dir) / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # 在测试集上评估
    test_metrics = evaluate_on_test(
        trainer.model, test_dataset, trainer.device, trainer.criterion
    )
    metadata['test_metrics'] = test_metrics

    # 重新保存带test_metrics的metadata
    with open(Path(save_dir) / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Experiment {name} completed in {elapsed:.1f}s: "
        f"best_val_loss={metadata['best_val_loss']:.4f}, "
        f"test_auc_pr={test_metrics.get('auc_pr', 0):.4f}, "
        f"dp_epsilon_spent={metadata.get('dp_epsilon_spent')}"
    )

    return metadata


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


def build_comparison_table(all_results: List[Dict[str, Any]]) -> None:
    """构建对比表并保存为JSON和CSV"""
    comparison = []
    for result in all_results:
        test_m = result.get('test_metrics', {})
        entry = {
            'experiment': result['experiment_name'],
            'dp_training': result.get('dp_training', False),
            'dp_epsilon_spent': result.get('dp_epsilon_spent'),
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

    # 保存JSON
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_DIR / "comparison_table.json", 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    # 保存CSV
    if comparison:
        with open(RESULTS_DIR / "comparison_table.csv", 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=comparison[0].keys())
            writer.writeheader()
            writer.writerows(comparison)

    logger.info(f"Comparison table saved to {RESULTS_DIR / 'comparison_table.csv'}")

    # 打印对比表
    print("\n" + "=" * 100)
    print("对比实验结果 (Comparison Experiment Results)")
    print("=" * 100)
    header = (
        f"{'实验':<20} {'DP训练':<8} {'ε_spent':<10} "
        f"{'AUC-PR':<8} {'AUC-ROC':<8} {'HR@4':<6} {'HR@10':<6} "
        f"{'Sep.':<6} {'SVR@4':<7} {'时间(s)':<8}"
    )
    print(header)
    print("-" * 100)
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
            f"{e['experiment']:<20} {dp_str:<8} {eps_str:<10} "
            f"{auc_pr_str:<8} {auc_roc_str:<8} {hr4_str:<6} {hr10_str:<6} "
            f"{sep_str:<6} {svr_str:<7} {time_str:<8}"
        )
    print("=" * 100)


def main():
    """运行4组对比实验"""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 加载数据（共享一次pipeline）
    logger.info("Loading pipeline data...")
    pipeline_data = load_pipeline_data()

    logger.info("Running pipeline...")
    pipeline_result = run_pipeline(pipeline_data)

    logger.info(
        f"Pipeline ready: {len(pipeline_result['train_dataset'])} train + "
        f"{len(pipeline_result['val_dataset'])} val + "
        f"{len(pipeline_result['test_dataset'])} test samples, "
        f"field_dims={pipeline_result['field_dims']}"
    )

    all_results = []

    # ── 实验1: No-DP Baseline ──
    result1 = run_experiment(
        name="no_dp_baseline",
        pipeline_result=pipeline_result,
        dp_training=False,
        epochs=15,
    )
    all_results.append(result1)

    # ── 实验2: DP-SGD (epsilon=1.0) ──
    result2 = run_experiment(
        name="dp_sgd_eps1",
        pipeline_result=pipeline_result,
        dp_training=True,
        dp_target_epsilon=1.0,
        epochs=15,
    )
    all_results.append(result2)

    # ── 实验3: DP-SGD (epsilon=5.0) — 宽松预算对比 ──
    result3 = run_experiment(
        name="dp_sgd_eps5",
        pipeline_result=pipeline_result,
        dp_training=True,
        dp_target_epsilon=5.0,
        epochs=15,
    )
    all_results.append(result3)

    # ── 实验4: DP-SGD (epsilon=0.5) — 严格预算对比 ──
    result4 = run_experiment(
        name="dp_sgd_eps05",
        pipeline_result=pipeline_result,
        dp_training=True,
        dp_target_epsilon=0.5,
        epochs=15,
    )
    all_results.append(result4)

    # 构建对比表
    build_comparison_table(all_results)

    logger.info("All experiments completed!")


if __name__ == "__main__":
    main()
