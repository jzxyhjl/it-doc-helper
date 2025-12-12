"""
文件处理工具函数
"""
import os
import uuid
from pathlib import Path
from typing import Optional, List
from fastapi import UploadFile
import structlog

logger = structlog.get_logger()


def get_file_extension(filename: str) -> str:
    """获取文件扩展名"""
    return Path(filename).suffix.lower().lstrip('.')


def is_allowed_file(filename: str, allowed_extensions: list) -> bool:
    """检查文件类型是否允许"""
    ext = get_file_extension(filename)
    return ext in allowed_extensions


def validate_file_size(file_size: int, max_size: int) -> bool:
    """验证文件大小"""
    return file_size <= max_size


def generate_unique_filename(original_filename: str) -> str:
    """生成唯一文件名"""
    ext = Path(original_filename).suffix
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


async def save_upload_file(
    file: UploadFile,
    upload_dir: str,
    max_size: int,
    allowed_extensions: List[str]
) -> tuple[str, int]:
    """
    保存上传文件
    
    Returns:
        tuple: (文件路径, 文件大小)
    """
    # 验证文件类型
    if not is_allowed_file(file.filename, allowed_extensions):
        raise ValueError(f"不支持的文件类型: {file.filename}")
    
    # 读取文件内容
    content = await file.read()
    file_size = len(content)
    
    # 验证文件大小
    if not validate_file_size(file_size, max_size):
        raise ValueError(f"文件大小超过限制: {file_size} bytes > {max_size} bytes")
    
    # 生成唯一文件名
    unique_filename = generate_unique_filename(file.filename)
    file_path = os.path.join(upload_dir, unique_filename)
    
    # 确保上传目录存在
    os.makedirs(upload_dir, exist_ok=True)
    
    # 保存文件
    with open(file_path, "wb") as f:
        f.write(content)
    
    logger.info("文件保存成功", filename=file.filename, saved_path=file_path, size=file_size)
    
    return file_path, file_size

