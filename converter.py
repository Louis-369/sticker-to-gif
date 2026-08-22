import os
import subprocess
import requests
from bs4 import BeautifulSoup

def convert_apng_to_gif_pure_ezgif(apng_url: str, output_gif_path: str):
    """
    Strictly uses ezgif.com/apng-to-gif pipeline to convert APNG to infinite loop transparent GIF.
    Locks encoder method to 'libvips' for optimal semi-transparent rendering and sharp line edges.
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
    
    # Collect form inputs and strictly force method to libvips
    form_data = {}
    for inp in form.find_all("input"):
        name = inp.get("name")
        val = inp.get("value", "")
        if name:
            form_data[name] = val
            
    # Force encoder method to libvips (recommended for high quality transparent stickers)
    form_data["method"] = "libvips"
    if "quality" not in form_data:
        form_data["quality"] = "96"
            
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

def process_sticker_ezgif(sticker: dict, output_dir: str):
    """
    Processes a single sticker object:
    - If animated: downloads via convert_apng_to_gif_pure_ezgif (libvips)
    - If static: downloads clean PNG directly
    """
    s_id = sticker.get("id")
    is_anim = sticker.get("is_animated", False)
    
    if is_anim:
        filename = f"{s_id}.gif"
        out_path = os.path.join(output_dir, filename)
        convert_apng_to_gif_pure_ezgif(sticker["animation_url"], out_path)
        return {
            "id": s_id,
            "filename": filename,
            "url": f"/files/{os.path.basename(output_dir)}/{filename}",
            "type": "gif"
        }
    else:
        filename = f"{s_id}.png"
        out_path = os.path.join(output_dir, filename)
        resp = requests.get(sticker["static_url"], timeout=15)
        with open(out_path, "wb") as f:
            f.write(resp.content)
        return {
            "id": s_id,
            "filename": filename,
            "url": f"/files/{os.path.basename(output_dir)}/{filename}",
            "type": "png"
        }
