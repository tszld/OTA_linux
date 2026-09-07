"""管理员 Web 路由"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required
from .. import database

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/robots')
@login_required
def robot_list():
    """机器人列表页"""
    robots = database.get_all_robots()
    batches = database.get_all_batches()
    departments = database.get_all_departments()
    
    # 计算在线状态
    threshold = datetime.now() - timedelta(minutes=current_app.config['ONLINE_THRESHOLD_MINUTES'])
    robot_data = []
    for robot in robots:
        is_online = False
        if robot['last_online_at']:
            try:
                last_online = datetime.strptime(robot['last_online_at'], '%Y-%m-%d %H:%M:%S')
                is_online = last_online > threshold
            except (ValueError, TypeError):
                pass
        
        robot_data.append({
            **dict(robot),
            'is_online': is_online
        })
    
    return render_template('admin/robots.html', robots=robot_data, batches=batches, departments=departments)


@admin_bp.route('/robots/<int:robot_id>/toggle', methods=['POST'])
@login_required
def robot_toggle_status(robot_id):
    """切换机器人状态"""
    robot = database.get_robot_by_id(robot_id)
    if not robot:
        flash('机器人不存在', 'error')
        return redirect(url_for('admin.robot_list'))
    
    new_status = 'disabled' if robot['status'] == 'active' else 'active'
    database.update_robot_status(robot_id, new_status)
    
    status_text = '已启用' if new_status == 'active' else '已禁用'
    flash(f'机器人 {robot["device_id"][:8]}... {status_text}', 'success')
    return redirect(url_for('admin.robot_list'))


@admin_bp.route('/robots/<int:robot_id>/reset-update-key', methods=['POST'])
@login_required
def robot_reset_update_key(robot_id):
    """重置 update_key"""
    robot = database.get_robot_by_id(robot_id)
    if not robot:
        flash('机器人不存在', 'error')
        return redirect(url_for('admin.robot_list'))
    
    new_key = database.reset_update_key(robot_id)
    flash(f'update_key 已重置，新密钥：{new_key}', 'success')
    return redirect(url_for('admin.robot_list'))


@admin_bp.route('/robots/<int:robot_id>/reset-api-key', methods=['POST'])
@login_required
def robot_reset_api_key(robot_id):
    """重置 api_key"""
    robot = database.get_robot_by_id(robot_id)
    if not robot:
        flash('机器人不存在', 'error')
        return redirect(url_for('admin.robot_list'))
    
    # 从表单获取新 api_key，如果为空则自动生成
    new_api_key = request.form.get('api_key', '').strip()
    if not new_api_key:
        import secrets
        new_api_key = f'sk-{secrets.token_hex(16)}'
    
    database.reset_api_key(robot_id, new_api_key)
    
    # 获取新的版本号
    updated_robot = database.get_robot_by_id(robot_id)
    flash(f'api_key 已重置，新密钥：{new_api_key}，版本号：{updated_robot["api_key_version"]}', 'success')
    return redirect(url_for('admin.robot_list'))


@admin_bp.route('/robots/<int:robot_id>/assign-batch', methods=['POST'])
@login_required
def robot_assign_batch(robot_id):
    """分配批次"""
    robot = database.get_robot_by_id(robot_id)
    if not robot:
        flash('机器人不存在', 'error')
        return redirect(url_for('admin.robot_list'))
    
    batch_id = request.form.get('batch_id')
    if batch_id:
        batch_id = int(batch_id)
        # 验证批次存在
        batch = database.get_batch(batch_id)
        if not batch:
            flash('批次不存在', 'error')
            return redirect(url_for('admin.robot_list'))
    
    # 更新机器人的批次
    database.assign_batch(robot_id, batch_id if batch_id else None)
    flash(f'机器人 {robot["device_id"][:8]}... 批次已更新', 'success')
    return redirect(url_for('admin.robot_list'))


# ============ 批次管理 ============

@admin_bp.route('/batches')
@login_required
def batch_list():
    """批次管理页"""
    batches = database.get_all_batches()
    departments = database.get_all_departments()
    
    # 计算每个批次的机器人数
    batch_data = []
    for batch in batches:
        robot_count = database.get_robots_by_batch(batch['id'])
        batch_data.append({
            **dict(batch),
            'robot_count': len(robot_count)
        })
    
    return render_template('admin/batches.html', batches=batch_data)


@admin_bp.route('/batches/create', methods=['POST'])
@login_required
def batch_create():
    """创建批次"""
    name = request.form.get('name', '').strip()
    update_time = request.form.get('update_time', '').strip()
    
    if not name or not update_time:
        flash('请填写完整信息', 'error')
        return redirect(url_for('admin.batch_list'))
    
    batch_id, error = database.create_batch(name, update_time)
    if error:
        flash(error, 'error')
    else:
        flash(f'批次 "{name}" 创建成功', 'success')
    
    return redirect(url_for('admin.batch_list'))


@admin_bp.route('/batches/<int:batch_id>/delete', methods=['POST'])
@login_required
def batch_delete(batch_id):
    """删除批次"""
    batch = database.get_batch(batch_id)
    if not batch:
        flash('批次不存在', 'error')
        return redirect(url_for('admin.batch_list'))
    
    success, error = database.delete_batch(batch_id)
    if success:
        flash(f'批次 "{batch["name"]}" 已删除', 'success')
    else:
        flash(error, 'error')
    
    return redirect(url_for('admin.batch_list'))


@admin_bp.route('/robots/<int:robot_id>/delete', methods=['POST'])
@login_required
def robot_delete(robot_id):
    """删除机器人"""
    robot = database.get_robot_by_id(robot_id)
    if not robot:
        flash('机器人不存在', 'error')
        return redirect(url_for('admin.robot_list'))
    
    database.delete_robot(robot_id)
    flash(f'机器人 {robot["device_id"][:8]}... 已删除', 'success')
    return redirect(url_for('admin.robot_list'))


@admin_bp.route('/robots/<int:robot_id>/assign-dept', methods=['POST'])
@login_required
def robot_assign_dept(robot_id):
    """分配部门"""
    robot = database.get_robot_by_id(robot_id)
    if not robot:
        flash('机器人不存在', 'error')
        return redirect(url_for('admin.robot_list'))
    
    dept_id = request.form.get('dept_id')
    if dept_id:
        dept_id = int(dept_id)
    
    db = database.get_db()
    db.execute('UPDATE robots SET dept_id = ? WHERE id = ?', (dept_id, robot_id))
    db.commit()
    
    flash(f'机器人 {robot["device_id"][:8]}... 部门已更新', 'success')
    return redirect(url_for('admin.robot_list'))
