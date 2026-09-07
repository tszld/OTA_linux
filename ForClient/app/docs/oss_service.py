"""OSS 对象存储服务"""
import os
import time
import tempfile
import oss2
from flask import current_app


def _get_bucket():
    """获取 OSS Bucket 实例"""
    auth = oss2.Auth(
        current_app.config['OSS_ACCESS_KEY_ID'],
        current_app.config['OSS_ACCESS_KEY_SECRET']
    )
    return oss2.Bucket(auth, current_app.config['OSS_ENDPOINT'], current_app.config['OSS_BUCKET'])


def upload(data, object_key: str) -> bool:
    """
    上传数据到 OSS
    :param data: 文件对象或 bytes
    :param object_key: OSS 对象 key
    :return: 是否成功
    """
    try:
        bucket = _get_bucket()
        bucket.put_object(object_key, data)
        return True
    except Exception as e:
        current_app.logger.error(f'上传失败 [{object_key}]: {str(e)}')
        return False


def download_to_temp(object_key: str):
    """
    从 OSS 下载文件到临时目录
    :param object_key: OSS 对象 key
    :return: (临时文件路径, 原始文件名不含扩展名) 元组，失败返回 (None, None)
    """
    try:
        bucket = _get_bucket()
        
        # 从 object_key 提取原始文件名
        basename = os.path.basename(object_key)
        if '_' in basename:
            parts = basename.split('_', 1)
            if len(parts) == 2 and parts[0].isdigit():
                basename = parts[1]
        
        # 提取原始文件名（不含扩展名）
        original_name = os.path.splitext(basename)[0]
        ext = os.path.splitext(basename)[1]
        
        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        bucket.get_object_to_file(object_key, temp_path)
        return temp_path, original_name
    except Exception as e:
        current_app.logger.error(f'下载文件失败 [{object_key}]: {str(e)}')
        return None, None


def get_download_url(object_key: str, expires: int = 3600):
    """
    生成 OSS 下载签名 URL
    :param object_key: OSS 对象 key
    :param expires: URL 有效期（秒）
    :return: 签名 URL 或 None
    """
    try:
        bucket = _get_bucket()
        return bucket.sign_url('GET', object_key, expires)
    except Exception as e:
        current_app.logger.error(f'生成下载链接失败：{str(e)}')
        return None


def delete(object_key: str) -> bool:
    """
    删除 OSS 对象
    :param object_key: OSS 对象 key
    :return: 是否成功
    """
    try:
        bucket = _get_bucket()
        bucket.delete_object(object_key)
        return True
    except Exception as e:
        current_app.logger.error(f'删除失败 [{object_key}]: {str(e)}')
        return False


def exists(object_key: str) -> bool:
    """
    检查 OSS 对象是否存在
    :param object_key: OSS 对象 key
    :return: 是否存在
    """
    try:
        bucket = _get_bucket()
        result = bucket.head_object(object_key)
        return result.status == 200
    except oss2.exceptions.NoSuchKey:
        return False
    except Exception as e:
        current_app.logger.error(f'检查文件存在失败 [{object_key}]: {str(e)}')
        return False


def list_files(prefix: str):
    """
    列出指定前缀下的所有文件
    :param prefix: OSS 路径前缀
    :return: 文件列表
    """
    try:
        bucket = _get_bucket()
        files = []
        for obj in oss2.ObjectIterator(bucket, prefix=prefix):
            if obj.key.endswith('/'):
                continue
            parts = obj.key.split('_', 1)
            display_name = parts[1] if len(parts) > 1 else obj.key.split('/')[-1]
            files.append({
                'key': obj.key,
                'filename': display_name,
                'last_modified': obj.last_modified
            })
        return files
    except Exception as e:
        current_app.logger.error(f'列出文件失败：{str(e)}')
        return []


def move_to_recycle(object_key: str):
    """
    将文件移入回收站（复制 + 删除原文件）
    :param object_key: OSS 对象 key
    :return: (成功, 错误信息) 元组
    """
    try:
        bucket = _get_bucket()
        recycle_prefix = current_app.config.get('OSS_RECYCLE_PREFIX', 'recycle')
        recycle_key = f"{recycle_prefix}/{object_key}"
        bucket.copy_object(current_app.config['OSS_BUCKET'], object_key, recycle_key)
        bucket.delete_object(object_key)
        return True, None
    except Exception as e:
        return False, f'操作失败：{str(e)}'


def restore_from_recycle(object_key: str):
    """
    从回收站恢复文件（复制回原位置 + 删除回收站文件）
    :param object_key: OSS 对象 key（不含回收站前缀）
    :return: (成功, 错误信息) 元组
    """
    try:
        bucket = _get_bucket()
        recycle_prefix = current_app.config.get('OSS_RECYCLE_PREFIX', 'recycle')
        recycle_key = f"{recycle_prefix}/{object_key}"
        bucket.copy_object(current_app.config['OSS_BUCKET'], recycle_key, object_key)
        bucket.delete_object(recycle_key)
        return True, None
    except Exception as e:
        return False, f'操作失败：{str(e)}'


def hard_delete_from_recycle(object_key: str):
    """
    从回收站彻底删除文件
    :param object_key: OSS 对象 key（不含回收站前缀）
    :return: (成功, 错误信息) 元组
    """
    try:
        bucket = _get_bucket()
        recycle_prefix = current_app.config.get('OSS_RECYCLE_PREFIX', 'recycle')
        recycle_key = f"{recycle_prefix}/{object_key}"
        print(f"[OSS] 彻底删除回收站文件：{recycle_key}")
        result = bucket.delete_object(recycle_key)
        print(f"[OSS] 删除结果：status={result.status}")
        return True, None
    except Exception as e:
        print(f"[OSS] 删除失败：{e}")
        return False, f'删除失败：{str(e)}'
