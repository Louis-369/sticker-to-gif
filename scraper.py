import re
import json
import subprocess
from bs4 import BeautifulSoup

def scrape_line_stickers(url: str):
    """
    Scrapes a LINE sticker product page and returns structured metadata
    including sticker items (static & animated URLs).
    """
    # Fetch html via curl to bypass strict policy/SSL blocks
    cmd = ["curl", "-s", "-A", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", url]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    html = result.stdout
    
    soup = BeautifulSoup(html, "html.parser")
    
    # Title
    title_el = soup.find("p", {"data-test": "sticker-name-title"})
    title = title_el.get_text(strip=True) if title_el else "LINE Sticker Set"
    
    # Author
    author_el = soup.find("a", {"data-test": "sticker-author"})
    author = author_el.get_text(strip=True) if author_el else ""
    
    # Main Icon
    main_img_el = soup.find("img", class_="FnImage")
    main_image = main_img_el["src"] if main_img_el and "src" in main_img_el.attrs else ""
    
    # Sticker items
    stickers = []
    has_animation = False
    
    items = soup.find_all("li", class_="FnStickerPreviewItem")
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
            
            is_anim = bool(animation_url and sticker_type == "animation")
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
        except Exception as e:
            continue
            
    return {
        "title": title,
        "author": author,
        "main_image": main_image,
        "url": url,
        "is_animated_set": has_animation,
        "count": len(stickers),
        "stickers": stickers
    }

if __name__ == "__main__":
    test_url = "https://store.line.me/stickershop/product/37599/zh-Hant"
    res = scrape_line_stickers(test_url)
    print(f"Title: {res['title']}, Animated: {res['is_animated_set']}, Count: {res['count']}")
    print(f"Sample sticker: {res['stickers'][0]}")
