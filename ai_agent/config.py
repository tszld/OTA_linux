"""ai-agent 配置模块"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 明确加载 ai-agent 目录下的 .env 文件
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


class Config:
    """ai-agent 配置"""
    
    # LLM API 配置
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    LLM_API_BASE = os.getenv('LLM_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    LLM_MODEL = os.getenv('LLM_MODEL', 'qwen-plus')
    
    # Token 限制
    PUBLIC_MAX_TOKENS = int(os.getenv('PUBLIC_MAX_TOKENS', '5000'))
    DEPT_MAX_TOKENS = int(os.getenv('DEPT_MAX_TOKENS', '10000'))
