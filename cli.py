#!/usr/bin/env python3
"""
Interactive Command-Line Interface for YouTube Downloader.
Can be run via: python cli.py or python main.py --cli
"""

import os
import sys
import time

from core.engine import DownloadEngine, QUALITY_PRESETS
from core.playlist_utils import is_playlist_url, parse_episodes, sanitize_folder_name
from core.config import ConfigManager

def print_banner(engine, config):
    q_key = config.get("default_quality", "1")
    q_name = QUALITY_PRESETS.get(q_key, QUALITY_PRESETS['1'])['short']
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                                                      ║")
    print("  ║        🎬  YouTube Video & Playlist Downloader  🎬   ║")
    print("  ║        ─────────────────────────────────────────     ║")
    print("  ║        4K • 1080p • 720p • Audio MP3 • Playlists     ║")
    print(f"  ║        Default Quality: {q_name:<29s}║")
    print("  ║                                                      ║")
    print("  ╚══════════════════════════════════════════════════════╝")

def print_menu():
    print()
    print("  ┌──────────────────────────────────────────────────────┐")
    print("  │                     Main Menu                        │")
    print("  ├──────────────────────────────────────────────────────┤")
    print("  │  1. Download a single video                          │")
    print("  │  2. Download a playlist / show                       │")
    print("  │  3. Change default quality                           │")
    print("  │  4. Change default download directory                │")
    print("  │  0. Exit                                             │")
    print("  └──────────────────────────────────────────────────────┘")

def select_quality_prompt(current_default="1"):
    print("\n  Available Qualities:")
    for k, v in QUALITY_PRESETS.items():
        marker = " (Default)" if k == current_default else ""
        print(f"    [{k}] {v['name']}{marker}")
    choice = input(f"  Enter choice (1-6, press Enter for default): ").strip()
    return choice if choice in QUALITY_PRESETS else current_default

def main():
    config = ConfigManager()
    engine = DownloadEngine()

    print_banner(engine, config)
    save_path = config.get("download_dir", os.path.dirname(os.path.abspath(__file__)))
    print(f"  📁 Default save directory: {save_path}")

    if engine.ffmpeg_dir:
        print(f"  ✓ FFmpeg detected: {engine.ffmpeg_dir}")
    else:
        print("  ⚠ FFmpeg not found — limited to single stream formats.")

    while True:
        print_menu()
        try:
            choice = input("\n  Enter choice (0-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye! 👋")
            break

        if choice == "1":
            url = input("\n  Enter video URL: ").strip()
            if not url:
                continue

            q_key = select_quality_prompt(config.get("default_quality", "1"))
            print("  Downloading...")
            success, path = engine.download_single(
                url,
                save_path,
                quality_key=q_key,
                status_cb=lambda msg, lvl: print(f"  [{lvl.upper()}] {msg}")
            )

        elif choice == "2":
            url = input("\n  Enter playlist URL: ").strip()
            if not url:
                continue

            info = engine.fetch_info(url)
            if not info or not info.get("is_playlist"):
                print("  ⚠ Could not load playlist info.")
                continue

            title = info.get("title", "YouTube Playlist")
            count = info.get("count", 0)
            print(f"\n  Found Playlist: {title} ({count} episodes)")

            folder = input(f"  Enter folder name [Press Enter for '{sanitize_folder_name(title)}']: ").strip()
            folder_clean = sanitize_folder_name(folder or title)

            print("\n  Episode selection:")
            print(f"    [1] All episodes (1 to {count})")
            print(f"    [2] Download specific range (e.g. 5-15)")
            print(f"    [3] SKIP specific range (e.g. 1-3)")
            ep_opt = input("  Choice (1-3, default=1): ").strip()

            selected = list(range(1, count + 1))
            if ep_opt == "2":
                r_str = input(f"  Enter range (e.g. 1-10 or 5-{count}): ").strip()
                selected = parse_episodes(r_str, count)
            elif ep_opt == "3":
                s_str = input("  Enter episodes to SKIP (e.g. 1-3): ").strip()
                skip_set = set(parse_episodes(s_str, count))
                selected = [i for i in range(1, count + 1) if i not in skip_set]

            q_key = select_quality_prompt(config.get("default_quality", "1"))

            engine.download_playlist(
                url,
                save_path,
                folder_name=folder_clean,
                quality_key=q_key,
                selected_indices=selected,
                status_cb=lambda msg, lvl: print(f"  [{lvl.upper()}] {msg}")
            )

        elif choice == "3":
            new_q = select_quality_prompt(config.get("default_quality", "1"))
            config.set("default_quality", new_q)
            print(f"  ✓ Default quality set to: {QUALITY_PRESETS[new_q]['name']}")

        elif choice == "4":
            new_dir = input(f"  Enter new download directory: ").strip()
            if new_dir:
                os.makedirs(new_dir, exist_ok=True)
                config.set("download_dir", new_dir)
                save_path = new_dir
                print(f"  ✓ Directory saved: {new_dir}")

        elif choice == "0":
            print("\n  Goodbye! 👋")
            break

if __name__ == "__main__":
    main()
