"""审计日志 — 简化版JSON文件日志

每次推荐请求生成一条审计记录，持久化到audit_log_dir目录。
日志结构不含PII，仅记录决策过程与安全标记。
"""

import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuditLogger:
    """JSON文件审计日志器

    每次predict调用写入一个JSON文件:
      audit_log_dir/YYYY-MM-DD/<request_id>.json
    """

    def __init__(self, audit_log_dir: str = "audit_logs") -> None:
        self._base_dir = Path(audit_log_dir)

    def _ensure_dir(self, date_str: str) -> Path:
        day_dir = self._base_dir / date_str
        day_dir.mkdir(parents=True, exist_ok=True)
        return day_dir

    def log_prediction(
        self,
        *,
        request_id: str,
        user_id: Optional[str],
        patient_summary: Dict[str, Any],
        dp_config: Optional[Dict[str, Any]],
        excluded_drugs: List[Dict[str, Any]],
        recommended_drugs: List[Dict[str, Any]],
        budget_info: Optional[Dict[str, Any]],
        total_candidates: int,
        total_excluded: int,
        total_safe: int,
    ) -> str:
        """记录一次推荐审计日志

        Args:
            request_id: 请求唯一标识
            user_id: 用户标识
            patient_summary: 患者摘要（不含PII，仅疾病/过敏/用药类别统计）
            dp_config: 差分隐私配置
            excluded_drugs: SafetyFilter排除的药物列表
            recommended_drugs: 最终推荐药物列表（含安全标记和分数）
            budget_info: 隐私预算消耗信息
            total_candidates: 候选药物总数
            total_excluded: 排除药物总数
            total_safe: 安全候选药物数

        Returns:
            写入的文件路径
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = self._ensure_dir(today)

        record: Dict[str, Any] = {
            "requestId": request_id,
            "timestamp": _now_iso(),
            "userId": user_id or "anonymous",
            "patientSummary": patient_summary,
            "dpConfig": dp_config,
            "safetyFilterResult": {
                "totalCandidates": total_candidates,
                "totalExcluded": total_excluded,
                "totalSafe": total_safe,
                "excludedDrugs": [
                    {
                        "drugName": e.get("drugName", ""),
                        "reason": e.get("reason", ""),
                        "category": e.get("category", ""),
                        "safetyType": e.get("safetyType", ""),
                    }
                    for e in excluded_drugs
                ],
            },
            "recommendedDrugs": [
                {
                    "drugId": r.get("drugId"),
                    "drugName": r.get("drugName", ""),
                    "score": r.get("score"),
                    "rawScore": r.get("rawScore"),
                    "dpNoise": r.get("dpNoise"),
                    "mode": r.get("mode"),
                    "safetyType": r.get("safetyType"),
                    "requiresReview": r.get("requiresReview"),
                    "warnings": r.get("warnings", []),
                    "dpAnomaly": r.get("dpAnomaly"),
                }
                for r in recommended_drugs
            ],
            "privacyBudget": budget_info,
        }

        file_path = day_dir / f"{request_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            logger.info(f"Audit log written: {file_path}")
        except Exception:
            logger.error(f"Failed to write audit log: {file_path}", exc_info=True)

        return str(file_path)

    def log_consent(
        self,
        *,
        user_id: str,
        consent_given: bool,
        dp_config: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """记录知情同意确认

        Args:
            user_id: 用户标识
            consent_given: 是否同意
            dp_config: DP配置（记录用户同意的隐私参数）
            request_id: 关联的推荐请求ID

        Returns:
            写入的文件路径
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_dir = self._ensure_dir(today)

        consent_id = f"consent_{uuid.uuid4().hex[:8]}"
        record: Dict[str, Any] = {
            "consentId": consent_id,
            "timestamp": _now_iso(),
            "userId": user_id,
            "consentGiven": consent_given,
            "dpConfig": dp_config,
            "relatedRequestId": request_id,
        }

        file_path = day_dir / f"{consent_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            logger.info(f"Consent log written: {file_path}")
        except Exception:
            logger.error(f"Failed to write consent log: {file_path}", exc_info=True)

        return str(file_path)

    def query_recent(
        self,
        limit: int = 20,
        date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查询最近的审计日志

        Args:
            limit: 返回条数上限
            date: 指定单日 (YYYY-MM-DD)，默认今天。与start_date/end_date互斥
            start_date: 起始日期 (YYYY-MM-DD)，含
            end_date: 结束日期 (YYYY-MM-DD)，含。默认今天

        Returns:
            审计记录列表，按时间倒序
        """
        if start_date:
            # 跨日查询模式
            end = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            day_dirs = self._day_dirs_in_range(start_date, end)
        else:
            # 单日查询模式（兼容旧接口）
            target = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            day_dir = self._base_dir / target
            day_dirs = [day_dir] if day_dir.exists() else []

        records: List[Dict[str, Any]] = []
        # 收集所有日期目录的文件，按修改时间倒序
        all_files: List[Path] = []
        for dd in day_dirs:
            all_files.extend(dd.glob("*.json"))
        all_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for fp in all_files[:limit]:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    records.append(json.load(f))
            except Exception:
                logger.warning(f"Failed to read audit log: {fp}")

        return records

    def _day_dirs_in_range(self, start_date: str, end_date: str) -> List[Path]:
        """获取日期范围内的所有日志目录"""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Invalid date format: start={start_date}, end={end_date}")
            return []

        if start_dt > end_dt:
            return []

        dirs: List[Path] = []
        current = start_dt
        while current <= end_dt:
            day_dir = self._base_dir / current.strftime("%Y-%m-%d")
            if day_dir.exists():
                dirs.append(day_dir)
            # 安全上限: 最多查询31天
            if (current - start_dt).days >= 31:
                break
            current = current + timedelta(days=1)

        return dirs


# 全局单例
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """获取审计日志器单例"""
    global _audit_logger
    if _audit_logger is None:
        from app.config import settings
        log_dir = getattr(settings, "audit_log_dir", "audit_logs")
        _audit_logger = AuditLogger(audit_log_dir=log_dir)
    return _audit_logger


def build_patient_summary(patient_data: Dict[str, Any]) -> Dict[str, Any]:
    """从患者数据构建不含PII的摘要

    仅保留疾病/过敏/用药的类别统计，不包含具体数值
    """
    diseases = patient_data.get("chronic_diseases", []) or []
    symptoms = patient_data.get("symptoms", "") or ""
    allergies = patient_data.get("allergies", []) or []
    medications = patient_data.get("current_medications", []) or []

    return {
        "ageGroup": _age_group(patient_data.get("age")),
        "gender": patient_data.get("gender"),
        "diseaseCount": len(diseases),
        "diseases": [d for d in diseases if d and d != "__unknown__"][:5],
        "hasSymptoms": bool(symptoms),
        "allergyCount": len(allergies),
        "allergies": allergies[:5],
        "medicationCount": len(medications),
    }


def _age_group(age: Any) -> str:
    """年龄分组，避免记录精确年龄"""
    if age is None:
        return "unknown"
    try:
        a = int(age)
    except (ValueError, TypeError):
        return "unknown"
    if a < 18:
        return "pediatric"
    if a < 65:
        return "adult"
    return "elderly"
