"""应用配置"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """应用配置"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

    # 数据库配置 - 指向 ForClient 的数据库
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DB_PATH = os.path.join(BASE_DIR, '..', 'ForClient', 'instance', 'app.db')

    # 阿里云 OSS 配置
    OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
    OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
    OSS_BUCKET = os.getenv('OSS_BUCKET', 'demo-bucket')
    OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', 'https://oss-cn-beijing.aliyuncs.com')

    # OSS 路径前缀配置
    OSS_RAW_PREFIX = os.getenv('OSS_RAW_PREFIX', 'raw')
    OSS_PROCESSED_PREFIX = os.getenv('OSS_PROCESSED_PREFIX', 'processed')

    # 短信服务配置
    SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'mock')

    # 机器人管理配置
    API_KEY_ROTATE_DAYS = int(os.getenv('API_KEY_ROTATE_DAYS', 30))
    UPDATE_WINDOW_TOLERANCE_HOURS = int(os.getenv('UPDATE_WINDOW_TOLERANCE_HOURS', 1))
    ONLINE_THRESHOLD_MINUTES = int(os.getenv('ONLINE_THRESHOLD_MINUTES', 5))

    # JSON 配置 - 禁止 Unicode 转义
    JSON_AS_ASCII = False
