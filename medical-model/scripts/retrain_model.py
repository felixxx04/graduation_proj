"""模型重训练脚本 — 使用合并后的安全数据

直接调用 PipelineRunner + DeepFMTrainer 进行训练,
无需启动 FastAPI 服务。

用法: python scripts/retrain_model.py [--epochs 20] [--batch-size 256]
"""

import json
import sys
import os
import argparse
import logging
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# 确保可以导入 app 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.pipeline.runner import PipelineRunner
from app.models.trainer import DeepFMTrainer
from app.config import settings


def main():
    parser = argparse.ArgumentParser(description='Retrain DeepFM model with merged safety data')
    parser.add_argument('--epochs', type=int, default=20, help='Training epochs')
    parser.add_argument('--batch-size', type=int, default=256, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--focal-alpha', type=float, default=0.4, help='Focal loss alpha')
    parser.add_argument('--focal-gamma', type=float, default=2.0, help='Focal loss gamma')
    parser.add_argument('--dp-enabled', action='store_true', help='Enable DP-SGD training')
    parser.add_argument('--epsilon', type=float, default=1.0, help='DP epsilon target')
    args = parser.parse_args()

    pipeline_path = Path(settings.data_dir) / "pipeline_data.json"
    if not pipeline_path.exists():
        logger.error("pipeline_data.json not found")
        sys.exit(1)

    logger.info("Loading pipeline_data.json...")
    with open(pipeline_path, 'r', encoding='utf-8') as f:
        pipeline_data = json.load(f)

    contra_map = pipeline_data.get('contraindication_map', {})
    inter_map = pipeline_data.get('interaction_map', {})
    indication_map = pipeline_data.get('indication_map', {})
    merged_drugs = pipeline_data.get('merged_drugs', {})
    patient_records = pipeline_data.get('patient_records', [])

    logger.info(f"Contraindication_map: {len(contra_map)} drugs")
    logger.info(f"Interaction_map: {len(inter_map)} drugs")
    logger.info(f"Indication_map: {len(indication_map)} drugs")
    logger.info(f"Merged_drugs: {len(merged_drugs)} drugs")
    logger.info(f"Patient_records: {len(patient_records)} patients")

    if not patient_records:
        logger.error("No patient_records found — cannot train")
        sys.exit(1)

    # 初始化 PipelineRunner
    runner = PipelineRunner()
    runner.load_safety_data(contra_map, inter_map)
    runner.load_indication_data(indication_map)

    drugs_list = list(merged_drugs.values())

    logger.info("Running pipeline to generate training data...")
    pipeline_result = runner.run(patient_records, drugs_list, seed=42)

    train_dataset = pipeline_result['train_dataset']
    val_dataset = pipeline_result['val_dataset']
    field_dims = pipeline_result['field_dims']

    logger.info(f"Training samples: {len(train_dataset)}")
    logger.info(f"Validation samples: {len(val_dataset)}")
    logger.info(f"Field dims: {field_dims}")

    # 初始化 Trainer
    trainer = DeepFMTrainer(
        field_dims=field_dims,
        dp_enabled=args.dp_enabled,
        dp_target_epsilon=args.epsilon,
        focal_alpha=args.focal_alpha,
        focal_gamma=args.focal_gamma,
    )

    logger.info(f"Training config: epochs={args.epochs}, lr={args.lr}, "
                f"batch_size={args.batch_size}, dp={args.dp_enabled}")

    # 训练
    train_metadata = trainer.train(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        epochs=args.epochs,
        learning_rate=args.lr,
        batch_size=args.batch_size,
    )

    # 保存 encoder
    encoder_path = Path(settings.saved_models_dir) / "encoder.json"
    pipeline_result['encoder'].save(str(encoder_path))
    logger.info(f"Encoder saved to {encoder_path}")

    # 保存 metadata
    metadata_path = Path(settings.saved_models_dir) / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(train_metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"Metadata saved to {metadata_path}")

    # 输出最终结果
    best_epoch = train_metadata['best_epoch']
    best_val_loss = train_metadata['best_val_loss']
    best_auc_pr = train_metadata['train_history'][-1].get('auc_pr', 0)

    logger.info(f"\n{'='*60}")
    logger.info(f"Training completed!")
    logger.info(f"  Best epoch: {best_epoch}")
    logger.info(f"  Best val loss: {best_val_loss:.6f}")
    logger.info(f"  Best AUC-PR: {best_auc_pr:.4f}")
    logger.info(f"  Model saved: {settings.saved_models_dir}/best_model.pt")
    logger.info(f"{'='*60}")

    # 输出训练历史摘要
    logger.info("\nTraining history:")
    for entry in train_metadata['train_history']:
        epoch = entry['epoch']
        auc = entry.get('auc_pr', 0)
        hr4 = entry.get('hr@4', 0)
        sv4 = entry.get('safety_violation_rate@4', 0)
        logger.info(f"  Epoch {epoch:3d}: AUC-PR={auc:.4f}, HR@4={hr4:.2f}, SV@4={sv4:.2f}")


if __name__ == '__main__':
    main()