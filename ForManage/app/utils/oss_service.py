"""OSS 对象存储服务（精简版，仅用于生成下载链接）"""
import oss2
from flask import current_app


def _get_bucket():
    """获取 OSS Bucket 实例"""
    auth = oss2.Auth(
        current_app.config['OSS_ACCESS_KEY_ID'],
        current_app.config['OSS_ACCESS_KEY_SECRET']
    )
    return oss2.Bucket(auth, current_app.config['OSS_ENDPOINT'], current_app.config['OSS_BUCKET'])


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
