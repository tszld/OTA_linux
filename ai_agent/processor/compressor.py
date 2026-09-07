"""文档压缩器"""
from openai import OpenAI
from ..config import Config


class DocumentCompressor:
    """使用 LLM 压缩文档"""
    
    # 复用客户端实例
    _client = None
    
    def __init__(self):
        """初始化 LLM 客户端"""
        if not Config.LLM_API_KEY:
            raise ValueError("LLM_API_KEY 未配置")
        
        # 单例模式，复用客户端
        if DocumentCompressor._client is None:
            DocumentCompressor._client = OpenAI(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_API_BASE,
                timeout=60.0
            )
        self.client = DocumentCompressor._client
        self.model = Config.LLM_MODEL
    
    def compress(self, text: str, max_tokens: int) -> str:
        """
        压缩文档内容
        
        :param text: 原始文档文本
        :param max_tokens: 最大输出 token 数
        :return: 压缩后的 Markdown 文本
        """
        if not text.strip():
            raise ValueError("输入文本为空，无法压缩")
        
        # 简化 prompt，减少 token 消耗
        prompt = f"""请压缩以下文档，保留关键信息，使用 Markdown 格式，控制在 {max_tokens} token 以内：

{text}"""

        try:
            print(f"  调用 LLM ({self.model})...")
            print(f"  输入文本长度: {len(text)} 字符")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是文档整理助手，擅长压缩关键信息。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3
            )
            
            result = response.choices[0].message.content.strip()
            print(f"  LLM 响应完成")
            return result
            
        except Exception as e:
            raise RuntimeError(f"LLM 压缩失败: {str(e)}")
