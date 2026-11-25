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

def clean_single_video_url(url):
    """
    Clean and canonicalize a YouTube single video URL.
    Strips playlist tracking parameters (&list=, &index=) while preserving the video ID.
    Handles watch?v=, youtu.be/, /shorts/, and mobile URLs.
    """
    if not url:
        return ""
    u = url.strip()
    # youtu.be/<id>
    if "youtu.be/" in u:
        vid = u.split("youtu.be/")[1].split("?")[0].split("&")[0].strip("/")
        return f"https://www.youtube.com/watch?v={vid}"
    # youtube.com/shorts/<id>
    if "/shorts/" in u:
        vid = u.split("/shorts/")[1].split("?")[0].split("&")[0].strip("/")
        return f"https://www.youtube.com/watch?v={vid}"
    # watch?v=<id>
    if "watch?v=" in u:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(u)
            qs = urllib.parse.parse_qs(parsed.query)
            if "v" in qs and qs["v"]:
                return f"https://www.youtube.com/watch?v={qs['v'][0]}"
        except Exception:
            pass
    return u


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
        'format_ffmpeg': 'bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo+bestaudio/best',
        'format_no_ffmpeg': 'best[ext=mp4]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '2': {
        'name': '1080p (Full HD — LED TV Compatible)',
        'short': '1080p Full HD',
        'badge': '1080p',
        'format_ffmpeg': 'bestvideo[height<=1080][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080][vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo[height<=1080]+bestaudio[acodec^=mp4a]/best[height<=1080][ext=mp4]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best',
        'format_no_ffmpeg': 'best[height<=1080][ext=mp4]/best[height<=1080]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '3': {
        'name': '720p (HD — LED TV & All Devices Compatible)',
        'short': '720p HD (Universal)',
        'badge': '720p',
        'format_ffmpeg': 'bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=720][vcodec^=avc]+bestaudio[acodec^=mp4a]/bestvideo[height<=720]+bestaudio[acodec^=mp4a]/best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
        'format_no_ffmpeg': 'best[height<=720][ext=mp4]/best[height<=720]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '4': {
        'name': '480p (SD — Universal MP4)',
        'short': '480p SD',
        'badge': '480p',
        'format_ffmpeg': 'bestvideo[height<=480][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=480][vcodec^=avc]+bestaudio[acodec^=mp4a]/best[height<=480][ext=mp4]/bestvideo[height<=480]+bestaudio/best[height<=480]/best',
        'format_no_ffmpeg': 'best[height<=480][ext=mp4]/best[height<=480]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '5': {
        'name': '360p (Low — Smallest MP4)',
        'short': '360p Low',
        'badge': '360p',
        'format_ffmpeg': 'bestvideo[height<=360][vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo[height<=360][vcodec^=avc]+bestaudio[acodec^=mp4a]/best[height<=360][ext=mp4]/bestvideo[height<=360]+bestaudio/best[height<=360]/best',
        'format_no_ffmpeg': 'best[height<=360][ext=mp4]/best[height<=360]/best',
        'is_audio': False,
        'merge_fmt': 'mp4'
    },
    '6': {
        'name': 'Audio Only: MP3 (320 kbps Ultra Quality)',
        'short': 'Audio MP3 320k',
        'badge': 'MP3 320k',
        'format_ffmpeg': 'bestaudio/best',
        'format_no_ffmpeg': 'bestaudio[ext=m4a]/bestaudio/best',
        'is_audio': True,
        'audio_codec': 'mp3',
        'audio_quality': '320',
        'merge_fmt': None
    },
    '7': {
        'name': 'Audio Only: MP3 (192 kbps Standard Quality)',
        'short': 'Audio MP3 192k',
        'badge': 'MP3 192k',
        'format_ffmpeg': 'bestaudio/best',
        'format_no_ffmpeg': 'bestaudio[ext=m4a]/bestaudio/best',
        'is_audio': True,
        'audio_codec': 'mp3',
        'audio_quality': '192',
        'merge_fmt': None
    },
    '8': {
        'name': 'Audio Only: M4A / AAC (Original Audio Quality)',
        'short': 'Audio M4A',
        'badge': 'M4A AAC',
        'format_ffmpeg': 'bestaudio[ext=m4a]/bestaudio/best',
        'format_no_ffmpeg': 'bestaudio[ext=m4a]/bestaudio/best',
        'is_audio': True,
        'audio_codec': 'm4a',
        'audio_quality': '128',
        'merge_fmt': None
    },
    '9': {
        'name': 'Audio Only: WAV (Uncompressed Studio Master)',
        'short': 'Audio WAV',
        'badge': 'WAV Lossless',
        'format_ffmpeg': 'bestaudio/best',
        'format_no_ffmpeg': 'bestaudio/best',
        'is_audio': True,
        'audio_codec': 'wav',
        'audio_quality': '0',
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

    def fetch_info(self, url, force_single=False):
        """
        Extract video or playlist metadata without downloading.
        Returns a dictionary with comprehensive stream intelligence,
        dynamic quality presets with estimated file sizes, subtitles, and channel stats.
        """
        if not url or not url.strip():
            return None

        url = url.strip()
        has_single_marker = ("watch?v=" in url or "/shorts/" in url or "youtu.be/" in url)
        if force_single or (has_single_marker and not url.startswith("https://www.youtube.com/playlist")):
            target_url = clean_single_video_url(url)
            is_pl = False
        else:
            target_url = url
            is_pl = is_playlist_url(url)

        ydl_opts = {
            'extract_flat': True if is_pl else False,
            'noplaylist': True if (force_single or not is_pl) else False,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False if (force_single or not is_pl) else True,
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
                info = ydl.extract_info(target_url, download=False)
                if not info:
                    return None

                entries = info.get('entries')
                is_actually_playlist = (
                    not force_single and (
                        entries is not None or
                        info.get('_type') in ('playlist', 'multi_video', 'channel', 'show')
                    )
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

                    thumb = info.get('thumbnail') or (entries_list[0].get('thumbnail') if entries_list else None)

                    return {
                        'is_playlist': True,
                        'title': detected_title,
                        'raw_title': raw_title,
                        'uploader': uploader,
                        'count': len(entries_list),
                        'entries': entries_list,
                        'thumbnail': thumb,
                        'url': target_url
                    }
                else:
                    # ── Comprehensive Single Video Extraction ─────────────────
                    title = info.get('title', 'YouTube Video')
                    uploader = info.get('uploader') or info.get('channel') or 'Unknown Channel'
                    channel_url = info.get('channel_url') or info.get('uploader_url') or ''
                    duration = info.get('duration') or 0
                    view_count = info.get('view_count')
                    like_count = info.get('like_count')
                    upload_date = str(info.get('upload_date') or '')
                    description = info.get('description') or ''
                    categories = info.get('categories') or []
                    tags_raw = info.get('tags') or []

                    # Duration formatting
                    mins, secs = divmod(int(duration), 60)
                    hours, mins = divmod(mins, 60)
                    duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours else f"{mins:02d}:{secs:02d}"

                    # Subscriber count
                    subs_count = info.get('channel_follower_count')
                    if subs_count:
                        if subs_count >= 1_000_000:
                            subs_str = f"{subs_count / 1_000_000:.2f}M subscribers"
                        elif subs_count >= 1_000:
                            subs_str = f"{subs_count / 1_000:.1f}K subscribers"
                        else:
                            subs_str = f"{subs_count} subscribers"
                    else:
                        subs_str = ""

                    # Formatted views and likes
                    view_str = f"{view_count:,} views" if view_count is not None else "— views"
                    if like_count is not None:
                        if like_count >= 1_000_000:
                            like_str = f"{like_count / 1_000_000:.1f}M likes"
                        elif like_count >= 1_000:
                            like_str = f"{like_count / 1_000:.1f}K likes"
                        else:
                            like_str = f"{like_count:,} likes"
                    else:
                        like_str = "— likes"

                    # Upload date format (YYYYMMDD -> DD/MM/YYYY)
                    if upload_date and len(upload_date) == 8:
                        upload_date_fmt = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[:4]}"
                    else:
                        upload_date_fmt = upload_date or "—"

                    # Pick highest resolution thumbnail
                    thumbnails = info.get('thumbnails', [])
                    best_thumb = info.get('thumbnail')
                    if thumbnails:
                        try:
                            valid_thumbs = [t for t in thumbnails if t.get('url')]
                            if valid_thumbs:
                                valid_thumbs.sort(key=lambda t: (t.get('width') or 0) * (t.get('height') or 0), reverse=True)
                                best_thumb = valid_thumbs[0]['url']
                        except Exception:
                            pass

                    # Parse streams, resolutions, FPS, and calculate real approximate sizes
                    formats = info.get('formats', [])
                    best_audio_size = 0
                    best_audio_bitrate = 128
                    for f in formats:
                        if f.get('vcodec') == 'none' and f.get('acodec') != 'none':
                            sz = f.get('filesize') or f.get('filesize_approx') or 0
                            if sz > best_audio_size:
                                best_audio_size = sz
                            abr = f.get('abr') or 0
                            if abr > best_audio_bitrate:
                                best_audio_bitrate = abr

                    if best_audio_size == 0 and duration > 0:
                        best_audio_size = int((best_audio_bitrate * 1000 / 8) * duration)

                    res_map = {}
                    max_fps = 30
                    for f in formats:
                        h = f.get('height')
                        if not h:
                            continue
                        fps = f.get('fps') or 30
                        if fps > max_fps:
                            max_fps = int(fps)
                        filesize = f.get('filesize') or f.get('filesize_approx') or 0
                        vcodec = f.get('vcodec', 'none')
                        acodec = f.get('acodec', 'none')
                        total_size = filesize + (best_audio_size if acodec == 'none' else 0)

                        if h not in res_map or total_size > res_map[h]['total_size']:
                            res_map[h] = {
                                'height': h,
                                'fps': int(fps) if fps else 30,
                                'total_size': total_size,
                                'vcodec': vcodec,
                                'acodec': acodec,
                                'format_id': f.get('format_id')
                            }

                    resolutions = sorted(res_map.keys(), reverse=True)

                    # Dynamic Stream Options tailored specifically for this video
                    stream_options = []
                    max_h = resolutions[0] if resolutions else 1080
                    best_sz = res_map.get(max_h, {}).get('total_size', 0) if resolutions else 0
                    best_sz_str = f" • ~{best_sz / (1024*1024):.1f} MB" if best_sz > 0 else ""
                    stream_options.append(f"[1] Best Available (Original: {max_h}p){best_sz_str}")

                    if any(h >= 1080 for h in resolutions):
                        sz_1080 = res_map.get(1080, {}).get('total_size', 0)
                        fps_1080 = res_map.get(1080, {}).get('fps', 30)
                        sz_str = f" • ~{sz_1080 / (1024*1024):.1f} MB" if sz_1080 > 0 else ""
                        fps_str = f" ({fps_1080}fps)" if fps_1080 and fps_1080 >= 50 else ""
                        stream_options.append(f"[2] 1080p (Full HD{fps_str}){sz_str} [LED TV Ready]")
                    elif max_h > 1080:
                        stream_options.append("[2] 1080p (Full HD — Downscaled) [LED TV Ready]")

                    if any(h >= 720 for h in resolutions):
                        sz_720 = res_map.get(720, {}).get('total_size', 0)
                        fps_720 = res_map.get(720, {}).get('fps', 30)
                        sz_str = f" • ~{sz_720 / (1024*1024):.1f} MB" if sz_720 > 0 else ""
                        fps_str = f" ({fps_720}fps)" if fps_720 and fps_720 >= 50 else ""
                        stream_options.append(f"[3] 720p (HD{fps_str}){sz_str} [Universal MP4]")

                    if any(h >= 480 for h in resolutions):
                        sz_480 = res_map.get(480, {}).get('total_size', 0)
                        sz_str = f" • ~{sz_480 / (1024*1024):.1f} MB" if sz_480 > 0 else ""
                        stream_options.append(f"[4] 480p (SD){sz_str}")

                    if any(h >= 360 for h in resolutions):
                        sz_360 = res_map.get(360, {}).get('total_size', 0)
                        sz_str = f" • ~{sz_360 / (1024*1024):.1f} MB" if sz_360 > 0 else ""
                        stream_options.append(f"[5] 360p (Low){sz_str}")

                    # Audio options with estimated sizes
                    audio_sz_320 = int((320 * 1000 / 8) * duration) if duration > 0 else best_audio_size
                    audio_sz_192 = int((192 * 1000 / 8) * duration) if duration > 0 else int(best_audio_size * 0.6)
                    audio_sz_128 = int((128 * 1000 / 8) * duration) if duration > 0 else int(best_audio_size * 0.4)

                    sz_a320 = f" • ~{audio_sz_320 / (1024*1024):.1f} MB" if audio_sz_320 > 0 else ""
                    sz_a192 = f" • ~{audio_sz_192 / (1024*1024):.1f} MB" if audio_sz_192 > 0 else ""
                    sz_a128 = f" • ~{audio_sz_128 / (1024*1024):.1f} MB" if audio_sz_128 > 0 else ""

                    stream_options.append(f"[6] Audio Only: MP3 (320 kbps Ultra Quality){sz_a320}")
                    stream_options.append(f"[7] Audio Only: MP3 (192 kbps Standard Quality){sz_a192}")
                    stream_options.append(f"[8] Audio Only: M4A / AAC (Original Audio Quality){sz_a128}")
                    stream_options.append(f"[9] Audio Only: WAV (Uncompressed Studio Master)")

                    # Feature badges
                    badges = []
                    if any(h >= 2160 for h in resolutions):
                        badges.append("4K Ultra HD")
                    elif any(h >= 1440 for h in resolutions):
                        badges.append("2K Quad HD")
                    elif any(h >= 1080 for h in resolutions):
                        badges.append("1080p Full HD")
                    elif any(h >= 720 for h in resolutions):
                        badges.append("720p HD")

                    if max_fps >= 50:
                        badges.append(f"{max_fps} FPS")

                    badges.append("LED TV Ready (H.264+AAC)")

                    # Check Shorts
                    is_short = ("/shorts/" in url) or (info.get('width') and info.get('height') and info['height'] > info['width'])
                    if is_short:
                        badges.append("📱 YouTube Short")

                    if categories:
                        badges.append(f"Category: {categories[0]}")

                    # Subtitles parsing with language names
                    sub_map = {
                        'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                        'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
                        'ko': 'Korean', 'zh': 'Chinese', 'hi': 'Hindi', 'ur': 'Urdu',
                        'ar': 'Arabic', 'tr': 'Turkish', 'id': 'Indonesian', 'vi': 'Vietnamese',
                        'bn': 'Bengali', 'pa': 'Punjabi', 'te': 'Telugu', 'ta': 'Tamil'
                    }
                    raw_subs = list(info.get('subtitles', {}).keys()) + list(info.get('automatic_captions', {}).keys())
                    subtitles_list = ["all: All Available Languages", "en: English (Default)"]
                    seen_sub_codes = {'en'}
                    for s in raw_subs:
                        code = s.split('-')[0].lower()
                        if code not in seen_sub_codes:
                            seen_sub_codes.add(code)
                            name = sub_map.get(code, code.upper())
                            subtitles_list.append(f"{code}: {name}")

                    if len(raw_subs) > 0:
                        badges.append(f"{len(seen_sub_codes)} Subtitles")

                    width = info.get('width') or (1920 if any(h >= 1080 for h in resolutions) else 1280)
                    height = info.get('height') or (max_h if resolutions else 720)
                    dimensions_str = f"{width}x{height} ({max_h}p)"

                    return {
                        'is_playlist': False,
                        'title': title,
                        'uploader': uploader,
                        'channel_url': channel_url,
                        'subscribers_str': subs_str,
                        'duration': duration,
                        'duration_str': duration_str,
                        'thumbnail': best_thumb,
                        'view_count': view_count,
                        'view_count_str': view_str,
                        'like_count': like_count,
                        'like_count_str': like_str,
                        'upload_date': upload_date,
                        'upload_date_str': upload_date_fmt,
                        'dimensions_str': dimensions_str,
                        'resolutions': resolutions,
                        'stream_options': stream_options,
                        'subtitles_list': subtitles_list,
                        'badges': badges,
                        'description': description,
                        'categories': categories,
                        'tags': tags_raw[:10],
                        'is_short': is_short,
                        'fps': max_fps,
                        'url': target_url
                    }

        except Exception as e:
            return {'error': str(e)}

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
                # Guarantee audio inside MP4 container is standard AAC stereo for 100% LED TV playback
                ydl_opts['postprocessor_args'] = {
                    'Merger': ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']
                }

        if ffmpeg_dir:
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

        if preset.get('is_audio') and ffmpeg_dir:
            codec = preset.get('audio_codec', 'mp3')
            quality = preset.get('audio_quality', '320')
            pp = {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': codec,
            }
            if quality and quality != '0':
                pp['preferredquality'] = quality
            ydl_opts['postprocessors'] = [pp]

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
