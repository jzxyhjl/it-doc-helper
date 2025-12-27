"""
Celery任务队列配置
"""
from celery import Celery
from app.core.config import settings

# 创建Celery应用
celery_app = Celery(
    "it_doc_helper",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.document_processing"]
)

# Celery配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=1800,  # 30分钟超时（大文档、多次AI调用和向量生成需要更长时间）
    task_soft_time_limit=1500,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# 任务路由配置
celery_app.conf.task_routes = {
    "app.tasks.document_processing.process_document": {"queue": "celery"},
    "app.tasks.document_processing.process_secondary_views": {"queue": "celery"},
}

