import os
import sys
import json
import requests

def test_giphy_upload(cookie_str: str, gif_path: str):
    print("=" * 50)
    print("🧪 GIPHY 上傳診斷測試工具")
    print("=" * 50)
    
    if not os.path.exists(gif_path):
        print(f"❌ 測試失敗：找不到測試用的 GIF 檔案: {gif_path}")
        return False
        
    print(f"1. 測試 GIF 檔案確認: {gif_path} (大小: {os.path.getsize(gif_path)} bytes)")
    
    # Parse cookie string
    cookies = {}
    for item in cookie_str.split(";"):
        item = item.strip()
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k.strip()] = v.strip()
            
    print(f"2. 提取到 {len(cookies)} 個 Cookie 欄位 (包含: {', '.join(list(cookies.keys())[:5])}...)")
    
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Referer": "https://giphy.com/upload",
        "Origin": "https://giphy.com",
        "Accept": "application/json, text/plain, */*",
        "Cookie": cookie_str
    }
    
    upload_url = "https://upload.giphy.com/v1/gifs"
    api_key = cookies.get("giphy_token") or "3eToGIHNe6WdVUgvO"
    
    print(f"3. 正在向 GIPHY Upload API 發送 POST 請求...")
    print(f"   - API Key: {api_key}")
    print(f"   - Target: {upload_url}")
    
    try:
        with open(gif_path, "rb") as f:
            files = {"file": (os.path.basename(gif_path), f, "image/gif")}
            data = {
                "api_key": api_key,
                "tags": "test_sticker,diagnostic",
                "is_private": "true"
            }
            
            resp = session.post(upload_url, headers=headers, data=data, files=files, timeout=30)
            
        print("\n" + "=" * 50)
        print(f"📡 GIPHY 伺服器回傳狀態碼 (Status Code): {resp.status_code}")
        print("=" * 50)
        
        try:
            res_json = resp.json()
            print("📦 回傳內容 (JSON):")
            print(json.dumps(res_json, indent=2, ensure_ascii=False))
            
            if resp.status_code in [200, 201]:
                gif_id = res_json.get("data", {}).get("id")
                print(f"\n🎉 上傳成功！")
                print(f"🔗 你的私人 GIF 網址: https://giphy.com/gifs/{gif_id}")
                return True
            else:
                print(f"\n❌ 上傳失敗！錯誤代碼: {resp.status_code}")
                return False
        except Exception:
            print("📦 回傳內容 (Raw Text):")
            print(resp.text[:500])
            return False
            
    except Exception as e:
        print(f"\n💥 發送請求時發生異常: {str(e)}")
        return False

if __name__ == "__main__":
    cookie_input = sys.argv[1] if len(sys.argv) > 1 else ""
    gif_file = "/Users/louis/.gemini/antigravity/scratch/ditto_test/sticker.gif"
    
    if not cookie_input:
        print("請提供 Cookie 字串作為第一個參數，例如：")
        print("python3 test_upload.py \"giphy_token=xxx; sessionid=yyy;\"")
    else:
        test_giphy_upload(cookie_input, gif_file)
