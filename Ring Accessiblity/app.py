from flask import Flask, jsonify, request, render_template, Response, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timezone
import sqlite3, json, os, time, secrets
from pathlib import Path
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth
import re, csv, io

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "ring_alert.db"))
INITIAL_MODE = os.getenv("RING_MODE", "demo").lower()
if INITIAL_MODE not in ("demo", "live"):
    INITIAL_MODE = "demo"
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true")
oauth = OAuth(app)

def _register_oauth_clients():
    google_id, google_secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
    if google_id and google_secret:
        oauth.register(name="google", client_id=google_id, client_secret=google_secret, server_metadata_url="https://accounts.google.com/.well-known/openid-configuration", client_kwargs={"scope":"openid email profile"})
    github_id, github_secret = os.getenv("GITHUB_CLIENT_ID"), os.getenv("GITHUB_CLIENT_SECRET")
    if github_id and github_secret:
        oauth.register(name="github", client_id=github_id, client_secret=github_secret, access_token_url="https://github.com/login/oauth/access_token", authorize_url="https://github.com/login/oauth/authorize", api_base_url="https://api.github.com/", client_kwargs={"scope":"read:user user:email"})
    li_id, li_secret = os.getenv("LINKEDIN_CLIENT_ID"), os.getenv("LINKEDIN_CLIENT_SECRET")
    if li_id and li_secret:
        oauth.register(name="linkedin", client_id=li_id, client_secret=li_secret, server_metadata_url="https://www.linkedin.com/oauth/.well-known/openid-configuration", client_kwargs={"scope":"openid profile email"})
_register_oauth_clients()

EVENT_TYPES = {
    "doorbell_pressed": ("Doorbell pressed", "Someone is at your front door", "bell"),
    "person_detected": ("Person detected", "A person was detected at the front door", "person"),
    "motion_detected": ("Motion detected", "Movement was detected near the front door", "motion"),
    "package_detected": ("Package detected", "A delivery may have arrived", "package"),
    "front_door_activity": ("Front door activity", "Activity was detected at the front door", "door"),
    "custom_alert": ("Custom alert", "A custom alert was triggered", "alert"),
}
DEFAULT_SETTINGS = {
    "high_contrast": False, "large_text": False, "extra_large_alert": True,
    "vibration": True, "screen_flash": False, "reduced_motion": False,
    "theme": "dark", "alert_duration": 12, "smart_display": False,
    "visual_notifications": True, "repeated_vibration": False, "emergency_mode": False
}
DEFAULT_RULES = [
    {"name":"Doorbell: full visual alert", "event_type":"doorbell_pressed",
     "actions":["fullscreen","visual","vibrate"], "enabled":True},
    {"name":"Person: prominent notification", "event_type":"person_detected",
     "actions":["visual","open_event"], "enabled":True},
    {"name":"Motion: save to history", "event_type":"motion_detected",
     "actions":["history"], "enabled":True}
]

def db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          id TEXT PRIMARY KEY, event_type TEXT NOT NULL, device_name TEXT NOT NULL,
          timestamp TEXT NOT NULL, description TEXT NOT NULL, source TEXT NOT NULL,
          media_ref TEXT, acknowledged INTEGER NOT NULL DEFAULT 0,
          processing_status TEXT NOT NULL DEFAULT 'processed'
        );
        CREATE TABLE IF NOT EXISTS settings (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS rules (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        if not con.execute("SELECT 1 FROM settings WHERE id=1").fetchone():
            con.execute("INSERT INTO settings(id,data) VALUES(1,?)", (json.dumps(DEFAULT_SETTINGS),))
        if not con.execute("SELECT 1 FROM rules LIMIT 1").fetchone():
            for rule in DEFAULT_RULES:
                con.execute("INSERT INTO rules(data) VALUES(?)", (json.dumps(rule),))
        con.execute("INSERT OR IGNORE INTO app_config(key,value) VALUES('mode',?)", (INITIAL_MODE,))
        # A local Demo Account
        username, password = os.getenv("APP_USERNAME"), os.getenv("APP_PASSWORD")
        if username and password and not con.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
            con.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                        (username, generate_password_hash(password)))

init_db()

def get_mode():
    try:
        with db() as con:
            row = con.execute("SELECT value FROM app_config WHERE key='mode'").fetchone()
        return row["value"] if row and row["value"] in ("demo", "live") else INITIAL_MODE
    except sqlite3.Error:
        return INITIAL_MODE

def auth_required():
    return os.getenv("AUTH_REQUIRED", "true").lower() == "true"

def require_auth(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if auth_required() and not session.get("user"):
            return jsonify({"error":"Authentication required"}), 401
        return fn(*args, **kwargs)
    return wrapped

def publish_event(event):
    # SSE Client Persisted Stream Using Last-Event-ID-like Cursor.
    return event

def normalize_event(payload, source="simulated"):
    event_type = payload.get("event_type")
    if event_type not in EVENT_TYPES:
        raise ValueError("Unsupported event_type")
    device = str(payload.get("device_name", "Front Door")).strip()[:80]
    if not device:
        raise ValueError("device_name cannot be empty")
    title, default_desc, _ = EVENT_TYPES[event_type]
    desc = str(payload.get("description") or default_desc).strip()[:240]
    now = datetime.now(timezone.utc).isoformat()
    event_id = str(payload.get("event_id") or secrets.token_hex(8))[:64]
    return {"id":event_id, "event_type":event_type, "device_name":device,
            "timestamp":now, "description":desc, "source":source,
            "media_ref":None, "acknowledged":False, "processing_status":"processed"}

def process_event(payload, source="simulated"):
    event = normalize_event(payload, source)
    with db() as con:
        existing = con.execute("SELECT * FROM events WHERE id=?", (event["id"],)).fetchone()
        if existing:
            return dict(existing), False
        con.execute("""INSERT INTO events(id,event_type,device_name,timestamp,description,source,media_ref,acknowledged,processing_status)
          VALUES(?,?,?,?,?,?,?,?,?)""",
          (event["id"],event["event_type"],event["device_name"],event["timestamp"],
           event["description"],event["source"],event["media_ref"],0,event["processing_status"]))
    return event, True

def get_settings():
    with db() as con:
        row = con.execute("SELECT data FROM settings WHERE id=1").fetchone()
    return json.loads(row["data"])

def get_rules():
    with db() as con:
        rows = con.execute("SELECT id,data FROM rules ORDER BY id").fetchall()
    return [{"id":r["id"], **json.loads(r["data"])} for r in rows]

@app.route("/")
def index():
    if auth_required() and not session.get("user"):
        return redirect(url_for("login"))
    return render_template("index.html", current_user=session.get("display_name", session.get("user", "Guest")))

@app.get("/login")
def login():
    if session.get("user"):
        return redirect(url_for("index"))
    session.setdefault("auth_csrf", secrets.token_urlsafe(24))
    return render_template("auth.html", page="login", oauth_providers=oauth_providers(), csrf_token=session["auth_csrf"])

@app.get("/register")
def register():
    if session.get("user"):
        return redirect(url_for("index"))
    session.setdefault("auth_csrf", secrets.token_urlsafe(24))
    return render_template("auth.html", page="register", oauth_providers=oauth_providers(), csrf_token=session["auth_csrf"])

def oauth_providers():
    return {name: bool(oauth.create_client(name)) for name in ("google", "github", "linkedin")}

@app.post("/auth/register")
def register_account():
    if not secrets.compare_digest(str(request.form.get("csrf_token", "")), str(session.get("auth_csrf", ""))):
        flash("Your form expired. Please try again.", "error"); return redirect(url_for("register"))
    username = str(request.form.get("email", "")).strip().lower()[:254]
    password = request.form.get("password", "")
    display_name = str(request.form.get("name", "")).strip()[:80]
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", username):
        flash("Enter a valid email address.", "error")
        return redirect(url_for("register"))
    if len(password) < 10 or len(password) > 256:
        flash("Use a password between 10 and 256 characters.", "error")
        return redirect(url_for("register"))
    if not display_name:
        display_name = username.split("@", 1)[0]
    try:
        with db() as con:
            con.execute("INSERT INTO users(username,password_hash) VALUES(?,?)", (username, generate_password_hash(password)))
    except sqlite3.IntegrityError:
        flash("An account with that email already exists. Please sign in.", "error")
        return redirect(url_for("login"))
    session.clear(); session["user"] = username; session["display_name"] = display_name
    return redirect(url_for("index"))

@app.post("/auth/login")
def login_account():
    if not secrets.compare_digest(str(request.form.get("csrf_token", "")), str(session.get("auth_csrf", ""))):
        flash("Your form expired. Please try again.", "error"); return redirect(url_for("login"))
    username = str(request.form.get("email", "")).strip().lower()[:254]
    password = request.form.get("password", "")
    with db() as con:
        row = con.execute("SELECT username,password_hash FROM users WHERE username=?", (username,)).fetchone()
    if not row or row["password_hash"].startswith("oauth$") or not check_password_hash(row["password_hash"], password):
        flash("Email or password is incorrect.", "error")
        return redirect(url_for("login"))
    session.clear(); session["user"] = row["username"]; session["display_name"] = row["username"].split("@",1)[0]
    return redirect(url_for("index"))

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.get("/auth/<provider>")
def oauth_login(provider):
    if provider not in ("google", "github", "linkedin"):
        return jsonify({"error":"Unsupported sign-in provider"}), 404
    client = oauth.create_client(provider)
    if client is None:
        flash(f"{provider.title()} sign-in is not configured yet. Add its client ID and secret to .env.", "error")
        return redirect(url_for("login"))
    redirect_uri = url_for("oauth_callback", provider=provider, _external=True)
    return client.authorize_redirect(redirect_uri)

@app.get("/auth/<provider>/callback")
def oauth_callback(provider):
    client = oauth.create_client(provider)
    if client is None:
        flash("That sign-in provider is not configured.", "error"); return redirect(url_for("login"))
    try:
        token = client.authorize_access_token()
        if provider in ("google", "linkedin"):
            info = token.get("userinfo") or client.parse_id_token(token)
            subject = str(info.get("sub", "")); display = info.get("name") or info.get("given_name") or provider.title()
            email = info.get("email") or ""
        else:
            info = client.get("user").json()
            subject = str(info.get("id", "")); display = info.get("name") or info.get("login") or "GitHub user"
            email = info.get("email") or ""
            if not email:
                emails = client.get("user/emails").json()
                email = next((x.get("email") for x in emails if x.get("primary") and x.get("verified")), "")
        if not subject:
            raise ValueError("Provider did not return a stable account identifier")
        username = f"oauth:{provider}:{subject}"
        with db() as con:
            con.execute("INSERT OR IGNORE INTO users(username,password_hash) VALUES(?,?)", (username, "oauth$" + provider))
        session.clear(); session["user"] = username; session["display_name"] = str(display)[:80]; session["provider"] = provider
        return redirect(url_for("index"))
    except Exception:
        app.logger.exception("OAuth callback failed for %s", provider)
        flash("Sign-in could not be completed. Check provider settings and try again.", "error")
        return redirect(url_for("login"))

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","mode":get_mode() if get_mode()=="demo" else "live_unconfigured",
                    "database":"connected","timestamp":datetime.now(timezone.utc).isoformat()})

@app.get("/api/events")
@require_auth
def events():
    limit = min(max(request.args.get("limit", 100, type=int), 1), 500)
    event_type = request.args.get("type")
    device = request.args.get("device")
    unread = request.args.get("unread")
    sql, params = "SELECT * FROM events WHERE 1=1", []
    if event_type in EVENT_TYPES:
        sql += " AND event_type=?"; params.append(event_type)
    if device:
        sql += " AND device_name LIKE ?"; params.append("%"+device[:80]+"%")
    if unread == "true":
        sql += " AND acknowledged=0"
    sql += " ORDER BY timestamp DESC LIMIT ?"; params.append(limit)
    with db() as con:
        rows = con.execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

@app.post("/api/events/demo")
@require_auth
def demo_event():
    if get_mode() != "demo":
        return jsonify({"error":"Demo event generation is disabled in live mode. Switch back to Demo to generate sample events."}), 403
    data = request.get_json(silent=True) or {}
    try:
        event, created = process_event(data, "simulated")
    except ValueError as exc:
        return jsonify({"error":str(exc)}), 400
    return jsonify({"event":event,"created":created}), 201 if created else 200

@app.patch("/api/events/<event_id>/acknowledge")
@require_auth
def acknowledge(event_id):
    with db() as con:
        cur = con.execute("UPDATE events SET acknowledged=1 WHERE id=?", (event_id,))
        if cur.rowcount == 0:
            return jsonify({"error":"Event not found"}), 404
        row = con.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    return jsonify(dict(row))

@app.delete("/api/events")
@require_auth
def clear_events():
    # For Distractive Action;But UI Ask Before Action
    with db() as con:
        con.execute("DELETE FROM events")
    return jsonify({"cleared":True})

@app.get("/api/settings")
@require_auth
def settings():
    return jsonify(get_settings())

@app.put("/api/settings")
@require_auth
def save_settings():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error":"Expected JSON object"}), 400
    allowed = set(DEFAULT_SETTINGS)
    current = get_settings()
    for key, value in data.items():
        if key not in allowed:
            return jsonify({"error":f"Unknown setting: {key}"}), 400
        if key == "alert_duration":
            if not isinstance(value, int) or not 3 <= value <= 60:
                return jsonify({"error":"alert_duration must be between 3 and 60"}), 400
        elif key == "theme":
            if value not in ("dark","light"):
                return jsonify({"error":"theme must be dark or light"}), 400
        elif not isinstance(value, bool):
            return jsonify({"error":f"{key} must be boolean"}), 400
        current[key] = value
    with db() as con:
        con.execute("UPDATE settings SET data=? WHERE id=1", (json.dumps(current),))
    return jsonify(current)

@app.get("/api/rules")
@require_auth
def rules():
    return jsonify(get_rules())

@app.post("/api/rules")
@require_auth
def create_rule():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name","")).strip()[:100]
    event_type = data.get("event_type")
    actions = data.get("actions", [])
    allowed_actions = {"fullscreen","visual","vibrate","flash","history","open_event","smart_display"}
    if not name or event_type not in EVENT_TYPES or not isinstance(actions,list) or not actions:
        return jsonify({"error":"Provide a name, supported event type, and one or more actions"}), 400
    if any(a not in allowed_actions for a in actions):
        return jsonify({"error":"Unsupported action selected"}), 400
    rule = {"name":name,"event_type":event_type,"actions":list(dict.fromkeys(actions)),
            "enabled":bool(data.get("enabled", True))}
    with db() as con:
        cur = con.execute("INSERT INTO rules(data) VALUES(?)", (json.dumps(rule),))
        rule["id"] = cur.lastrowid
    return jsonify(rule), 201

@app.patch("/api/rules/<int:rule_id>")
@require_auth
def toggle_rule(rule_id):
    with db() as con:
        row = con.execute("SELECT data FROM rules WHERE id=?", (rule_id,)).fetchone()
        if not row: return jsonify({"error":"Rule not found"}), 404
        rule = json.loads(row["data"])
        data = request.get_json(silent=True) or {}
        if "enabled" in data:
            if not isinstance(data["enabled"], bool): return jsonify({"error":"enabled must be boolean"}), 400
            rule["enabled"] = data["enabled"]
        con.execute("UPDATE rules SET data=? WHERE id=?", (json.dumps(rule), rule_id))
    return jsonify({"id":rule_id,**rule})

@app.get("/api/ring/status")
def ring_status():
    mode = get_mode()
    if mode != "live":
        return jsonify({"mode":"demo","connected":False,"label":"Demo simulator active",
                        "detail":"Events are simulated. No physical Ring device is connected."})
    # do not claim connectivity without an approved integration adapter.
    configured = bool(os.getenv("RING_ADAPTER_MODULE") and os.getenv("RING_ACCESS_TOKEN"))
    return jsonify({"mode":"live","connected":False,"label":"Live adapter not connected",
                    "detail":"Configure the hackathon-approved Ring adapter and credentials before live use.",
                    "credentials_configured":configured})

@app.post("/api/mode")
@require_auth
def set_mode():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode")
    if mode not in ("demo", "live"):
        return jsonify({"error":"mode must be demo or live"}), 400
    with db() as con:
        con.execute("INSERT INTO app_config(key,value) VALUES('mode',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (mode,))
    if mode == "live":
        return jsonify({"mode":"live", "connected":False, "message":"Live mode selected. The app will not invent Ring events; an approved Ring adapter must be configured and verified."})
    return jsonify({"mode":"demo", "message":"Demo simulator enabled. Generated events will be clearly labeled as simulated."})

@app.get("/api/events/export.csv")
@require_auth
def export_events():
    with db() as con:
        rows = con.execute("SELECT id,event_type,device_name,timestamp,description,source,acknowledged FROM events ORDER BY timestamp DESC").fetchall()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "event_type", "device_name", "timestamp", "description", "source", "acknowledged"])
    for row in rows: writer.writerow([row[k] for k in row.keys()])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment; filename=ring-accessible-alert-events.csv"})

@app.get("/api/stream")
@require_auth
def stream():
    def generate():
        last_id = request.headers.get("Last-Event-ID","")
        cursor = last_id
        while True:
            with db() as con:
                rows = con.execute("SELECT * FROM events WHERE timestamp > ? ORDER BY timestamp ASC", (cursor,)).fetchall()
            for row in rows:
                item = dict(row)
                cursor = item["timestamp"]
                yield f"id: {cursor}\nevent: ring-event\ndata: {json.dumps(item)}\n\n"
            yield "event: heartbeat\ndata: {}\n\n"
            time.sleep(1.2)
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})

@app.get("/api/automation/preview")
def automation_preview():
    return jsonify({"rules":get_rules(),"supported_actions":{
        "fullscreen":"Shows the in-app full-screen alert overlay",
        "visual":"Adds a prominent visual notification",
        "vibrate":"Uses browser vibration only if supported and permitted",
        "flash":"Brief visual border cue; never the only alert signal",
        "history":"Event is persisted in SQLite",
        "open_event":"Focuses the new event card",
        "smart_display":"Not connected in this prototype; requires a supported display integration"
    }})

if __name__ == "__main__":
    app.run(host=os.getenv("HOST","127.0.0.1"), port=int(os.getenv("PORT","5000")), debug=False, threaded=True)
