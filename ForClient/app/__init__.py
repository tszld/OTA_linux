import os
from flask import Flask
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
    # 获取项目根目录
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    app = Flask(__name__, 
                template_folder=os.path.join(root_dir, 'templates'),
                static_folder=os.path.join(root_dir, 'static'))
    app.config.from_object(Config)

    # 初始化短信服务
    app.sms_service = create_sms_service(app.config.get('SMS_PROVIDER', 'mock'))

    # 初始化登录管理器
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'

    # 注册蓝图
    from .auth.routes import auth_bp
    from .docs.routes import docs_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # 初始化数据库
    database.init_db(app)
    
    # 注册数据库连接清理
    app.teardown_appcontext(database.close_db)

    # 根路由重定向
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('docs.public_docs'))

    return app
