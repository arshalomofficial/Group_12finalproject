import sqlite3
import os
import csv
import bcrypt

DB_PATH = "gridcare.db"


def get_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL CHECK (role IN
                ('admin','engineer','technician','customer_service'))
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS substations (
            substation_id INTEGER PRIMARY KEY,
            name          TEXT NOT NULL,
            region        TEXT NOT NULL,
            voltage       INTEGER,
            status        TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS outages (
            outage_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            substation_id    INTEGER NOT NULL,
            reported_by      INTEGER NOT NULL,
            description      TEXT,
            severity         TEXT DEFAULT 'Medium' CHECK (severity IN
                ('Low','Medium','High','Critical')),
            status           TEXT DEFAULT 'Open' CHECK (status IN
                ('Open','In Progress','Resolved')),
            reported_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            resolved_at      TEXT,
            resolution_notes TEXT,
            FOREIGN KEY (substation_id) REFERENCES substations(substation_id),
            FOREIGN KEY (reported_by)   REFERENCES users(user_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS work_orders (
            work_order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
            outage_id           INTEGER NOT NULL,
            assigned_technician INTEGER,
            scheduled_date      TEXT,
            status              TEXT DEFAULT 'Pending' CHECK (status IN
                ('Pending','Scheduled','In Progress','Completed')),
            created_by          INTEGER,
            FOREIGN KEY (outage_id)           REFERENCES outages(outage_id),
            FOREIGN KEY (assigned_technician) REFERENCES users(user_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            complaint_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            outage_id     INTEGER,
            customer_name TEXT NOT NULL,
            contact_info  TEXT,
            description   TEXT,
            logged_by     INTEGER NOT NULL,
            logged_at     TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (outage_id) REFERENCES outages(outage_id),
            FOREIGN KEY (logged_by) REFERENCES users(user_id)
        )
    ''')

    conn.commit()
    conn.close()


def hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def check_password(plain, hashed):
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_user(username, password, role, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
            (username, hash_password(password), role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def authenticate_user(username, password, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT user_id, password_hash, role FROM users WHERE username=?", (username,))
    row  = cur.fetchone()
    conn.close()
    if row and check_password(password, row[1]):
        return {"user_id": row[0], "role": row[2]}
    return None


def seed_demo_users(db_path=DB_PATH):
    for uname, pw, role in [
        ("admin1",    "Admin@123",    "admin"),
        ("engineer1", "Engineer@123", "engineer"),
        ("tech1",     "Tech@123",     "technician"),
        ("cs1",       "Service@123",  "customer_service"),
    ]:
        create_user(uname, pw, role, db_path=db_path)


def import_substations_from_csv(csv_path, db_path=DB_PATH):
    if not os.path.exists(csv_path):
        return 0
    conn  = get_connection(db_path)
    cur   = conn.cursor()
    count = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cur.execute(
                "INSERT OR REPLACE INTO substations (substation_id,name,region,voltage,status) VALUES (?,?,?,?,?)",
                (int(row["Substation ID"]), row["Short Name"], row["Region"],
                 int(float(row["Voltage (kV)"])) if row["Voltage (kV)"] else None,
                 row["Status"]),
            )
            count += 1
    conn.commit()
    conn.close()
    return count


def get_all_substations(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT substation_id,name,region FROM substations ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_technicians(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT user_id,username FROM users WHERE role='technician'")
    rows = cur.fetchall()
    conn.close()
    return rows


def log_outage(substation_id, reported_by, description, severity, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO outages (substation_id,reported_by,description,severity) VALUES (?,?,?,?)",
        (substation_id, reported_by, description, severity),
    )
    conn.commit()
    oid = cur.lastrowid
    conn.close()
    return oid


def get_outages(status_filter=None, db_path=DB_PATH):
    conn  = get_connection(db_path)
    cur   = conn.cursor()
    sql   = ("SELECT o.outage_id,s.name,o.description,o.severity,o.status,o.reported_at "
             "FROM outages o JOIN substations s ON o.substation_id=s.substation_id")
    args  = ()
    if status_filter and status_filter != "All":
        sql  += " WHERE o.status=?"
        args  = (status_filter,)
    sql += " ORDER BY o.reported_at DESC"
    cur.execute(sql, args)
    rows = cur.fetchall()
    conn.close()
    return rows


def resolve_outage(outage_id, resolution_notes="", db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute(
        "UPDATE outages SET status='Resolved',resolved_at=CURRENT_TIMESTAMP,resolution_notes=? WHERE outage_id=?",
        (resolution_notes, outage_id),
    )
    conn.commit()
    conn.close()


def create_work_order(outage_id, technician_id, scheduled_date, created_by, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO work_orders (outage_id,assigned_technician,scheduled_date,status,created_by) VALUES (?,?,?,'Scheduled',?)",
        (outage_id, technician_id, scheduled_date, created_by),
    )
    cur.execute("UPDATE outages SET status='In Progress' WHERE outage_id=?", (outage_id,))
    conn.commit()
    wid = cur.lastrowid
    conn.close()
    return wid


def get_work_orders_for_technician(technician_id, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute(
        ("SELECT w.work_order_id,o.outage_id,s.name,o.description,w.status,w.scheduled_date "
         "FROM work_orders w "
         "JOIN outages o ON w.outage_id=o.outage_id "
         "JOIN substations s ON o.substation_id=s.substation_id "
         "WHERE w.assigned_technician=? ORDER BY w.scheduled_date"),
        (technician_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def update_work_order_status(work_order_id, new_status, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute("UPDATE work_orders SET status=? WHERE work_order_id=?", (new_status, work_order_id))
    if new_status == "Completed":
        cur.execute("SELECT outage_id FROM work_orders WHERE work_order_id=?", (work_order_id,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE outages SET status='Resolved',resolved_at=CURRENT_TIMESTAMP WHERE outage_id=?",
                (row[0],))
    conn.commit()
    conn.close()


def log_complaint(outage_id, customer_name, contact_info, description, logged_by, db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO complaints (outage_id,customer_name,contact_info,description,logged_by) VALUES (?,?,?,?,?)",
        (outage_id or None, customer_name, contact_info, description, logged_by),
    )
    conn.commit()
    conn.close()


def get_complaints(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute(
        "SELECT complaint_id,outage_id,customer_name,contact_info,description,logged_at "
        "FROM complaints ORDER BY logged_at DESC"
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_report_stats(db_path=DB_PATH):
    conn = get_connection(db_path)
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM outages WHERE status='Open'")
    open_n = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM outages WHERE status='In Progress'")
    ip_n = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM outages WHERE status='Resolved'")
    res_n = cur.fetchone()[0]
    cur.execute(
        "SELECT s.region,COUNT(*) FROM outages o "
        "JOIN substations s ON o.substation_id=s.substation_id "
        "GROUP BY s.region ORDER BY COUNT(*) DESC"
    )
    by_region = cur.fetchall()
    conn.close()
    return {"open": open_n, "in_progress": ip_n, "resolved": res_n, "by_region": by_region}
