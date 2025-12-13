import sqlite3 as sql
from logging import Logger
from flask import jsonify
from shared import DB_PATH
import json


def prepare(log: Logger):
    """Prepares the database by populating it with the required data.

    If any databases or data exist, it will not fail, just continue on.

    This is a transactional function, which can allow for rollbacks in case
    this app decides to think for itself.
    """

    conn = sql.connect(DB_PATH)
    cur = conn.cursor()
    log.info("Connected to database")
    
    try:
        cur.execute("PRAGMA foreign_keys = ON;")
        
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                totp_secret TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_login DATETIME
            );
            """
        )
        log.info("Users table ready")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                repository_url TEXT,
                created_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                description TEXT,
                FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """
        )
        log.info("Projects table ready")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS log_entries (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                log_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                time_worked_minutes INTEGER NOT NULL,
                developer_notes TEXT NOT NULL,
                related_commits TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            );
            """
        )
        log.info("Log entries table ready")

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_log_entries_user 
            ON log_entries(user_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_log_entries_project 
            ON log_entries(project_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_log_entries_timestamp 
            ON log_entries(log_timestamp);
            """
        )
        log.info("Indexes created")

        conn.commit()
        log.info("Database schema committed successfully")
        
    except sql.Error as e:
        conn.rollback()
        log.error(f"Database preparation failed: {e}")
        raise
    
    finally:
        conn.close()
        log.info("Database connection closed")



def fetch_devlogs(user_id=None, project_id=None):
    """Fetch all log entries, optionally filtered by user_id and/or project_id"""
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    query = """
        SELECT 
            l.log_id,
            l.user_id,
            u.username,
            l.project_id,
            p.project_name,
            l.start_time,
            l.end_time,
            l.log_timestamp,
            l.time_worked_minutes,
            p.repository_url,
            l.developer_notes,
            l.related_commits
        FROM log_entries l
        JOIN users u ON l.user_id = u.user_id
        JOIN projects p ON l.project_id = p.project_id
    """
    
    conditions = []
    params = []
    
    if user_id:
        conditions.append("l.user_id = ?")
        params.append(user_id)
    
    if project_id:
        conditions.append("l.project_id = ?")
        params.append(project_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY l.log_timestamp DESC"
    
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def add_log(data, user_id):
    """Add a new log entry with project information"""
    conn = sql.connect(DB_PATH)
    cur = conn.cursor()

    try:
        project_id = data.get("project_id")
        
        if not project_id:
            project_name = data.get("project_name")
            if not project_name:
                raise ValueError("Either project_id or project_name is required")
            
            cur.execute(
                """
                INSERT INTO projects (project_name, repository_url, created_by)
                VALUES (?, ?, ?)
                """,
                (project_name, data.get("repository_url"), user_id)
            )
            project_id = cur.lastrowid

        related_commits = data.get("related_commits")
        if related_commits:
            if isinstance(related_commits, list):
                related_commits = json.dumps(related_commits)
            elif isinstance(related_commits, str):
                try:
                    json.loads(related_commits)
                except json.JSONDecodeError:
                    related_commits = None
        else:
            related_commits = None

        cur.execute(
            """
            INSERT INTO log_entries (
                user_id, project_id, start_time, end_time, 
                time_worked_minutes, developer_notes, related_commits
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                project_id,
                data["start_time"],
                data["end_time"],
                data["time_worked_minutes"],
                data.get("developer_notes", ""),
                related_commits,
            ),
        )

        log_id = cur.lastrowid
        conn.commit()
        return log_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def remove_log(log_id, user_id=None):
    """Remove a log entry, optionally verify ownership"""
    conn = sql.connect(DB_PATH)
    cur = conn.cursor()

    if user_id:
        cur.execute(
            "DELETE FROM log_entries WHERE log_id = ? AND user_id = ?",
            (log_id, user_id)
        )
    else:
        cur.execute("DELETE FROM log_entries WHERE log_id = ?", (log_id,))

    row_count = cur.rowcount

    if row_count != 0:
        conn.commit()
    conn.close()

    return row_count


def fetch_one_devlog(log_id, user_id=None):
    """Fetch a single log entry with joined data"""
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    if user_id:
        cur.execute("""
            SELECT 
                l.log_id,
                l.user_id,
                u.username,
                l.project_id,
                p.project_name,
                l.start_time,
                l.end_time,
                l.log_timestamp,
                l.time_worked_minutes,
                p.repository_url,
                l.developer_notes,
                l.related_commits
            FROM log_entries l
            JOIN users u ON l.user_id = u.user_id
            JOIN projects p ON l.project_id = p.project_id
            WHERE l.log_id = ? AND l.user_id = ?
        """, (log_id, user_id))
    else:
        cur.execute("""
            SELECT 
                l.log_id,
                l.user_id,
                u.username,
                l.project_id,
                p.project_name,
                l.start_time,
                l.end_time,
                l.log_timestamp,
                l.time_worked_minutes,
                p.repository_url,
                l.developer_notes,
                l.related_commits
            FROM log_entries l
            JOIN users u ON l.user_id = u.user_id
            JOIN projects p ON l.project_id = p.project_id
            WHERE l.log_id = ?
        """, (log_id,))
    
    row = cur.fetchone()
    conn.close()

    return dict(row) if row else None


def get_user_by_email(email):
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()

    conn.close()

    return dict(row) if row else None


def update_log(log_id, data, user_id):
    """Update an existing log entry"""
    conn = sql.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute(
            "SELECT log_id FROM log_entries WHERE log_id = ? AND user_id = ?",
            (log_id, user_id)
        )
        if not cur.fetchone():
            return 0

        update_fields = []
        params = []

        if 'start_time' in data:
            update_fields.append("start_time = ?")
            params.append(data['start_time'])

        if 'end_time' in data:
            update_fields.append("end_time = ?")
            params.append(data['end_time'])

        if 'time_worked_minutes' in data:
            update_fields.append("time_worked_minutes = ?")
            params.append(data['time_worked_minutes'])

        if 'developer_notes' in data:
            update_fields.append("developer_notes = ?")
            params.append(data['developer_notes'])

        if 'project_id' in data:
            update_fields.append("project_id = ?")
            params.append(data['project_id'])

        if 'related_commits' in data:
            import json
            related_commits = data['related_commits']
            if isinstance(related_commits, list):
                related_commits = json.dumps(related_commits)
            elif isinstance(related_commits, str):
                try:
                    json.loads(related_commits)
                except json.JSONDecodeError:
                    related_commits = None
            update_fields.append("related_commits = ?")
            params.append(related_commits)

        if not update_fields:
            return 0

        params.append(log_id)
        params.append(user_id)

        query = f"UPDATE log_entries SET {', '.join(update_fields)} WHERE log_id = ? AND user_id = ?"
        cur.execute(query, params)

        row_count = cur.rowcount
        conn.commit()
        return row_count
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def fetch_projects(user_id=None):
    """Fetch all projects, optionally filtered by creator"""
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    cur = conn.cursor()

    if user_id:
        cur.execute("""
            SELECT 
                project_id,
                project_name,
                repository_url,
                created_by,
                created_at,
                description
            FROM projects
            WHERE created_by = ?
            ORDER BY created_at DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT 
                project_id,
                project_name,
                repository_url,
                created_by,
                created_at,
                description
            FROM projects
            ORDER BY created_at DESC
        """)
    
    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def create_project(project_name, user_id, repository_url=None, description=None):
    """Create a new project"""
    conn = sql.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO projects (project_name, repository_url, created_by, description)
            VALUES (?, ?, ?, ?)
            """,
            (project_name, repository_url, user_id, description)
        )
        
        project_id = cur.lastrowid
        conn.commit()
        return project_id
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
