import sys
import os
import sqlite3
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app, jsonify
from flask_login import login_required, current_user
from . import oss_service
from .. import database

# 添加项目根目录到路径，以便导入 ai_agent
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


docs_bp = Blueprint('docs', __name__)


def _allowed_file(filename):
    """检查文件扩展名是否允许"""
    from flask import current_app
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def _extract_filename_from_key(object_key: str) -> str:
    """
    从 object_key 提取原始文件名（不含扩展名）
    
    object_key 格式：dept-1/1234567890_产品手册.pdf
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



@docs_bp.route('/public')
@login_required
def public_docs():
    """公共文档列表页"""
    files = database.get_documents_by_type('public')
    return render_template('docs/public.html', files=files)




@docs_bp.route('/api/docs/public/status')
@login_required
def public_docs_status_api():
    """API - 返回公共文档状态"""
    files = database.get_documents_by_type('public')
    result = [{'file_key': f['file_key'], 'status': f['status'], 'error_message': f['error_message']} for f in files]
    return jsonify(result)


@docs_bp.route('/api/docs/dept/status')
@login_required
def dept_docs_status_api():
    """API - 返回部门文档状态"""
    if not current_user.dept_id:
        return jsonify([])
    files = database.get_documents_by_type('dept', current_user.dept_id)
    result = [{'file_key': f['file_key'], 'status': f['status'], 'error_message': f['error_message']} for f in files]
    return jsonify(result)

@docs_bp.route('/dept/docs')
@login_required
def dept_docs():
    """部门文档列表页"""
    if not current_user.dept_id:
        flash('你还未分配部门', 'error')
        return redirect(url_for('docs.public_docs'))

    files = database.get_documents_by_type('dept', current_user.dept_id)
    return render_template('docs/dept.html', files=files, dept_name=current_user.dept_name)


@docs_bp.route('/dept/docs/upload', methods=['POST'])
@login_required
def upload_dept_doc():
    """上传部门文档（支持多文件）"""
    if not current_user.dept_id:
        flash('你还未分配部门', 'error')
        return redirect(url_for('docs.dept_docs'))

    files = request.files.getlist('file')
    if not files or all(not f.filename for f in files):
        flash('请选择文件', 'error')
        return redirect(url_for('docs.dept_docs'))

    prefix = f"dept-{current_user.dept_id}"
    app = current_app._get_current_object()
    
    success_count = 0
    fail_count = 0
    duplicate_count = 0
    
    for file in files:
        if not file or not file.filename:
            continue
        
        # 校验文件格式
        if not _allowed_file(file.filename):
            fail_count += 1
            continue
        
        # 提取文件名（用于检查同名）
        import os
        filename_without_ext = os.path.splitext(file.filename)[0]
        
        # 检查同名文件
        if database.check_duplicate_filename(filename_without_ext, 'dept', current_user.dept_id):
            duplicate_count += 1
            continue
        
        # 上传到 OSS
        import time
        timestamp = int(time.time())
        raw_prefix = current_app.config.get('OSS_RAW_PREFIX', 'raw')
        object_key = f"{raw_prefix}/{prefix}/{timestamp}_{file.filename}"
        success = oss_service.upload(file, object_key)
        if not success:
            fail_count += 1
            continue
        file_key = object_key
        
        # 提取文件名
        filename = _extract_filename_from_key(file_key)
        
        # 创建文档记录
        db_success, db_error = database.create_document(file_key, filename, 'dept', current_user.dept_id)
        if not db_success:
            fail_count += 1
            continue
        
        success_count += 1
        
        # 提交后台任务
        from .. import tasks
        tasks.submit_process_document(current_app._get_current_object(), file_key, 'dept', current_user.dept_id)
    
    # 汇总消息
    if success_count > 0:
        flash(f'成功上传 {success_count} 个文件，正在后台整理...', 'success')
    if duplicate_count > 0:
        flash(f'{duplicate_count} 个文件因重名未上传', 'warning')
    if fail_count > 0:
        flash(f'{fail_count} 个文件上传失败', 'error')
    
    return redirect(url_for('docs.dept_docs'))


@docs_bp.route('/dept/docs/delete', methods=['POST'])
@login_required
def delete_dept_doc():
    """删除部门文档（移入回收站）"""
    object_key = request.form.get('key')
    if not object_key:
        flash('参数错误', 'error')
        return redirect(url_for('docs.dept_docs'))

    # 验证文件属于当前部门
    raw_prefix = current_app.config.get('OSS_RAW_PREFIX', 'raw')
    prefix = f"{raw_prefix}/dept-{current_user.dept_id}/"
    if not object_key.startswith(prefix):
        flash('无权操作此文件', 'error')
        return redirect(url_for('docs.dept_docs'))

    # 检查 OSS 文件是否存在
    if not oss_service.exists(object_key):
        # OSS 文件不存在，彻底删除数据库记录（不进回收站）
        print(f"[数据检查] 删除时发现 OSS 文件不存在，彻底清理数据库记录：{object_key}")
        database.hard_delete_document(object_key)
        flash('文件已失效，已彻底清理记录', 'warning')
        return redirect(url_for('docs.dept_docs'))

    # 移动文件到回收站
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
            processed_key = f"{processed_prefix}/dept-{current_user.dept_id}/{filename}.md"
            oss_service.delete(processed_key)
            print(f"[OSS] 已删除处理后文档：{processed_key}")
        except Exception as e:
            print(f"[警告] 删除处理后文档失败：{e}")
    else:
        flash(error, 'error')
    return redirect(url_for('docs.dept_docs'))


@docs_bp.route('/download')
@login_required
def download():
    """下载文件"""
    object_key = request.args.get('key')
    if not object_key:
        flash('参数错误', 'error')
        return redirect(url_for('docs.public_docs'))

    # 检查 OSS 文件是否存在
    if not oss_service.exists(object_key):
        # OSS 文件不存在，彻底删除数据库记录
        print(f"[数据检查] 下载时发现 OSS 文件不存在，彻底清理数据库记录：{object_key}")
        database.hard_delete_document(object_key)
        flash('文件已失效或不存在，已自动清理记录', 'warning')
        return redirect(url_for('docs.public_docs'))
    
    # 获取下载链接
    url = oss_service.get_download_url(object_key)
    if url:
        return redirect(url)
    
    flash('获取下载链接失败', 'error')
    return redirect(url_for('docs.public_docs'))
