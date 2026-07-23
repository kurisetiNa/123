"""基于 SQLite 的轻量级本地用户认证服务。"""

import hashlib
import hmac
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from utils.path_tool import get_abs_path


DB_PATH = get_abs_path("data/users.db")
PBKDF2_ITERATIONS = 600_000


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def init_user_db() -> None:
    """创建用户表；重复调用不会覆盖已有数据。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with closing(_connect()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash BLOB NOT NULL,
                password_salt BLOB NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.commit()


def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )


def _public_user(database_id: int, username: str) -> dict:
    """返回安全的登录用户信息；用户名同时作为报告查询标识。"""
    return {"id": database_id, "username": username}


def register_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    """注册用户，返回（是否成功、提示信息、用户信息）。"""
    username = username.strip()
    if not 2 <= len(username) <= 32:
        return False, "用户名长度需要在 2～32 个字符之间。", None
    if not all(char.isalnum() or char == "_" for char in username):
        return False, "用户名只能包含中文、字母、数字和下划线。", None
    if not 6 <= len(password) <= 128:
        return False, "密码长度需要在 6～128 个字符之间。", None

    salt = os.urandom(16)
    password_hash = _hash_password(password, salt)

    try:
        with closing(_connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO users (username, password_hash, password_salt, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    password_hash,
                    salt,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
            user = _public_user(cursor.lastrowid, username)
    except sqlite3.IntegrityError:
        return False, "该用户名已经被注册。", None

    return True, "注册成功。", user


def authenticate_user(username: str, password: str) -> dict | None:
    """校验用户名和密码，成功时返回不含密码的用户信息。"""
    with closing(_connect()) as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, password_salt
            FROM users
            WHERE username = ?
            """,
            (username.strip(),),
        ).fetchone()

    if row is None:
        return None

    candidate_hash = _hash_password(password, row["password_salt"])
    if not hmac.compare_digest(candidate_hash, row["password_hash"]):
        return None

    return _public_user(row["id"], row["username"])
