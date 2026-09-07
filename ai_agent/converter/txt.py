"""TXT 文档转换器"""
from .base import BaseConverter


class TxtConverter(BaseConverter):
    """TXT 转 Markdown 转换器"""
    
    def convert(self, input_path: str) -> str:
        """
        将 TXT 转换为 Markdown 格式
        
        :param input_path: TXT 文件路径
        :return: Markdown 格式的文本
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(input_path, 'r', encoding='gbk') as f:
                content = f.read()
        except Exception as e:
            raise ValueError(f"TXT 读取失败 [{input_path}]: {str(e)}")
        
        # 简单包装为 Markdown
        # 按双换行分段，每段之间加空行
        paragraphs = content.split('\n\n')
        markdown_parts = []
        
        for para in paragraphs:
            para = para.strip()
            if para:
                markdown_parts.append(para)
                markdown_parts.append('\n\n')
        
        return ''.join(markdown_parts).strip()
    
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.txt']
