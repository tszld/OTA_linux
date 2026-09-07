from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from .. import database, User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
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
        user_row = database.get_user_by_phone(phone)
        if not user_row:
            flash('该手机号未注册', 'error')
            return render_template('auth/login.html', phone=phone)

        if user_row['status'] == 'pending':
            flash('账号审核中，请耐心等待', 'warning')
            return render_template('auth/login.html', phone=phone)

        if user_row['status'] == 'rejected':
            flash('账号审核未通过', 'error')
            return render_template('auth/login.html', phone=phone)

        user = User(user_row)
        login_user(user)
        flash('登录成功', 'success')

        # 根据角色跳转
        if user.is_admin:
            return redirect(url_for('admin.departments'))
        else:
            return redirect(url_for('docs.dept_docs'))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """注册页面（部门管理员注册）"""
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        code = request.form.get('code', '').strip()
        dept_id = request.form.get('dept_id', '').strip()

        if not phone or not code or not dept_id:
            flash('请填写完整信息', 'error')
            departments = database.get_all_departments()
            return render_template('auth/register.html', departments=departments)

        # 校验验证码
        if not current_app.sms_service.verify_code(phone, code):
            flash('验证码错误', 'error')
            departments = database.get_all_departments()
            return render_template('auth/register.html', departments=departments, phone=phone, dept_id=dept_id)

        # 检查手机号是否已注册
        existing_user = database.get_user_by_phone(phone)
        if existing_user:
            flash('该手机号已注册', 'error')
            departments = database.get_all_departments()
            return render_template('auth/register.html', departments=departments, phone=phone, dept_id=dept_id)

        # 注册用户
        success, error = database.register_user(phone, int(dept_id))
        if success:
            flash('注册成功，请等待管理员审批', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash(error, 'error')
            departments = database.get_all_departments()
            return render_template('auth/register.html', departments=departments, phone=phone, dept_id=dept_id)

    # GET 请求
    departments = database.get_all_departments()
    return render_template('auth/register.html', departments=departments)


@auth_bp.route('/logout')
@login_required
def logout():
    """登出"""
    logout_user()
    flash('已退出登录', 'success')
    return redirect(url_for('auth.login'))
