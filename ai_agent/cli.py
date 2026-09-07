"""命令行入口"""
import argparse
import sys
import os
from pathlib import Path

# 确保可以作为脚本直接运行
if __name__ == '__main__' and __package__ is None:
    # 添加父目录到路径，使 ai_agent 可导入
    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

from ai_agent import process_document


def extract_filename(file_path: str) -> str:
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


def process_document_cli(file_path: str, doc_type: str, dept_id: int | None = None, output_dir: str | None = None):
    """
    处理单个文档
    
    :param file_path: 文档文件路径
    :param doc_type: 文档类型，'public' 或 'dept'
    :param dept_id: 部门 ID（部门文档必须）
    :param output_dir: 输出目录（可选，用于调试）
    """
    # 提取原始文件名
    original_filename = extract_filename(file_path)
    
    print(f"开始处理文档: {file_path}")
    print(f"原始文件名: {original_filename}")
    print(f"文档类型: {doc_type}, 部门 ID: {dept_id}")
    
    # 处理文档
    result = process_document(file_path, doc_type, dept_id)
    
    print(f"\n处理完成！")
    print(f"  原始文件名: {result['filename']}")
    print(f"  原始 Markdown 长度: {len(result['raw_markdown'])} 字符")
    print(f"  压缩后文本长度: {len(result['compressed_text'])} 字符")
    
    # 如果指定了输出目录，保存结果用于调试
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存原始 Markdown
        raw_path = os.path.join(output_dir, f"{result['filename']}_raw.md")
        with open(raw_path, 'w', encoding='utf-8') as f:
            f.write(result['raw_markdown'])
        print(f"\n  原始 Markdown 已保存: {raw_path}")
        
        # 保存压缩后文本
        compressed_path = os.path.join(output_dir, f"{result['filename']}_compressed.md")
        with open(compressed_path, 'w', encoding='utf-8') as f:
            f.write(result['compressed_text'])
        print(f"  压缩后文本已保存: {compressed_path}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(description='ai-agent 文档整理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # process 命令
    process_parser = subparsers.add_parser('process', help='处理单个文档')
    process_parser.add_argument('file_path', help='文档文件路径（支持 .pdf/.md/.txt）')
    process_parser.add_argument('--type', dest='doc_type', choices=['public', 'dept'], 
                                required=True, help='文档类型')
    process_parser.add_argument('--dept-id', type=int, help='部门 ID（部门文档必须）')
    process_parser.add_argument('--output', help='输出目录（可选，用于调试）')
    
    args = parser.parse_args()
    
    if args.command == 'process':
        if args.doc_type == 'dept' and args.dept_id is None:
            print("错误: 部门文档必须提供 --dept-id 参数")
            sys.exit(1)
        
        try:
            process_document_cli(args.file_path, args.doc_type, args.dept_id, args.output)
        except Exception as e:
            print(f"\n错误: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
