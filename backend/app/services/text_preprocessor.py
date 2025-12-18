"""
文本预处理服务
在调用AI之前对文档内容进行格式统一、文本清洗和噪声过滤
"""
import re
import asyncio
from typing import Dict, Any, List
from difflib import SequenceMatcher
import structlog

logger = structlog.get_logger()


class TextPreprocessor:
    """文本预处理器"""
    
    @staticmethod
    def normalize_format(content: str) -> str:
        """
        格式统一
        
        Args:
            content: 原始文档内容
            
        Returns:
            格式统一后的内容
        """
        if not content:
            return content
        
        # 1. 统一换行符（\r\n -> \n, \r -> \n）
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # 2. 统一空格（保留必要的缩进）
        # 多个连续空格合并为单个空格，但保留行首空格（缩进）
        lines = content.split('\n')
        normalized_lines = []
        for line in lines:
            # 保留行首空格（缩进）
            leading_spaces = len(line) - len(line.lstrip())
            # 行内多个空格合并为单个
            normalized_line = ' ' * leading_spaces + ' '.join(line.lstrip().split())
            normalized_lines.append(normalized_line)
        content = '\n'.join(normalized_lines)
        
        # 3. 统一制表符（转换为4个空格）
        content = content.replace('\t', '    ')
        
        return content
    
    @staticmethod
    def clean_text(content: str) -> str:
        """
        文本清洗
        
        Args:
            content: 格式统一后的内容
            
        Returns:
            清洗后的内容
        """
        if not content:
            return content
        
        # 1. 去除不可见字符（保留换行符和空格）
        # 去除零宽字符、控制字符（除了换行符、制表符）
        content = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', content)
        
        # 2. 去除零宽字符
        content = re.sub(r'[\u200B-\u200D\uFEFF]', '', content)
        
        # 3. 修复常见的编码错误（如全角空格转半角）
        content = content.replace('\u3000', ' ')  # 全角空格
        
        # 4. 规范化多余空白行（保留段落间的单个空行）
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # 5. 去除行尾空格
        lines = content.split('\n')
        content = '\n'.join(line.rstrip() for line in lines)
        
        return content
    
    @staticmethod
    def filter_noise(content: str, file_type: str = 'pdf') -> str:
        """
        噪声过滤
        
        Args:
            content: 清洗后的内容
            file_type: 文件类型（pdf/docx/pptx/md/txt）
            
        Returns:
            过滤噪声后的内容
        """
        if not content:
            return content
        
        lines = content.split('\n')
        filtered_lines = []
        
        # 1. 去除页眉页脚（PDF常见模式）
        if file_type == 'pdf':
            # 识别页码模式（如 "1 / 10"、"第1页"、"Page 1"等）
            page_pattern = re.compile(
                r'^\s*(第?\d+[页/]\d*|Page\s+\d+|第\d+页|^\d+\s*/\s*\d+)\s*$',
                re.IGNORECASE
            )
            
            for line in lines:
                if not page_pattern.match(line.strip()):
                    filtered_lines.append(line)
            lines = filtered_lines
            filtered_lines = []
        
        # 2. 去除无意义的短行
        for line in lines:
            stripped = line.strip()
            # 保留空行（用于段落分隔）
            if not stripped:
                filtered_lines.append(line)
                continue
            
            # 跳过单独的数字、符号
            if re.match(r'^[\d\s\-_=]+$', stripped):
                continue
            
            # 跳过过短的行（少于3个字符，且不是常见标点）
            if len(stripped) < 3 and not re.match(r'^[，。！？；：、]+$', stripped):
                continue
            
            filtered_lines.append(line)
        
        # 3. 去除重复段落（基于相似度）
        content = '\n'.join(filtered_lines)
        paragraphs = content.split('\n\n')
        unique_paragraphs = []
        seen_paragraphs = set()
        
        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped:
                continue
            
            # 检查是否与已见过的段落高度相似
            is_duplicate = False
            for seen_para in seen_paragraphs:
                similarity = SequenceMatcher(None, para_stripped, seen_para).ratio()
                if similarity > 0.9:  # 相似度超过90%认为是重复
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_paragraphs.append(para)
                seen_paragraphs.add(para_stripped)
        
        return '\n\n'.join(unique_paragraphs)
    
    @staticmethod
    async def preprocess(
        content: str, 
        file_type: str = 'pdf',
        timeout: float = 10.0
    ) -> Dict[str, Any]:
        """
        完整的文本预处理流程
        
        Args:
            content: 原始文档内容
            file_type: 文件类型（pdf/docx/pptx/md/txt）
            timeout: 超时时间（秒），超过则使用快速模式
            
        Returns:
            {
                "cleaned_content": str,
                "stats": {
                    "original_length": int,
                    "cleaned_length": int,
                    "removed_chars": int,
                    "removed_paragraphs": int
                }
            }
        """
        if not content:
            return {
                "cleaned_content": "",
                "stats": {
                    "original_length": 0,
                    "cleaned_length": 0,
                    "removed_chars": 0,
                    "removed_paragraphs": 0
                }
            }
        
        original_length = len(content)
        original_paragraphs = len(content.split('\n\n'))
        
        try:
            # 使用超时保护
            async def _preprocess():
                # 1. 格式统一
                cleaned = TextPreprocessor.normalize_format(content)
                
                # 2. 文本清洗
                cleaned = TextPreprocessor.clean_text(cleaned)
                
                # 3. 噪声过滤
                cleaned = TextPreprocessor.filter_noise(cleaned, file_type)
                
                return cleaned
            
            # 执行预处理，带超时保护
            try:
                cleaned_content = await asyncio.wait_for(
                    _preprocess(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "文本预处理超时，使用快速模式",
                    file_type=file_type,
                    content_length=original_length
                )
                # 快速模式：只做基本的格式统一和清洗，跳过噪声过滤
                cleaned_content = TextPreprocessor.normalize_format(content)
                cleaned_content = TextPreprocessor.clean_text(cleaned_content)
                # 跳过噪声过滤以节省时间
            
            cleaned_length = len(cleaned_content)
            cleaned_paragraphs = len(cleaned_content.split('\n\n'))
            
            stats = {
                "original_length": original_length,
                "cleaned_length": cleaned_length,
                "removed_chars": original_length - cleaned_length,
                "removed_paragraphs": original_paragraphs - cleaned_paragraphs
            }
            
            logger.info(
                "文本预处理完成",
                file_type=file_type,
                original_length=original_length,
                cleaned_length=cleaned_length,
                removed_chars=stats["removed_chars"],
                removed_paragraphs=stats["removed_paragraphs"]
            )
            
            return {
                "cleaned_content": cleaned_content,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(
                "文本预处理失败，使用原始内容",
                file_type=file_type,
                error=str(e)
            )
            # 预处理失败时返回原始内容
            return {
                "cleaned_content": content,
                "stats": {
                    "original_length": original_length,
                    "cleaned_length": original_length,
                    "removed_chars": 0,
                    "removed_paragraphs": 0
                }
            }

