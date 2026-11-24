import os
import sys
import time
import json
import subprocess
import glob
import yt_dlp

from .ffmpeg_utils import get_ffmpeg_dir, get_ffprobe_path
from .playlist_utils import (
    is_playlist_url,
    parse_episodes,
    infer_playlist_name_from_entries,
    sanitize_folder_name,
    find_existing_episode_file
)

# ──────────────────────────────────────────────────────────────
# Quality presets configuration
# ──────────────────────────────────────────────────────────────

def parse_speed_limit(val):
    """Convert human speed string (e.g. '2M', '500K') to bytes/sec."""
    if not val:
        return None
    val = str(val).strip().upper()
    try:
        if val.endswith('M') or val.endswith('MB'):
            num = float(val.rstrip('MB'))
            return int(num * 1024 * 1024)
        elif val.endswith('K') or val.endswith('KB'):
            num = float(val.rstrip('KB'))
            return int(num * 1024)
        elif val.isdigit():
            return int(val)
        else:
            return int(float(val))
    except Exception:
        return None

QUALITY_PRESETS = {
    '1': {
        'name': 'Best Available (Original: 4K / 2K / 1080p)',
        'short': 'Best Available',
        'badge': '4K / 1080p',
        'format_ffmpeg': 'bestvideo+bestaudio/best',
        'format_no_ffmpeg': 'best[ext=mp4]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '2': {
        'name': '1080p (Full HD)',
        'short': '1080p Full HD',
        'badge': '1080p',
        'format_ffmpeg': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'format_no_ffmpeg': 'best[height<=1080][ext=mp4]/best[height<=1080]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '3': {
        'name': '720p (HD — Fast & Balanced)',
        'short': '720p HD',
        'badge': '720p',
        'format_ffmpeg': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'format_no_ffmpeg': 'best[height<=720][ext=mp4]/best[height<=720]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '4': {
        'name': '480p (SD — Data Saver)',
        'short': '480p SD',
        'badge': '480p',
        'format_ffmpeg': 'bestvideo[height<=480]+bestaudio/best[height<=480]/best',
        'format_no_ffmpeg': 'best[height<=480][ext=mp4]/best[height<=480]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '5': {
        'name': '360p (Low — Smallest File)',
        'short': '360p Low',
        'badge': '360p',
        'format_ffmpeg': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best',
        'format_no_ffmpeg': 'best[height<=360][ext=mp4]/best[height<=360]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '6': {
        'name': 'Audio Only (Highest Quality MP3)',
        'short': 'Audio MP3',
        'badge': 'MP3',
        'format_ffmpeg': 'bestaudio/best',
        'format_no_ffmpeg': 'bestaudio[ext=m4a]/bestaudio/best',
        'is_audio': True,
        'merge_fmt': None
    }
}


class DownloadEngine:
    """Core download management engine for single videos, playlists, and queues."""

    def __init__(self):
        self.ffmpeg_dir = get_ffmpeg_dir()

    def refresh_ffmpeg(self):
        """Re-scan system for ffmpeg."""
        self.ffmpeg_dir = get_ffmpeg_dir()
        return self.ffmpeg_dir

    def fetch_info(self, url):
        """
        Extract video or playlist metadata without downloading.
        Returns a dictionary with normalized information.
        """
        if not url or not url.strip():
            return None

        url = url.strip()
        is_pl = is_playlist_url(url)

        ydl_opts = {
            'extract_flat': True if is_pl else 'in_playlist',
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/127.0.0.0 Safari/537.36'
                )
            }
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None

                entries = info.get('entries')
                is_actually_playlist = (
                    entries is not None or
                    info.get('_type') in ('playlist', 'multi_video', 'channel', 'show')
                )

                if is_actually_playlist:
                    entries_list = [e for e in entries if e is not None] if entries else []
                    raw_title = (
                        info.get('title') or
                        info.get('playlist_title') or
                        info.get('series') or
                        info.get('album') or
                        ''
                    ).strip()

                    uploader = (
                        info.get('uploader') or
                        info.get('channel') or
                        info.get('uploader_id') or
                        'Unknown Channel'
                    )

                    generic_names = {'show', 'shows', 'playlist', 'videos', 'uploads', 'unknown'}
                    detected_title = raw_title
                    if not detected_title or detected_title.lower() in generic_names:
                        inferred = infer_playlist_name_from_entries(entries_list)
                        if inferred:
                            detected_title = inferred
                        elif uploader and uploader != 'Unknown Channel':
                            detected_title = f"{uploader} Playlist"
                        else:
                            detected_title = "YouTube Playlist"

                    # Get thumbnail from first entry or playlist
                    thumb = info.get('thumbnail') or (entries_list[0].get('thumbnail') if entries_list else None)

                    return {
                        'is_playlist': True,
                        'title': detected_title,
                        'raw_title': raw_title,
                        'uploader': uploader,
                        'count': len(entries_list),
                        'entries': entries_list,
                        'thumbnail': thumb,
                        'url': url
                    }
                else:
                    # Single video
                    title = info.get('title', 'YouTube Video')
                    uploader = info.get('uploader') or info.get('channel') or 'Unknown'
                    duration = info.get('duration') or 0
                    thumb = info.get('thumbnail')
                    view_count = info.get('view_count')
                    formats = info.get('formats', [])

                    # Detect available qualities and features
                    resolutions = []
                    tags = []
                    has_60fps = False
                    for f in formats:
                        h = f.get('height')
                        if h and h not in resolutions:
                            resolutions.append(h)
                        if f.get('fps') and f.get('fps') >= 60:
                            has_60fps = True

                    resolutions.sort(reverse=True)
                    if any(h >= 2160 for h in resolutions):
                        tags.append("4K Ultra HD")
                    elif any(h >= 1440 for h in resolutions):
                        tags.append("2K Quad HD")
                    elif any(h >= 1080 for h in resolutions):
                        tags.append("1080p Full HD")
                    elif any(h >= 720 for h in resolutions):
                        tags.append("720p HD")

                    if has_60fps:
                        tags.append("60 FPS")

                    return {
                        'is_playlist': False,
                        'title': title,
                        'uploader': uploader,
                        'duration': duration,
                        'thumbnail': thumb,
                        'view_count': view_count,
                        'like_count': info.get('like_count'),
                        'upload_date': info.get('upload_date', ''),
                        'resolutions': resolutions,
                        'tags': tags,
                        'url': url
                    }

        except Exception as e:
            return {'error': str(e)}

    def build_ydl_opts(self, save_dir, quality_key='1', outtmpl=None, progress_hook=None, speed_limit=None):
        """Construct yt-dlp options dictionary."""
        preset = QUALITY_PRESETS.get(str(quality_key), QUALITY_PRESETS['1'])
        ffmpeg_dir = self.ffmpeg_dir

        if ffmpeg_dir:
            format_str = preset['format_ffmpeg']
            merge_fmt = preset.get('merge_fmt')
        else:
            format_str = preset['format_no_ffmpeg']
            merge_fmt = None

        if outtmpl is None:
            outtmpl = os.path.join(save_dir, '%(title)s.%(ext)s')

        ydl_opts = {
            'outtmpl': outtmpl,
            'format': format_str,
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/127.0.0.0 Safari/537.36'
                ),
            },
            'retries': 15,
            'fragment_retries': 15,
            'http_chunk_size': 2 * 1024 * 1024,
            'socket_timeout': 60,
            'extractor_retries': 5,
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'continuedl': True,
            'source_address': '0.0.0.0',
            'prefer_free_formats': False,
        }

        limit_bytes = parse_speed_limit(speed_limit)
        if limit_bytes:
            ydl_opts['ratelimit'] = limit_bytes

        if progress_hook:
            ydl_opts['progress_hooks'] = [progress_hook]

        if merge_fmt and not preset['is_audio']:
            ydl_opts['merge_output_format'] = merge_fmt

        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

        if preset['is_audio'] and ffmpeg_dir:
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        return ydl_opts

    def validate_file(self, filepath, is_audio=False):
        """Validate media file playable status using file size and ffprobe."""
        if not filepath or not os.path.isfile(filepath):
            return False

        min_size = 20 * 1024 if is_audio else 100 * 1024
        try:
            size = os.path.getsize(filepath)
        except OSError:
            return False

        if size < min_size:
            # File is empty or truncated header only
            try:
                os.remove(filepath)
            except OSError:
                pass
            return False

        ffprobe = get_ffprobe_path()
        if ffprobe and os.path.isfile(ffprobe):
            try:
                res = subprocess.run(
                    [
                        ffprobe,
                        "-v", "error",
                        "-show_entries", "stream=codec_type,width,height",
                        "-of", "json",
                        filepath,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                if res.returncode == 0 and res.stdout:
                    data = json.loads(res.stdout)
                    streams = data.get("streams", [])
                    if streams:
                        if is_audio:
                            has_audio = any(s.get("codec_type") == "audio" for s in streams)
                            return has_audio
                        else:
                            has_video = any(s.get("codec_type") == "video" for s in streams)
                            return has_video
            except Exception:
                # If ffprobe errors out or times out, but file is >= min_size, keep it
                return True

        return True

    def get_downloaded_path(self, info, ydl, merge_fmt=None, is_audio=False):
        """Locate exact downloaded output path."""
        if not info:
            return None

        req = info.get('requested_downloads')
        if req and isinstance(req, list):
            for r in reversed(req):
                fp = r.get('filepath')
                if fp and os.path.isfile(fp):
                    return fp

        fn = info.get('_filename')
        if fn and os.path.isfile(fn):
            return fn

        if ydl:
            base_prep = ydl.prepare_filename(info)
            root, _ = os.path.splitext(base_prep)
            candidates = []
            if is_audio:
                candidates.extend([f"{root}.mp3", f"{root}.m4a", base_prep])
            else:
                if merge_fmt:
                    candidates.append(f"{root}.{merge_fmt}")
                candidates.extend([base_prep, f"{root}.mp4", f"{root}.mkv", f"{root}.webm"])

            for c in candidates:
                if os.path.isfile(c):
                    return c

        return None

    def download_single(
        self,
        url,
        save_dir,
        quality_key='1',
        progress_cb=None,
        status_cb=None,
        cancel_event=None,
        extra_opts=None,
        speed_limit=None,
        outtmpl=None
    ):
        """
        Download a single video with live callbacks.
        progress_cb signature: (percent, downloaded_bytes, total_bytes, speed_str, eta_str)
        status_cb signature: (message, level)  # level: "info", "success", "error", "warning"
        """
        os.makedirs(save_dir, exist_ok=True)
        preset = QUALITY_PRESETS.get(str(quality_key), QUALITY_PRESETS['1'])
        is_audio = preset['is_audio']

        def hook(d):
            if cancel_event and cancel_event.is_set():
                raise KeyboardInterrupt("Cancelled by user")

            if d["status"] == "downloading" and progress_cb:
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                speed = d.get("speed")
                eta = d.get("eta")

                pct = (downloaded / total * 100) if total > 0 else 0.0
                speed_str = f"{speed / 1048576:.1f} MB/s" if speed else "--"
                eta_str = f"{int(eta)}s" if eta else "--"
                progress_cb(pct, downloaded, total, speed_str, eta_str)

            elif d["status"] == "finished" and status_cb:
                status_cb("Merging formats & finalizing file...", "info")

        ydl_opts = self.build_ydl_opts(save_dir, quality_key=quality_key, outtmpl=outtmpl, progress_hook=hook, speed_limit=speed_limit)
        ydl_opts['noplaylist'] = True
        if extra_opts:
            ydl_opts.update(extra_opts)

        MAX_ATTEMPTS = 4
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if cancel_event and cancel_event.is_set():
                if status_cb:
                    status_cb("Download cancelled.", "warning")
                return False, None

            try:
                if status_cb:
                    status_cb(f"Connecting to YouTube (attempt {attempt}/{MAX_ATTEMPTS})...", "info")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        if status_cb:
                            status_cb("Could not retrieve stream info.", "error")
                        continue

                    merge_fmt = ydl_opts.get('merge_output_format')
                    final_path = self.get_downloaded_path(info, ydl, merge_fmt=merge_fmt, is_audio=is_audio)

                    if not final_path or not os.path.isfile(final_path):
                        # Fallback search
                        title = info.get('title', '')
                        for f in glob.glob(os.path.join(save_dir, "*")):
                            if not f.endswith(('.part', '.ytdl', '.temp')):
                                final_path = f
                                break

                    if final_path and os.path.isfile(final_path):
                        if status_cb:
                            status_cb("Verifying media file integrity...", "info")

                        if self.validate_file(final_path, is_audio=is_audio):
                            size_mb = os.path.getsize(final_path) / 1048576
                            fn = os.path.basename(final_path)
                            if status_cb:
                                status_cb(f"✓ Download complete: {fn} ({size_mb:.1f} MB)", "success")
                            return True, final_path
                        else:
                            if status_cb:
                                status_cb("Validation failed — file corrupt.", "warning")

            except KeyboardInterrupt:
                if status_cb:
                    status_cb("Download cancelled by user.", "warning")
                return False, None
            except Exception as e:
                err_msg = str(e)
                if status_cb:
                    status_cb(f"Error: {err_msg}", "error")
                if attempt < MAX_ATTEMPTS:
                    time.sleep(3)

        return False, None

    def download_playlist(
        self,
        url,
        base_save_dir,
        folder_name=None,
        quality_key='1',
        selected_indices=None,
        skip_existing=True,
        filename_format='numbered_title',
        overall_progress_cb=None,
        video_progress_cb=None,
        status_cb=None,
        cancel_event=None,
        speed_limit=None,
        cached_info=None,
        extra_opts=None
    ):
        """
        Download playlist/show with dedicated folder and episode selection.
        overall_progress_cb: (current_step, total_selected, video_title)
        video_progress_cb: (pct, downloaded_bytes, total_bytes, speed_str, eta_str)
        status_cb: (message, level)
        """
        if cached_info and cached_info.get('is_playlist') and cached_info.get('entries'):
            info_dict = cached_info
        else:
            if status_cb:
                status_cb("Fetching playlist information...", "info")
            info_dict = self.fetch_info(url)

        if not info_dict or not info_dict.get('is_playlist'):
            if status_cb:
                status_cb("URL is not a valid playlist or could not be retrieved.", "error")
            return False, []

        entries = info_dict.get('entries', [])
        total_episodes = len(entries)
        if total_episodes == 0:
            if status_cb:
                status_cb("Playlist contains 0 playable entries.", "error")
            return False, []

        # Determine target folder
        clean_folder = sanitize_folder_name(folder_name or info_dict.get('title'))
        target_dir = os.path.join(base_save_dir, clean_folder)
        os.makedirs(target_dir, exist_ok=True)

        # Episode selection
        if not selected_indices:
            selected_indices = list(range(1, total_episodes + 1))

        # Filter out of range indices
        selected_indices = [i for i in selected_indices if 1 <= i <= total_episodes]
        total_selected = len(selected_indices)

        if total_selected == 0:
            if status_cb:
                status_cb("No valid episodes selected for download.", "warning")
            return False, []

        if status_cb:
            status_cb(
                f"Starting playlist: '{clean_folder}' — {total_selected} episodes to process.",
                "info"
            )

        preset = QUALITY_PRESETS.get(str(quality_key), QUALITY_PRESETS['1'])
        is_audio = preset['is_audio']
        downloaded_paths = []
        succeeded = 0
        skipped = 0
        failed = 0

        for step, idx in enumerate(selected_indices, 1):
            if cancel_event and cancel_event.is_set():
                if status_cb:
                    status_cb("Playlist download stopped by user.", "warning")
                break

            entry = entries[idx - 1]
            if not entry:
                continue

            video_title = entry.get('title') or f"Episode {idx}"
            raw_url = entry.get('url') or entry.get('id')
            if not raw_url:
                continue

            v_str = str(raw_url).strip()
            if v_str.startswith('http://') or v_str.startswith('https://'):
                video_url = v_str
            elif 'watch?v=' in v_str:
                video_url = f"https://www.youtube.com/{v_str.lstrip('/')}"
            elif v_str.startswith('/watch'):
                video_url = f"https://www.youtube.com{v_str}"
            else:
                video_url = f"https://www.youtube.com/watch?v={v_str}"

            # Check if already exists (Auto-Resume)
            if skip_existing:
                existing = find_existing_episode_file(target_dir, idx)
                if existing:
                    skipped += 1
                    fn = os.path.basename(existing)
                    if status_cb:
                        status_cb(f"[{step}/{total_selected}] (Ep {idx}) Already exists: {fn}", "info")
                    if overall_progress_cb:
                        overall_progress_cb(step, total_selected, f"[Skipped] {video_title}")
                    if video_progress_cb:
                        video_progress_cb(100.0, 100, 100, "Skipped", "0s")
                    continue

            if status_cb:
                status_cb(f"[{step}/{total_selected}] (Ep {idx}) Downloading: {video_title}", "info")

            if overall_progress_cb:
                overall_progress_cb(step, total_selected, video_title)

            # Template for this episode
            if filename_format == 'numeric':
                outtmpl = os.path.join(target_dir, f'{idx}.%(ext)s')
            elif filename_format == 'title':
                outtmpl = os.path.join(target_dir, '%(title)s.%(ext)s')
            else:  # 'numbered_title'
                outtmpl = os.path.join(target_dir, f'{idx:02d} - %(title)s.%(ext)s')

            def per_video_hook(d):
                if cancel_event and cancel_event.is_set():
                    raise KeyboardInterrupt("Cancelled")
                if d["status"] == "downloading" and video_progress_cb:
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    downloaded = d.get("downloaded_bytes", 0)
                    speed = d.get("speed")
                    eta = d.get("eta")
                    pct = (downloaded / total * 100) if total > 0 else 0.0
                    speed_str = f"{speed / 1048576:.1f} MB/s" if speed else "--"
                    eta_str = f"{int(eta)}s" if eta else "--"
                    video_progress_cb(pct, downloaded, total, speed_str, eta_str)
                elif d["status"] == "finished" and status_cb:
                    status_cb(f"[{step}/{total_selected}] Finalizing & merging Ep {idx}...", "info")

            ydl_opts = self.build_ydl_opts(target_dir, quality_key=quality_key, outtmpl=outtmpl, progress_hook=per_video_hook, speed_limit=speed_limit)
            ydl_opts['noplaylist'] = True
            ydl_opts['ignoreerrors'] = True
            if extra_opts:
                ydl_opts.update(extra_opts)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    inf = ydl.extract_info(video_url, download=True)
                    final_path = self.get_downloaded_path(inf, ydl, merge_fmt=ydl_opts.get('merge_output_format'), is_audio=is_audio)

                    # Robust fallback search for this episode
                    if not final_path or not os.path.isfile(final_path):
                        final_path = find_existing_episode_file(target_dir, idx)

                    if not final_path or not os.path.isfile(final_path):
                        # Match any media file created in target_dir
                        candidates = [
                            os.path.join(target_dir, f) for f in os.listdir(target_dir)
                            if not f.endswith(('.part', '.ytdl', '.temp')) and os.path.isfile(os.path.join(target_dir, f))
                        ]
                        if candidates:
                            candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                            final_path = candidates[0]

                    if final_path and self.validate_file(final_path, is_audio=is_audio):
                        succeeded += 1
                        downloaded_paths.append(final_path)
                        fn = os.path.basename(final_path)
                        if status_cb:
                            status_cb(f"[{step}/{total_selected}] ✓ Completed: {fn}", "success")
                    else:
                        failed += 1
                        if status_cb:
                            status_cb(f"[{step}/{total_selected}] Failed to download Ep {idx}", "warning")
            except KeyboardInterrupt:
                if status_cb:
                    status_cb("Playlist download stopped by user.", "warning")
                break
            except Exception as e:
                failed += 1
                if status_cb:
                    status_cb(f"Error on ep {idx}: {e}", "warning")

            time.sleep(0.5)

        summary_msg = (
            f"Playlist finished: {succeeded} downloaded, {skipped} existing skipped, {failed} failed. "
            f"Folder: {clean_folder}"
        )
        if status_cb:
            status_cb(summary_msg, "success" if succeeded > 0 or skipped > 0 else "warning")

        return (succeeded > 0 or skipped > 0), downloaded_paths
