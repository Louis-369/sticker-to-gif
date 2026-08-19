import re
import json
import requests
from bs4 import BeautifulSoup

def scrape_line_stickers(url: str):
    """
    Scrapes a LINE sticker product page and returns structured metadata
    including sticker items (static & animated URLs).
    Uses robust requests with standard browser headers.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    resp = requests.get(url, headers=headers, timeout=20)
    html = resp.text
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Title extraction
    title_el = soup.find("p", {"data-test": "sticker-name-title"}) or soup.find("h3", class_="mdCMN08Ttl")
    title = title_el.get_text(strip=True) if title_el else "Sticker Set"
    
    # Author extraction
    author_el = soup.find("a", {"data-test": "sticker-author"}) or soup.find("a", class_="mdCMN08Name")
    author = author_el.get_text(strip=True) if author_el else ""
    
    # Main Icon extraction
    main_img_el = soup.find("img", class_="FnImage") or soup.find("img", class_="mdCMN08Img")
    main_image = main_img_el["src"] if main_img_el and "src" in main_img_el.attrs else ""
    
    # Sticker items extraction
    stickers = []
    has_animation = False
    
    items = soup.find_all("li", class_="FnStickerPreviewItem")
    if not items:
        # Fallback search for any element containing data-preview
        items = soup.find_all(lambda tag: tag.has_attr("data-preview"))
        
    for item in items:
        data_preview_str = item.get("data-preview")
        if not data_preview_str:
            continue
        try:
            data = json.loads(data_preview_str)
            sticker_id = str(data.get("id"))
            sticker_type = data.get("type", "static")
            static_url = data.get("staticUrl") or data.get("fallbackStaticUrl")
            animation_url = data.get("animationUrl")
            
            is_anim = bool(animation_url and (sticker_type == "animation" or "animation" in str(data)))
            if is_anim:
                has_animation = True
                
            stickers.append({
                "id": sticker_id,
                "is_animated": is_anim,
                "type": "animation" if is_anim else "static",
                "preview_url": animation_url if is_anim else static_url,
                "static_url": static_url,
                "animation_url": animation_url if is_anim else None
            })
        except Exception:
            continue
            
    # If main_image is still empty and we have stickers, use first sticker's static image
    if not main_image and stickers:
        main_image = stickers[0].get("static_url", "")
        
    return {
        "title": title,
        "author": author,
        "main_image": main_image,
        "url": url,
        "is_animated_set": has_animation,
        "count": len(stickers),
        "stickers": stickers
    }
