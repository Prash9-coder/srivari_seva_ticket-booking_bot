from fastapi import FastAPI, HTTPException, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import threading
import uvicorn
import os
from typing import List, Optional

from ttd_bot import TTDBookingBot

app = FastAPI(title="TTD Bot API", version="1.0")

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploads so frontend can preview images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# Serve project images folder for existing paths like 'images/1.jpg'
app.mount("/images", StaticFiles(directory=os.path.join(os.getcwd(), "images")), name="images")

# Allow local dev frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Single bot instance (headless)
bot = TTDBookingBot(root=None)

class StartPayload(BaseModel):
    open_browser: bool = True

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
    photo: Optional[str] = None

class General(BaseModel):
    group_size: Optional[int] = None
    download_dir: Optional[str] = None
    auto_select_date: Optional[bool] = None
    auto_download_ticket: Optional[bool] = None

class ConfigPayload(BaseModel):
    general: General
    members: List[Member]

@app.get("/status")
def status():
    url = None
    try:
        if bot.driver:
            url = bot.driver.current_url
    except Exception:
        url = None
    return {
        "running": bot.is_running,
        "browser_open": bot.is_browser_open,
        "has_driver": bot.driver is not None,
        "url": url,
    }

@app.post("/open-browser")
def open_browser():
    threading.Thread(target=bot.open_browser, daemon=True).start()
    return {"ok": True}

@app.post("/start")
def start(payload: StartPayload | None = None):
    if payload and payload.open_browser:
        if not bot.is_browser_open:
            threading.Thread(target=bot.open_browser, daemon=True).start()
    if not bot.is_running:
        bot.start_bot()
    return {"ok": True}

@app.post("/stop")
def stop():
    bot.stop_bot()
    return {"ok": True}

@app.post("/close-browser")
def close_browser():
    try:
        if bot.driver:
            try:
                bot.driver.quit()
            except Exception:
                pass
        bot.driver = None
        bot.is_browser_open = False
        bot.log_message("Browser closed via API.")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/screenshot")
def screenshot():
    try:
        if not bot.driver:
            raise HTTPException(status_code=409, detail="Driver not available")
        # Capture PNG bytes
        data = bot.driver.get_screenshot_as_png()
        return Response(content=data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/current-url")
def current_url():
    try:
        if not bot.driver:
            return {"url": None}
        return {"url": bot.driver.current_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs")
def logs(since: int = 0):
    # Return buffered logs newer than sequence 'since'
    items = []
    try:
        for item in list(bot._log_buffer):
            if item.get("seq", 0) > since:
                items.append(item)
    except Exception:
        pass
    latest = items[-1]["seq"] if items else since
    return {"items": items, "latest": latest}

@app.get("/config")
def get_config():
    cfg = bot.load_srivari_source()
    return cfg

@app.post("/config")
def set_config(payload: ConfigPayload):
    data = {
        "general": (payload.general.model_dump(exclude_none=True) if payload.general else {}),
        "members": [m.model_dump(exclude_none=True) for m in (payload.members or [])],
    }
    try:
        with open("srivari_group_data.json", "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2)
        bot.log_message("Configuration updated via API.")
        return {"ok": True}
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

if __name__ == "__main__":
    # Run API server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="127.0.0.1", port=port)