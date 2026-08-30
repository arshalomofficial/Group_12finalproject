import os
import uuid
from datetime import datetime, date

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory, abort
)
import bcrypt

from utils.storage import load_json, save_json
from utils import validators

app = Flask(__name__)
app.secret_key = os.environ.get("CLINICCARE_SECRET", "dev-secret-change-this")

DATA_DIR         = os.path.join(os.path.dirname(__file__), "data")
SUBMISSIONS_DIR  = os.path.join(os.path.dirname(__file__), "submissions")

USERS_FILE         = os.path.join(DATA_DIR, "users.json")
TASKS_FILE         = os.path.join(DATA_DIR, "health_tasks.json")
SUBMISSIONS_FILE   = os.path.join(DATA_DIR, "task_submissions.json")
MESSAGES_FILE      = os.path.join(DATA_DIR, "messages.json")
ANNOUNCEMENTS_FILE = os.path.join(DATA_DIR, "announcements.json")

# admin categories only — not diagnoses
REVIEW_OUTCOMES = ["Pending", "Reviewed - Normal", "Needs Follow-up", "Escalated"]

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)


def _users():         return load_json(USERS_FILE)
def _tasks():         return load_json(TASKS_FILE)
def _submissions():   return load_json(SUBMISSIONS_FILE)
def _messages():      return load_json(MESSAGES_FILE)
def _announcements(): return load_json(ANNOUNCEMENTS_FILE)


def hash_pw(plain):          return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
def check_pw(plain, hashed): return bcrypt.checkpw(plain.encode(), hashed.encode())


def current_user():
    uid = session.get("user_id")
    return _users().get(uid) if uid else None


def require_login(role=None):
    user = current_user()
    if not user:
        abort(401)
    if role and user["role"] != role:
        abort(403)
    return user


@app.context_processor
def inject_theme():
    t   = session.get("theme", "")
    cls = "dark-theme" if t == "dark" else "colorful-theme" if t == "colorful" else ""
    return {"body_theme": cls}


@app.route("/")
def index():
    return redirect(url_for("dashboard") if session.get("user_id") else url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        role     = request.form.get("role", "").strip()
        user_id  = request.form.get("user_id", "").strip()
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        ok, msg = validators.validate_user_id(user_id, role)
        if not ok:
            flash(msg, "error")
            return render_template("register.html")

        ok, msg = validators.validate_password(password)
        if not ok:
            flash(msg, "error")
            return render_template("register.html")

        users = _users()
        if user_id in users:
            flash("That user ID is already taken.", "error")
            return render_template("register.html")

        users[user_id] = {
            "user_id": user_id, "name": name, "email": email,
            "password_hash": hash_pw(password), "role": role,
            "registered_at": datetime.now().isoformat(),
        }
        save_json(USERS_FILE, users)
        flash("Account created - you can log in now.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id  = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")
        users    = _users()
        user     = users.get(user_id)
        if not user or not check_pw(password, user["password_hash"]):
            flash("Incorrect user ID or password.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user_id
        session["role"]    = user["role"]
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    return redirect(url_for("clinician_dashboard" if user["role"] == "clinician" else "patient_dashboard"))


@app.route("/clinician")
def clinician_dashboard():
    user      = require_login(role="clinician")
    tasks     = _tasks()
    subs      = _submissions()
    users     = _users()
    inbox     = _get_inbox(user["user_id"])
    anns      = _announcements()
    patients  = {uid: u for uid, u in users.items() if u["role"] == "patient"}
    today_str = date.today().isoformat()

    total_tasks   = len(tasks)
    total_subs    = len(subs)
    pending       = sum(1 for s in subs.values() if s.get("review_status") == "Pending")
    reviewed      = total_subs - pending
    submitted_ids = {s["task_id"] for s in subs.values()}
    overdue       = sum(1 for t in tasks.values()
                        if t.get("due_date", "9999") < today_str
                        and t.get("task_id") not in submitted_ids)
    comp_rate     = round(reviewed / total_subs * 100 if total_subs else 0)

    analytics = {
        "total_tasks": total_tasks, "total_submissions": total_subs,
        "pending_reviews": pending, "reviewed_count": reviewed,
        "overdue_count": overdue, "completion_rate": comp_rate,
    }

    return render_template(
        "clinician_dashboard.html",
        user=user, tasks=tasks, submissions=subs,
        patients=patients, inbox=inbox, announcements=anns,
        analytics=analytics, review_outcomes=REVIEW_OUTCOMES,
    )


@app.route("/patient")
def patient_dashboard():
    user      = require_login(role="patient")
    my_id     = user["user_id"]
    all_tasks = _tasks()
    subs      = _submissions()
    inbox     = _get_inbox(my_id)
    anns      = _announcements()

    tasks   = {tid: t for tid, t in all_tasks.items()
               if not t.get("assigned_patients") or my_id in t.get("assigned_patients", [])}
    my_subs = {sid: s for sid, s in subs.items() if s.get("patient_id") == my_id}

    engagement = _get_engagement(tasks, my_subs)
    today_str  = date.today().isoformat()
    upcoming   = sorted(
        [t for t in tasks.values() if t.get("due_date", "") >= today_str],
        key=lambda t: t.get("due_date", "")
    )[:3]

    return render_template(
        "patient_dashboard.html",
        user=user, tasks=tasks, submissions=my_subs,
        inbox=inbox, announcements=anns,
        engagement=engagement, today=today_str,
        upcoming_reminders=upcoming,
    )


@app.route("/clinician/tasks/new", methods=["POST"])
def create_task():
    user        = require_login(role="clinician")
    title       = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date    = request.form.get("due_date", "").strip()
    assigned    = request.form.getlist("assigned_patients")

    if not title or not description or not due_date:
        flash("Title, description and due date are all required.", "error")
        return redirect(url_for("clinician_dashboard"))

    tasks   = _tasks()
    ints    = [int(k) for k in tasks if k.isdigit()]
    task_id = str(max(ints) + 1) if ints else "1"
    tasks[task_id] = {
        "task_id": task_id, "title": title, "description": description,
        "due_date": due_date, "created_by": user["user_id"],
        "assigned_patients": assigned, "created_at": datetime.now().isoformat(),
    }
    save_json(TASKS_FILE, tasks)
    flash(f"Task '{title}' assigned.", "success")
    return redirect(url_for("clinician_dashboard"))


@app.route("/patient/tasks/<task_id>/submit", methods=["POST"])
def submit_task(task_id):
    user  = require_login(role="patient")
    tasks = _tasks()
    my_id = user["user_id"]

    if task_id not in tasks:
        flash("Task not found.", "error")
        return redirect(url_for("patient_dashboard"))

    task = tasks[task_id]
    if task.get("assigned_patients") and my_id not in task["assigned_patients"]:
        flash("This task was not assigned to you.", "error")
        return redirect(url_for("patient_dashboard"))

    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("Please choose a file.", "error")
        return redirect(url_for("patient_dashboard"))

    file_bytes = uploaded.read()
    ok, msg    = validators.validate_file(uploaded.filename, len(file_bytes))
    if not ok:
        flash(msg, "error")
        return redirect(url_for("patient_dashboard"))

    ext    = uploaded.filename.rsplit(".", 1)[-1].lower() if "." in uploaded.filename else ""
    issues = []
    if ext == "csv":
        _, issues = validators.check_csv_completeness(file_bytes)
    elif ext == "txt":
        _, issues = validators.check_txt_not_empty(file_bytes)

    dest = os.path.join(SUBMISSIONS_DIR, my_id)
    os.makedirs(dest, exist_ok=True)
    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{task_id}_{ts}_{uploaded.filename}"
    save_path = os.path.join(dest, safe_name)
    with open(save_path, "wb") as f:
        f.write(file_bytes)

    subs   = _submissions()
    sub_id = str(uuid.uuid4())[:8]
    subs[sub_id] = {
        "submission_id": sub_id, "task_id": task_id,
        "patient_id": my_id, "file_path": save_path,
        "timestamp": datetime.now().isoformat(),
        "review_status": "Pending", "review_notes": "",
        "reviewer_id": "", "completeness_issues": issues,
    }
    save_json(SUBMISSIONS_FILE, subs)

    if issues:
        flash("File saved, but formatting issues found: " + "; ".join(issues), "success")
    else:
        flash("Submission received. Your clinician will review it soon.", "success")
    return redirect(url_for("patient_dashboard"))


@app.route("/clinician/submissions/<submission_id>/review", methods=["POST"])
def review_submission(submission_id):
    user    = require_login(role="clinician")
    outcome = request.form.get("outcome", "").strip()
    notes   = request.form.get("notes", "").strip()

    if outcome not in REVIEW_OUTCOMES or outcome == "Pending":
        flash("Pick a valid review outcome.", "error")
        return redirect(url_for("clinician_dashboard"))

    subs = _submissions()
    if submission_id not in subs:
        flash("Submission not found.", "error")
        return redirect(url_for("clinician_dashboard"))

    subs[submission_id].update({
        "review_status": outcome, "review_notes": notes,
        "reviewer_id": user["user_id"],
        "reviewed_at": datetime.now().isoformat(),
    })
    save_json(SUBMISSIONS_FILE, subs)

    _add_to_inbox(
        subs[submission_id]["patient_id"], user["user_id"],
        f"Your submission has been reviewed. Outcome: {outcome}. Notes: {notes or 'None'}",
    )
    flash("Review recorded.", "success")
    return redirect(url_for("clinician_dashboard"))


@app.route("/clinician/announce", methods=["POST"])
def create_announcement():
    user   = require_login(role="clinician")
    text   = request.form.get("text", "").strip()
    urgent = bool(request.form.get("urgent"))

    if not text:
        flash("Announcement text is required.", "error")
        return redirect(url_for("clinician_dashboard"))

    anns   = _announcements()
    ann_id = str(uuid.uuid4())[:8]
    anns[ann_id] = {
        "text": text, "urgent": urgent,
        "posted_by": user["user_id"],
        "posted_at": datetime.now().isoformat(),
    }
    save_json(ANNOUNCEMENTS_FILE, anns)

    if urgent:
        for uid, u in _users().items():
            if u["role"] == "patient":
                _add_to_inbox(uid, user["user_id"], f"[Urgent] {text}")

    flash("Announcement posted.", "success")
    return redirect(url_for("clinician_dashboard"))


@app.route("/messages/send", methods=["POST"])
def send_message():
    user         = require_login()
    recipient_id = request.form.get("recipient_id", "").strip()
    content      = request.form.get("content", "").strip()

    if not recipient_id or not content:
        flash("Recipient and message are required.", "error")
        return redirect(url_for("dashboard"))

    recipient = _users().get(recipient_id)
    if not recipient:
        flash("Recipient not found.", "error")
        return redirect(url_for("dashboard"))

    if user["role"] == "patient" and recipient["role"] == "patient":
        flash("You can only message your clinician.", "error")
        return redirect(url_for("patient_dashboard"))

    _add_to_inbox(recipient_id, user["user_id"], content)
    flash("Message sent.", "success")
    return redirect(url_for("dashboard"))


@app.route("/clinician/analytics")
def clinician_analytics():
    user  = require_login(role="clinician")
    subs  = _submissions()
    tasks = _tasks()

    total_tasks = len(tasks)
    submitted   = len({s["task_id"] for s in subs.values()})
    pending     = sum(1 for s in subs.values() if s.get("review_status") == "Pending")
    reviewed    = len(subs) - pending

    turnarounds = []
    for s in subs.values():
        if s.get("reviewed_at") and s.get("timestamp"):
            try:
                t1 = datetime.fromisoformat(s["timestamp"])
                t2 = datetime.fromisoformat(s["reviewed_at"])
                turnarounds.append((t2 - t1).days)
            except Exception:
                pass
    avg_ta = round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else 0

    outcome_counts = {}
    for s in subs.values():
        o = s.get("review_status", "Pending")
        outcome_counts[o] = outcome_counts.get(o, 0) + 1

    stats = {
        "total_tasks": total_tasks, "tasks_with_submissions": submitted,
        "total_submissions": len(subs), "pending_reviews": pending,
        "reviewed_count": reviewed, "avg_turnaround_days": avg_ta,
        "outcome_counts": outcome_counts,
    }
    return render_template("analytics.html", user=user, stats=stats)


@app.route("/files/<patient_id>/<filename>")
def download_file(patient_id, filename):
    user = require_login()
    if user["role"] == "patient" and user["user_id"] != patient_id:
        abort(403)
    return send_from_directory(
        os.path.join(SUBMISSIONS_DIR, patient_id), filename, as_attachment=True)


@app.route("/theme/<theme>")
def set_theme(theme):
    if theme in ("dark", "colorful", "default"):
        session["theme"] = theme
    return redirect(request.referrer or url_for("dashboard"))


def _get_inbox(user_id):
    msgs = _messages()
    return sorted(
        [m for m in msgs.values() if m.get("recipient_id") == user_id],
        key=lambda m: m.get("timestamp", ""), reverse=True,
    )


def _add_to_inbox(recipient_id, sender_id, content):
    msgs = _messages()
    mid  = str(uuid.uuid4())[:8]
    msgs[mid] = {
        "msg_id": mid, "sender_id": sender_id,
        "recipient_id": recipient_id, "content": content,
        "timestamp": datetime.now().isoformat(), "read": False,
    }
    save_json(MESSAGES_FILE, msgs)


def _get_engagement(tasks, my_subs):
    on_time = 0
    for sub in my_subs.values():
        task = tasks.get(sub.get("task_id"))
        if task and sub.get("timestamp", "") <= task.get("due_date", "9999") + "T23:59:59":
            on_time += 1
    return {
        "points": len(my_subs) * 10 + on_time * 5,
        "tasks_completed_on_time": on_time,
        "total_submissions": len(my_subs),
    }


def load_json(path):
    from utils.storage import load_json as _lj
    return _lj(path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
