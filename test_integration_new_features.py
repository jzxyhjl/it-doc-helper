#!/usr/bin/env python3
"""
集成测试脚本 - 新功能测试
测试可信度、来源片段、异常处理、文档大小控制、失败策略
"""
import requests
import json
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"


class Colors:
    """终端颜色"""
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


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")


def check_health() -> bool:
    """检查服务健康状态"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("服务健康检查通过")
            return True
        else:
            print_error(f"服务健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"无法连接到服务: {str(e)}")
        print_info("请确保服务已启动: docker-compose up -d")
        return False


def upload_document(file_path: str) -> Optional[Dict]:
    """上传文档"""
    if not os.path.exists(file_path):
        print_error(f"文件不存在: {file_path}")
        return None
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            response = requests.post(
                f"{API_BASE}/documents/upload",
                files=files,
                timeout=30
            )
        
        if response.status_code == 201:
            data = response.json()
            print_success(f"文档上传成功: {data.get('filename')}")
            print_info(f"  Document ID: {data.get('document_id')}")
            print_info(f"  Task ID: {data.get('task_id')}")
            return data
        else:
            print_error(f"文档上传失败: {response.status_code}")
            print_error(f"  错误信息: {response.text}")
            return None
    except Exception as e:
        print_error(f"上传文档时出错: {str(e)}")
        return None


def check_progress(document_id: str) -> Optional[Dict]:
    """检查处理进度"""
    try:
        response = requests.get(
            f"{API_BASE}/documents/{document_id}/progress",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            print_error(f"获取进度失败: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"检查进度时出错: {str(e)}")
        return None


def wait_for_completion(document_id: str, max_wait: int = 300) -> Optional[str]:
    """等待处理完成"""
    print_info(f"等待处理完成（最多等待{max_wait}秒）...")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        progress = check_progress(document_id)
        if not progress:
            time.sleep(2)
            continue
        
        status = progress.get('status')
        current_progress = progress.get('progress', 0)
        stage = progress.get('current_stage', '')
        
        print_info(f"  进度: {current_progress}% - {stage} - 状态: {status}")
        
        if status == 'completed':
            print_success("处理完成")
            return 'completed'
        elif status in ['failed', 'timeout', 'low_quality']:
            print_warning(f"处理失败: {status}")
            print_info(f"  错误信息: {stage}")
            return status
        
        time.sleep(3)
    
    print_error("处理超时")
    return None


def get_result(document_id: str) -> Optional[Dict]:
    """获取处理结果"""
    try:
        response = requests.get(
            f"{API_BASE}/documents/{document_id}/result",
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        else:
            print_error(f"获取结果失败: {response.status_code}")
            print_error(f"  错误信息: {response.text}")
            return None
    except Exception as e:
        print_error(f"获取结果时出错: {str(e)}")
        return None


def validate_confidence_and_sources(result: Dict) -> bool:
    """验证可信度和来源片段"""
    print_info("验证可信度和来源片段...")
    
    result_data = result.get('result', {})
    doc_type = result.get('document_type', '')
    
    if doc_type == 'technical':
        # 技术文档：完整展示
        checks = [
            ('prerequisites', '前置条件'),
            ('learning_path', '学习路径'),
            ('learning_methods', '学习方法建议'),
            ('related_technologies', '相关技术')
        ]
        
        for key, name in checks:
            section = result_data.get(key)
            if section:
                has_confidence = 'confidence' in section or 'confidence_label' in section
                has_sources = 'sources' in section and isinstance(section.get('sources'), list)
                
                if has_confidence:
                    print_success(f"  {name}: 包含可信度信息")
                else:
                    print_warning(f"  {name}: 缺少可信度信息")
                
                if has_sources:
                    sources_count = len(section.get('sources', []))
                    print_success(f"  {name}: 包含来源片段 ({sources_count}个)")
                else:
                    print_warning(f"  {name}: 缺少来源片段")
    
    elif doc_type in ['interview', 'architecture']:
        # 面试题/架构文档：弱展示（可能不显示，但数据应该存在）
        print_info(f"  文档类型: {doc_type} (弱展示模式)")
        # 检查数据是否存在（即使不显示）
        has_data = bool(result_data)
        if has_data:
            print_success("  结果数据存在")
        else:
            print_warning("  结果数据为空")
    
    return True


def test_document_size_validation():
    """测试文档大小验证"""
    print_section("测试1: 文档大小验证")
    
    # 测试超大文件（应该被拒绝）
    print_info("测试超大文件上传（应该被拒绝）...")
    # 创建一个临时大文件（模拟）
    # 注意：实际测试需要真实的大文件
    
    print_warning("  需要手动测试：上传超过30MB的文件")


def test_file_upload_success():
    """测试文件上传成功"""
    print_section("测试2: 正常文档处理流程")
    
    # 检查是否有测试文件
    test_file = Path("test_document.md")
    if not test_file.exists():
        print_warning("测试文件不存在，创建示例文件...")
        test_file.write_text("""
# Python基础教程

## 简介
Python是一种高级编程语言，具有简洁的语法和强大的功能。

## 基本语法
- 变量定义
- 数据类型
- 控制流

## 进阶内容
- 面向对象编程
- 异常处理
- 模块和包
        """)
        print_success("创建测试文件: test_document.md")
    
    # 上传文档
    upload_result = upload_document(str(test_file))
    if not upload_result:
        return False
    
    document_id = upload_result.get('document_id')
    if not document_id:
        print_error("未获取到document_id")
        return False
    
    # 等待处理完成
    status = wait_for_completion(document_id, max_wait=180)
    
    if status == 'completed':
        # 获取结果
        result = get_result(document_id)
        if result:
            print_success("成功获取处理结果")
            
            # 验证可信度和来源
            validate_confidence_and_sources(result)
            
            # 显示结果摘要
            print_info("\n结果摘要:")
            print_info(f"  文档类型: {result.get('document_type')}")
            print_info(f"  处理时间: {result.get('processing_time')}秒")
            if result.get('quality_score'):
                print_info(f"  质量分数: {result.get('quality_score')}")
            
            return True
        else:
            print_error("无法获取处理结果")
            return False
    else:
        print_error(f"处理失败: {status}")
        return False


def test_error_handling():
    """测试错误处理"""
    print_section("测试3: 错误处理")
    
    # 测试无效文件类型
    print_info("测试无效文件类型...")
    invalid_file = Path("test_invalid.exe")
    invalid_file.write_bytes(b"fake content")
    
    upload_result = upload_document(str(invalid_file))
    if upload_result:
        print_error("应该拒绝无效文件类型")
    else:
        print_success("正确拒绝了无效文件类型")
    
    # 清理
    if invalid_file.exists():
        invalid_file.unlink()
    
    # 测试空文件
    print_info("测试空文件...")
    empty_file = Path("test_empty.txt")
    empty_file.write_text("")
    
    upload_result = upload_document(str(empty_file))
    if upload_result:
        document_id = upload_result.get('document_id')
        status = wait_for_completion(document_id, max_wait=60)
        if status in ['failed', 'low_quality']:
            print_success("正确处理了空文件")
        else:
            print_warning("空文件处理状态异常")
    else:
        print_success("正确拒绝了空文件")
    
    # 清理
    if empty_file.exists():
        empty_file.unlink()


def test_timeout_handling():
    """测试超时处理"""
    print_section("测试4: 超时处理")
    
    print_warning("超时测试需要大文件，跳过自动测试")
    print_info("  手动测试：上传大文件（>5MB），观察是否在300秒内超时")


def main():
    """主测试函数"""
    print_section("集成测试 - 新功能验证")
    
    # 1. 健康检查
    if not check_health():
        return
    
    # 2. 测试文档大小验证
    test_document_size_validation()
    
    # 3. 测试正常流程
    success = test_file_upload_success()
    
    # 4. 测试错误处理
    test_error_handling()
    
    # 5. 测试超时处理
    test_timeout_handling()
    
    # 总结
    print_section("测试总结")
    if success:
        print_success("核心功能测试通过")
    else:
        print_error("部分测试失败")
    
    print_info("\n测试完成！")
    print_info("请检查上述输出，确认所有功能正常工作")


if __name__ == "__main__":
    main()

