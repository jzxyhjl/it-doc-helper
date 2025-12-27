"""
测试辅助函数
"""
import requests
import asyncio
import time
from typing import Dict, Optional, List
from pathlib import Path
import structlog

logger = structlog.get_logger()


async def upload_test_document(
    file_path: str,
    base_url: str = "http://localhost:8000",
    api_base: str = "http://localhost:8000/api/v1"
) -> Optional[str]:
    """
    上传测试文档
    
    Args:
        file_path: 测试文档路径
        base_url: 后端服务基础URL
        api_base: API基础URL
        
    Returns:
        文档ID，如果上传失败返回None
    """
    if not Path(file_path).exists():
        logger.error("测试文档不存在", file_path=file_path)
        return None
    
    try:
        # 使用同步请求（因为requests是同步的）
        with open(file_path, 'rb') as f:
            files = {'file': (Path(file_path).name, f)}
            response = requests.post(
                f"{api_base}/documents/upload",
                files=files,
                timeout=30
            )
        
        if response.status_code == 201:
            data = response.json()
            document_id = data.get('document_id')
            logger.info("测试文档上传成功", document_id=document_id, file_path=file_path)
            return document_id
        else:
            logger.error("测试文档上传失败", 
                        status_code=response.status_code, 
                        error=response.text)
            return None
    except Exception as e:
        logger.error("上传测试文档时出错", error=str(e), file_path=file_path)
        return None


async def get_task_id(
    document_id: str,
    api_base: str = "http://localhost:8000/api/v1"
) -> Optional[str]:
    """
    获取文档的处理任务ID
    
    Args:
        document_id: 文档ID
        api_base: API基础URL
        
    Returns:
        任务ID，如果获取失败返回None
    """
    try:
        # 从进度接口获取任务信息（进度接口会返回最新的任务信息）
        response = requests.get(
            f"{api_base}/documents/{document_id}/progress",
            timeout=5
        )
        
        if response.status_code == 200:
            # 注意：progress接口不直接返回task_id，但我们可以通过document_id查询
            # 这里返回document_id，后续可以通过document_id查询进度
            logger.info("获取文档进度信息成功", document_id=document_id)
            return document_id  # 返回document_id用于后续查询
        else:
            logger.error("获取文档进度信息失败", 
                        status_code=response.status_code,
                        document_id=document_id)
            return None
    except Exception as e:
        logger.error("获取任务ID时出错", error=str(e), document_id=document_id)
        return None


async def wait_for_completion(
    document_id: str,
    timeout: int = 600,
    poll_interval: int = 5,
    api_base: str = "http://localhost:8000/api/v1"
) -> Optional[Dict]:
    """
    等待文档处理完成
    
    Args:
        document_id: 文档ID
        timeout: 超时时间（秒）
        poll_interval: 轮询间隔（秒）
        api_base: API基础URL
        
    Returns:
        处理结果，如果超时或失败返回None
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # 查询处理进度
            response = requests.get(
                f"{api_base}/documents/{document_id}/progress",
                timeout=5
            )
            
            if response.status_code == 200:
                progress_data = response.json()
                status = progress_data.get('status')
                
                if status == 'completed':
                    # 获取处理结果
                    result_response = requests.get(
                        f"{api_base}/documents/{document_id}/result",
                        timeout=10
                    )
                    if result_response.status_code == 200:
                        result = result_response.json()
                        logger.info("文档处理完成", 
                                  document_id=document_id,
                                  duration=time.time() - start_time)
                        return result
                    else:
                        logger.error("获取处理结果失败", 
                                    status_code=result_response.status_code,
                                    document_id=document_id)
                        return None
                elif status in ['failed', 'timeout']:
                    logger.error("文档处理失败", 
                               status=status,
                               document_id=document_id,
                               message=progress_data.get('current_stage'))
                    return None
                # status == 'running' 或 'pending'，继续等待
            else:
                logger.warning("查询处理进度失败", 
                             status_code=response.status_code,
                             document_id=document_id)
            
            # 等待后继续轮询
            await asyncio.sleep(poll_interval)
            
        except Exception as e:
            logger.error("等待文档处理完成时出错", 
                        error=str(e),
                        document_id=document_id)
            await asyncio.sleep(poll_interval)
    
    logger.error("文档处理超时", 
                document_id=document_id,
                timeout=timeout)
    return None


async def monitor_progress(
    document_id: str,
    timeout: int = 600,
    poll_interval: int = 2,
    api_base: str = "http://localhost:8000/api/v1"
):
    """
    监听处理进度（生成器）
    
    Args:
        document_id: 文档ID
        timeout: 超时时间（秒）
        poll_interval: 轮询间隔（秒）
        api_base: API基础URL
        
    Yields:
        进度信息字典
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(
                f"{api_base}/documents/{document_id}/progress",
                timeout=5
            )
            
            if response.status_code == 200:
                progress_data = response.json()
                status = progress_data.get('status')
                
                yield progress_data
                
                if status in ['completed', 'failed', 'timeout']:
                    break
            else:
                logger.warning("查询文档进度失败", 
                             status_code=response.status_code,
                             document_id=document_id)
            
            await asyncio.sleep(poll_interval)
            
        except Exception as e:
            logger.error("监听处理进度时出错", 
                        error=str(e),
                        document_id=document_id)
            await asyncio.sleep(poll_interval)
    
    logger.warning("监听处理进度超时", 
                  document_id=document_id,
                  timeout=timeout)

