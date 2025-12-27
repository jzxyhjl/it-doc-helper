"""
应用配置管理
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    APP_NAME: str = "IT学习辅助系统"
    DEBUG: bool = False
    
    # 数据库配置
    # 注意：Docker环境下使用 postgres:5432，本地开发使用 localhost:5432
    DATABASE_URL: str = "postgresql://it_doc_helper:password@localhost:5432/it_doc_helper"
    
    # Redis配置
    # 注意：Docker环境下使用 redis:6379，本地开发使用 localhost:6379
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # DeepSeek API配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com"
    
    # 向量化服务配置
    USE_LOCAL_EMBEDDING: bool = True  # 是否使用本地嵌入模型（优先）
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 本地嵌入模型名称
    OPENAI_API_KEY: str = ""  # OpenAI API Key（可选，用于OpenAI Embeddings API）
    
    # 文件上传配置
    UPLOAD_DIR: str = "/app/uploads"
    UPLOAD_MAX_SIZE: int = 15728640  # 15MB
    ALLOWED_EXTENSIONS: str = "pdf,docx,pptx,md,txt"  # 逗号分隔的字符串
    
    def get_allowed_extensions(self) -> List[str]:
        """获取允许的文件扩展名列表"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    # CORS配置
    CORS_ORIGINS: str = "http://localhost,http://localhost:80,http://localhost:3000,http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176"  # 逗号分隔的字符串
    
    def get_cors_origins(self) -> List[str]:
        """获取CORS允许的来源列表"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    
    # AI Mock配置（测试环境）
    ENABLE_AI_MOCK: bool = False  # 是否启用AI Mock（生产环境必须为False）
    AI_MOCK_FAILURE_TYPE: str = "timeout"  # 失败类型：timeout, rate_limit, server_error, network_error, invalid_response
    AI_MOCK_FAILURE_PROBABILITY: float = 0.0  # 失败概率（0.0-1.0）
    
    # 监控配置
    ENABLE_AI_MONITORING: bool = True  # 是否启用AI监控
    MONITORING_RETENTION_DAYS: int = 30  # 监控数据保留天数
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

