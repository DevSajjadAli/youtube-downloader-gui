# YouTube Downloader Core Package
from .config import ConfigManager
from .ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path, get_ffmpeg_dir, is_ffmpeg_available
from .playlist_utils import is_playlist_url, parse_episodes, infer_playlist_name_from_entries, find_existing_episode_file
from .engine import DownloadEngine, QUALITY_PRESETS
