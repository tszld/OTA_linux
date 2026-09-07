"""ai-agent 文档整理模块（纯功能模块，不涉及存储）

提供文档格式转换和 LLM 压缩功能，返回处理结果。
"""
import os
from .converter import PdfConverter, MarkdownConverter, TxtConverter
from .processor import DocumentCompressor
from .config import Config


def _extract_filename(file_path: str) -> str:
    """
    从文件路径提取原始文件名（不含扩展名）
    
    ForClient 上传的文件格式：{timestamp}_{original_name}.{ext}
    例如：1234567890_产品手册.pdf -> 产品手册
    """
    basename = os.path.basename(file_path)
    
    # 尝试去掉时间戳前缀（格式：{timestamp}_{filename}）
    if '_' in basename:
        parts = basename.split('_', 1)
        if len(parts) == 2 and parts[0].isdigit():
            basename = parts[1]
    
    # 去掉扩展名
    name_without_ext = os.path.splitext(basename)[0]
    return name_without_ext


def process_document(file_path: str, doc_type: str, dept_id: int | None = None, original_filename: str | None = None) -> dict:
    """
    处理单个文档的完整流程：转换 → 压缩
    
    :param file_path: 文档文件路径
    :param doc_type: 文档类型，'public' 或 'dept'
    :param dept_id: 部门 ID（仅部门文档需要）
    :param original_filename: 原始文件名（不含扩展名），不传则从 file_path 自动提取
    :return: 处理结果字典
        - raw_markdown: 转换后的原始 Markdown 文本
        - compressed_text: LLM 压缩后的文本
        - filename: 原始文件名（不含扩展名）
    """
    # 提取原始文件名
    if original_filename:
        filename = original_filename
    else:
        filename = _extract_filename(file_path)
    print(f"  原始文件名: {filename}")
    
    # 根据文件扩展名选择转换器
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        converter = PdfConverter()
    elif ext == '.md':
        converter = MarkdownConverter()
    elif ext == '.txt':
        converter = TxtConverter()
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
    
    # 1. 格式转换
    print(f"[1/2] 转换文档格式...")
    markdown_text = converter.convert(file_path)
    print(f"  转换完成，文本长度: {len(markdown_text)} 字符")
    
    # 2. LLM 压缩
    print(f"[2/2] 调用 LLM 压缩...")
    compressor = DocumentCompressor()
    max_tokens = Config.PUBLIC_MAX_TOKENS if doc_type == 'public' else Config.DEPT_MAX_TOKENS
    compressed_text = compressor.compress(markdown_text, max_tokens)
    print(f"  压缩完成，输出长度: {len(compressed_text)} 字符")
    
    return {
        'raw_markdown': markdown_text,
        'compressed_text': compressed_text,
        'filename': filename
    }


__all__ = ['process_document',
           'PdfConverter', 'MarkdownConverter', 'TxtConverter', 
           'DocumentCompressor', 'Config']
