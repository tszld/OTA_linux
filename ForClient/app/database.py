import sqlite3
import os
from flask import g, current_app


def get_db():
    """获取数据库连接（每个请求一个连接）"""
    if 'db' not in g:
        db_path = os.path.join(current_app.root_path, '..', 'instance', 'app.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """初始化数据库：建表和种子数据"""
    db_path = os.path.join(app.root_path, '..', 'instance', 'app.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    
    # 建表
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'dept_admin',
            dept_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dept_id) REFERENCES departments(id)
        );
        
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_key TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            doc_type TEXT NOT NULL,
            dept_id INTEGER,
            status TEXT NOT NULL DEFAULT 'pending',
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP
        );
    ''')
    
    # 种子数据
    cursor = db.execute('SELECT COUNT(*) FROM departments')
    if cursor.fetchone()[0] == 0:
        # 创建测试部门
        db.execute('INSERT INTO departments (name) VALUES (?)', ('测试营业厅',))
        dept_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        
        # 创建 admin 用户（已审批）
        db.execute('INSERT INTO users (phone, role, status) VALUES (?, ?, ?)',
                   ('13800000000', 'admin', 'approved'))
        
        # 创建部门管理员（已审批）
        db.execute('INSERT INTO users (phone, role, dept_id, status) VALUES (?, ?, ?, ?)',
                   ('13900000001', 'dept_admin', dept_id, 'approved'))
        
        db.commit()
    
    db.close()


# 用户操作
def get_user_by_phone(phone):
    """根据手机号查询用户"""
    db = get_db()
    user = db.execute(
        'SELECT u.*, d.name as dept_name FROM users u LEFT JOIN departments d ON u.dept_id = d.id WHERE u.phone = ?',
        (phone,)
    ).fetchone()
    return user


def get_user_by_id(user_id):
    """根据 ID 查询用户"""
    db = get_db()
    user = db.execute(
        'SELECT u.*, d.name as dept_name FROM users u LEFT JOIN departments d ON u.dept_id = d.id WHERE u.id = ?',
        (user_id,)
    ).fetchone()
    return user


def register_user(phone, dept_id):
    """注册新用户（部门管理员）"""
    db = get_db()
    try:
        db.execute('INSERT INTO users (phone, role, dept_id, status) VALUES (?, ?, ?, ?)',
                   (phone, 'dept_admin', dept_id, 'pending'))
        db.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, '该手机号已注册'


def get_pending_users():
    """获取待审批用户列表"""
    db = get_db()
    return db.execute(
        'SELECT u.*, d.name as dept_name FROM users u LEFT JOIN departments d ON u.dept_id = d.id WHERE u.status = ? ORDER BY u.created_at DESC',
        ('pending',)
    ).fetchall()


def approve_user(user_id):
    """审批通过用户"""
    db = get_db()
    db.execute('UPDATE users SET status = ? WHERE id = ?', ('approved', user_id))
    db.commit()


def reject_user(user_id):
    """拒绝用户"""
    db = get_db()
    db.execute('UPDATE users SET status = ? WHERE id = ?', ('rejected', user_id))
    db.commit()


# 部门操作
def get_all_departments():
    """获取所有部门"""
    db = get_db()
    return db.execute('SELECT * FROM departments ORDER BY created_at DESC').fetchall()


def get_department(dept_id):
    """获取单个部门"""
    db = get_db()
    return db.execute('SELECT * FROM departments WHERE id = ?', (dept_id,)).fetchone()


def create_department(name):
    """创建部门"""
    db = get_db()
    try:
        db.execute('INSERT INTO departments (name) VALUES (?)', (name,))
        db.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, '部门名称已存在'


def delete_department(dept_id):
    """删除部门"""
    db = get_db()
    # 检查是否有用户关联
    cursor = db.execute('SELECT COUNT(*) FROM users WHERE dept_id = ?', (dept_id,))
    if cursor.fetchone()[0] > 0:
        return False, '该部门下还有用户，无法删除'
    
    db.execute('DELETE FROM departments WHERE id = ?', (dept_id,))
    db.commit()
    return True, None


# 文档操作
def check_duplicate_filename(filename, doc_type, dept_id=None):
    """检查是否存在同名文件（非删除状态）"""
    db = get_db()
    if dept_id is not None:
        row = db.execute(
            'SELECT id FROM documents WHERE filename = ? AND doc_type = ? AND dept_id = ? AND status != ?',
            (filename, doc_type, dept_id, 'deleted')
        ).fetchone()
    else:
        row = db.execute(
            'SELECT id FROM documents WHERE filename = ? AND doc_type = ? AND status != ?',
            (filename, doc_type, 'deleted')
        ).fetchone()
    return row is not None


def create_document(file_key, filename, doc_type, dept_id=None):
    """创建文档记录"""
    db = get_db()
    try:
        db.execute(
            'INSERT INTO documents (file_key, filename, doc_type, dept_id, status) VALUES (?, ?, ?, ?, ?)',
            (file_key, filename, doc_type, dept_id, 'pending')
        )
        db.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, '文档已存在'


def update_document_status(file_key, status, error_message=None):
    """更新文档状态"""
    db = get_db()
    db.execute(
        'UPDATE documents SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP WHERE file_key = ?',
        (status, error_message, file_key)
    )
    db.commit()


def get_documents_by_type(doc_type, dept_id=None, include_deleted=False):
    """获取指定类型的文档列表"""
    db = get_db()
    
    if include_deleted:
        if dept_id is not None:
            return db.execute(
                'SELECT * FROM documents WHERE doc_type = ? AND dept_id = ? ORDER BY created_at DESC',
                (doc_type, dept_id)
            ).fetchall()
        else:
            return db.execute(
                'SELECT * FROM documents WHERE doc_type = ? ORDER BY created_at DESC',
                (doc_type,)
            ).fetchall()
    else:
        if dept_id is not None:
            return db.execute(
                'SELECT * FROM documents WHERE doc_type = ? AND dept_id = ? AND status != ? ORDER BY created_at DESC',
                (doc_type, dept_id, 'deleted')
            ).fetchall()
        else:
            return db.execute(
                'SELECT * FROM documents WHERE doc_type = ? AND status != ? ORDER BY created_at DESC',
                (doc_type, 'deleted')
            ).fetchall()


def get_document_by_key(file_key):
    """根据 file_key 获取文档"""
    db = get_db()
    return db.execute(
        'SELECT * FROM documents WHERE file_key = ?',
        (file_key,)
    ).fetchone()


def soft_delete_document(file_key):
    """软删除文档，返回是否成功"""
    db = get_db()
    cursor = db.execute(
        'UPDATE documents SET status = ?, deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE file_key = ?',
        ('deleted', file_key)
    )
    db.commit()
    return cursor.rowcount > 0

def get_deleted_documents():
    """获取所有已删除的文档"""
    db = get_db()
    return db.execute(
        'SELECT * FROM documents WHERE status = ? ORDER BY deleted_at DESC',
        ('deleted',)
    ).fetchall()


def restore_document(file_key, status='completed'):
    """恢复文档（可指定状态，默认为 completed）"""
    db = get_db()
    db.execute(
        'UPDATE documents SET status = ?, deleted_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE file_key = ?',
        (status, file_key)
    )
    db.commit()


def hard_delete_document(file_key):
    """彻底删除文档（从数据库删除）"""
    db = get_db()
    db.execute('DELETE FROM documents WHERE file_key = ?', (file_key,))
    db.commit()








def get_all_users():
    """获取所有用户（包括已审批和待审批）"""
    db = get_db()
    return db.execute(
        'SELECT u.*, d.name as dept_name FROM users u LEFT JOIN departments d ON u.dept_id = d.id ORDER BY u.created_at DESC'
    ).fetchall()


def delete_user(user_id):
    """删除用户"""
    db = get_db()
    try:
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        return True, None
    except Exception as e:
        return False, str(e)
