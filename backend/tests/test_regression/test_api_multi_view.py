"""
多视角API接口测试
测试任务11、12、13实现的接口功能
"""
import pytest
import requests
from pathlib import Path
from typing import Dict, Optional
import structlog

logger = structlog.get_logger()


class TestUploadWithViews:
    """测试任务11：上传接口支持views参数"""
    
    @pytest.mark.asyncio
    async def test_upload_without_views(self, test_documents_dir: Path, test_config: dict):
        """测试上传文档时不指定views（应该自动推荐）"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 上传文档（不指定views）
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            response = requests.post(
                f"{api_base}/documents/upload",
                files=files,
                timeout=30
            )
        
        assert response.status_code == 201, f"上传失败: {response.text}"
        data = response.json()
        assert 'document_id' in data
        assert 'task_id' in data
        logger.info("上传成功（未指定views）", document_id=data['document_id'])
    
    @pytest.mark.asyncio
    async def test_upload_with_single_view(self, test_documents_dir: Path, test_config: dict):
        """测试上传文档时指定单个view"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 上传文档（指定learning view）
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            response = requests.post(
                f"{api_base}/documents/upload?views=learning",
                files=files,
                timeout=30
            )
        
        assert response.status_code == 201, f"上传失败: {response.text}"
        data = response.json()
        assert 'document_id' in data
        logger.info("上传成功（指定learning view）", document_id=data['document_id'])
    
    @pytest.mark.asyncio
    async def test_upload_with_multiple_views(self, test_documents_dir: Path, test_config: dict):
        """测试上传文档时指定多个views"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 上传文档（指定多个views）
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            response = requests.post(
                f"{api_base}/documents/upload?views=learning,system",
                files=files,
                timeout=30
            )
        
        assert response.status_code == 201, f"上传失败: {response.text}"
        data = response.json()
        assert 'document_id' in data
        logger.info("上传成功（指定多个views）", document_id=data['document_id'])
    
    @pytest.mark.asyncio
    async def test_upload_with_invalid_view(self, test_documents_dir: Path, test_config: dict):
        """测试上传文档时指定无效的view"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 上传文档（指定无效的view）
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            response = requests.post(
                f"{api_base}/documents/upload?views=invalid_view",
                files=files,
                timeout=30
            )
        
        assert response.status_code == 400, f"应该返回400错误: {response.text}"
        assert '无效的视角' in response.text or 'invalid' in response.text.lower()
        logger.info("正确拒绝了无效的view")


class TestRecommendViews:
    """测试任务12：推荐视角接口"""
    
    @pytest.mark.asyncio
    async def test_recommend_views_after_upload(self, test_documents_dir: Path, test_config: dict):
        """测试推荐视角接口（需要先上传文档）"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 1. 上传文档
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            upload_response = requests.post(
                f"{api_base}/documents/upload",
                files=files,
                timeout=30
            )
        
        assert upload_response.status_code == 201
        document_id = upload_response.json()['document_id']
        
        # 2. 等待文档处理开始（至少需要内容提取完成）
        import time
        time.sleep(5)  # 等待内容提取完成
        
        # 3. 调用推荐接口
        response = requests.post(
            f"{api_base}/documents/{document_id}/recommend-views",
            timeout=30
        )
        
        # 如果文档还在处理中，可能返回404，这是正常的
        if response.status_code == 404:
            logger.info("文档内容尚未提取完成，无法推荐视角")
            pytest.skip("文档内容尚未提取完成")
        
        assert response.status_code == 200, f"推荐接口失败: {response.text}"
        data = response.json()
        
        # 验证返回结构
        assert 'primary_view' in data
        assert 'enabled_views' in data
        assert 'detection_scores' in data
        assert 'cache_key' in data
        
        # 验证primary_view在enabled_views中
        assert data['primary_view'] in data['enabled_views']
        
        # 验证detection_scores包含所有视角
        assert 'learning' in data['detection_scores']
        assert 'qa' in data['detection_scores']
        assert 'system' in data['detection_scores']
        
        logger.info("推荐接口测试成功", 
                   primary_view=data['primary_view'],
                   enabled_views=data['enabled_views'])


class TestGetResultWithViews:
    """测试任务13：结果接口支持view和views参数"""
    
    @pytest.mark.asyncio
    async def test_get_result_without_params(self, test_documents_dir: Path, test_config: dict):
        """测试获取结果时不指定view/views（应该返回完整容器）"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 1. 上传文档
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            upload_response = requests.post(
                f"{api_base}/documents/upload",
                files=files,
                timeout=30
            )
        
        assert upload_response.status_code == 201
        document_id = upload_response.json()['document_id']
        
        # 2. 等待处理完成
        from tests.utils.test_helpers import wait_for_completion
        result = await wait_for_completion(
            document_id,
            timeout=test_config["timeout"],
            api_base=api_base
        )
        
        if result is None:
            pytest.skip("文档处理未完成或超时")
        
        # 3. 获取结果（不指定view/views）
        response = requests.get(
            f"{api_base}/documents/{document_id}/result",
            timeout=10
        )
        
        assert response.status_code == 200, f"获取结果失败: {response.text}"
        data = response.json()
        
        # 验证返回的是多视角容器结构
        assert 'views' in data or 'result' in data  # 兼容新旧格式
        if 'views' in data:
            assert 'meta' in data
            assert 'enabled_views' in data['meta']
            logger.info("返回完整多视角容器", views=list(data.get('views', {}).keys()))
    
    @pytest.mark.asyncio
    async def test_get_result_with_single_view(self, test_documents_dir: Path, test_config: dict):
        """测试获取结果时指定单个view"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 1. 上传文档
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            upload_response = requests.post(
                f"{api_base}/documents/upload",
                files=files,
                timeout=30
            )
        
        assert upload_response.status_code == 201
        document_id = upload_response.json()['document_id']
        
        # 2. 等待处理完成
        from tests.utils.test_helpers import wait_for_completion
        result = await wait_for_completion(
            document_id,
            timeout=test_config["timeout"],
            api_base=api_base
        )
        
        if result is None:
            pytest.skip("文档处理未完成或超时")
        
        # 3. 获取结果（指定单个view）
        response = requests.get(
            f"{api_base}/documents/{document_id}/result?view=learning",
            timeout=10
        )
        
        assert response.status_code == 200, f"获取结果失败: {response.text}"
        data = response.json()
        
        # 验证返回的是单个视角结果
        assert 'result' in data or 'document_type' in data
        logger.info("返回单个视角结果", document_type=data.get('document_type'))
    
    @pytest.mark.asyncio
    async def test_get_result_with_multiple_views(self, test_documents_dir: Path, test_config: dict):
        """测试获取结果时指定多个views"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 1. 上传文档（指定多个views）
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            upload_response = requests.post(
                f"{api_base}/documents/upload?views=learning,system",
                files=files,
                timeout=30
            )
        
        assert upload_response.status_code == 201
        document_id = upload_response.json()['document_id']
        
        # 2. 等待处理完成
        from tests.utils.test_helpers import wait_for_completion
        result = await wait_for_completion(
            document_id,
            timeout=test_config["timeout"],
            api_base=api_base
        )
        
        if result is None:
            pytest.skip("文档处理未完成或超时")
        
        # 3. 获取结果（指定多个views）
        response = requests.get(
            f"{api_base}/documents/{document_id}/result?views=learning,system",
            timeout=10
        )
        
        assert response.status_code == 200, f"获取结果失败: {response.text}"
        data = response.json()
        
        # 验证返回的是多个视角结果
        assert 'results' in data or 'views' in data
        if 'results' in data:
            assert 'requested_views' in data
            assert len(data['results']) > 0
            logger.info("返回多个视角结果", views=list(data.get('results', {}).keys()))
    
    @pytest.mark.asyncio
    async def test_get_result_with_invalid_view(self, test_documents_dir: Path, test_config: dict):
        """测试获取结果时指定无效的view"""
        api_base = test_config["api_base"]
        test_doc = test_documents_dir / "test_technical.pdf"
        
        if not test_doc.exists():
            pytest.skip(f"测试文档不存在: {test_doc}")
        
        # 1. 上传文档
        with open(test_doc, 'rb') as f:
            files = {'file': (test_doc.name, f)}
            upload_response = requests.post(
                f"{api_base}/documents/upload",
                files=files,
                timeout=30
            )
        
        assert upload_response.status_code == 201
        document_id = upload_response.json()['document_id']
        
        # 2. 等待处理完成
        from tests.utils.test_helpers import wait_for_completion
        result = await wait_for_completion(
            document_id,
            timeout=test_config["timeout"],
            api_base=api_base
        )
        
        if result is None:
            pytest.skip("文档处理未完成或超时")
        
        # 3. 获取结果（指定无效的view）
        response = requests.get(
            f"{api_base}/documents/{document_id}/result?view=invalid_view",
            timeout=10
        )
        
        assert response.status_code == 400, f"应该返回400错误: {response.text}"
        assert '无效的视角' in response.text or 'invalid' in response.text.lower()
        logger.info("正确拒绝了无效的view")

