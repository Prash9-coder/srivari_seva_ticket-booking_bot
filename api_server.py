from fastapi import FastAPI, HTTPException, Response, UploadFile, File, Depends, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import threading
import uvicorn
import os
import time
import uuid
from typing import List, Optional

from ttd_bot import TTDBookingBot

app = FastAPI(title="TTD Bot API", version="1.0")

# Optional outbound notifications (webhooks)
NOTIFY_WEBHOOK_URL = os.getenv("NOTIFY_WEBHOOK_URL") or os.getenv("WEBHOOK_URL")

# Simple counters for metrics
_METRICS = {
    "bot_runs_total": 0,
    "bot_completed_total": 0,
    "last_run_duration_seconds": 0.0,
    "notifications_sent_total": 0,
    "notifications_failed_total": 0,
}

def _notify(event: str, payload: dict | None = None):
    url = NOTIFY_WEBHOOK_URL
    # Try to read from config if not set via env
    if not url:
        try:
            import json as _json
            if os.path.exists("srivari_group_data.json"):
                with open("srivari_group_data.json", "r", encoding="utf-8") as f:
                    cfg = _json.load(f) or {}
                    g = (cfg.get("general") or {})
                    url = g.get("webhook_url")
        except Exception:
            url = None
    if not url:
        return
    try:
        import json as _json
        import urllib.request
        # Build generic body
        body = {
            "event": event,
            "ts": time.time(),
            "status": {
                "running": bot.is_running,
                "browser_open": bot.is_browser_open,
            },
            "payload": payload or {},
        }
        headers = {"Content-Type": "application/json"}
        data_bytes = None
        # Slack-compatible formatting when posting to Slack incoming webhook
        if "slack.com" in (url or ""):
            # Create a compact message
            title_map = {
                "bot.started": ":rocket: TTD Bot started",
                "bot.stopped": ":stop_sign: TTD Bot stopped",
                "browser.closed": ":x: Browser closed",
            }
            title = title_map.get(event, f"TTD Bot: {event}")
            details = []
            try:
                if event == "bot.stopped" and isinstance(payload, dict) and payload.get("duration") is not None:
                    details.append(f"duration: {payload.get('duration'):.1f}s")
            except Exception:
                pass
            details.append(f"running={body['status']['running']}, browser={body['status']['browser_open']}")
            text = title + (" — " + ", ".join(details) if details else "")
            slack_payload = {"text": text}
            data_bytes = _json.dumps(slack_payload).encode("utf-8")
        else:
            data_bytes = _json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as _:
            pass
        _METRICS["notifications_sent_total"] += 1
    except Exception:
        _METRICS["notifications_failed_total"] += 1
        # swallow errors to not break API
        return

# Simple in-memory session store
SESSIONS: dict[str, float] = {}
SESSION_TTL = 24 * 3600  # 24h
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") or os.getenv("TTD_ADMIN_PASSWORD")

def _touch_session(token: str):
    SESSIONS[token] = time.time() + SESSION_TTL

def require_auth(session: Optional[str] = Cookie(default=None)):
    # Authentication disabled globally
    return True

class LoginPayload(BaseModel):
    password: str

@app.post("/login")
def login(payload: LoginPayload, resp: Response):
    # Authentication disabled globally; always OK
    return {"ok": True, "note": "auth disabled"}

@app.post("/logout")
def logout(session: Optional[str] = Cookie(default=None), resp: Response = None):
    # Authentication disabled globally; no-op
    if resp is not None:
        try:
            resp.delete_cookie("session")
        except Exception:
            pass
    return {"ok": True}

@app.get("/")
def root():
    # Helpful hint when someone opens the API root directly
    return {"ok": True, "message": "TTD Bot API is running", "docs": "/docs", "status": "/status"}

@app.get("/healthz")
def healthz():
    return {"ok": True, "uptime": max(0.0, time.time() - (TIMER.get("start") or time.time()))}

@app.get("/metrics")
def metrics():
    # Prometheus-style minimal text
    lines = []
    def add(name, value):
        lines.append(f"{name} {value}")
    add("bot_runs_total", _METRICS.get("bot_runs_total", 0))
    add("bot_completed_total", _METRICS.get("bot_completed_total", 0))
    add("notifications_sent_total", _METRICS.get("notifications_sent_total", 0))
    add("notifications_failed_total", _METRICS.get("notifications_failed_total", 0))
    add("last_run_duration_seconds", _METRICS.get("last_run_duration_seconds", 0.0))
    return Response(content="\n".join(str(x) for x in lines) + "\n", media_type="text/plain")

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploads so frontend can preview images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# Serve project images folder for existing paths like 'images/1.jpg'
app.mount("/images", StaticFiles(directory=os.path.join(os.getcwd(), "images")), name="images")

# Allow frontend origins via env (plus dev defaults)
_frontend_origins = os.getenv("FRONTEND_ORIGINS", "").split(",") if os.getenv("FRONTEND_ORIGINS") else []
_frontend_origins = [o.strip() for o in _frontend_origins if o.strip()]
allow_origins = ["http://localhost:5173", "http://127.0.0.1:5173"] + _frontend_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,  # needed so browser sends cookies
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Single bot instance (headless)
bot = TTDBookingBot(root=None)

# Load persisted general flags into bot on startup
try:
    import json
    # Prefer env-provided config path if present
    _cfg_path = os.getenv("TTD_CONFIG_PATH") or "srivari_group_data.json"
    if os.path.exists(_cfg_path):
        with open(_cfg_path, "r", encoding="utf-8") as f:
            cfg = json.load(f) or {}
            g = (cfg.get("general") or {})
            bot.respect_existing = bool(g.get("respect_existing", True))
            v = int(g.get("aadhaar_autofill_wait_seconds", 6))
            bot.aadhaar_autofill_wait_seconds = max(1, min(v, 30))
except Exception:
    pass

# Simple run timer to measure fill duration (start on /start, auto-finish when final save detected)
TIMER = {
    "start": None,   # float epoch seconds
    "end": None,     # float epoch seconds
    "last_seq": 0,   # last processed log seq
}


def _timer_start():
    # Start immediately when API /start is called
    TIMER["start"] = time.time()
    TIMER["end"] = None
    # Reset last processed sequence so we can detect final-save from fresh
    try:
        TIMER["last_seq"] = bot._log_buffer[-1]["seq"] if bot._log_buffer else 0
    except Exception:
        TIMER["last_seq"] = 0


def _timer_finish():
    if TIMER.get("start") and not TIMER.get("end"):
        TIMER["end"] = time.time()


def _timer_check_logs_for_completion():
    # Detect the start (first fill) and completion (final reset) from logs
    try:
        last_seq = TIMER.get("last_seq", 0)
        for item in list(bot._log_buffer):
            seq = item.get("seq", 0)
            if seq <= last_seq:
                continue
            msg = (item.get("msg") or "").lower()
            # Start timer when we begin filling team leader
            if TIMER.get("start") is None and ("filling team leader" in msg or "srivari seva form detected" in msg):
                TIMER["start"] = time.time()
            # Finish timer when final reset detected
            if "detected final form reset" in msg:
                _timer_finish()
            TIMER["last_seq"] = max(TIMER.get("last_seq", 0), seq)
    except Exception:
        pass


class StartPayload(BaseModel):
    open_browser: bool = True

class SchedulePayload(BaseModel):
    # epoch seconds to start; if in the past, starts immediately
    start_at: Optional[float] = None

class Member(BaseModel):
    name: Optional[str] = None 
    dob: Optional[str] = None
    age: Optional[str] = None
    blood_group: Optional[str] = None
    gender: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_number: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    street: Optional[str] = None
    doorno: Optional[str] = None
    pincode: Optional[str] = None
    nearest_ttd_temple: Optional[str] = None
    photo: Optional[str] = None

class General(BaseModel):
    group_size: Optional[int] = None
    download_dir: Optional[str] = None
    auto_select_date: Optional[bool] = None
    auto_download_ticket: Optional[bool] = None
    respect_existing: Optional[bool] = True
    aadhaar_autofill_wait_seconds: Optional[int] = 6

class ConfigPayload(BaseModel):
    general: General
    members: List[Member]

@app.get("/status")
def status():
    # Update timer by scanning recent logs for the final-save message
    _timer_check_logs_for_completion()
    url = None
    try:
        if bot.driver:
            url = bot.driver.current_url
    except Exception:
        url = None
    now = time.time()
    elapsed = None
    if TIMER.get("start"):
        if TIMER.get("end"):
            elapsed = max(0.0, TIMER["end"] - TIMER["start"]) 
        else:
            elapsed = max(0.0, now - TIMER["start"]) 
    return {
        "running": bot.is_running,
        "browser_open": bot.is_browser_open,
        "has_driver": bot.driver is not None,
        "url": url,
        "timer": {
            "started": bool(TIMER.get("start")),
            "ended": bool(TIMER.get("end")),
            "start": TIMER.get("start"),
            "end": TIMER.get("end"),
            "elapsed_seconds": elapsed,
        },
    }

@app.get("/timer")
def get_timer():
    # On demand, also try to auto-finish if final-save was logged
    _timer_check_logs_for_completion()
    now = time.time()
    elapsed = None
    if TIMER.get("start"):
        if TIMER.get("end"):
            elapsed = max(0.0, TIMER["end"] - TIMER["start"]) 
        else:
            elapsed = max(0.0, now - TIMER["start"]) 
    return {
        "started": bool(TIMER.get("start")),
        "ended": bool(TIMER.get("end")),
        "start": TIMER.get("start"),
        "end": TIMER.get("end"),
        "elapsed_seconds": elapsed,
    }

@app.post("/open-browser")
def open_browser(_: bool = Depends(require_auth)):
    threading.Thread(target=bot.open_browser, daemon=True).start()
    return {"ok": True}

@app.post("/start")
def start(payload: StartPayload | None = None, _: bool = Depends(require_auth)):
    if payload and payload.open_browser:
        if not bot.is_browser_open:
            threading.Thread(target=bot.open_browser, daemon=True).start()
    if not bot.is_running:
        _timer_start()
        bot.start_bot()
        _METRICS["bot_runs_total"] += 1
        _notify("bot.started", {"at": TIMER.get("start")})
    return {"ok": True}

# Simple one-shot scheduler stored in memory
_SCHED = {"thread": None, "at": None}

@app.post("/schedule")
def schedule(payload: SchedulePayload, _: bool = Depends(require_auth)):
    when = float(payload.start_at or 0)
    if when <= 0:
        raise HTTPException(status_code=400, detail="start_at (epoch seconds) is required")
    now = time.time()
    delay = max(0.0, when - now)

    # cancel existing
    t = _SCHED.get("thread")
    if t:
        try:
            # Python threads cannot be force-stopped; we rely on short sleep loop
            _SCHED["thread"] = None
        except Exception:
            pass

    def worker():
        target = time.time() + delay
        while time.time() < target:
            time.sleep(0.5)
            if _SCHED.get("thread") is None:
                return
        try:
            # Open browser if not open, then start
            if not bot.is_browser_open:
                bot.open_browser()
            if not bot.is_running:
                _timer_start()
                bot.start_bot()
        finally:
            _SCHED["thread"] = None
            _SCHED["at"] = None

    thr = threading.Thread(target=worker, daemon=True)
    _SCHED["thread"] = thr
    _SCHED["at"] = when
    thr.start()
    return {"ok": True, "scheduled_for": when}

@app.get("/schedule")
def get_schedule(_: bool = Depends(require_auth)):
    return {"at": _SCHED.get("at")}

@app.post("/schedule/cancel")
def cancel_schedule(_: bool = Depends(require_auth)):
    if _SCHED.get("thread"):
        _SCHED["thread"] = None
        _SCHED["at"] = None
    return {"ok": True}

@app.post("/stop")
def stop(_: bool = Depends(require_auth)):
    bot.stop_bot()
    _timer_finish()
    try:
        if TIMER.get("start") and TIMER.get("end"):
            _METRICS["last_run_duration_seconds"] = max(0.0, TIMER["end"] - TIMER["start"])
            _METRICS["bot_completed_total"] += 1
    except Exception:
        pass
    _notify("bot.stopped", {"duration": _METRICS.get("last_run_duration_seconds")})
    return {"ok": True}

@app.post("/close-browser")
def close_browser(_: bool = Depends(require_auth)):
    try:
        if bot.driver:
            try:
                bot.driver.quit()
            except Exception:
                pass
        bot.driver = None
        bot.is_browser_open = False
        bot.log_message("Browser closed via API.")
        _timer_finish()
        _notify("browser.closed", {})
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screenshot")
def screenshot(_: bool = Depends(require_auth)):
    try:
        if not bot.driver:
            raise HTTPException(status_code=409, detail="Driver not available")
        data = bot.driver.get_screenshot_as_png()
        return Response(content=data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/current-url")
def current_url(_: bool = Depends(require_auth)):
    try:
        if not bot.driver:
            return {"url": None}
        return {"url": bot.driver.current_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
def logs(since: int = 0, _: bool = Depends(require_auth)):
    # Return buffered logs newer than sequence 'since' and also update timer state if final-save seen
    items = []
    latest = since
    try:
        for item in list(bot._log_buffer):
            seq = item.get("seq", 0)
            if seq > since:
                items.append(item)
                latest = max(latest, seq)
    except Exception:
        pass
    # Update timer by checking any new logs since last check
    _timer_check_logs_for_completion()
    return {"items": items, "latest": latest}

@app.get("/config")
def get_config(_: bool = Depends(require_auth)):
    cfg = bot.load_srivari_source()
    return cfg

@app.post("/config/path")
def set_config_path(path: str, _: bool = Depends(require_auth)):
    # Allow selecting a different group JSON at runtime (per-process)
    try:
        import os as _os
        # Expand env vars and user home
        resolved = _os.path.expandvars(_os.path.expanduser(path))
        if not _os.path.isabs(resolved):
            resolved = _os.path.abspath(resolved)
        if not _os.path.exists(resolved):
            raise HTTPException(status_code=400, detail="Config file not found")
        _os.environ["TTD_CONFIG_PATH"] = resolved
        # Trigger immediate reload for any watchers
        try:
            bot._members_file = resolved
            bot._members_mtime = _os.path.getmtime(resolved)
        except Exception:
            pass
        bot.log_message(f"Config path updated to: {resolved}")
        return {"ok": True, "path": resolved}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
def set_config(payload: ConfigPayload, _: bool = Depends(require_auth)):
    data = {
        "general": (payload.general.model_dump(exclude_none=True) if payload.general else {}),
        "members": [m.model_dump(exclude_none=True) for m in (payload.members or [])],
    }
    try:
        # Write to configured path if provided
        import os
        cfg_path = os.getenv("TTD_CONFIG_PATH") or os.path.join(os.getcwd(), "srivari_group_data.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2)
        # Apply behavior flags immediately to running bot
        try:
            g = data.get("general", {})
            bot.respect_existing = bool(g.get("respect_existing", True))
            v = int(g.get("aadhaar_autofill_wait_seconds", 6))
            bot.aadhaar_autofill_wait_seconds = max(1, min(v, 30))
        except Exception:
            pass
        bot.log_message("Configuration updated via API.")
        return {"ok": True, "path": cfg_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    try:
        # Sanitize filename and save to uploads directory
        import uuid
        from pathlib import Path
        suffix = Path(file.filename).suffix.lower()
        if suffix not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        new_name = f"{uuid.uuid4().hex}{suffix}"
        dest_path = os.path.join(UPLOAD_DIR, new_name)
        with open(dest_path, "wb") as out:
            out.write(await file.read())
        # Return a relative path we can store in config
        return {"ok": True, "path": f"uploads/{new_name}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/import-csv")
async def import_csv(file: UploadFile = File(...), _: bool = Depends(require_auth)):
    try:
        import csv, io
        raw = await file.read()
        text = raw.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        def norm(s: str) -> str:
            return "" if s is None else str(s).strip()
        # header normalization map
        def keynorm(k: str) -> str:
            k = (k or "").strip().lower()
            k = k.replace(" ", "").replace("-", "").replace("_", "")
            return k
        aliases = {
            "idproof": "id_proof_type", "idprooftype": "id_proof_type", "idtype": "id_proof_type",
            "aadhaar": "id_number", "aadhar": "id_number", "aadharno": "id_number", "aadhar_number": "id_number", "aadhaarno": "id_number",
            "doorno": "doorno", "doornumber": "doorno", "door_no": "doorno",
            "bloodgroup": "blood_group", "blood_grp": "blood_group",
            "nearestattdtemple": "nearest_ttd_temple", "nearestttdtemple": "nearest_ttd_temple",
        }
        allowed = {"name","dob","age","blood_group","gender","id_proof_type","id_number","mobile","email","state","district","city","street","doorno","pincode","nearest_ttd_temple","photo"}
        members = []
        for row in reader:
            item = {}
            for k, v in (row or {}).items():
                nk = aliases.get(keynorm(k), None)
                if not nk:
                    # map exact canonical if already valid
                    ck = k.lower().strip()
                    if ck in allowed:
                        nk = ck
                if nk in allowed:
                    val = norm(v)
                    if val != "":
                        item[nk] = val
            if item:
                members.append(item)
            if len(members) >= 100:  # server-side limit
                break
        return {"ok": True, "members": members}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV parse error: {e}")

@app.get("/export/csv")
def export_csv(_: bool = Depends(require_auth)):
    try:
        import csv, io
        cfg = bot.load_srivari_source() or {}
        members = cfg.get("members", []) or []
        headers = ["name","dob","age","blood_group","gender","id_proof_type","id_number","mobile","email","state","district","city","street","doorno","pincode","nearest_ttd_temple","photo"]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for m in members:
            try:
                writer.writerow({h: (m.get(h) or "") for h in headers})
            except Exception:
                pass
        data = buf.getvalue()
        return Response(content=data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=srivari_members.csv"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/json")
def export_json(_: bool = Depends(require_auth)):
    try:
        import json as _json
        cfg = bot.load_srivari_source() or {}
        data = _json.dumps(cfg, indent=2)
        return Response(content=data, media_type="application/json", headers={"Content-Disposition": "attachment; filename=srivari_config.json"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run API server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)