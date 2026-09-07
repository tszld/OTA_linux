"""PDF 文档转换器"""
import pymupdf
from .base import BaseConverter


class PdfConverter(BaseConverter):
    """PDF 转 Markdown 转换器"""
    
    def convert(self, input_path: str) -> str:
        """
        将 PDF 转换为 Markdown 格式
        
        :param input_path: PDF 文件路径
        :return: Markdown 格式的文本
        """
        try:
            doc = pymupdf.open(input_path)
            page_count = len(doc)
            markdown_parts = []
            
            for page_num, page in enumerate(doc, 1):
                # 提取文本
                text = page.get_text()
                if text.strip():
                    # 添加页码标记
                    markdown_parts.append(f"<!-- Page {page_num} -->\n")
                    markdown_parts.append(text)
                    markdown_parts.append("\n\n")
            
            doc.close()
            result = ''.join(markdown_parts).strip()
            
            # 检查是否为空（可能是扫描件）
            if not result:
                raise ValueError(
                    f"PDF 提取文本为空 [{input_path}]，共 {page_count} 页。"
                    "可能是扫描件（图片），需要 OCR 处理。"
                    "当前版本不支持 OCR，请上传可提取文本的 PDF。"
                )
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"PDF 转换失败 [{input_path}]: {str(e)}")
    
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.pdf']
