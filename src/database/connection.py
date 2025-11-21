import sqlite3
from pathlib import Path
import hashlib
import datetime
import csv
from typing import List, Dict

# project root (two levels up from this file: src/database -> project root)
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "hospital.db"

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_db_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_tables(conn)
    return conn

def _ensure_tables(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        contact TEXT,
        diagnosis TEXT,
        anonymized_name TEXT,
        anonymized_contact TEXT,
        date_added TEXT
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        action TEXT,
        timestamp TEXT,
        details TEXT
    )""")
    conn.commit()
    _seed_users(conn)

def _seed_users(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as c FROM users")
    row = cur.fetchone()
    if row and row["c"] == 0:
        users = [
            ("admin", "admin123", "admin"),
            ("drbob", "doc123", "doctor"),
            ("alice_recep", "rec123", "receptionist")
        ]
        for username, pwd, role in users:
            cur.execute(
                "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?,?,?)",
                (username, _hash_password(pwd), role)
            )
        conn.commit()

def log_action(user_id, role, action, details=""):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        timestamp = datetime.datetime.utcnow().isoformat()
        cur.execute(
            "INSERT INTO logs (user_id, role, action, timestamp, details) VALUES (?,?,?,?,?)",
            (user_id, role, action, timestamp, details)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # keep UI stable on logging errors

# Patient helpers

def mask_contact(contact: str) -> str:
    if not contact:
        return ""
    digits = "".join([c for c in contact if c.isdigit()])
    if len(digits) >= 4:
        return "XXX-XXX-" + digits[-4:]
    return "XXX-XXX-XXXX"

def anonymize_name(name: str, patient_id: int) -> str:
    # deterministic anonymized label using hash of id+name
    h = hashlib.sha256(f"{patient_id}:{name}".encode("utf-8")).hexdigest()
    return f"ANON_{h[:8]}"

def add_patient(name: str, contact: str, diagnosis: str, added_by_user_id=None, role=None) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    timestamp = datetime.datetime.utcnow().isoformat()
    cur.execute(
        "INSERT INTO patients (name, contact, diagnosis, date_added) VALUES (?,?,?,?)",
        (name, contact, diagnosis, timestamp)
    )
    patient_id = cur.lastrowid
    conn.commit()
    conn.close()
    log_action(added_by_user_id, role, "add_patient", f"patient_id={patient_id}")
    return patient_id

def get_patients() -> List[Dict]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM patients ORDER BY patient_id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def anonymize_all_patients(triggered_by_user_id=None, role=None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT patient_id, name, contact FROM patients")
    rows = cur.fetchall()
    for r in rows:
        pid = r["patient_id"]
        name = r["name"] or ""
        contact = r["contact"] or ""
        anon_name = anonymize_name(name, pid)
        anon_contact = mask_contact(contact)
        cur.execute(
            "UPDATE patients SET anonymized_name = ?, anonymized_contact = ? WHERE patient_id = ?",
            (anon_name, anon_contact, pid)
        )
    conn.commit()
    conn.close()
    log_action(triggered_by_user_id, role, "anonymize_all", "anonymized all patients")

def export_patients_csv(path: str) -> str:
    rows = get_patients()
    fieldnames = ["patient_id", "name", "contact", "diagnosis", "anonymized_name", "anonymized_contact", "date_added"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})
    return str(path)