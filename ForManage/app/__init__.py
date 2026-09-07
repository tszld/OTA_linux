"""Flask 应用工厂"""
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from .config import Config
from . import database
from .sms import create_sms_service

login_manager = LoginManager()


class User:
    """用户类（用于 flask-login）"""
    def __init__(self, user_row):
        self.id = user_row['id']
        self.phone = user_row['phone']
        self.role = user_row['role']
        self.dept_id = user_row['dept_id']
        self.status = user_row['status']
        self.dept_name = user_row['dept_name']
    
    @property
    def is_authenticated(self):
        return True
    
    @property
    def is_active(self):
        return self.status == 'approved'
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    user_row = database.get_user_by_id(int(user_id))
    if user_row:
        return User(user_row)
    return None


def create_app():
    """Flask 应用工厂"""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    app = Flask(__name__,
                template_folder=os.path.join(root_dir, 'templates'),
                static_folder=os.path.join(root_dir, 'static'))
    app.config.from_object(Config)
    
    # 确保 DB_PATH 是绝对路径
    if not os.path.isabs(app.config['DB_PATH']):
        app.config['DB_PATH'] = os.path.abspath(app.config['DB_PATH'])
    
    # Flask 3.x: 禁止 JSON Unicode 转义
    app.json.ensure_ascii = False
    
    # 初始化短信服务
    app.sms_service = create_sms_service(app.config.get('SMS_PROVIDER', 'mock'))
    
    # 初始化登录管理器
    login_manager.init_app(app)
    login_manager.login_view = 'auth.admin_login'
    login_manager.login_message = '请先登录'
    
    # 注册蓝图
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .api.routes import api_bp
    app.register_blueprint(auth_bp, url_prefix='/admin')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/robot')
    
    # 初始化数据库
    database.init_db(app)
    
    # 注册数据库连接清理
    app.teardown_appcontext(database.close_db)
    
    # 根路由重定向
    @app.route('/')
    def index():
        return redirect(url_for('auth.admin_login'))
    
    return app
