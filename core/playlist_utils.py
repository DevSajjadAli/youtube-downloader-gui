import os
import re
from collections import Counter
import yt_dlp

def extract_episode_number(title):
    """
    Extract integer episode number from a video title.
    Matches: 'Episode 01', 'Ep 2', 'Part 3', '#10', 'E05', '1 - Title', etc.
    """
    if not title:
        return None
    patterns = [
        r'\b(?:ep|episode|part|pt|e)\.?\s*#?\s*0*(\d+)\b',
        r'#\s*0*(\d+)\b',
        r'\[\s*0*(\d+)\s*\]',
        r'\(\s*0*(\d+)\s*\)',
        r'^\s*0*(\d+)\s*[-–.]\s+',
        r'-\s*0*(\d+)\s*-',
        r'\b0*(\d+)\s*(?:st|nd|rd|th)?\s*(?:ep|episode|part)\b',
    ]
    for p in patterns:
        m = re.search(p, title, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass
    return None

def fetch_upload_date_for_video(video_id_or_url):
    """
    Fast extraction of upload date for a YouTube video using web scraping.
    Returns ISO date string (e.g. '2023-05-12') or formatted 'YYYYMMDD' or None.
    """
    vid = video_id_or_url
    if 'watch?v=' in str(vid):
        m = re.search(r'v=([a-zA-Z0-9_-]{11})', str(vid))
        if m:
            vid = m.group(1)
    elif str(vid).startswith('http'):
        vid = str(vid).rstrip('/').split('/')[-1]

    if not vid or len(str(vid)) != 11:
        return None

    import urllib.request
    url = f"https://www.youtube.com/watch?v={vid}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            m = re.search(r'"uploadDate":"([^"]+)"', html)
            if m:
                # Return YYYY-MM-DD
                return m.group(1)[:10]
            m = re.search(r'"dateText":\{"simpleText":"([^"]+)"\}', html)
            if m:
                return m.group(1)
    except Exception:
        return None
    return None

def fetch_playlist_upload_dates(entries, max_workers=6, progress_cb=None):
    """
    Fetch upload dates for entries in parallel and update the entry dicts.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    to_fetch = []
    for idx, e in enumerate(entries):
        if not e.get("upload_date") and not e.get("date_str"):
            vid = e.get("id") or e.get("url")
            to_fetch.append((idx, vid))

    total = len(to_fetch)
    if total == 0:
        return entries

    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(fetch_upload_date_for_video, vid): idx
            for idx, vid in to_fetch
        }
        for fut in as_completed(future_map):
            idx = future_map[fut]
            try:
                date_val = fut.result()
                if date_val:
                    entries[idx]["upload_date"] = date_val.replace("-", "")
                    entries[idx]["date_str"] = date_val
            except Exception:
                pass
            done += 1
            if progress_cb:
                progress_cb(done, total)

    return entries

def sort_playlist_entries(entries, sort_mode='date_asc'):
    """
    Sort playlist entries intelligently:
      - 'date_asc': Oldest upload first (Ep 1 -> End)
      - 'date_desc': Newest upload first (End -> Ep 1)
      - 'ep_title_asc': Episode number in title (1, 2, 3...)
      - 'reverse': Reverse current order
      - 'original': Keep original YouTube order
    """
    if not entries:
        return []

    # Ensure original index is tagged
    for i, e in enumerate(entries):
        if "_original_index" not in e:
            e["_original_index"] = i + 1

    if sort_mode == 'reverse':
        return list(reversed(entries))

    elif sort_mode == 'original':
        return sorted(entries, key=lambda x: x.get("_original_index", 0))

    elif sort_mode == 'ep_title_asc':
        def ep_key(e):
            num = extract_episode_number(e.get("title", ""))
            return (0 if num is not None else 1, num if num is not None else 0, e.get("_original_index", 0))
        return sorted(entries, key=ep_key)

    elif sort_mode == 'date_asc':
        def date_asc_key(e):
            d = str(e.get("upload_date") or e.get("date_str") or "")
            ep_num = extract_episode_number(e.get("title", ""))
            # If dates are missing, fallback to title episode number or original index
            if not d:
                return ("99999999", ep_num if ep_num is not None else e.get("_original_index", 0))
            return (d, ep_num if ep_num is not None else e.get("_original_index", 0))
        return sorted(entries, key=date_asc_key)

    elif sort_mode == 'date_desc':
        def date_desc_key(e):
            d = str(e.get("upload_date") or e.get("date_str") or "")
            ep_num = extract_episode_number(e.get("title", ""))
            if not d:
                return ("", -(ep_num if ep_num is not None else e.get("_original_index", 0)))
            return (d, -(ep_num if ep_num is not None else e.get("_original_index", 0)))
        return sorted(entries, key=date_desc_key, reverse=True)

    return entries

def is_playlist_url(url):
    """Detect if a URL points to a YouTube playlist, show, or collection."""
    if not url:
        return False
    url = url.strip()
    playlist_patterns = [
        r'[?&]list=',               # Playlist parameter
        r'youtube\.com/playlist',   # Playlist URL
        r'youtu\.be/.*[?&]list=',   # Shortened URL with playlist
        r'youtube\.com/show/',      # YouTube TV show / series
        r'youtube\.com/(?:c/|channel/|user/|@)[^/]+/(?:playlists|videos|streams|shorts)',  # Channel tabs
    ]
    for pattern in playlist_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def parse_episodes(input_str, total_count):
    """
    Parses a user input range string into a sorted list of 1-based episode indices.
    Examples:
      - '1-10' -> [1, 2, ..., 10]
      - '5, 8, 12' -> [5, 8, 12]
      - '1-5, 8, 11-15' -> [1, 2, 3, 4, 5, 8, 11, 12, 13, 14, 15]
      - '5-' -> [5, 6, ..., total_count]
      - '-10' -> [1, 2, ..., 10]
    """
    if not input_str or not input_str.strip():
        return list(range(1, total_count + 1))

    selected = set()
    parts = [p.strip() for p in input_str.split(',') if p.strip()]
    for part in parts:
        if '-' in part:
            bounds = part.split('-', 1)
            start_str, end_str = bounds[0].strip(), bounds[1].strip()
            start = int(start_str) if start_str.isdigit() else 1
            end = int(end_str) if end_str.isdigit() else total_count
            if start > end:
                start, end = end, start
            for i in range(max(1, start), min(total_count, end) + 1):
                selected.add(i)
        else:
            try:
                num = int(part)
                if 1 <= num <= total_count:
                    selected.add(num)
            except ValueError:
                pass
    return sorted(selected)

def infer_playlist_name_from_entries(entries):
    """
    Extract a sensible show or playlist title from individual episode titles
    when YouTube's playlist title is generic (e.g. 'show', 'playlist', 'videos').
    """
    if not entries:
        return ""

    sample_titles = []
    for entry in entries[:10]:
        if isinstance(entry, dict):
            t = entry.get('title')
            if t and t.strip():
                sample_titles.append(t.strip())

    if not sample_titles:
        return ""

    cleaned_titles = []
    for t in sample_titles:
        # Strip common episode patterns
        c = re.sub(r'[\s|–\-]+(?:Episode|Ep\.?|Part|Pt\.?|OST|Promo|Teaser)\s*\d+.*$', '', t, flags=re.IGNORECASE)
        # Strip trailing channel names
        c = re.sub(r'[\s|–\-]+(?:HUM TV|ARY Digital|Geo TV|Har Pal Geo|Green TV|Express TV|YouTube).*$', '', c, flags=re.IGNORECASE)
        c = re.sub(r'[\s|–\-]+$', '', c).strip()
        if c:
            cleaned_titles.append(c)

    if cleaned_titles:
        counts = Counter(cleaned_titles)
        most_common, _ = counts.most_common(1)[0]
        if most_common and len(most_common) > 2:
            return most_common

    return sample_titles[0][:40]

def sanitize_folder_name(name, fallback="YouTube_Playlist"):
    """Sanitize directory name for Windows/cross-platform filesystem safety."""
    if not name:
        return fallback
    clean = yt_dlp.utils.sanitize_filename(name).strip()
    if clean.lower() in ("show", "shows", "playlist", "videos", "uploads", ""):
        return fallback
    return clean

def find_existing_episode_file(folder, idx):
    """
    Check if an episode file matching index `idx` already exists in `folder`.
    Matches patterns like '1.mp4', '01.mp4', '01 - Title.mp4', '1 - Title.mp4'.
    """
    if not os.path.isdir(folder):
        return None

    try:
        filenames = os.listdir(folder)
    except OSError:
        return None

    prefix_simple = f"{idx}."
    prefix_zero = f"{idx:02d}."
    prefix_dash1 = f"{idx} - "
    prefix_dash2 = f"{idx:02d} - "
    prefix_ep1 = f"episode {idx}."
    prefix_ep2 = f"episode {idx:02d}."
    prefix_ep3 = f"ep {idx}."
    prefix_ep4 = f"ep {idx:02d}."

    valid_exts = ('.mp4', '.mkv', '.webm', '.m4a', '.mp3')

    for fn in filenames:
        if fn.endswith(('.part', '.ytdl', '.temp')):
            continue
        lower = fn.lower()
        if any(lower.endswith(ext) for ext in valid_exts):
            if (
                lower.startswith(prefix_simple) or
                lower.startswith(prefix_zero) or
                lower.startswith(prefix_dash1) or
                lower.startswith(prefix_dash2) or
                lower.startswith(prefix_ep1) or
                lower.startswith(prefix_ep2) or
                lower.startswith(prefix_ep3) or
                lower.startswith(prefix_ep4)
            ):
                full_path = os.path.join(folder, fn)
                if os.path.isfile(full_path) and os.path.getsize(full_path) > 100 * 1024:
                    return full_path
    return None
