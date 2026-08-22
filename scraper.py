import re
import json
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

def scrape_line_stickers(url: str):
    """
    Universal LINE Extractor supporting both Sticker Sets (stickershop) and Emoji Sets (emojishop).
    1. For Sticker sets (/stickershop/product/12345): uses LINE CDN productInfo.meta.
    2. For Emoji sets (/emojishop/product/6902d244...): 
       - Fetches Title & Author from HTML.
       - Uses fast parallel CDN probes to extract all 40~48 items (001...048) with 100% reliability, bypassing datacenter HTML blocks.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "*/*"
    }
    
    # 1. Standard Sticker Shop Handler (/stickershop/product/12345)
    if "/stickershop/" in url:
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

    # 2. Emoji Shop Handler (/emojishop/product/hex_id)
    emoji_match = re.search(r'/product/([a-f0-9]+)', url, re.IGNORECASE)
    if emoji_match:
        emoji_pkg_id = emoji_match.group(1)
        
        # A. Fetch metadata (Title & Author)
        title = "LINE Emoji Set"
        author = ""
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            title_el = soup.find("p", class_="mdCMN38Item01Ttl") or soup.find("p", {"data-test": "emoji-name"})
            if title_el:
                title = title_el.get_text(strip=True)
            elif soup.find("title"):
                title = re.split(r'[-–—|]', soup.find("title").get_text(strip=True))[0].strip()
                
            author_el = soup.find("a", class_="mdCMN38Item01Author") or soup.find("a", href=lambda h: h and "/author/" in h)
            if author_el:
                author = author_el.get_text(strip=True)
        except Exception:
            pass

        # B. Check animation support on CDN
        anim_test = requests.head(f"https://stickershop.line-scdn.net/sticonshop/v1/sticon/{emoji_pkg_id}/iPhone/001_animation.png", headers=headers, timeout=5)
        has_anim = (anim_test.status_code == 200)
        
        # C. Fast parallel probing for all 001..050 items
        def check_emoji_item(idx):
            num_str = f"{idx:03d}"
            static_url = f"https://stickershop.line-scdn.net/sticonshop/v1/sticon/{emoji_pkg_id}/iPhone/{num_str}.png"
            anim_url = f"https://stickershop.line-scdn.net/sticonshop/v1/sticon/{emoji_pkg_id}/iPhone/{num_str}_animation.png" if has_anim else None
            try:
                r = requests.head(static_url, headers=headers, timeout=5)
                if r.status_code == 200:
                    return {
                        "id": num_str,
                        "is_animated": has_anim,
                        "type": "animation" if has_anim else "static",
                        "preview_url": anim_url if has_anim else static_url,
                        "static_url": static_url,
                        "animation_url": anim_url
                    }
            except Exception:
                pass
            return None

        stickers = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(check_emoji_item, range(1, 55)))
            stickers = [item for item in results if item is not None]
            
        main_image = f"https://stickershop.line-scdn.net/sticonshop/v1/product/{emoji_pkg_id}/iPhone/main.png"
        if not stickers and main_image:
            main_image = ""
            
        if stickers:
            return {
                "title": title,
                "author": author,
                "main_image": main_image or stickers[0]["static_url"],
                "url": url,
                "is_animated_set": has_anim,
                "count": len(stickers),
                "stickers": stickers
            }

    # 3. Universal Fallback
    resp = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    title_el = soup.find("p", {"data-test": "sticker-name-title"}) or soup.find("h3", class_="mdCMN08Ttl")
    title = title_el.get_text(strip=True) if title_el else "Sticker Set"
    
    stickers = []
    items = soup.find_all("li", class_="FnStickerPreviewItem") or soup.find_all(lambda tag: tag.name == "li" and tag.has_attr("data-preview"))
    for item in items:
        data_preview_str = item.get("data-preview")
        if not data_preview_str:
            continue
        try:
            data = json.loads(data_preview_str)
            s_id = str(data.get("id"))
            static_url = data.get("staticUrl") or data.get("fallbackStaticUrl")
            anim_url = data.get("animationUrl")
            is_anim = bool(anim_url)
            stickers.append({
                "id": s_id,
                "is_animated": is_anim,
                "type": "animation" if is_anim else "static",
                "preview_url": anim_url if is_anim else static_url,
                "static_url": static_url,
                "animation_url": anim_url
            })
        except Exception:
            continue

    return {
        "title": title,
        "author": "",
        "main_image": stickers[0]["static_url"] if stickers else "",
        "url": url,
        "is_animated_set": any(s["is_animated"] for s in stickers),
        "count": len(stickers),
        "stickers": stickers
    }
