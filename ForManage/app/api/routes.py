"""机器人 API 路由"""
import hmac
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Blueprint, request, jsonify, current_app
from .. import database
from ..utils import oss_service

api_bp = Blueprint('api', __name__)

# 定义北京时区
BEIJING_TZ = ZoneInfo('Asia/Shanghai')


@api_bp.route('/register', methods=['POST'])
def robot_register():
    """
    机器人注册接口
    
    请求体：
    {
        "hardware_fingerprint": "硬件指纹 SHA256",
        "model": "x86|arm|voice_module",
        "dept_id": 1  // 可选，部门ID
    }
    
    返回：
    {
        "device_id": "生成的 UUID",
        "update_key": "生成的更新密钥"
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体必须是 JSON'}), 400
    
    hardware_fingerprint = data.get('hardware_fingerprint')
    model = data.get('model')
    dept_id = data.get('dept_id')
    registered_by = data.get('registered_by')  # 注册负责人
    location = data.get('location')  # 地点
    
    # 参数校验
    if not hardware_fingerprint:
        return jsonify({'error': '缺少 hardware_fingerprint'}), 400
    
    if not model:
        return jsonify({'error': '缺少 model'}), 400
    
    # 验证 model 值
    valid_models = ['x86', 'arm', 'voice_module']
    if model not in valid_models:
        return jsonify({'error': f'model 必须是 {valid_models} 之一'}), 400
    
    # 获取客户端 IP
    registered_ip = request.remote_addr
    
    # 创建机器人（传入 dept_id）
    robot_id, device_id, update_key = database.create_robot(
        hardware_fingerprint=hardware_fingerprint,
        model=model,
        dept_id=dept_id,
        registered_ip=registered_ip,
        registered_by=registered_by,
        location=location
    )
    
    if robot_id is None:
        # 创建失败（指纹已存在）
        return jsonify({'error': update_key}), 409  # update_key 此时是错误信息
    
    return jsonify({
        'device_id': device_id,
        'update_key': update_key
    }), 201


@api_bp.route('/authenticate', methods=['POST'])
def robot_authenticate():
    """
    机器人认证接口
    
    请求体：
    {
        "device_id": "机器人 UUID",
        "update_key": "更新密钥"
    }
    
    返回：
    {
        "api_key": "百炼 API Key",
        "key_version": 版本号
    }
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体必须是 JSON'}), 400
    
    device_id = data.get('device_id')
    update_key = data.get('update_key')
    
    # 参数校验
    if not device_id:
        return jsonify({'error': '缺少 device_id'}), 400
    
    if not update_key:
        return jsonify({'error': '缺少 update_key'}), 400
    
    # 查找机器人
    robot = database.get_robot_by_device_id(device_id)
    if not robot:
        return jsonify({'error': '设备不存在'}), 404
    
    # 检查状态
    if robot['status'] != 'active':
        return jsonify({'error': '设备已禁用'}), 403
    
    # 验证 update_key（使用 hmac.compare_digest 防时序攻击）
    if not hmac.compare_digest(robot['update_key'], update_key):
        # 认证失败，增加失败次数
        database.increment_auth_failures(robot['id'])
        return jsonify({'error': 'update_key 错误'}), 401
    
    # 认证成功：更新最后在线时间，重置失败次数
    client_ip = request.remote_addr
    database.update_last_online(robot['id'], client_ip)
    database.reset_auth_failures(robot['id'])
    
    # 返回 api_key 和版本号
    # 注意：api_key 可能为空（管理员还未设置）
    return jsonify({
        'api_key': robot['api_key'] or '',
        'key_version': robot['api_key_version']
    }), 200


@api_bp.route('/check-update', methods=['GET'])
def robot_check_update():
    """
    检查更新接口（文档更新，批次模式）
    
    请求参数（query string）：
    - device_id: 机器人 UUID
    - update_key: 更新密钥
    
    返回：
    {
        "status": "wait" | "update",
        "message": "提示信息",
        "files": [...]  // 仅 status=update 时存在
    }
    """
    device_id = request.args.get('device_id')
    update_key = request.args.get('update_key')
    
    if not device_id or not update_key:
        return jsonify({'error': '缺少 device_id 或 update_key'}), 400
    
    # 查找机器人
    robot = database.get_robot_by_device_id(device_id)
    if not robot:
        return jsonify({'error': '设备不存在'}), 404
    
    # 检查状态
    if robot['status'] != 'active':
        return jsonify({'error': '设备已禁用'}), 403
    
    # 验证 update_key
    if not hmac.compare_digest(robot['update_key'], update_key):
        database.increment_auth_failures(robot['id'])
        return jsonify({'error': 'update_key 错误'}), 401
    
    # 认证成功，更新在线时间
    client_ip = request.remote_addr
    database.update_last_online(robot['id'], client_ip)
    database.reset_auth_failures(robot['id'])
    
    # 检查批次时间窗口
    batch_id = robot['batch_id']
    if not batch_id:
        return jsonify({
            'status': 'wait',
            'message': '未分配批次，无法更新'
        }), 200
    
    batch = database.get_batch(batch_id)
    if not batch:
        return jsonify({
            'status': 'wait',
            'message': '批次不存在'
        }), 200
    
    # 解析批次更新时间
    try:
        update_time_str = batch['update_time']  # 格式: "HH:MM:SS" 或 "HH:MM"
        update_hour, update_minute = map(int, update_time_str.split(':')[:2])
    except (ValueError, AttributeError):
        return jsonify({
            'status': 'wait',
            'message': '批次时间配置错误'
        }), 200
    
    # 获取当前北京时间
    now = datetime.now(BEIJING_TZ)
    current_hour = now.hour
    current_minute = now.minute
    
    # 调试日志
    current_app.logger.info(f"[check-update] 当前北京时间: {current_hour:02d}:{current_minute:02d}")
    current_app.logger.info(f"[check-update] 批次更新时间: {update_hour:02d}:{update_minute:02d}")
    current_app.logger.info(f"[check-update] 批次名称: {batch['name']}")
    
    # 计算时间差（分钟）
    current_total_minutes = current_hour * 60 + current_minute
    update_total_minutes = update_hour * 60 + update_minute
    
    # 处理跨天情况
    time_diff = abs(current_total_minutes - update_total_minutes)
    if time_diff > 12 * 60:  # 超过12小时，说明跨天了
        time_diff = 24 * 60 - time_diff
    
    current_app.logger.info(f"[check-update] 时间差: {time_diff} 分钟")
    
    # 检查是否在允许窗口内（默认 ±1 小时）
    tolerance_minutes = current_app.config['UPDATE_WINDOW_TOLERANCE_HOURS'] * 60
    current_app.logger.info(f"[check-update] 允许窗口: {tolerance_minutes} 分钟")
    
    if time_diff > tolerance_minutes:
        return jsonify({
            'status': 'wait',
            'message': f'未到更新时间，批次更新时间为 {update_time_str}'
        }), 200
    
    # 在时间窗口内，查询文档
    dept_id = robot['dept_id']
    
    # 查询公共文档
    public_docs = database.get_completed_public_documents()
    
    # 查询部门文档（如果有绑定部门）
    dept_docs = []
    if dept_id:
        dept_docs = database.get_completed_documents_by_dept(dept_id)
    
    # 生成 OSS 临时下载链接（使用处理后的文档）
    processed_prefix = current_app.config.get('OSS_PROCESSED_PREFIX', 'processed')
    
    public_files = []
    for doc in public_docs:
        # 构造 processed 目录的 file_key
        processed_key = f"{processed_prefix}/public/{doc['filename']}.md"
        download_url = oss_service.get_download_url(processed_key)
        if download_url:
            public_files.append({
                'filename': doc['filename'],
                'type': doc['doc_type'],
                'url': download_url
            })
    
    dept_files = []
    for doc in dept_docs:
        # 构造 processed 目录的 file_key
        processed_key = f"{processed_prefix}/dept-{dept_id}/{doc['filename']}.md"
        download_url = oss_service.get_download_url(processed_key)
        if download_url:
            dept_files.append({
                'filename': doc['filename'],
                'type': doc['doc_type'],
                'url': download_url
            })
    
    total_count = len(public_files) + len(dept_files)
    
    return jsonify({
        'status': 'update',
        'message': f'发现 {total_count} 个文档更新',
        'public_docs': public_files,
        'dept_docs': dept_files
    }), 200
