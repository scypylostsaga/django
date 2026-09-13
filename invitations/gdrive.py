import json
import logging
import os
import re
import urllib.parse
import urllib.request
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def extract_gdrive_folder_id(url: str) -> str:
    """Extract folder ID from various Google Drive folder URL formats."""
    if not url:
        return ""
    url = url.strip()
    m = re.search(r"folders/([a-zA-Z0-9_-]{15,})", url)
    if m:
        return m.group(1)
    m = re.search(r"[?&]id=([a-zA-Z0-9_-]{15,})", url)
    if m:
        return m.group(1)
    return ""


def extract_gdrive_file_id(url: str) -> str:
    """Extract single file ID from Google Drive sharing link."""
    if not url:
        return ""
    m = re.search(r"(?:file/d/|id=)([a-zA-Z0-9_-]{20,})", url)
    if m:
        return m.group(1)
    return ""


def fetch_photos_from_gdrive_folder(folder_url: str):
    """
    Retrieves all photo items from a public Google Drive folder URL.
    Returns a list of dicts: [{'id': file_id, 'url': direct_cdn_url, 'caption': filename}, ...]
    """
    folder_id = extract_gdrive_folder_id(folder_url)
    if not folder_id:
        return []

    cache_key = f"gdrive_folder_photos_{folder_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    photos = []
    seen_ids = {folder_id}

    # 1. Try Google Drive API v3 if API key configured
    api_key = getattr(settings, "GOOGLE_DRIVE_API_KEY", "") or os.environ.get("GOOGLE_DRIVE_API_KEY", "")
    if api_key:
        try:
            query = urllib.parse.quote(f"'{folder_id}' in parents and trashed = false")
            endpoint = (
                f"https://www.googleapis.com/drive/v3/files"
                f"?q={query}&fields=files(id,name,mimeType)&key={api_key}&pageSize=100"
            )
            req = urllib.request.Request(endpoint, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as res:
                data = json.loads(res.read().decode("utf-8"))
                for item in data.get("files", []):
                    fid = item.get("id")
                    mime = item.get("mimeType", "")
                    name = item.get("name", "")
                    is_image = "image" in mime or re.search(r"\.(jpe?g|png|webp|gif|bmp)$", name, re.IGNORECASE)
                    if fid and fid not in seen_ids and (is_image or not mime):
                        seen_ids.add(fid)
                        photos.append({
                            "id": fid,
                            "url": f"https://lh3.googleusercontent.com/d/{fid}",
                            "caption": re.sub(r"\.[a-zA-Z0-9]+$", "", name),
                        })
        except Exception as e:
            logger.warning("Google Drive API v3 failed: %s", e)

    # 2. Fallback: Parse public folder HTML
    if not photos:
        urls_to_try = [
            f"https://drive.google.com/embeddedfolderview?id={folder_id}#grid",
            f"https://drive.google.com/drive/folders/{folder_id}",
        ]
        for fetch_url in urls_to_try:
            try:
                req = urllib.request.Request(
                    fetch_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
                with urllib.request.urlopen(req, timeout=8) as res:
                    html = res.read().decode("utf-8", errors="ignore")

                # Pattern A: flip-entry with ID and caption
                matches = re.findall(
                    r'id=["\']entry-([a-zA-Z0-9_-]{20,})["\'].*?flip-entry-title["\']>([^<]+)<',
                    html,
                    re.DOTALL,
                )
                for fid, title in matches:
                    if fid not in seen_ids:
                        seen_ids.add(fid)
                        caption = re.sub(r"\.[a-zA-Z0-9]+$", "", title.strip())
                        photos.append({
                            "id": fid,
                            "url": f"https://lh3.googleusercontent.com/d/{fid}",
                            "caption": caption,
                        })

                # Pattern B: Match thumbnail and direct file IDs
                direct_matches = re.findall(
                    r'(?:thumbnail\?id=|/file/d/|lh3\.googleusercontent\.com/d/)([a-zA-Z0-9_-]{25,})',
                    html,
                )
                for fid in direct_matches:
                    if fid not in seen_ids:
                        seen_ids.add(fid)
                        photos.append({
                            "id": fid,
                            "url": f"https://lh3.googleusercontent.com/d/{fid}",
                            "caption": "",
                        })

                if photos:
                    break
            except Exception as e:
                logger.warning("Error fetching folder HTML %s: %s", fetch_url, e)

    # Cache for 15 minutes (900 seconds) if photos found
    if photos:
        cache.set(cache_key, photos, 900)

    return photos
