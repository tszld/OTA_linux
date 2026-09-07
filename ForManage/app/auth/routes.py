"""管理员认证路由"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .. import database, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    """管理员登录页面"""
    # 已登录的管理员直接跳转到管理首页
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.robot_list'))
    
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        code = request.form.get('code', '').strip()
        
        if not phone or not code:
            flash('请输入手机号和验证码', 'error')
            return render_template('auth/login.html')
        
        # 校验验证码
        if not current_app.sms_service.verify_code(phone, code):
            flash('验证码错误', 'error')
            return render_template('auth/login.html', phone=phone)
        
        # 查找用户
        db = database.get_db()
        user_row = db.execute(
            'SELECT u.*, d.name as dept_name FROM users u LEFT JOIN departments d ON u.dept_id = d.id WHERE u.phone = ?',
            (phone,)
        ).fetchone()
        
        if not user_row:
            flash('该手机号未注册', 'error')
            return render_template('auth/login.html', phone=phone)
        
        if user_row['status'] != 'approved':
            flash('账号未审批或已被拒绝', 'error')
            return render_template('auth/login.html', phone=phone)
        
        user = User(user_row)
        
        # 仅允许管理员登录
        if not user.is_admin:
            flash('仅管理员可访问此系统', 'error')
            return render_template('auth/login.html', phone=phone)
        
        login_user(user)
        flash('登录成功', 'success')
        return redirect(url_for('admin.robot_list'))
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def admin_logout():
    """管理员登出"""
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('auth.admin_login'))
