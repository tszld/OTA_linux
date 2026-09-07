import sys
import os
from pathlib import Path
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app, jsonify
from flask_login import login_required, current_user
from .. import database
from ..docs import oss_service

# 添加项目根目录到路径，以便导入 ai_agent
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


def _extract_filename_from_key(object_key: str) -> str:
    """
    从 object_key 提取原始文件名（不含扩展名）
    
    object_key 格式：public/1234567890_产品手册.pdf
    返回：产品手册
    """
    basename = os.path.basename(object_key)
    
    # 尝试去掉时间戳前缀（格式：{timestamp}_{filename}）
    if '_' in basename:
        parts = basename.split('_', 1)
        if len(parts) == 2 and parts[0].isdigit():
            basename = parts[1]
    
    # 去掉扩展名
    name_without_ext = os.path.splitext(basename)[0]
    return name_without_ext



@admin_bp.route('/docs')
@admin_required
def admin_docs():
    """管理员 - 公共文档管理"""
    files = database.get_documents_by_type('public')
    return render_template('admin/docs.html', files=files)




@admin_bp.route('/api/docs/status')
@admin_required
def docs_status_api():
    """API - 返回公共文档状态"""
    files = database.get_documents_by_type('public')
    result = [{'file_key': f['file_key'], 'status': f['status'], 'error_message': f['error_message']} for f in files]
    return jsonify(result)

@admin_bp.route('/docs/upload', methods=['POST'])
@admin_required
def upload_public_doc():
    """管理员 - 上传公共文档（支持多文件）"""
    files = request.files.getlist('file')
    if not files or all(not f.filename for f in files):
        flash('请选择文件', 'error')
        return redirect(url_for('admin.admin_docs'))

    from flask import current_app
    allowed = current_app.config['ALLOWED_EXTENSIONS']
    
    success_count = 0
    fail_count = 0
    duplicate_count = 0
    
    for file in files:
        if not file or not file.filename:
            continue
        
        # 校验文件格式
        if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed:
            fail_count += 1
            continue
        
        # 提取文件名（用于检查同名）
        import os
        filename_without_ext = os.path.splitext(file.filename)[0]
        
        # 检查同名文件
        if database.check_duplicate_filename(filename_without_ext, 'public'):
            duplicate_count += 1
            continue
        
        # 上传到 OSS
        import time
        timestamp = int(time.time())
        raw_prefix = current_app.config.get('OSS_RAW_PREFIX', 'raw')
        object_key = f"{raw_prefix}/public/{timestamp}_{file.filename}"
        success = oss_service.upload(file, object_key)
        if not success:
            fail_count += 1
            continue
        file_key = object_key
        
        # 提取文件名
        filename = _extract_filename_from_key(file_key)
        
        # 创建文档记录
        db_success, db_error = database.create_document(file_key, filename, 'public')
        if not db_success:
            fail_count += 1
            continue
        
        success_count += 1
        
        # 提交后台任务
        from .. import tasks
        tasks.submit_process_document(current_app._get_current_object(), file_key, 'public', None)
    
    # 汇总消息
    if success_count > 0:
        flash(f'成功上传 {success_count} 个文件，正在后台整理...', 'success')
    if duplicate_count > 0:
        flash(f'{duplicate_count} 个文件因重名未上传', 'warning')
    if fail_count > 0:
        flash(f'{fail_count} 个文件上传失败', 'error')
    
    return redirect(url_for('admin.admin_docs'))


@admin_bp.route('/docs/delete', methods=['POST'])
@admin_required
def delete_public_doc():
    """管理员 - 删除公共文档"""
    object_key = request.form.get('key')
    if not object_key:
        flash('参数错误', 'error')
        return redirect(url_for('admin.admin_docs'))

    raw_prefix = current_app.config.get('OSS_RAW_PREFIX', 'raw')
    if not object_key.startswith(f"{raw_prefix}/public/"):
        flash('无权操作此文件', 'error')
        return redirect(url_for('admin.admin_docs'))

    # 检查 OSS 文件是否存在
    if not oss_service.exists(object_key):
        # OSS 文件不存在，彻底删除数据库记录（不进回收站）
        print(f"[数据检查] 删除时发现 OSS 文件不存在，彻底清理数据库记录：{object_key}")
        database.hard_delete_document(object_key)
        flash('文件已失效，已彻底清理记录', 'warning')
        return redirect(url_for('admin.admin_docs'))

    success, error = oss_service.move_to_recycle(object_key)
    if success:
        # 软删除文档记录
        deleted = database.soft_delete_document(object_key)
        if not deleted:
            print(f"[警告] 文件已移到回收站，但数据库更新失败: {object_key}")
            flash('文件已删除，但数据库更新失败', 'warning')
        else:
            flash('文件已删除', 'success')
        
        # 删除 OSS 上的处理后文档
        try:
            filename = _extract_filename_from_key(object_key)
            processed_prefix = current_app.config.get('OSS_PROCESSED_PREFIX', 'processed')
            processed_key = f"{processed_prefix}/public/{filename}.md"
            oss_service.delete(processed_key)
            print(f"[OSS] 已删除处理后文档：{processed_key}")
        except Exception as e:
            print(f"[警告] 删除处理后文档失败：{e}")
    else:
        flash(error, 'error')
    return redirect(url_for('admin.admin_docs'))






    
    user_id = int(user_id)
    
    # 不能删除自己
    if user_id == current_user.id:
        flash('不能删除当前登录用户', 'error')
        return redirect(url_for('admin.pending_users'))
    
    success, error = database.delete_user(user_id)
    if success:
        flash('用户已删除', 'success')
    else:
        flash(f'删除失败: {error}', 'error')
    
    return redirect(url_for('admin.pending_users'))


@admin_bp.route('/depts')
@admin_required
def departments():
    """管理员 - 部门管理"""
    depts = database.get_all_departments()
    return render_template('admin/departments.html', departments=depts)


@admin_bp.route('/depts/create', methods=['POST'])
@admin_required
def create_department():
    """管理员 - 创建部门"""
    name = request.form.get('name', '').strip()
    if not name:
        flash('部门名称不能为空', 'error')
        return redirect(url_for('admin.departments'))

    success, error = database.create_department(name)
    if success:
        flash('部门创建成功', 'success')
    else:
        flash(error, 'error')
    
    return redirect(url_for('admin.departments'))


@admin_bp.route('/depts/<int:dept_id>/delete', methods=['POST'])
@admin_required
def delete_department(dept_id):
    """管理员 - 删除部门"""
    dept = database.get_department(dept_id)
    if not dept:
        flash('部门不存在', 'error')
        return redirect(url_for('admin.departments'))

    success, error = database.delete_department(dept_id)
    if success:
        flash('部门已删除', 'success')
    else:
        flash(error, 'error')
    
    return redirect(url_for('admin.departments'))


@admin_bp.route('/users')
@admin_required
def pending_users():
    """管理员 - 用户管理（显示所有用户）"""
    users = database.get_all_users()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    """管理员 - 审批通过用户"""
    user = database.get_user_by_id(user_id)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.pending_users'))

    if user['status'] != 'pending':
        flash('用户状态已变更', 'warning')
        return redirect(url_for('admin.pending_users'))

    database.approve_user(user_id)
    flash('用户已审批通过', 'success')
    return redirect(url_for('admin.pending_users'))


@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    """管理员 - 拒绝用户"""
    user = database.get_user_by_id(user_id)
    if not user:
        flash('用户不存在', 'error')
        return redirect(url_for('admin.pending_users'))

    if user['status'] != 'pending':
        flash('用户状态已变更', 'warning')
        return redirect(url_for('admin.pending_users'))

    database.reject_user(user_id)
    flash('用户已被拒绝', 'success')
    return redirect(url_for('admin.pending_users'))


@admin_bp.route('/recycle')
@admin_required
def recycle_bin():
    """管理员 - 回收站"""
    deleted_docs = database.get_deleted_documents()
    return render_template('admin/recycle.html', files=deleted_docs)


@admin_bp.route('/recycle/restore', methods=['POST'])
@admin_required
def restore_document():
    """管理员 - 恢复文档"""
    file_key = request.form.get('file_key')
    if not file_key:
        flash('参数错误', 'error')
        return redirect(url_for('admin.recycle_bin'))
    
    # 检查文档是否存在且已删除
    doc = database.get_document_by_key(file_key)
    if not doc or doc['status'] != 'deleted':
        flash('文档不存在或未被删除', 'error')
        return redirect(url_for('admin.recycle_bin'))
    
    # 检查是否存在同名文件
    if database.check_duplicate_filename(doc['filename'], doc['doc_type'], doc['dept_id']):
        flash(f'恢复失败：已存在同名文件 "{doc["filename"]}"', 'error')
        return redirect(url_for('admin.recycle_bin'))
    
    # 从回收站移回原位置
    success, error = oss_service.restore_from_recycle(file_key)
    if success:
        # 更新数据库状态为 pending（待处理）
        database.restore_document(file_key, status='pending')
        flash('文档已恢复，正在重新整理...', 'success')
        
        # 提交后台任务
        from .. import tasks
        tasks.submit_process_document(current_app._get_current_object(), file_key, doc['doc_type'], doc['dept_id'])
    else:
        flash(f'恢复失败: {error}', 'error')
    
    return redirect(url_for('admin.recycle_bin'))


@admin_bp.route('/recycle/delete', methods=['POST'])
@admin_required
def hard_delete_document():
    """管理员 - 彻底删除文档"""
    file_key = request.form.get('file_key')
    if not file_key:
        flash('参数错误', 'error')
        return redirect(url_for('admin.recycle_bin'))
    
    # 检查文档是否存在且已删除
    doc = database.get_document_by_key(file_key)
    if not doc or doc['status'] != 'deleted':
        flash('文档不存在或未被删除', 'error')
        return redirect(url_for('admin.recycle_bin'))
    
    # 从文件系统彻底删除
    success, error = oss_service.hard_delete_from_recycle(file_key)
    if success:
        # 从数据库删除
        database.hard_delete_document(file_key)
        flash('文档已彻底删除', 'success')
    else:
        flash(f'删除失败: {error}', 'error')
    
    return redirect(url_for('admin.recycle_bin'))




@admin_bp.route('/users/delete', methods=['POST'])
@admin_required
def delete_user():
    """管理员 - 删除用户"""
    user_id = request.form.get('user_id')
    if not user_id:
        flash('参数错误', 'error')
        return redirect(url_for('admin.pending_users'))
    
    user_id = int(user_id)
    
    # 不能删除自己
    if user_id == current_user.id:
        flash('不能删除当前登录用户', 'error')
        return redirect(url_for('admin.pending_users'))
    
    success, error = database.delete_user(user_id)
    if success:
        flash('用户已删除', 'success')
    else:
        flash(f'删除失败: {error}', 'error')
    
    return redirect(url_for('admin.pending_users'))
