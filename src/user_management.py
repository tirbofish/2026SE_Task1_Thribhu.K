import sqlite3 as sql
from logging import Logger
from flask import jsonify


def prepare(log: Logger):
    """Prepares the database by populating it with the required data.

    If any databases or data exist, it will not fail, just continue on.

    This is a transactional function, which can allow for rollbacks in case
    this app decides to think for itself.
    """

    conn = sql.connect("databaseFiles/mono.db")
    cur = conn.cursor()
    log.info("Created database file")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS devlogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time_user_logged REAL NOT NULL,
            name TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            description TEXT
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        """
    )

    conn.commit()
    conn.close()
    log.info("Committed!")


def fetch_devlogs():
    conn = sql.connect("databaseFiles/mono.db")
    conn.row_factory = sql.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM devlogs")
    rows = cur.fetchall()

    conn.close()

    return [dict(row) for row in rows]


def add_log(data, user_id):
    conn = sql.connect("databaseFiles/mono.db")
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO devlogs (time_user_logged, name, user_id, description)
        VALUES (?, ?, ?, ?)
        """,
        (
            data["time_user_logged"],
            data["name"],
            user_id,
            data.get("description"),
        ),
    )

    log_id = cur.lastrowid

    conn.commit()
    conn.close()

    return log_id


def remove_log(log_id):
    conn = sql.connect("databaseFiles/mono.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM devlogs WHERE id = ?", (log_id,))

    row_count = cur.rowcount

    if row_count != 0:
        conn.commit()
    conn.close()

    return row_count

def fetch_one_devlog(log_id):
    conn = sql.connect("databaseFiles/mono.db")
    conn.row_factory = sql.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM devlogs WHERE id = ?", (log_id,))
    row = cur.fetchone()
    
    conn.close()
    
    return dict(row) if row else None

def get_user_by_email(email):
    conn = sql.connect("databaseFiles/mono.db")
    conn.row_factory = sql.Row
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cur.fetchone()
    
    conn.close()
    
    return dict(row) if row else None