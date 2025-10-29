import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path='chatbot_admin.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database if it doesn't exist"""
        if not os.path.exists(self.db_path):
            from init_db import init_database
            init_database()
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    # Admin Management Methods
    def get_all_admins(self):
        """Get all admin users"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, created_at, last_login, is_active
                FROM admins
                WHERE is_active = 1
                ORDER BY created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_admin_by_username(self, username):
        """Get admin by username"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, created_at, last_login, is_active
                FROM admins
                WHERE username = ? AND is_active = 1
            ''', (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_admin(self, username, password):
        """Create new admin user"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                password_hash = generate_password_hash(password)
                cursor.execute('''
                    INSERT INTO admins (username, password_hash, created_at)
                    VALUES (?, ?, ?)
                ''', (username, password_hash, datetime.now().isoformat()))
                conn.commit()
                return {"status": "success", "message": f"Admin '{username}' berhasil ditambahkan"}
        except sqlite3.IntegrityError:
            return {"status": "error", "message": "Username sudah ada"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    def delete_admin(self, username):
        """Delete admin user (soft delete)"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Check if admin exists
                admin = self.get_admin_by_username(username)
                if not admin:
                    return {"status": "error", "message": "Admin tidak ditemukan"}
                
                # Check if it's the last active admin
                cursor.execute('SELECT COUNT(*) FROM admins WHERE is_active = 1')
                if cursor.fetchone()[0] <= 1:
                    return {"status": "error", "message": "Tidak dapat menghapus admin terakhir"}
                
                # Soft delete
                cursor.execute('''
                    UPDATE admins
                    SET is_active = 0
                    WHERE username = ?
                ''', (username,))
                conn.commit()
                return {"status": "success", "message": f"Admin '{username}' berhasil dihapus"}
        except Exception as e:
            return {"status": "error", "message": f"Error: {str(e)}"}
    
    def verify_admin_credentials(self, username, password):
        """Verify admin login credentials"""
        admin = self.get_admin_by_username(username)
        if admin and check_password_hash(admin['password_hash'], password):
            # Update last login
            self.update_last_login(admin['id'])
            return admin
        return None
    
    def update_last_login(self, admin_id):
        """Update last login timestamp"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE admins
                SET last_login = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), admin_id))
            conn.commit()
    
    def get_admin_count(self):
        """Get total number of active admins"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM admins WHERE is_active = 1')
            return cursor.fetchone()[0]
    
    # Activity Logging Methods
    def log_activity(self, admin_id, action, description=None, ip_address=None):
        """Log admin activity"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO activity_logs (admin_id, action, description, ip_address, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (admin_id, action, description, ip_address, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            print(f"Error logging activity: {e}")
    
    def get_recent_activities(self, limit=10):
        """Get recent admin activities"""
        with self.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    al.action,
                    al.description,
                    al.created_at,
                    al.ip_address,
                    a.username
                FROM activity_logs al
                LEFT JOIN admins a ON al.admin_id = a.id
                ORDER BY al.created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Session Management Methods
    def create_session(self, session_id, admin_id, ip_address=None, user_agent=None):
        """Create admin session record"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
                cursor.execute('''
                    INSERT INTO admin_sessions (session_id, admin_id, expires_at, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session_id, admin_id, expires_at, ip_address, user_agent))
                conn.commit()
        except Exception as e:
            print(f"Error creating session: {e}")
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        try:
            with self.get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM admin_sessions
                    WHERE expires_at < ?
                ''', (datetime.now().isoformat(),))
                conn.commit()
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")

# Global database instance
db_manager = DatabaseManager()