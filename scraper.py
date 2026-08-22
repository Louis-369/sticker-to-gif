import re
import json
import requests
from bs4 import BeautifulSoup

def scrape_line_stickers(url: str):
    """
    Universal LINE Extractor supporting both Sticker Sets (stickershop) and Emoji Sets (emojishop).
    - For Sticker sets (/stickershop/product/12345): uses LINE CDN productInfo.meta with HTML fallback.
    - For Emoji sets (/emojishop/product/6902d244...): parses emojishop DOM & data-preview objects.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "*/*"
    }
    
    # Check if this is an Emoji set (/emojishop/) or Sticker set (/stickershop/)
    is_emoji_shop = "/emojishop/" in url
    
    # 1. If it is a Sticker shop with numeric ID, try LINE CDN productInfo.meta
    if not is_emoji_shop:
        match = re.search(r'/product/(\d+)', url)
        if match:
            pkg_id = match.group(1)
            cdn_meta_url = f"https://stickershop.line-scdn.net/stickershop/v1/product/{pkg_id}/iPhone/productInfo.meta"
            try:
                meta_resp = requests.get(cdn_meta_url, headers=headers, timeout=10)
                if meta_resp.status_code == 200:
                    meta = meta_resp.json()
                    titles = meta.get("title", {})
                    title = titles.get("zh-Hant") or titles.get("zh_TW") or titles.get("en") or next(iter(titles.values()), "Sticker Set")
                    authors = meta.get("author", {})
                    author = authors.get("zh-Hant") or authors.get("zh_TW") or authors.get("en") or next(iter(authors.values()), "")
                    has_anim = bool(meta.get("hasAnimation") or meta.get("stickerResourceType") == "ANIMATION" or meta.get("stickerResourceType") == "ANIMATION_SOUND")
                    
                    stickers = []
                    for s in meta.get("stickers", []):
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

    # 2. HTML Scraping (Handles both Emoji Shop & Sticker Shop fallback)
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Title extraction
    title_el = (
        soup.find("p", class_="mdCMN38Item01Ttl") or 
        soup.find("p", {"data-test": "emoji-name"}) or 
        soup.find("p", {"data-test": "sticker-name-title"}) or 
        soup.find("h3", class_="mdCMN08Ttl")
    )
    if title_el:
        title = title_el.get_text(strip=True)
    elif soup.find("title"):
        raw_title = soup.find("title").get_text(strip=True)
        title = re.split(r'[-–—|]', raw_title)[0].strip()
    else:
        title = "Sticker / Emoji Set"
        
    # Author extraction
    author_el = (
        soup.find("a", class_="mdCMN38Item01Author") or 
        soup.find("a", {"data-test": "sticker-author"}) or 
        soup.find("a", class_="mdCMN08Name") or
        soup.find("a", href=lambda h: h and "/author/" in h)
    )
    author = author_el.get_text(strip=True) if author_el else ""
    
    # Main Icon extraction
    main_img_el = (
        soup.find("img", class_="FnImage") or 
        soup.find("img", class_="mdCMN08Img") or
        soup.find("div", class_="mdCMN38Img")
    )
    main_image = ""
    if main_img_el:
        if main_img_el.name == "img" and "src" in main_img_el.attrs:
            main_image = main_img_el["src"]
        elif main_img_el.has_attr("data-preview"):
            try:
                p_data = json.loads(main_img_el["data-preview"])
                main_image = p_data.get("staticUrl") or p_data.get("animationUrl") or ""
            except Exception:
                pass

    # Items extraction (Filter out the header wrapper item if tag is div)
    stickers = []
    has_animation = False
    
    items = soup.find_all("li", class_="FnStickerPreviewItem") or soup.find_all("li", class_="mdCMN09Li")
    if not items:
        # Fallback to any <li> containing data-preview
        items = soup.find_all(lambda tag: tag.name == "li" and tag.has_attr("data-preview"))
        
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
