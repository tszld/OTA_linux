"""应用配置"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """应用配置"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 数据库配置
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

    # 阿里云 OSS 配置
    OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
    OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
    OSS_BUCKET = os.getenv('OSS_BUCKET', 'demo-bucket')
    OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'https://oss-cn-beijing.aliyuncs.com')

    # OSS 路径前缀配置
    OSS_RAW_PREFIX = os.getenv('OSS_RAW_PREFIX', 'raw')              # 原始文档
    OSS_PROCESSED_PREFIX = os.getenv('OSS_PROCESSED_PREFIX', 'processed')  # 处理后文档
    OSS_RECYCLE_PREFIX = os.getenv('OSS_RECYCLE_PREFIX', 'recycle')  # 回收站

    # 文件上传配置
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))  # 16MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md'}

    # 短信服务配置
    SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'mock')  # 'mock' 或 'aliyun'
