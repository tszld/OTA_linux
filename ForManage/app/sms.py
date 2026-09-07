"""短信验证码服务模块

当前使用 Mock 模式适用于开发环境。
生产环境需替换为阿里云短信服务（AliyunSmsService）。
"""
from abc import ABC, abstractmethod


class BaseSmsService(ABC):
    """短信服务基类"""
    
    @abstractmethod
    def send_code(self, phone: str) -> bool:
        """
        发送验证码
        :param phone: 手机号
        :return: 是否发送成功
        """
        pass
    
    @abstractmethod
    def verify_code(self, phone: str, code: str) -> bool:
        """
        校验验证码
        :param phone: 手机号
        :param code: 用户输入的验证码
        :return: 是否正确
        """
        pass


class MockSmsService(BaseSmsService):
    """开发环境：Mock 实现"""
    MOCK_CODE = '123456'
    
    def send_code(self, phone: str) -> bool:
        print(f"[Mock SMS] 发送验证码到 {phone}: {self.MOCK_CODE}")
        return True
    
    def verify_code(self, phone: str, code: str) -> bool:
        return code == self.MOCK_CODE


class AliyunSmsService(BaseSmsService):
    """生产环境：阿里云实现（预留）"""
    
    def send_code(self, phone: str) -> bool:
        # TODO: 接入阿里云短信 SDK
        return False
    
    def verify_code(self, phone: str, code: str) -> bool:
        # TODO: 接入阿里云验证码校验
        return False


def create_sms_service(provider: str) -> BaseSmsService:
    """
    工厂函数：根据配置创建服务实例
    :param provider: 服务商名称 ('mock' 或 'aliyun')
    :return: 短信服务实例
    """
    if provider == 'aliyun':
        return AliyunSmsService()
    return MockSmsService()  # 默认 mock
