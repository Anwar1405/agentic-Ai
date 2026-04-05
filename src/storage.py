import os
import json
import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Any, Dict, List, Tuple


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def db_path() -> str:
    return os.path.join(_project_root(), "agridss.db")


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                processed_at TEXT,
                officer_action_at TEXT,
                officer_decision TEXT,
                officer_comment TEXT,
                farmer_data_json TEXT NOT NULL,
                agent_results_json TEXT,
                ai_decision_json TEXT
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL,
                mobile TEXT,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TEXT NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(application_id) REFERENCES applications(application_id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )

        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                role TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(email) REFERENCES users(email)
            )
            """
        )
        con.commit()

    _ensure_demo_users()


def _hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return dk.hex()


def _ensure_demo_users() -> None:
    demo = [
        ("admin@agridss.gov.in", "System Admin", "admin", "admin123"),
        ("officer@agridss.gov.in", "Agriculture Officer", "officer", "officer123"),
        ("farmer", "Farmer User", "farmer", "farmer123"),
    ]

    with connect() as con:
        for email, name, role, password in demo:
            cur = con.execute("SELECT email FROM users WHERE email = ?", (email,))
            if cur.fetchone() is not None:
                continue
            salt_hex = secrets.token_bytes(16).hex()
            pw_hash = _hash_password(password, salt_hex)
            con.execute(
                "INSERT INTO users(email, name, role, salt, password_hash) VALUES (?, ?, ?, ?, ?)",
                (email, name, role, salt_hex, pw_hash),
            )
        con.commit()


def verify_user(email: str, password: str) -> Optional[Dict[str, str]]:
    with connect() as con:
        row = con.execute("SELECT email, name, role, salt, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            return None
        if _hash_password(password, row["salt"]) != row["password_hash"]:
            return None
        return {"email": row["email"], "name": row["name"], "role": row["role"]}


def create_session(email: str, role: str, ttl_seconds: int = 60 * 60 * 12) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now.timestamp() + ttl_seconds
    expires_at = datetime.fromtimestamp(expires).isoformat()
    with connect() as con:
        con.execute(
            "INSERT INTO sessions(token, email, role, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (token, email, role, now.isoformat(), expires_at),
        )
        con.commit()
    return token


def get_session(token: str) -> Optional[Dict[str, str]]:
    with connect() as con:
        row = con.execute(
            "SELECT token, email, role, created_at, expires_at FROM sessions WHERE token = ?",
            (token,),
        ).fetchone()
        if row is None:
            return None
        # Expiry check
        try:
            if datetime.fromisoformat(row["expires_at"]) < datetime.now():
                con.execute("DELETE FROM sessions WHERE token = ?", (token,))
                con.commit()
                return None
        except Exception:
            return None
        return {"email": row["email"], "role": row["role"]}


def delete_session(token: str) -> None:
    with connect() as con:
        con.execute("DELETE FROM sessions WHERE token = ?", (token,))
        con.commit()


def list_users() -> List[Dict[str, str]]:
    with connect() as con:
        rows = con.execute("SELECT email, name, role FROM users ORDER BY role, email").fetchall()
        return [{"email": r["email"], "name": r["name"], "role": r["role"]} for r in rows]


def create_application(application_id: str, farmer_data: Dict[str, Any]) -> None:
    now = datetime.now().isoformat()
    with connect() as con:
        con.execute(
            """
            INSERT INTO applications(
                application_id, status, submitted_at, farmer_data_json
            ) VALUES (?, ?, ?, ?)
            """,
            (application_id, "SUBMITTED", now, json.dumps(farmer_data, ensure_ascii=True)),
        )
        con.commit()


def get_application(application_id: str) -> Optional[Dict[str, Any]]:
    with connect() as con:
        row = con.execute("SELECT * FROM applications WHERE application_id = ?", (application_id,)).fetchone()
        if row is None:
            return None
        return _row_to_application(row)


def list_applications(status: Optional[str] = None) -> List[Dict[str, Any]]:
    with connect() as con:
        if status:
            rows = con.execute("SELECT * FROM applications WHERE status = ? ORDER BY submitted_at DESC", (status,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM applications ORDER BY submitted_at DESC").fetchall()
        return [_row_to_application(r) for r in rows]


def list_applications_by_mobile(mobile: str) -> List[Dict[str, Any]]:
    # farmer_data_json contains mobile_number; use LIKE for simple search
    pattern = f'"mobile_number": "{mobile}"'
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM applications WHERE farmer_data_json LIKE ? ORDER BY submitted_at DESC",
            (f"%{pattern}%",),
        ).fetchall()
        return [_row_to_application(r) for r in rows]


def update_application_ai(application_id: str, status: str, processed_at: Optional[str], agent_results: Any, ai_decision: Any) -> None:
    with connect() as con:
        con.execute(
            """
            UPDATE applications
            SET status = ?, processed_at = ?, agent_results_json = ?, ai_decision_json = ?
            WHERE application_id = ?
            """,
            (
                status,
                processed_at,
                json.dumps(agent_results, ensure_ascii=True) if agent_results is not None else None,
                json.dumps(ai_decision, ensure_ascii=True) if ai_decision is not None else None,
                application_id,
            ),
        )
        con.commit()


def update_application_officer(application_id: str, decision: str, comment: str) -> None:
    now = datetime.now().isoformat()
    with connect() as con:
        con.execute(
            """
            UPDATE applications
            SET status = ?, officer_decision = ?, officer_comment = ?, officer_action_at = ?
            WHERE application_id = ?
            """,
            (decision, decision, comment, now, application_id),
        )
        con.commit()


def set_status(application_id: str, status: str) -> None:
    with connect() as con:
        con.execute("UPDATE applications SET status = ? WHERE application_id = ?", (status, application_id))
        con.commit()


def add_notification(application_id: str, mobile: str, notif_type: str, message: str) -> None:
    with connect() as con:
        con.execute(
            """
            INSERT INTO notifications(application_id, mobile, type, message, sent_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (application_id, mobile, notif_type, message, datetime.now().isoformat(), "sent"),
        )
        con.commit()


def get_notifications(application_id: str) -> List[Dict[str, Any]]:
    with connect() as con:
        rows = con.execute(
            "SELECT id, application_id, mobile, type, message, sent_at, status FROM notifications WHERE application_id = ? ORDER BY id ASC",
            (application_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _row_to_application(row: sqlite3.Row) -> Dict[str, Any]:
    farmer_data = json.loads(row["farmer_data_json"]) if row["farmer_data_json"] else {}
    agent_results = json.loads(row["agent_results_json"]) if row["agent_results_json"] else None
    ai_decision = json.loads(row["ai_decision_json"]) if row["ai_decision_json"] else None
    return {
        "application_id": row["application_id"],
        "status": row["status"],
        "submitted_at": row["submitted_at"],
        "processed_at": row["processed_at"],
        "officer_action_at": row["officer_action_at"],
        "officer_decision": row["officer_decision"],
        "officer_comment": row["officer_comment"],
        "farmer_data": farmer_data,
        "agent_results": agent_results,
        "ai_decision": ai_decision,
    }
