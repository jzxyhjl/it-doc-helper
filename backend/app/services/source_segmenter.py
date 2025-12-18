"""
段落切分服务
将文档内容按段落切分，生成段落索引和映射关系
"""
import re
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger()


class SourceSegmenter:
    """段落切分器"""
    
    # 超长段落阈值（字符数）
    MAX_SEGMENT_LENGTH = 2000
    
    @staticmethod
    def segment_content(content: str, timeout: float = 5.0) -> List[Dict]:
        """
        切分文档内容为段落
        
        Args:
            content: 文档内容
            timeout: 超时时间（秒），超过则使用快速模式
            
        Returns:
            [
                {
                    "id": 1,
                    "text": "段落内容",
                    "position": 0,
                    "length": 100
                },
                ...
            ]
        """
        if not content:
            return []
        
        try:
            import asyncio
            import time
            
            start_time = time.time()
            segments = []
            position = 0
            
            # 1. 按空行切分
            paragraphs = re.split(r'\n\s*\n', content)
            
            segment_id = 1
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # 2. 识别Markdown block（代码块、引用块等）
                markdown_blocks = SourceSegmenter._extract_markdown_blocks(para)
                
                if markdown_blocks:
                    # 如果包含Markdown block，按block切分
                    for block in markdown_blocks:
                        block_text = block["text"]
                        block_position = position + content[position:].find(block_text)
                        
                        # 3. 处理超长段落
                        if len(block_text) > SourceSegmenter.MAX_SEGMENT_LENGTH:
                            sub_segments = SourceSegmenter._split_long_segment(
                                block_text, block_position
                            )
                            segments.extend(sub_segments)
                        else:
                            segments.append({
                                "id": segment_id,
                                "text": block_text,
                                "position": block_position,
                                "length": len(block_text)
                            })
                            segment_id += 1
                        
                        position = block_position + len(block_text)
                else:
                    # 普通段落
                    para_position = position + content[position:].find(para)
                    
                    # 3. 处理超长段落
                    if len(para) > SourceSegmenter.MAX_SEGMENT_LENGTH:
                        sub_segments = SourceSegmenter._split_long_segment(
                            para, para_position
                        )
                        segments.extend(sub_segments)
                    else:
                        segments.append({
                            "id": segment_id,
                            "text": para,
                            "position": para_position,
                            "length": len(para)
                        })
                        segment_id += 1
                    
                    position = para_position + len(para)
            
            # 检查超时
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                logger.warning(
                    "段落切分超时，使用快速模式",
                    elapsed_time=elapsed_time,
                    timeout=timeout,
                    content_length=len(content)
                )
                # 快速模式：简化切分
                return SourceSegmenter._fast_segment(content)
            
            # 重新分配ID（确保连续）
            for idx, segment in enumerate(segments, 1):
                segment["id"] = idx
            
            logger.info(
                "段落切分完成",
                total_segments=len(segments),
                total_length=sum(s["length"] for s in segments),
                elapsed_time=elapsed_time
            )
            
            return segments
            
        except Exception as e:
            logger.error(
                "段落切分失败，使用兜底策略",
                error=str(e),
                error_type=type(e).__name__,
                content_length=len(content)
            )
            # 兜底策略：按固定长度切分
            return SourceSegmenter._fallback_segment(content)
    
    @staticmethod
    def _extract_markdown_blocks(text: str) -> List[Dict]:
        """
        提取Markdown block（代码块、引用块等）
        
        Returns:
            [{"text": "block内容", "type": "code|quote|list"}, ...]
        """
        blocks = []
        
        # 代码块（```...``` 或 ```language...```）
        code_pattern = r'```[\s\S]*?```'
        for match in re.finditer(code_pattern, text):
            blocks.append({
                "text": match.group(0),
                "type": "code",
                "start": match.start(),
                "end": match.end()
            })
        
        # 引用块（> 开头）
        quote_pattern = r'^>.*$'
        quote_lines = []
        for line in text.split('\n'):
            if re.match(quote_pattern, line):
                quote_lines.append(line)
            elif quote_lines:
                blocks.append({
                    "text": '\n'.join(quote_lines),
                    "type": "quote",
                    "start": text.find('\n'.join(quote_lines)),
                    "end": text.find('\n'.join(quote_lines)) + len('\n'.join(quote_lines))
                })
                quote_lines = []
        
        # 有序/无序列表
        list_pattern = r'^[\s]*[-*+]\s+|^[\s]*\d+\.\s+'
        list_lines = []
        for line in text.split('\n'):
            if re.match(list_pattern, line):
                list_lines.append(line)
            elif list_lines:
                blocks.append({
                    "text": '\n'.join(list_lines),
                    "type": "list",
                    "start": text.find('\n'.join(list_lines)),
                    "end": text.find('\n'.join(list_lines)) + len('\n'.join(list_lines))
                })
                list_lines = []
        
        # 按位置排序
        blocks.sort(key=lambda x: x["start"])
        
        return blocks
    
    @staticmethod
    def _split_long_segment(text: str, base_position: int) -> List[Dict]:
        """
        切分超长段落，使用滑动窗口找到最强连续子段
        
        Args:
            text: 超长段落文本
            base_position: 基础位置（在原文中的位置）
            
        Returns:
            段落列表
        """
        segments = []
        window_size = SourceSegmenter.MAX_SEGMENT_LENGTH
        step_size = window_size // 2  # 滑动步长
        
        # 尝试在句子边界切分
        sentence_endings = re.compile(r'[。！？\n]')
        sentences = sentence_endings.split(text)
        
        current_segment = ""
        current_length = 0
        segment_start = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_length = len(sentence)
            
            # 如果当前段落加上新句子不超过阈值，则添加
            if current_length + sentence_length <= window_size:
                if current_segment:
                    current_segment += " " + sentence
                else:
                    current_segment = sentence
                    segment_start = base_position + text.find(sentence)
                current_length += sentence_length
            else:
                # 保存当前段落
                if current_segment:
                    segments.append({
                        "id": 0,  # 稍后重新分配
                        "text": current_segment,
                        "position": segment_start,
                        "length": len(current_segment)
                    })
                
                # 开始新段落
                current_segment = sentence
                segment_start = base_position + text.find(sentence)
                current_length = sentence_length
        
        # 添加最后一个段落
        if current_segment:
            segments.append({
                "id": 0,  # 稍后重新分配
                "text": current_segment,
                "position": segment_start,
                "length": len(current_segment)
            })
        
        # 如果仍然没有段落（极端情况），按固定长度切分
        if not segments:
            chunk_size = SourceSegmenter.MAX_SEGMENT_LENGTH
            for i in range(0, len(text), chunk_size):
                chunk = text[i:i + chunk_size]
                segments.append({
                    "id": 0,
                    "text": chunk,
                    "position": base_position + i,
                    "length": len(chunk)
                })
        
        return segments
    
    @staticmethod
    def _fast_segment(content: str) -> List[Dict]:
        """
        快速切分模式：按空行简单切分
        
        Args:
            content: 文档内容
            
        Returns:
            段落列表
        """
        segments = []
        paragraphs = content.split('\n\n')
        
        for idx, para in enumerate(paragraphs, 1):
            para = para.strip()
            if not para:
                continue
            
            # 如果段落太长，简单截断
            if len(para) > SourceSegmenter.MAX_SEGMENT_LENGTH:
                para = para[:SourceSegmenter.MAX_SEGMENT_LENGTH] + "..."
            
            segments.append({
                "id": idx,
                "text": para,
                "position": content.find(para),
                "length": len(para)
            })
        
        logger.info(
            "快速切分完成",
            total_segments=len(segments),
            content_length=len(content)
        )
        
        return segments
    
    @staticmethod
    def _fallback_segment(content: str, chunk_size: int = 500) -> List[Dict]:
        """
        兜底策略：按固定长度切分
        
        Args:
            content: 文档内容
            chunk_size: 切分大小（字符数）
            
        Returns:
            段落列表
        """
        segments = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            segments.append({
                "id": len(segments) + 1,
                "text": chunk,
                "position": i,
                "length": len(chunk)
            })
        
        logger.warning(
            "使用兜底策略切分",
            total_segments=len(segments),
            chunk_size=chunk_size
        )
        
        return segments
    
    @staticmethod
    def format_segments_for_prompt(segments: List[Dict]) -> str:
        """
        格式化段落为prompt格式
        
        Args:
            segments: 段落列表
            
        Returns:
            格式化后的字符串，用于AI prompt
        """
        if not segments:
            return ""
        
        formatted_lines = []
        for segment in segments:
            formatted_lines.append(f"[段落{segment['id']}] {segment['text']}")
        
        return "\n\n".join(formatted_lines)
    
    @staticmethod
    def get_segments_by_ids(segments: List[Dict], source_ids: List[int]) -> List[Dict]:
        """
        根据source_ids获取对应的段落
        
        Args:
            segments: 所有段落列表
            source_ids: 段落ID列表
            
        Returns:
            对应的段落列表
        """
        segment_dict = {seg["id"]: seg for seg in segments}
        result = []
        
        for seg_id in source_ids:
            if seg_id in segment_dict:
                result.append(segment_dict[seg_id])
            else:
                logger.warning("无效的段落ID", segment_id=seg_id, total_segments=len(segments))
        
        return result

