"""
共享异常类型
为所有模块提供一致的错误层次结构和错误码

使用方式：
    from app.exceptions import ModelServiceError, PredictionError

异常层次：
    ModelServiceError
    ├── DataError
    │   ├── DataValidationError
    │   └── DataNotFoundError
    ├── ModelError
    │   ├── ModelNotLoadedError
    │   └── PredictionError
    ├── TrainingError
    │   ├── TrainingParameterError
    │   └── TrainingStateError
    ├── DataSourceError
    │   ├── DataSourceConnectionError
    │   ├── DataSourceRateLimitError
    │   └── DataSourceValidationError
    └── PrivacyError
        ├── PrivacyBudgetExceededError
        └── PrivacyConfigError
"""

from typing import Optional, Dict, Any


class ModelServiceError(Exception):
    """模型服务基础异常"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "SERVICE_ERROR"
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# ── 数据相关 ──

class DataError(ModelServiceError):
    """数据异常基类"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=kwargs.pop("error_code", "DATA_ERROR"), **kwargs)


class DataValidationError(DataError):
    """数据校验异常"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        super().__init__(message, error_code="DATA_VALIDATION_ERROR", details=details, **kwargs)


class DataNotFoundError(DataError):
    """数据未找到异常"""
    def __init__(self, message: str, resource: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if resource:
            details["resource"] = resource
        super().__init__(message, error_code="DATA_NOT_FOUND", details=details, **kwargs)


# ── 模型相关 ──

class ModelError(ModelServiceError):
    """模型异常基类"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=kwargs.pop("error_code", "MODEL_ERROR"), **kwargs)


class ModelNotLoadedError(ModelError):
    """模型未加载异常"""
    def __init__(self, message: str = "Model not loaded", **kwargs):
        super().__init__(message, error_code="MODEL_NOT_LOADED", **kwargs)


class PredictionError(ModelError):
    """预测异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="PREDICTION_ERROR", **kwargs)


# ── 训练相关 ──

class TrainingError(ModelServiceError):
    """训练异常基类"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=kwargs.pop("error_code", "TRAINING_ERROR"), **kwargs)


class TrainingParameterError(TrainingError):
    """训练参数校验异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="TRAINING_PARAMETER_ERROR", **kwargs)


class TrainingStateError(TrainingError):
    """训练状态异常（持久化/恢复失败等）"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="TRAINING_STATE_ERROR", **kwargs)


# ── 数据源相关 ──

class DataSourceError(ModelServiceError):
    """数据源异常基类"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=kwargs.pop("error_code", "DATASOURCE_ERROR"), **kwargs)


class DataSourceConnectionError(DataSourceError):
    """数据源连接异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DATASOURCE_CONNECTION_ERROR", **kwargs)


class DataSourceRateLimitError(DataSourceError):
    """数据源限流异常"""
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        details = kwargs.pop("details", {})
        if retry_after is not None:
            details["retry_after_seconds"] = retry_after
        super().__init__(message, error_code="DATASOURCE_RATE_LIMIT", details=details, **kwargs)


class DataSourceValidationError(DataSourceError):
    """数据源请求校验异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DATASOURCE_VALIDATION_ERROR", **kwargs)


# ── 隐私相关 ──

class PrivacyError(ModelServiceError):
    """隐私异常基类"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code=kwargs.pop("error_code", "PRIVACY_ERROR"), **kwargs)


class PrivacyBudgetExceededError(PrivacyError):
    """隐私预算超支异常"""
    def __init__(self, message: str, epsilon_spent: float = 0, epsilon_budget: float = 0, **kwargs):
        details = kwargs.pop("details", {})
        details["epsilon_spent"] = epsilon_spent
        details["epsilon_budget"] = epsilon_budget
        super().__init__(message, error_code="PRIVACY_BUDGET_EXCEEDED", details=details, **kwargs)


class PrivacyConfigError(PrivacyError):
    """隐私配置异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="PRIVACY_CONFIG_ERROR", **kwargs)
