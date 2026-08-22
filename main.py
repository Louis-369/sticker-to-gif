import os
import time
import shutil
import zipfile
import asyncio
import subprocess
from typing import List
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from scraper import scrape_line_stickers
from converter import process_sticker_ezgif

app = FastAPI(title="Sticker to GIF Backend Automator")

# Enable CORS for GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_BASE_DIR = "/tmp/LINE_Stickers"
os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

# Mount files for direct download
app.mount("/files", StaticFiles(directory=OUTPUT_BASE_DIR), name="files")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Automatic TTL Cleanup: Removes temporary generated GIFs/ZIPs older than 2 hours to protect free RAM
def cleanup_old_files():
    try:
        now = time.time()
        for item in os.listdir(OUTPUT_BASE_DIR):
            item_path = os.path.join(OUTPUT_BASE_DIR, item)
            # 2 hours TTL = 7200 seconds
            if os.path.getmtime(item_path) < (now - 7200):
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    os.remove(item_path)
    except Exception:
        pass

# Processing state
current_task = {
    "status": "idle",
    "progress": 0,
    "total": 0,
    "logs": [],
    "results": [],
    "folder_path": ""
}

class ParseRequest(BaseModel):
    url: str

class SingleConvertRequest(BaseModel):
    sticker: dict
    title: str

class ProcessRequest(BaseModel):
    stickers: List[dict]
    title: str

@app.get("/")
def get_index():
    cleanup_old_files()
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Sticker to GIF Backend"}

@app.post("/api/parse")
def parse_stickers(req: ParseRequest):
    try:
        data = scrape_line_stickers(req.url.strip())
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析貼圖失敗: {str(e)}")

@app.post("/api/convert-single")
def convert_single(req: SingleConvertRequest):
    try:
        clean_title = "".join(c for c in req.title if c.isalnum() or c in (' ', '_', '-')).strip() or "StickerSet"
        set_dir = os.path.join(OUTPUT_BASE_DIR, clean_title)
        os.makedirs(set_dir, exist_ok=True)
        
        res = process_sticker_ezgif(req.sticker, set_dir)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ezgif 轉檔失敗: {str(e)}")

async def run_batch_process(stickers: list, title: str):
    global current_task
    current_task["status"] = "processing"
    current_task["total"] = len(stickers)
    current_task["progress"] = 0
    current_task["logs"] = [f"🚀 開始透過 ezgif 處理項目組：{title}，共 {len(stickers)} 張..."]
    current_task["results"] = []
    
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip() or "StickerSet"
    set_dir = os.path.join(OUTPUT_BASE_DIR, clean_title)
    os.makedirs(set_dir, exist_ok=True)
    current_task["folder_path"] = set_dir
    
    for idx, s in enumerate(stickers):
        s_id = s.get("id")
        is_anim = s.get("is_animated", False)
        type_str = "動態 (ezgif 轉 GIF)" if is_anim else "靜態 (PNG)"
        
        current_task["logs"].append(f"[{idx+1}/{len(stickers)}] 正在透過 ezgif 處理 #{s_id} ({type_str})...")
        
        try:
            res = process_sticker_ezgif(s, set_dir)
            current_task["logs"].append(f"✅ #{s_id} 處理完成！")
            current_task["results"].append({
                "id": s_id,
                "type": res["type"],
                "filename": res["filename"],
                "download_url": res["url"],
                "success": True
            })
        except Exception as err:
            current_task["logs"].append(f"❌ #{s_id} ezgif 轉檔失敗: {str(err)}")
            current_task["results"].append({
                "id": s_id,
                "success": False,
                "error": str(err)
            })
            
        current_task["progress"] = idx + 1
        await asyncio.sleep(0.3)
        
    current_task["logs"].append(f"🎉 全部處理完成！所有檔案已準備就緒！")
    current_task["status"] = "completed"

@app.post("/api/process")
async def process_stickers(req: ProcessRequest, background_tasks: BackgroundTasks):
    global current_task
    if current_task["status"] == "processing":
        raise HTTPException(status_code=400, detail="已經有一個任務正在進行中")
        
    background_tasks.add_task(run_batch_process, req.stickers, req.title)
    return {"message": "Task started successfully"}

@app.get("/api/task-status")
def get_task_status():
    global current_task
    return current_task

@app.get("/api/download-zip")
def download_zip(title: str):
    clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).strip() or "StickerSet"
    set_dir = os.path.join(OUTPUT_BASE_DIR, clean_title)
    if not os.path.exists(set_dir):
        raise HTTPException(status_code=404, detail="Directory not found")
        
    zip_path = os.path.join(OUTPUT_BASE_DIR, f"{clean_title}.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(set_dir):
            for f in files:
                if not f.endswith(".zip"):
                    zipf.write(os.path.join(root, f), f)
                
    return FileResponse(zip_path, filename=f"{clean_title}.zip", media_type="application/zip")
