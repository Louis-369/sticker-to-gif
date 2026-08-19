import re
import json
import requests
from bs4 import BeautifulSoup

def scrape_line_stickers(url: str):
    """
    Bulletproof LINE sticker extractor.
    1. Extracts package ID from URL.
    2. Directly fetches official LINE CDN productInfo.meta (Fast, 100% accurate, unblockable by Cloudflare/datacenter filters).
    3. Fallbacks to HTML parsing if necessary.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "*/*"
    }
    
    # 1. Extract Package ID from URL
    match = re.search(r'/product/(\d+)', url)
    if match:
        pkg_id = match.group(1)
        cdn_meta_url = f"https://stickershop.line-scdn.net/stickershop/v1/product/{pkg_id}/iPhone/productInfo.meta"
        
        try:
            meta_resp = requests.get(cdn_meta_url, headers=headers, timeout=10)
            if meta_resp.status_code == 200:
                meta = meta_resp.json()
                
                # Title localization fallback
                titles = meta.get("title", {})
                title = titles.get("zh-Hant") or titles.get("zh_TW") or titles.get("en") or next(iter(titles.values()), "Sticker Set")
                
                # Author localization fallback
                authors = meta.get("author", {})
                author = authors.get("zh-Hant") or authors.get("zh_TW") or authors.get("en") or next(iter(authors.values()), "")
                
                has_anim = bool(meta.get("hasAnimation") or meta.get("stickerResourceType") == "ANIMATION" or meta.get("stickerResourceType") == "ANIMATION_SOUND")
                raw_stickers = meta.get("stickers", [])
                
                stickers = []
                for s in raw_stickers:
                    s_id = str(s.get("id"))
                    static_url = f"https://stickershop.line-scdn.net/stickershop/v1/sticker/{s_id}/iPhone/sticker@2x.png"
                    anim_url = f"https://stickershop.line-scdn.net/stickershop/v1/sticker/{s_id}/iPhone/sticker_animation@2x.png" if has_anim else None
                    
                    stickers.append({
                        "id": s_id,
                        "is_animated": has_anim,
                        "type": "animation" if has_anim else "static",
                        "preview_url": anim_url if has_anim else static_url,
                        "static_url": static_url,
                        "animation_url": anim_url
                    })
                    
                main_image = f"https://stickershop.line-scdn.net/stickershop/v1/product/{pkg_id}/iPhone/main@2x.png"
                
                return {
                    "title": title,
                    "author": author,
                    "main_image": main_image,
                    "url": url,
                    "is_animated_set": has_anim,
                    "count": len(stickers),
                    "stickers": stickers
                }
        except Exception:
            pass
            
    # 2. Fallback to HTML scraping
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    title_el = soup.find("p", {"data-test": "sticker-name-title"}) or soup.find("h3", class_="mdCMN08Ttl")
    title = title_el.get_text(strip=True) if title_el else "Sticker Set"
    
    author_el = soup.find("a", {"data-test": "sticker-author"}) or soup.find("a", class_="mdCMN08Name")
    author = author_el.get_text(strip=True) if author_el else ""
    
    main_img_el = soup.find("img", class_="FnImage") or soup.find("img", class_="mdCMN08Img")
    main_image = main_img_el["src"] if main_img_el and "src" in main_img_el.attrs else ""
    
    stickers = []
    has_animation = False
    
    items = soup.find_all("li", class_="FnStickerPreviewItem") or soup.find_all(lambda tag: tag.has_attr("data-preview"))
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
