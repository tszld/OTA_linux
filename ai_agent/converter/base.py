"""转换器基类"""
from abc import ABC, abstractmethod


class BaseConverter(ABC):
    """文档转换器基类"""
    
    @abstractmethod
    def convert(self, input_path: str) -> str:
        """
        将文档转换为 Markdown 格式
        
        :param input_path: 输入文件路径
        :return: Markdown 格式的文本
        """
        pass
    
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """
        返回支持的文件扩展名列表
        
        :return: 扩展名列表，如 ['.pdf', '.docx']
        """
        pass
