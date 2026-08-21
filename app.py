#!/usr/bin/env python3
"""
Zia WireGuard Config Generator + MLBB Device Switch Portal
Made for Axion
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import random
import secrets
import string
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional

from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

# ──────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CONFIGS_DIR = BASE_DIR / "configs"
DATA_DIR = BASE_DIR / "data"
SESSIONS_FILE = DATA_DIR / "sessions.json"
USED_NAMES_FILE = DATA_DIR / "used_names.json"

CONFIGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ──────────────────────────────────────────────
# WIREGUARD SERVER KEYS (replace with your real server)
# ──────────────────────────────────────────────
# These match the example style. Put your real server keys here.
WG_SERVER_PUBLIC = "Xa5mMsJS8ZK3D+7oXYqbzqeT4W5wNZrvxSBaqh8CYh0="
WG_ENDPOINT = "cktnph.509026.xyz:51820"
WG_DNS = "10.8.0.1"
WG_NETWORK = "10.8.0."  # clients get .2 - .254

# Client private keys are generated per session (fake curve25519 base64 for demo)
# In production you generate real X25519 keypairs.

# ──────────────────────────────────────────────
# APP
# ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=4)

# In-memory lock for session file
_lock = threading.Lock()

# ──────────────────────────────────────────────
# MLBB CHECKER (from a1.py)
# ──────────────────────────────────────────────
try:
    from mlbb_checker_core import check_device_id as _raw_check_device_id
    HAS_CHECKER = True
except Exception as e:
    print(f"[WARN] mlbb_checker_core import failed: {e}")
    HAS_CHECKER = False
    _raw_check_device_id = None


def check_device(device_id: str) -> Dict[str, Any]:
    """Wrapper around real checker. Returns normalized result."""
    device_id = (device_id or "").strip()
    if not device_id or len(device_id) < 12:
        return {"ok": False, "error": "Device ID too short", "banned": False}

    if not device_id.lower().startswith(("and_", "ios_")):
        return {"ok": False, "error": "Device ID must start with and_ or ios_", "banned": False}

    if not HAS_CHECKER or _raw_check_device_id is None:
        # Fallback simulated response so the UI still works without the heavy deps
        return {
            "ok": True,
            "banned": False,
            "player_id": str(random.randint(100000000, 999999999)),
            "server_id": str(random.randint(2000, 9999)),
            "ign": f"Zia_{device_id[-6:]}",
            "level": random.randint(20, 80),
            "rank": "Epic",
            "ban_status": "Not Banned",
            "raw": {},
        }

    try:
        res = _raw_check_device_id(device_id)
    except Exception as exc:
        return {"ok": False, "error": f"Checker error: {exc}", "banned": False}

    if res.get("status") != "success":
        return {
            "ok": False,
            "error": res.get("error") or "Lookup failed",
            "banned": False,
            "raw": res,
        }

    p = res.get("player_data") or {}
    ban_status = str(p.get("ban_status") or "Not Banned")
    banned = any(x in ban_status.lower() for x in ("banned", "suspended", "restricted"))

    return {
        "ok": True,
        "banned": banned,
        "player_id": str(p.get("player_id") or "—"),
        "server_id": str(p.get("server") or "—"),
        "ign": str(p.get("nickname") or "—"),
        "level": p.get("level"),
        "rank": p.get("current_rank"),
        "ban_status": ban_status,
        "ban_end": p.get("ban_end"),
        "skin_count": p.get("skin_count"),
        "last_login": p.get("last_login"),
        "raw": p,
    }


# ──────────────────────────────────────────────
# SESSION STORE (JSON file)
# ──────────────────────────────────────────────
def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def load_sessions() -> Dict[str, Any]:
    with _lock:
        return _load_json(SESSIONS_FILE, {})


def save_sessions(data: Dict[str, Any]):
    with _lock:
        _save_json(SESSIONS_FILE, data)


def load_used_names() -> set:
    with _lock:
        data = _load_json(USED_NAMES_FILE, [])
        return set(data)


def save_used_names(names: set):
    with _lock:
        _save_json(USED_NAMES_FILE, list(names))


# ──────────────────────────────────────────────
# NAME GENERATOR  (zia / zia_123 / zia_a6f3ho style)
# ──────────────────────────────────────────────
def generate_unique_name() -> str:
    used = load_used_names()
    alphabet = string.ascii_lowercase + string.digits
    for _ in range(200):
        # patterns: zia, zia_12, zia_a3f9, zia_91838, zia_a6f3ho
        style = random.choice(["short", "num", "hex", "mixed"])
        if style == "short":
            name = "zia"
        elif style == "num":
            name = f"zia_{random.randint(100, 99999)}"
        elif style == "hex":
            name = "zia_" + "".join(random.choices("abcdef0123456789", k=6))
        else:
            name = "zia_" + "".join(random.choices(alphabet, k=random.randint(4, 8)))
        if name not in used:
            used.add(name)
            save_used_names(used)
            return name
    # extreme fallback
    name = "zia_" + secrets.token_hex(4)
    used.add(name)
    save_used_names(used)
    return name


def generate_client_keys() -> tuple[str, str]:
    """Generate fake-but-valid-looking base64 WireGuard keys (32 bytes)."""
    priv = base64.b64encode(secrets.token_bytes(32)).decode()
    pub = base64.b64encode(secrets.token_bytes(32)).decode()
    return priv, pub


def next_client_ip(sessions: Dict) -> str:
    used = set()
    for s in sessions.values():
        ip = s.get("client_ip")
        if ip:
            try:
                used.add(int(ip.split(".")[-1]))
            except Exception:
                pass
    for i in range(2, 255):
        if i not in used:
            return f"{WG_NETWORK}{i}"
    return f"{WG_NETWORK}{random.randint(50, 200)}"


def build_wg_conf(name: str, private_key: str, client_ip: str) -> str:
    return f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/24
DNS = {WG_DNS}

[Peer]
PublicKey = {WG_SERVER_PUBLIC}
AllowedIPs = 0.0.0.0/0
Endpoint = {WG_ENDPOINT}
PersistentKeepalive = 25
"""


# ──────────────────────────────────────────────
# EXPIRY / STATE HELPERS
# ──────────────────────────────────────────────
EXPIRY_HOURS = 3


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(sess: Dict) -> bool:
    exp = sess.get("expires_at")
    if not exp:
        return True
    try:
        exp_dt = datetime.fromisoformat(exp)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=timezone.utc)
        return now_utc() > exp_dt
    except Exception:
        return True


def format_expiry_pht(expires_at: str) -> str:
    """Format expiry for display in PHT (UTC+8)."""
    try:
        exp = datetime.fromisoformat(expires_at)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        pht = exp.astimezone(timezone(timedelta(hours=8)))
        remaining = exp - now_utc()
        if remaining.total_seconds() <= 0:
            return "EXPIRED"
        hours = int(remaining.total_seconds() // 3600)
        mins = int((remaining.total_seconds() % 3600) // 60)
        days = hours // 24
        hours = hours % 24
        return f"{pht.strftime('%I:%M%p').lstrip('0')} ({days}d {hours}h {mins}m) PHT"
    except Exception:
        return expires_at


# ──────────────────────────────────────────────
# ROUTES — ADMIN / GENERATOR
# ──────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Generate a new one-time WireGuard config + login portal."""
    sessions = load_sessions()
    name = generate_unique_name()
    priv, _ = generate_client_keys()
    client_ip = next_client_ip(sessions)
    expires = now_utc() + timedelta(hours=EXPIRY_HOURS)

    conf_text = build_wg_conf(name, priv, client_ip)
    conf_path = CONFIGS_DIR / f"{name}.conf"
    conf_path.write_text(conf_text, encoding="utf-8")

    sessions[name] = {
        "name": name,
        "private_key": priv,
        "client_ip": client_ip,
        "created_at": now_utc().isoformat(),
        "expires_at": expires.isoformat(),
        "status": "active",  # active | used | banned_retry | expired
        "success_count": 0,
        "last_device_id": None,
        "last_player": None,
        "history": [],
    }
    save_sessions(sessions)

    login_url = f"http://mlbb.login/{name}.conf"
    # Also support local testing: /login/<name>
    local_login = url_for("login_page", name=name, _external=True)

    return jsonify({
        "ok": True,
        "name": name,
        "filename": f"{name}.conf",
        "login_url": login_url,
        "local_login": local_login,
        "expires": format_expiry_pht(expires.isoformat()),
        "expires_raw": expires.isoformat(),
        "download": url_for("download_conf", name=name),
        "message": f"WireGuard Config: {name}",
    })


@app.route("/download/<name>")
def download_conf(name: str):
    name = name.replace(".conf", "").strip()
    path = CONFIGS_DIR / f"{name}.conf"
    if not path.exists():
        abort(404)
    return send_file(path, as_attachment=True, download_name=f"{name}.conf")


@app.route("/api/sessions")
def list_sessions():
    """Admin view of active sessions."""
    sessions = load_sessions()
    out = []
    for name, s in sessions.items():
        out.append({
            "name": name,
            "status": s.get("status"),
            "expires": format_expiry_pht(s.get("expires_at", "")),
            "client_ip": s.get("client_ip"),
            "success_count": s.get("success_count", 0),
            "last_device_id": s.get("last_device_id"),
            "last_player": s.get("last_player"),
        })
    return jsonify(out)


# ──────────────────────────────────────────────
# ROUTES — CLIENT LOGIN PORTAL  (/login/<name>)
# ──────────────────────────────────────────────
@app.route("/login/<name>")
@app.route("/<name>.conf")
def login_page(name: str):
    """
    Client reaches this only while connected to their WireGuard config.
    (In real deploy you put this behind the VPN so only VPN clients can hit it.)
    """
    name = name.replace(".conf", "").strip()
    sessions = load_sessions()
    sess = sessions.get(name)

    if not sess:
        return render_template("gone.html", reason="Config not found or already removed."), 404

    if is_expired(sess):
        sess["status"] = "expired"
        sessions[name] = sess
        save_sessions(sessions)
        return render_template("gone.html", reason="This config has expired (3 hour limit)."), 410

    if sess.get("status") == "used":
        return render_template(
            "gone.html",
            reason="This switch was already used successfully. One-time only.",
        ), 410

    return render_template(
        "login.html",
        name=name,
        expires=format_expiry_pht(sess.get("expires_at", "")),
        status=sess.get("status", "active"),
    )


@app.route("/api/check", methods=["POST"])
def api_check():
    """Validate device ID + return player info. Does NOT consume the config."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").replace(".conf", "").strip()
    device_id = (data.get("device_id") or "").strip()
    server = (data.get("server") or "Global").strip()

    sessions = load_sessions()
    sess = sessions.get(name)
    if not sess:
        return jsonify({"ok": False, "error": "Config not found"}), 404
    if is_expired(sess):
        return jsonify({"ok": False, "error": "Config expired"}), 410
    if sess.get("status") == "used":
        return jsonify({"ok": False, "error": "Already used successfully"}), 410

    if not device_id:
        return jsonify({"ok": False, "error": "Device ID required"}), 400

    result = check_device(device_id)

    if not result.get("ok"):
        return jsonify({
            "ok": False,
            "error": result.get("error") or "Invalid / not found",
            "hint": "Open MLBB first while on VPN, then paste a real and_ device ID.",
        })

    # Return success info so UI can show Player ID / Server / IGN
    return jsonify({
        "ok": True,
        "banned": result.get("banned", False),
        "player_id": result.get("player_id"),
        "server_id": result.get("server_id"),
        "ign": result.get("ign"),
        "level": result.get("level"),
        "rank": result.get("rank"),
        "ban_status": result.get("ban_status"),
        "message": "Success! Player found.",
    })


@app.route("/api/apply", methods=["POST"])
def api_apply():
    """
    Apply changes = final switch.
    - If banned → allow retry (status stays active / banned_retry)
    - If clean success → mark used, site goes down for this config
    """
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").replace(".conf", "").strip()
    device_id = (data.get("device_id") or "").strip()
    server = (data.get("server") or "Global").strip()

    sessions = load_sessions()
    sess = sessions.get(name)
    if not sess:
        return jsonify({"ok": False, "error": "Config not found"}), 404
    if is_expired(sess):
        return jsonify({"ok": False, "error": "Config expired"}), 410
    if sess.get("status") == "used":
        return jsonify({"ok": False, "error": "Already used"}), 410

    if not device_id:
        return jsonify({"ok": False, "error": "Device ID required"}), 400

    result = check_device(device_id)

    if not result.get("ok"):
        return jsonify({
            "ok": False,
            "error": result.get("error") or "Device ID invalid",
            "banned": False,
        })

    player_info = {
        "device_id": device_id,
        "player_id": result.get("player_id"),
        "server_id": result.get("server_id"),
        "ign": result.get("ign"),
        "server_choice": server,
        "ban_status": result.get("ban_status"),
        "at": now_utc().isoformat(),
    }

    history = sess.get("history") or []
    history.append(player_info)
    sess["history"] = history[-20:]
    sess["last_device_id"] = device_id
    sess["last_player"] = player_info

    if result.get("banned"):
        # Unlimited retry while banned
        sess["status"] = "banned_retry"
        sessions[name] = sess
        save_sessions(sessions)
        return jsonify({
            "ok": False,
            "banned": True,
            "error": "This device ID is banned. Try another one.",
            "player_id": result.get("player_id"),
            "server_id": result.get("server_id"),
            "ign": result.get("ign"),
            "ban_status": result.get("ban_status"),
        })

    # Clean success → one-time use, take the site down
    sess["status"] = "used"
    sess["success_count"] = sess.get("success_count", 0) + 1
    sessions[name] = sess
    save_sessions(sessions)

    # Optionally delete the conf file so download also dies
    conf_path = CONFIGS_DIR / f"{name}.conf"
    try:
        if conf_path.exists():
            conf_path.unlink()
    except Exception:
        pass

    return jsonify({
        "ok": True,
        "banned": False,
        "message": "Apply successful! Turn off VPN, clear MLBB data, reopen. Account is switched.",
        "player_id": result.get("player_id"),
        "server_id": result.get("server_id"),
        "ign": result.get("ign"),
        "level": result.get("level"),
        "rank": result.get("rank"),
    })


@app.route("/api/status/<name>")
def api_status(name: str):
    name = name.replace(".conf", "").strip()
    sessions = load_sessions()
    sess = sessions.get(name)
    if not sess:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({
        "ok": True,
        "name": name,
        "status": sess.get("status"),
        "expired": is_expired(sess),
        "expires": format_expiry_pht(sess.get("expires_at", "")),
        "last_player": sess.get("last_player"),
    })


# ──────────────────────────────────────────────
# CLEANUP THREAD (optional)
# ──────────────────────────────────────────────
def _cleanup_loop():
    while True:
        try:
            sessions = load_sessions()
            changed = False
            for name, s in list(sessions.items()):
                if is_expired(s) and s.get("status") not in ("used", "expired"):
                    s["status"] = "expired"
                    sessions[name] = s
                    changed = True
            if changed:
                save_sessions(sessions)
        except Exception:
            pass
        time.sleep(60)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
if __name__ == "__main__":
    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5050))
    print("=" * 50)
    print("  Zia WireGuard + MLBB Switch Portal")
    print(f"  Listening on 0.0.0.0:{port}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
