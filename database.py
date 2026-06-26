"""
ArogyaAI — Database Layer v4.1
Added: vitals (bp_systolic, bp_diastolic, temperature_c)
"""
import hashlib, json, logging, sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import config

logger = logging.getLogger("db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'patient',
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS patients(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER UNIQUE,
    name              TEXT,
    age               INTEGER,
    gender            TEXT,
    weight_kg         REAL,
    height_cm         REAL,
    blood_group       TEXT,
    -- Vitals (added v4.1)
    bp_systolic       INTEGER,   -- e.g. 120
    bp_diastolic      INTEGER,   -- e.g. 80
    temperature_f     REAL,      -- e.g. 98.6
    -- Location & prefs
    state             TEXT,
    city              TEXT,
    language          TEXT DEFAULT 'English',
    conditions        TEXT DEFAULT '[]',
    allergies         TEXT DEFAULT '[]',
    current_meds      TEXT DEFAULT '[]',
    dietary_pref      TEXT DEFAULT 'Non-Vegetarian',
    emergency_contact TEXT,
    created_at        TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS sessions(
    id            TEXT PRIMARY KEY,
    patient_id    INTEGER,
    ts            TEXT,
    symptoms      TEXT,
    emergency     INTEGER DEFAULT 0,
    prescription  TEXT DEFAULT '{}',
    report_data   TEXT DEFAULT '{}',
    FOREIGN KEY(patient_id) REFERENCES patients(id)
);
CREATE INDEX IF NOT EXISTS ix_s_p ON sessions(patient_id);

CREATE TABLE IF NOT EXISTS medicines(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    generic_salt TEXT,
    drug_class TEXT,
    primary_uses TEXT,
    mechanism_of_action TEXT,
    common_side_effects TEXT,
    contraindications TEXT,
    popular_indian_brands TEXT,
    safety_advice TEXT
);
CREATE INDEX IF NOT EXISTS ix_meds_name ON medicines(name);
"""

def _conn():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    return c

def _sha(t):
    return hashlib.sha256(t.encode()).hexdigest()

def _jl(v):
    return json.dumps(v) if isinstance(v, list) else (v or "[]")

def _migrate():
    """Add new columns if upgrading from old DB that lacks them."""
    new_cols = [
        ("bp_systolic",  "INTEGER"),
        ("bp_diastolic", "INTEGER"),
        ("temperature_c","REAL"),
    ]
    with _conn() as conn:
        existing = {row[1] for row in
                    conn.execute("PRAGMA table_info(patients)").fetchall()}
        for col, ctype in new_cols:
            if col not in existing:
                conn.execute(f"ALTER TABLE patients ADD COLUMN {col} {ctype}")
                logger.info("Migrated: added patients.%s", col)

def init():
    with _conn() as conn:
        conn.executescript(SCHEMA)
    _migrate()
    with _conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE username=?",
                            (config.DOCTOR_USER,)).fetchone():
            conn.execute(
                "INSERT INTO users(username,password,role,created_at) VALUES(?,?,?,?)",
                (config.DOCTOR_USER, _sha(config.DOCTOR_PASS),
                 "doctor", datetime.utcnow().isoformat()))
        if not conn.execute("SELECT id FROM users WHERE username=?",
                            (config.ROOT_USER,)).fetchone():
            conn.execute(
                "INSERT INTO users(username,password,role,created_at) VALUES(?,?,?,?)",
                (config.ROOT_USER, _sha(config.ROOT_PASS),
                 "admin", datetime.utcnow().isoformat()))
    logger.info("DB ready: %s", config.DB_PATH)

def register(username: str, password: str) -> tuple[bool, str]:
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO users(username,password,role,created_at) VALUES(?,?,?,?)",
                (username.strip(), _sha(password), "patient", datetime.utcnow().isoformat()))
        return True, "Account created! Please login."
    except sqlite3.IntegrityError:
        return False, "Username already taken. Try another."

def login(username: str, password: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username.strip(), _sha(password))).fetchone()
        return dict(row) if row else None

def upsert_patient(user_id: int, **kw) -> int:
    for f in ("conditions", "allergies", "current_meds"):
        if f in kw and isinstance(kw[f], list):
            kw[f] = json.dumps(kw[f])
    now = datetime.utcnow().isoformat()
    with _conn() as conn:
        ex = conn.execute("SELECT id FROM patients WHERE user_id=?", (user_id,)).fetchone()
        if ex:
            sets = ", ".join(f"{k}=?" for k in kw)
            conn.execute(f"UPDATE patients SET {sets} WHERE user_id=?",
                         list(kw.values()) + [user_id])
            return ex["id"]
        kw.setdefault("conditions", "[]")
        kw.setdefault("allergies", "[]")
        kw.setdefault("current_meds", "[]")
        cols = ", ".join(kw.keys())
        ph   = ", ".join("?" * len(kw))
        cur  = conn.execute(
            f"INSERT INTO patients(user_id,{cols},created_at) VALUES(?,{ph},?)",
            [user_id] + list(kw.values()) + [now])
        return cur.lastrowid

def get_patient(user_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM patients WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for f in ("conditions", "allergies", "current_meds"):
            d[f] = json.loads(d.get(f) or "[]")
        return d

def list_patients() -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT p.*,u.username FROM patients p "
            "JOIN users u ON p.user_id=u.id "
            "ORDER BY p.created_at DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for f in ("conditions", "allergies", "current_meds"):
                d[f] = json.loads(d.get(f) or "[]")
            result.append(d)
        return result

def save_session(sid, pid, symptoms, emergency, prescription, report=None):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions"
            "(id,patient_id,ts,symptoms,emergency,prescription,report_data) "
            "VALUES(?,?,?,?,?,?,?)",
            (sid, pid, datetime.utcnow().isoformat(), symptoms[:500],
             int(emergency), json.dumps(prescription), json.dumps(report or {})))

def get_sessions(patient_id: int, limit: int = 20) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE patient_id=? ORDER BY ts DESC LIMIT ?",
            (patient_id, limit)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["prescription"] = json.loads(d.get("prescription") or "{}")
            d["report_data"]  = json.loads(d.get("report_data") or "{}")
            result.append(d)
        return result

def get_session_by_id(sid: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["prescription"] = json.loads(d.get("prescription") or "{}")
        d["report_data"]  = json.loads(d.get("report_data") or "{}")
        return d

def all_sessions(limit: int = 100) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT s.*,p.name as pname FROM sessions s "
            "LEFT JOIN patients p ON s.patient_id=p.id "
            "ORDER BY s.ts DESC LIMIT ?", (limit,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["prescription"] = json.loads(d.get("prescription") or "{}")
            d["report_data"]  = json.loads(d.get("report_data") or "{}")
            result.append(d)
        return result

def stats() -> dict:
    with _conn() as conn:
        return {
            "patients":  conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0],
            "sessions":  conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            "today":     conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE ts>=datetime('now','start of day')"
            ).fetchone()[0],
            "emergency": conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE emergency=1"
            ).fetchone()[0],
            "users":     conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        }

def insert_medicine(med_data: dict):
    with _conn() as conn:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO medicines 
                (name, generic_salt, drug_class, primary_uses, mechanism_of_action, 
                common_side_effects, contraindications, popular_indian_brands, safety_advice)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    med_data.get("name"),
                    med_data.get("generic_salt", ""),
                    med_data.get("drug_class", ""),
                    med_data.get("primary_uses", "[]"),
                    med_data.get("mechanism_of_action", ""),
                    med_data.get("common_side_effects", "[]"),
                    med_data.get("contraindications", "[]"),
                    med_data.get("popular_indian_brands", "[]"),
                    med_data.get("safety_advice", "")
                )
            )
        except Exception as e:
            logger.error("Failed to insert medicine %s: %s", med_data.get("name"), e)

def search_medicines(query: str) -> Optional[dict]:
    with _conn() as conn:
        # First try exact match
        row = conn.execute("SELECT * FROM medicines WHERE name = ? COLLATE NOCASE", (query,)).fetchone()
        if not row:
            # Try partial match (generic salt or name)
            search_str = f"%{query}%"
            row = conn.execute(
                "SELECT * FROM medicines WHERE name LIKE ? OR generic_salt LIKE ? LIMIT 1", 
                (search_str, search_str)
            ).fetchone()
        
        if not row:
            return None
            
        d = dict(row)
        for f in ("primary_uses", "common_side_effects", "contraindications", "popular_indian_brands"):
            try:
                d[f] = json.loads(d.get(f) or "[]")
            except Exception:
                d[f] = []
        return d

def admin_get_all_data() -> dict:
    with _conn() as conn:
        users = [dict(r) for r in conn.execute("SELECT id, username, role, password, created_at FROM users").fetchall()]
        patients = [dict(r) for r in conn.execute("SELECT * FROM patients").fetchall()]
        session_stats = [dict(r) for r in conn.execute(
            "SELECT patient_id, COUNT(id) as visit_count, MAX(ts) as last_visit, "
            "(SELECT id FROM sessions s2 WHERE s2.patient_id=sessions.patient_id ORDER BY ts DESC LIMIT 1) as latest_session_id "
            "FROM sessions GROUP BY patient_id"
        ).fetchall()]
        return {"users": users, "patients": patients, "session_stats": session_stats}

try:
    init()
except Exception as e:
    logging.warning("DB init: %s", e)
