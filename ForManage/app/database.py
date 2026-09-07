"""数据库操作模块

管理 robots 和 batches 表，复用 ForClient 的 users/departments 数据。
"""
import sqlite3
import uuid
import secrets
from flask import g, current_app


def get_db():
    """获取数据库连接（每个请求一个连接）"""
    if 'db' not in g:
        db_path = current_app.config['DB_PATH']
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """初始化数据库：创建 robots 和 batches 表"""
    db_path = app.config['DB_PATH']
    
    # 确保目录存在
    import os
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    
    # 创建 robots 表
    db.executescript('''
        CREATE TABLE IF NOT EXISTS robots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            hardware_fingerprint TEXT UNIQUE NOT NULL,
            update_key TEXT NOT NULL,
            api_key TEXT,
            api_key_version INTEGER DEFAULT 1,
            model TEXT NOT NULL,
            dept_id INTEGER,
            batch_id INTEGER,
            last_online_at TIMESTAMP,
            last_auth_ip TEXT,
            auth_failures INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            registered_ip TEXT,
            registered_by TEXT,
            location TEXT,
            FOREIGN KEY (dept_id) REFERENCES departments(id),
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        );
        
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            update_time TIME NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    db.commit()
    db.close()
    print(f"[数据库] 初始化完成: {db_path}")


# ============ 部门查询（复用 ForClient 数据） ============

def get_all_departments():
    """获取所有部门"""
    db = get_db()
    return db.execute('SELECT * FROM departments ORDER BY created_at DESC').fetchall()


def get_department(dept_id):
    """获取单个部门"""
    db = get_db()
    return db.execute('SELECT * FROM departments WHERE id = ?', (dept_id,)).fetchone()


# ============ 用户查询（复用 ForClient 数据） ============

def get_user_by_id(user_id):
    """根据 ID 查询用户"""
    db = get_db()
    return db.execute(
        'SELECT u.*, d.name as dept_name FROM users u LEFT JOIN departments d ON u.dept_id = d.id WHERE u.id = ?',
        (user_id,)
    ).fetchone()


# ============ 机器人 CRUD ============

def create_robot(hardware_fingerprint, model, dept_id=None, batch_id=None, registered_ip=None, registered_by=None, location=None):
    """
    创建机器人
    :return: (robot_id, device_id, update_key) 或 (None, None, error_msg)
    """
    db = get_db()
    device_id = str(uuid.uuid4())
    update_key = secrets.token_hex(32)
    
    try:
        cursor = db.execute(
            '''INSERT INTO robots 
               (device_id, hardware_fingerprint, update_key, model, dept_id, batch_id, registered_ip, registered_by, location)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (device_id, hardware_fingerprint, update_key, model, dept_id, batch_id, registered_ip, registered_by, location)
        )
        db.commit()
        return cursor.lastrowid, device_id, update_key
    except sqlite3.IntegrityError as e:
        return None, None, f'硬件指纹已存在: {e}'


def get_all_robots():
    """获取所有机器人（含部门和批次信息）"""
    db = get_db()
    return db.execute('''
        SELECT r.*, d.name as dept_name, b.name as batch_name, b.update_time
        FROM robots r
        LEFT JOIN departments d ON r.dept_id = d.id
        LEFT JOIN batches b ON r.batch_id = b.id
        ORDER BY r.registered_at DESC
    ''').fetchall()


def get_robot_by_id(robot_id):
    """根据 ID 获取机器人"""
    db = get_db()
    return db.execute('''
        SELECT r.*, d.name as dept_name, b.name as batch_name
        FROM robots r
        LEFT JOIN departments d ON r.dept_id = d.id
        LEFT JOIN batches b ON r.batch_id = b.id
        WHERE r.id = ?
    ''', (robot_id,)).fetchone()


def get_robot_by_device_id(device_id):
    """根据 device_id 获取机器人"""
    db = get_db()
    return db.execute('SELECT * FROM robots WHERE device_id = ?', (device_id,)).fetchone()


def get_robot_by_fingerprint(fingerprint):
    """根据硬件指纹获取机器人"""
    db = get_db()
    return db.execute('SELECT * FROM robots WHERE hardware_fingerprint = ?', (fingerprint,)).fetchone()


def update_robot_status(robot_id, status):
    """更新机器人状态"""
    db = get_db()
    db.execute('UPDATE robots SET status = ? WHERE id = ?', (status, robot_id))
    db.commit()


def reset_update_key(robot_id):
    """重置 update_key"""
    db = get_db()
    new_key = secrets.token_hex(32)
    db.execute('UPDATE robots SET update_key = ? WHERE id = ?', (new_key, robot_id))
    db.commit()
    return new_key


def reset_api_key(robot_id, new_api_key):
    """重置 API Key 并增加版本号"""
    db = get_db()
    db.execute(
        'UPDATE robots SET api_key = ?, api_key_version = api_key_version + 1 WHERE id = ?',
        (new_api_key, robot_id)
    )
    db.commit()


def update_last_online(robot_id, ip=None):
    """更新最后在线时间"""
    db = get_db()
    if ip:
        db.execute(
            'UPDATE robots SET last_online_at = CURRENT_TIMESTAMP, last_auth_ip = ? WHERE id = ?',
            (ip, robot_id)
        )
    else:
        db.execute(
            'UPDATE robots SET last_online_at = CURRENT_TIMESTAMP WHERE id = ?',
            (robot_id,)
        )
    db.commit()


def increment_auth_failures(robot_id):
    """增加认证失败次数"""
    db = get_db()
    db.execute('UPDATE robots SET auth_failures = auth_failures + 1 WHERE id = ?', (robot_id,))
    db.commit()


def reset_auth_failures(robot_id):
    """重置认证失败次数"""
    db = get_db()
    db.execute('UPDATE robots SET auth_failures = 0 WHERE id = ?', (robot_id,))
    db.commit()


# ============ 批次 CRUD ============

def create_batch(name, update_time):
    """创建批次"""
    db = get_db()
    try:
        cursor = db.execute(
            'INSERT INTO batches (name, update_time) VALUES (?, ?)',
            (name, update_time)
        )
        db.commit()
        return cursor.lastrowid, None
    except sqlite3.IntegrityError:
        return None, '批次名称已存在'


def get_all_batches():
    """获取所有批次"""
    db = get_db()
    return db.execute('SELECT * FROM batches ORDER BY update_time ASC').fetchall()


def get_batch(batch_id):
    """获取单个批次"""
    db = get_db()
    return db.execute('SELECT * FROM batches WHERE id = ?', (batch_id,)).fetchone()


def delete_batch(batch_id):
    """删除批次"""
    db = get_db()
    # 检查是否有机器人关联
    cursor = db.execute('SELECT COUNT(*) FROM robots WHERE batch_id = ?', (batch_id,))
    if cursor.fetchone()[0] > 0:
        return False, '该批次下还有机器人，无法删除'
    
    db.execute('DELETE FROM batches WHERE id = ?', (batch_id,))
    db.commit()
    return True, None


def assign_batch(robot_id, batch_id):
    """分配批次"""
    db = get_db()
    db.execute('UPDATE robots SET batch_id = ? WHERE id = ?', (batch_id, robot_id))
    db.commit()


def get_robots_by_batch(batch_id):
    """获取批次下的所有机器人"""
    db = get_db()
    return db.execute('SELECT * FROM robots WHERE batch_id = ?', (batch_id,)).fetchall()


def get_completed_documents_by_dept(dept_id):
    """获取部门下已完成的文档列表"""
    db = get_db()
    return db.execute(
        'SELECT * FROM documents WHERE dept_id = ? AND status = ? ORDER BY created_at DESC',
        (dept_id, 'completed')
    ).fetchall()


def get_completed_public_documents():
    """获取已完成的公共文档列表"""
    db = get_db()
    return db.execute(
        'SELECT * FROM documents WHERE doc_type = ? AND status = ? ORDER BY created_at DESC',
        ('public', 'completed')
    ).fetchall()


def delete_robot(robot_id):
    """删除机器人"""
    db = get_db()
    db.execute('DELETE FROM robots WHERE id = ?', (robot_id,))
    db.commit()
