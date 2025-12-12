"""
文档内容提取服务
支持PDF、Word、PPT、Markdown、TXT格式
"""
import os
from pathlib import Path
from typing import Optional
import structlog

logger = structlog.get_logger()


class DocumentExtractor:
    """文档内容提取器"""
    
    @staticmethod
    async def extract_pdf(file_path: str) -> str:
        """提取PDF文档内容"""
        try:
            import pdfplumber
            
            content_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        content_parts.append(text)
            
            content = "\n\n".join(content_parts)
            logger.info("PDF内容提取成功", file_path=file_path, pages=len(pdf.pages))
            return content
            
        except Exception as e:
            logger.error("PDF提取失败", file_path=file_path, error=str(e))
            raise Exception(f"PDF内容提取失败: {str(e)}")
    
    @staticmethod
    async def extract_word(file_path: str) -> str:
        """提取Word文档内容"""
        try:
            from docx import Document
            
            doc = Document(file_path)
            content_parts = []
            
            # 提取段落
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content_parts.append(paragraph.text)
            
            # 提取表格
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells])
                    if row_text.strip():
                        content_parts.append(row_text)
            
            content = "\n".join(content_parts)
            logger.info("Word内容提取成功", file_path=file_path)
            return content
            
        except Exception as e:
            logger.error("Word提取失败", file_path=file_path, error=str(e))
            raise Exception(f"Word内容提取失败: {str(e)}")
    
    @staticmethod
    async def extract_ppt(file_path: str) -> str:
        """提取PPT文档内容"""
        try:
            from pptx import Presentation
            
            prs = Presentation(file_path)
            content_parts = []
            
            for slide_num, slide in enumerate(prs.slides, 1):
                slide_content = []
                
                # 提取幻灯片标题和内容
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_content.append(shape.text.strip())
                
                if slide_content:
                    content_parts.append(f"--- 幻灯片 {slide_num} ---")
                    content_parts.extend(slide_content)
                    content_parts.append("")  # 空行分隔
            
            content = "\n".join(content_parts)
            logger.info("PPT内容提取成功", file_path=file_path, slides=len(prs.slides))
            return content
            
        except Exception as e:
            logger.error("PPT提取失败", file_path=file_path, error=str(e))
            raise Exception(f"PPT内容提取失败: {str(e)}")
    
    @staticmethod
    async def extract_markdown(file_path: str) -> str:
        """提取Markdown文档内容"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info("Markdown内容提取成功", file_path=file_path)
            return content
            
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                import chardet
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    encoding = chardet.detect(raw_data)['encoding']
                
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                
                logger.info("Markdown内容提取成功（检测编码）", file_path=file_path, encoding=encoding)
                return content
            except Exception as e:
                logger.error("Markdown提取失败", file_path=file_path, error=str(e))
                raise Exception(f"Markdown内容提取失败: {str(e)}")
        except Exception as e:
            logger.error("Markdown提取失败", file_path=file_path, error=str(e))
            raise Exception(f"Markdown内容提取失败: {str(e)}")
    
    @staticmethod
    async def extract_txt(file_path: str) -> str:
        """提取TXT文档内容"""
        try:
            import chardet
            
            # 检测编码
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                encoding = chardet.detect(raw_data)['encoding'] or 'utf-8'
            
            # 读取内容
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            
            logger.info("TXT内容提取成功", file_path=file_path, encoding=encoding)
            return content
            
        except Exception as e:
            logger.error("TXT提取失败", file_path=file_path, error=str(e))
            raise Exception(f"TXT内容提取失败: {str(e)}")
    
    @staticmethod
    async def extract(file_path: str, file_type: str) -> str:
        """
        根据文件类型提取内容
        
        Args:
            file_path: 文件路径
            file_type: 文件类型（pdf/docx/pptx/md/txt）
        
        Returns:
            提取的文本内容
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        file_type = file_type.lower()
        
        extractors = {
            'pdf': DocumentExtractor.extract_pdf,
            'docx': DocumentExtractor.extract_word,
            'pptx': DocumentExtractor.extract_ppt,
            'md': DocumentExtractor.extract_markdown,
            'markdown': DocumentExtractor.extract_markdown,
            'txt': DocumentExtractor.extract_txt,
        }
        
        extractor = extractors.get(file_type)
        if not extractor:
            raise ValueError(f"不支持的文件类型: {file_type}")
        
        return await extractor(file_path)

