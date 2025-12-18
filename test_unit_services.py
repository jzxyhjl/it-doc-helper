#!/usr/bin/env python3
"""
单元测试脚本 - 测试新服务
测试文本预处理、段落切分、可信度计算、文档大小验证

使用方法：
1. 在Docker容器中运行：
   docker-compose exec backend python /app/test_unit_services.py

2. 在本地运行（需要安装依赖）：
   cd backend
   source venv/bin/activate  # 或使用你的虚拟环境
   pip install -r requirements.txt
   python ../test_unit_services.py
"""
import sys
import os

# 添加backend路径
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
if os.path.exists(backend_path):
    sys.path.insert(0, backend_path)

from app.services.text_preprocessor import TextPreprocessor
from app.services.source_segmenter import SourceSegmenter
from app.services.confidence_calculator import ConfidenceCalculator
from app.services.document_size_validator import DocumentSizeValidator


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")


def test_text_preprocessor():
    """测试文本预处理服务"""
    print_section("测试1: 文本预处理服务")
    
    # 测试数据
    test_content = """
    这是测试内容
    
    包含多个段落
    
    还有一些特殊字符：\t\t制表符
    
    和换行符\n\n
    """
    
    try:
        import asyncio
        result = asyncio.run(TextPreprocessor.preprocess(test_content))
        
        if result and 'cleaned_content' in result:
            print_success("文本预处理成功")
            print_info(f"  原始长度: {result['stats']['original_length']}")
            print_info(f"  清理后长度: {result['stats']['cleaned_length']}")
            print_info(f"  移除字符数: {result['stats']['removed_chars']}")
        else:
            print_error("文本预处理返回格式错误")
    except Exception as e:
        print_error(f"文本预处理失败: {str(e)}")


def test_source_segmenter():
    """测试段落切分服务"""
    print_section("测试2: 段落切分服务")
    
    test_content = """
    第一段内容
    
    第二段内容
    
    ## Markdown标题
    
    第三段内容
    """
    
    try:
        segments = SourceSegmenter.segment_content(test_content)
        
        if segments and len(segments) > 0:
            print_success(f"段落切分成功，共{len(segments)}个段落")
            for seg in segments[:3]:  # 只显示前3个
                print_info(f"  段落 {seg['id']}: {seg['text'][:50]}...")
        else:
            print_error("段落切分返回空结果")
    except Exception as e:
        print_error(f"段落切分失败: {str(e)}")


def test_confidence_calculator():
    """测试可信度计算服务"""
    print_section("测试3: 可信度计算服务")
    
    # 模拟数据
    base_confidence = 80.0
    source_ids = [1, 2, 3]
    segments = [
        {"id": 1, "text": "段落1", "position": 0, "length": 100},
        {"id": 2, "text": "段落2", "position": 100, "length": 100},
        {"id": 3, "text": "段落3", "position": 200, "length": 100},
    ]
    similarity_scores = [0.9, 0.85, 0.8]
    
    try:
        result = ConfidenceCalculator.calculate_confidence(
            base_confidence=base_confidence,
            source_ids=source_ids,
            segments=segments,
            similarity_scores=similarity_scores,
            content="测试内容",
            ai_response="AI响应"
        )
        
        if result and 'score' in result and 'label' in result:
            print_success("可信度计算成功")
            print_info(f"  可信度分数: {result['score']}")
            print_info(f"  可信度标签: {result['label']}")
            if 'factors' in result:
                print_info(f"  加权因子: {result['factors']}")
        else:
            print_error("可信度计算返回格式错误")
    except Exception as e:
        print_error(f"可信度计算失败: {str(e)}")


def test_document_size_validator():
    """测试文档大小验证服务"""
    print_section("测试4: 文档大小验证服务")
    
    # 测试文件大小验证
    try:
        # 正常大小
        result = DocumentSizeValidator.validate_file_size(10 * 1024 * 1024)  # 10MB
        if result['valid']:
            print_success("文件大小验证通过（10MB）")
        else:
            print_error("文件大小验证失败")
    except Exception as e:
        print_error(f"文件大小验证异常: {str(e)}")
    
    # 测试超大文件（应该抛出异常）
    try:
        DocumentSizeValidator.validate_file_size(50 * 1024 * 1024)  # 50MB
        print_error("应该拒绝超大文件")
    except ValueError as e:
        print_success(f"正确拒绝了超大文件: {str(e)[:50]}...")
    except Exception as e:
        print_error(f"文件大小验证异常: {str(e)}")
    
    # 测试内容长度验证
    try:
        result = DocumentSizeValidator.validate_content_length(100000, "technical")
        if result['valid']:
            print_success("内容长度验证通过（10万字符）")
            print_info(f"  预计处理时间: {result.get('estimated_time')}秒")
        else:
            print_error("内容长度验证失败")
    except Exception as e:
        print_error(f"内容长度验证异常: {str(e)}")
    
    # 测试超长内容（应该抛出异常）
    try:
        DocumentSizeValidator.validate_content_length(600000, "technical")  # 60万字符
        print_error("应该拒绝超长内容")
    except ValueError as e:
        print_success(f"正确拒绝了超长内容: {str(e)[:50]}...")
    except Exception as e:
        print_error(f"内容长度验证异常: {str(e)}")


def main():
    """主测试函数"""
    print_section("单元测试 - 新服务验证")
    
    test_text_preprocessor()
    test_source_segmenter()
    test_confidence_calculator()
    test_document_size_validator()
    
    print_section("测试完成")
    print_info("所有单元测试执行完毕")


if __name__ == "__main__":
    main()

