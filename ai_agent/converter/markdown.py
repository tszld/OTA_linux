"""Markdown 文档转换器"""
from .base import BaseConverter


class MarkdownConverter(BaseConverter):
    """Markdown 转换器（直接读取，无需转换）"""
    
    def convert(self, input_path: str) -> str:
        """
        读取 Markdown 文件内容
        
        :param input_path: Markdown 文件路径
        :return: Markdown 格式的文本
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(input_path, 'r', encoding='gbk') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Markdown 读取失败 [{input_path}]: {str(e)}")
    
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名"""
        return ['.md']
