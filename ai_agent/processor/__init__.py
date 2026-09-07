"""文档处理模块"""


def DocumentCompressor():
    """延迟加载文档压缩器"""
    from .compressor import DocumentCompressor as _DocumentCompressor
    return _DocumentCompressor()


__all__ = ['DocumentCompressor']
