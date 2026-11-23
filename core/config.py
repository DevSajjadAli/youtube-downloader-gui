import os
import json

DEFAULT_CONFIG = {
    "download_dir": os.path.join(os.path.expanduser("~"), "Downloads", "YouTube"),
    "default_quality": "1",
    "appearance_mode": "Dark",
    "color_theme": "blue",
    "skip_existing": True,
    "filename_format": "numbered_title",  # "numbered_title", "numeric", "title"
    "auto_fetch_info": True,
    "clipboard_watch": False,
    "download_subtitles": False,
    "embed_thumbnail": False,
    "sound_notify": True,
    "auto_open_folder": False,
    "speed_limit": "",
    "output_template": "%(title)s.%(ext)s"
}

class ConfigManager:
    """Manages persistent application settings in a JSON configuration file."""

    def __init__(self, config_path=None):
        if config_path is None:
            # Place config.json next to main.py or in AppData
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.config_path = os.path.join(app_dir, "config.json")
        else:
            self.config_path = config_path

        self.data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Load settings from disk."""
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    if isinstance(saved, dict):
                        self.data.update(saved)
            except Exception as e:
                print(f"Warning: could not load config ({e}). Using defaults.")

        # Ensure download directory exists
        dl_dir = self.data.get("download_dir")
        if dl_dir:
            try:
                os.makedirs(dl_dir, exist_ok=True)
            except OSError:
                pass

    def save(self):
        """Save current settings to disk."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Warning: could not save config ({e})")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
