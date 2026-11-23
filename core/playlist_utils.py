import os
import re
from collections import Counter
import yt_dlp

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
