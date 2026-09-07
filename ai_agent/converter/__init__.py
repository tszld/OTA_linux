"""格式转换模块"""
from .base import BaseConverter


def PdfConverter():
    """延迟加载 PDF 转换器"""
    from .pdf import PdfConverter as _PdfConverter
    return _PdfConverter()


def MarkdownConverter():
    """延迟加载 Markdown 转换器"""
    from .markdown import MarkdownConverter as _MarkdownConverter
    return _MarkdownConverter()


def TxtConverter():
    """延迟加载 TXT 转换器"""
    from .txt import TxtConverter as _TxtConverter
    return _TxtConverter()


__all__ = ['BaseConverter', 'PdfConverter', 'MarkdownConverter', 'TxtConverter']
