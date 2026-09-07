"""后台任务管理模块

当前使用 ThreadPoolExecutor 适用于单实例部署。
若未来进行多实例/负载均衡部署，需替换为 Celery + Redis/RabbitMQ。
"""
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from flask import current_app

# 线程池：最多 5 个线程同时处理文档
_executor = ThreadPoolExecutor(max_workers=5)


def _process_document_task(app, file_key: str, doc_type: str, dept_id: int | None = None):
    """
    后台任务：处理单个文档
    
    :param app: Flask 应用实例
    :param file_key: OSS 对象 key
    :param doc_type: 文档类型，'public' 或 'dept'
    :param dept_id: 部门 ID（仅部门文档需要）
    """
    temp_path = None
    with app.app_context():
        from . import database
        from .docs import oss_service
        
        try:
            print(f"[ai_agent] 开始处理文档：{file_key}")
            
            # 更新状态为处理中
            database.update_document_status(file_key, 'processing')
            
            # 从 OSS 下载文件到临时目录（返回路径和原始文件名）
            temp_path, original_filename = oss_service.download_to_temp(file_key)
            if not temp_path:
                raise RuntimeError(f"下载文件失败：{file_key}")
            
            # 调用 ai_agent 处理文档（传入原始文件名）
            from ai_agent import process_document
            result = process_document(temp_path, doc_type, dept_id, original_filename)
            
            # 上传压缩后的文档到 OSS
            processed_prefix = current_app.config.get('OSS_PROCESSED_PREFIX', 'processed')
            if doc_type == 'public':
                processed_key = f"{processed_prefix}/public/{result['filename']}.md"
            else:
                processed_key = f"{processed_prefix}/dept-{dept_id}/{result['filename']}.md"
            
            upload_success = oss_service.upload(result['compressed_text'].encode('utf-8'), processed_key)
            if not upload_success:
                raise RuntimeError(f"上传处理后文档失败：{processed_key}")
            
            # 更新状态为已完成
            database.update_document_status(file_key, 'completed')
            print(f"[ai_agent] 文档处理完成，已上传：{processed_key}")
            
        except Exception as e:
            # 更新状态为失败
            database.update_document_status(file_key, 'failed', str(e))
            print(f"[ai_agent] 文档处理失败：{e}")
            
        finally:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print(f"[警告] 清理临时文件失败：{temp_path} - {e}")


def submit_process_document(app, file_key: str, doc_type: str, dept_id: int | None = None):
    """
    提交文档处理任务到线程池
    
    :param app: Flask 应用实例
    :param file_key: OSS 对象 key
    :param doc_type: 文档类型，'public' 或 'dept'
    :param dept_id: 部门 ID（仅部门文档需要）
    """
    _executor.submit(_process_document_task, app, file_key, doc_type, dept_id)


def shutdown():
    """关闭线程池（应用退出时调用）"""
    _executor.shutdown(wait=False)
