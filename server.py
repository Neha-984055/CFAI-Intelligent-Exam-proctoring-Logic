"""
IEPL — Intelligent Exam Proctoring Logic
Python/Flask Backend Server
Run: pip install flask flask-cors  →  python server.py
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import json
import os
import uuid

app = Flask(__name__, static_folder=".")
CORS(app)

# ── In-memory stores (replace with a real DB in production) ──────────
USERS = {
    "STU001": {"password": "exam123", "name": "Arjun Reddy",     "role": "student"},
    "STU002": {"password": "exam123", "name": "Priya Sharma",    "role": "student"},
    "STU003": {"password": "exam123", "name": "Mohammed Rizwan", "role": "student"},
    "ADMIN01":{"password": "admin123","name": "Dr. K. Srinivas", "role": "admin",
               "access_code": "IEPL2024"},
}

SESSIONS   = {}   # session_token -> user data
VIOLATIONS = {}   # student_id -> list of violation dicts
REPORTS    = {}   # student_id -> final report dict


# ── AUTH ──────────────────────────────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    uid  = data.get("id", "").strip()
    pwd  = data.get("password", "")
    name = data.get("name", "").strip()
    role = data.get("role", "student")

    user = USERS.get(uid)
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 401
    if user["password"] != pwd:
        return jsonify({"success": False, "message": "Incorrect password"}), 401
    if user["role"] != role:
        return jsonify({"success": False, "message": "Role mismatch"}), 401
    if role == "admin":
        if data.get("access_code") != user.get("access_code"):
            return jsonify({"success": False, "message": "Invalid access code"}), 401

    token = str(uuid.uuid4())
    SESSIONS[token] = {"id": uid, "name": user["name"], "role": role}
    print(f"[{_now()}] LOGIN  {uid} ({role})")
    return jsonify({"success": True, "token": token, "name": user["name"], "role": role})


@app.route("/api/logout", methods=["POST"])
def logout():
    token = _get_token()
    SESSIONS.pop(token, None)
    return jsonify({"success": True})


# ── VIOLATIONS (proctoring events from front-end) ─────────────────────
@app.route("/api/violation", methods=["POST"])
def log_violation():
    user = _auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    sid  = user["id"]
    VIOLATIONS.setdefault(sid, [])
    entry = {
        "time":    _now(),
        "message": data.get("message", ""),
        "level":   data.get("level", "warn"),   # info | warn | danger
    }
    VIOLATIONS[sid].append(entry)

    # Log to console
    lvl = entry["level"].upper()
    print(f"[{entry['time']}] VIOLATION [{lvl}] {sid}: {entry['message']}")

    # Return threat level
    total = len(VIOLATIONS[sid])
    threat = min(100, total * 10)
    return jsonify({"success": True, "total_violations": total, "threat_level": threat})


@app.route("/api/violations/<student_id>", methods=["GET"])
def get_violations(student_id):
    user = _auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user["role"] != "admin" and user["id"] != student_id:
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(VIOLATIONS.get(student_id, []))


# ── EXAM REPORT ───────────────────────────────────────────────────────
@app.route("/api/submit", methods=["POST"])
def submit_exam():
    user = _auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    sid  = user["id"]
    answers   = data.get("answers", [])
    questions = _get_questions()

    # Grade
    correct = sum(1 for i, a in enumerate(answers) if i < len(questions) and a == questions[i]["ans"])
    total   = len(questions)
    score   = round((correct / total) * 100, 1)

    v_list    = VIOLATIONS.get(sid, [])
    threat    = min(100, len(v_list) * 10)
    tab_sw    = sum(1 for v in v_list if "tab switch" in v["message"].lower())
    fs_exits  = sum(1 for v in v_list if "fullscreen" in v["message"].lower())

    # Verdict
    if threat < 20:
        verdict = "CLEAN"
    elif threat < 60:
        verdict = "REVIEW"
    else:
        verdict = "FAIL"

    report = {
        "student_id":        sid,
        "name":              user["name"],
        "score":             score,
        "correct":           correct,
        "total":             total,
        "violations":        len(v_list),
        "threat_level":      threat,
        "tab_switches":      tab_sw,
        "fullscreen_exits":  fs_exits,
        "integrity_verdict": verdict,
        "log":               v_list,
        "submitted_at":      _now(),
    }
    REPORTS[sid] = report
    print(f"[{_now()}] SUBMIT {sid} — Score:{score}% Threat:{threat}% Verdict:{verdict}")
    return jsonify({"success": True, "report": report})


@app.route("/api/report/<student_id>", methods=["GET"])
def get_report(student_id):
    user = _auth()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user["role"] != "admin" and user["id"] != student_id:
        return jsonify({"error": "Forbidden"}), 403
    report = REPORTS.get(student_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
    return jsonify(report)


# ── ADMIN: ALL REPORTS ────────────────────────────────────────────────
@app.route("/api/admin/reports", methods=["GET"])
def all_reports():
    user = _auth()
    if not user or user["role"] != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return jsonify(list(REPORTS.values()))


@app.route("/api/admin/live", methods=["GET"])
def live_status():
    """Active sessions and their current violation count."""
    user = _auth()
    if not user or user["role"] != "admin":
        return jsonify({"error": "Admin access required"}), 403
    live = []
    for token, u in SESSIONS.items():
        if u["role"] == "student":
            v = VIOLATIONS.get(u["id"], [])
            live.append({
                "id":         u["id"],
                "name":       u["name"],
                "violations": len(v),
                "threat":     min(100, len(v) * 10),
            })
    return jsonify(live)


# ── TERMINATE EXAM ────────────────────────────────────────────────────
@app.route("/api/admin/terminate/<student_id>", methods=["POST"])
def terminate(student_id):
    user = _auth()
    if not user or user["role"] != "admin":
        return jsonify({"error": "Admin access required"}), 403
    VIOLATIONS.setdefault(student_id, []).append({
        "time":    _now(),
        "message": "Exam terminated by examiner",
        "level":   "danger",
    })
    print(f"[{_now()}] TERMINATE {student_id} by admin {user['id']}")
    return jsonify({"success": True, "message": f"Exam for {student_id} terminated"})


# ── SERVE STATIC FILES ────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "login.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)


# ── HELPERS ───────────────────────────────────────────────────────────
def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _get_token():
    auth = request.headers.get("Authorization", "")
    return auth.replace("Bearer ", "").strip()

def _auth():
    return SESSIONS.get(_get_token())

def _get_questions():
    return [
        {"q": "Which data structure uses LIFO order?",              "ans": 1},
        {"q": "Time complexity of binary search?",                   "ans": 2},
        {"q": "Keyword to define a function in Python?",             "ans": 1},
        {"q": "What does HTML stand for?",                           "ans": 0},
        {"q": "Protocol for secure web communication?",              "ans": 2},
        {"q": "Best average-case sorting algorithm?",                "ans": 2},
        {"q": "Output of print(2**10)?",                             "ans": 2},
        {"q": "OSI layer where routing occurs?",                     "ans": 2},
        {"q": "SQL command to retrieve data?",                       "ans": 1},
        {"q": "What does RAM stand for?",                            "ans": 1},
    ]


# ── ENTRY POINT ───────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  IEPL — Intelligent Exam Proctoring Logic")
    print("  Python/Flask Backend  •  http://localhost:5000")
    print("=" * 55)
    print("  Demo credentials:")
    print("  Student  → STU001 / exam123")
    print("  Examiner → ADMIN01 / admin123 / IEPL2024")
    print("=" * 55)
    app.run(debug=True, port=5000)
