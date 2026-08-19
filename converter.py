import os
import subprocess
import requests
from bs4 import BeautifulSoup

def convert_apng_to_gif_pure_ezgif(apng_url: str, output_gif_path: str):
    """
    Strictly uses ezgif.com/apng-to-gif pipeline to convert APNG to infinite loop transparent GIF.
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    
    # 1. Step 1: Submit APNG URL to ezgif
    upload_url = "https://ezgif.com/apng-to-gif"
    resp = session.post(upload_url, data={"new-image-url": apng_url}, timeout=30)
    
    soup = BeautifulSoup(resp.text, "html.parser")
    form = soup.find("form", class_="ajax-form") or soup.find("form")
    if not form or "action" not in form.attrs:
        raise Exception("ezgif 伺服器未回傳轉換表單，請重試")
        
    action_path = form["action"]
    convert_endpoint = "https://ezgif.com" + action_path if action_path.startswith("/") else action_path
    
    # Collect form inputs
    form_data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            form_data[name] = val
            
    # 2. Step 2: Trigger Convert to GIF
    conv_resp = session.post(convert_endpoint, data=form_data, timeout=30)
    conv_soup = BeautifulSoup(conv_resp.text, "html.parser")
    
    # 3. Find converted GIF image strictly from the output area
    output_div = conv_soup.find("div", id="output")
    target_img = None
    if output_div:
        target_img = output_div.find("img", src=lambda s: s and s.endswith(".gif")) or output_div.find("img")
        
    if not target_img or not target_img.get("src"):
        for img in conv_soup.find_all("img"):
            src = img.get("src", "")
            if "ezgif-" in src and src.endswith(".gif"):
                target_img = img
                break
                
    if not target_img or not target_img.get("src"):
        raise Exception("ezgif 轉檔未產出 GIF 圖片")
        
    img_src = target_img["src"]
    download_url = "https:" + img_src if img_src.startswith("//") else ("https://ezgif.com" + img_src if img_src.startswith("/") else img_src)
    
    gif_data = session.get(download_url, timeout=30).content
    with open(output_gif_path, "wb") as f:
        f.write(gif_data)
        
    return output_gif_path

def process_sticker_ezgif(sticker_info: dict, output_dir: str):
    """
    Downloads sticker. If animated, converts via ezgif.com.
    If static, downloads transparent PNG directly.
    """
    os.makedirs(output_dir, exist_ok=True)
    sticker_id = sticker_info["id"]
    
    if sticker_info["is_animated"]:
        apng_url = sticker_info["animation_url"]
        output_gif = os.path.join(output_dir, f"{sticker_id}.gif")
        
        # Pure ezgif conversion
        convert_apng_to_gif_pure_ezgif(apng_url, output_gif)
            
        return {
            "id": sticker_id,
            "type": "gif",
            "path": output_gif,
            "filename": f"{sticker_id}.gif",
            "url": f"/files/{os.path.basename(output_dir)}/{sticker_id}.gif"
        }
    else:
        static_url = sticker_info["static_url"]
        output_png = os.path.join(output_dir, f"{sticker_id}.png")
        subprocess.run(["curl", "-s", "-o", output_png, static_url], check=True)
        return {
            "id": sticker_id,
            "type": "png",
            "path": output_png,
            "filename": f"{sticker_id}.png",
            "url": f"/files/{os.path.basename(output_dir)}/{sticker_id}.png"
        }
