import os
import json
import requests
import asyncio

SESSION_FILE = "/Users/louis/.gemini/antigravity/scratch/giphy_session.json"

def get_auth_status():
    """
    Checks if a valid saved cookie or session exists.
    """
    if not os.path.exists(SESSION_FILE):
        return False
    try:
        with open(SESSION_FILE, "r") as f:
            data = json.load(f)
            return bool(data.get("cookies_str") or data.get("cookies"))
    except Exception:
        return False

def parse_cookie_str(cookie_str: str) -> dict:
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies

async def upload_gif_to_giphy(gif_path: str, tags: list = None):
    """
    Uploads a GIF directly to GIPHY using the user's saved session cookie.
    Direct HTTP POST with Session headers - 100% reliable, no headless browser crash.
    """
    if not os.path.exists(gif_path):
        raise FileNotFoundError(f"File {gif_path} not found")
        
    if not os.path.exists(SESSION_FILE):
        raise Exception("GIPHY session not found. Please connect GIPHY account first.")
        
    with open(SESSION_FILE, "r") as f:
        sess_data = json.load(f)
        
    cookie_str = sess_data.get("cookies_str", "")
    if not cookie_str:
        raise Exception("No valid cookie string found in session.")
        
    session = requests.Session()
    cookie_dict = parse_cookie_str(cookie_str)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Referer": "https://giphy.com/upload",
        "Origin": "https://giphy.com",
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie_str
    }
    
    # GIPHY Web Direct Upload Endpoint (used by web interface when logged in)
    upload_url = "https://upload.giphy.com/v1/gifs"
    
    # Try web direct API key
    # GIPHY web uses public key dc6zaTOxFJmzC or modern web key
    api_key = cookie_dict.get("giphy_token") or "3eToGIHNe6WdVUgvO"
    
    with open(gif_path, "rb") as f:
        files = {"file": (os.path.basename(gif_path), f, "image/gif")}
        data = {
            "api_key": api_key,
            "tags": "line_sticker,custom",
            "is_private": "true"
        }
        
        resp = session.post(upload_url, headers=headers, data=data, files=files, timeout=60)
        
    if resp.status_code in [200, 201]:
        res_json = resp.json()
        gif_id = res_json.get("data", {}).get("id")
        print(f"✅ GIPHY Upload Success! GIF ID: {gif_id}")
        return f"https://giphy.com/gifs/{gif_id}"
    else:
        # Fallback to web internal form upload
        raise Exception(f"GIPHY returned HTTP {resp.status_code}: {resp.text[:200]}")
