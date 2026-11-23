<div align="center">

<img src="assets/logo.png" width="120" alt="YouTube Downloader Pro Logo"/>

# YouTube Downloader Pro

**The most complete YouTube downloader for Windows — built with Python & CustomTkinter**

[![GitHub Stars](https://img.shields.io/github/stars/DevSajjadAli/youtube-downloader-gui?style=flat-square&color=yellow)](https://github.com/DevSajjadAli/youtube-downloader-gui/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows)](https://github.com/DevSajjadAli/youtube-downloader-gui)

Download YouTube videos, full playlists, TV shows, and audio-only tracks — in any quality up to 4K — with a beautiful modern GUI.

</div>

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **4K / 2K / 1080p / 720p / 480p / 360p** | Full quality selection with FFmpeg-powered merging |
| **MP3 Audio Extraction** | Highest quality audio-only downloads |
| **Playlist & TV Show Manager** | Each playlist saved to its own named folder automatically |
| **Episode Range & Skip Filters** | Download all, a range (5–15), skip specific eps, or a custom list |
| **Auto-Resume / Skip Existing** | Skips already-verified files, resumes interrupted sessions |
| **Batch Download Queue** | Add videos & playlists to a queue, run all at once |
| **Download History** | Full history with timestamps, status badges, and open-folder buttons |
| **Clipboard URL Watch** | Auto-detects YouTube links copied to your clipboard |
| **Subtitle Download** | Optional caption/subtitle download |
| **Thumbnail Embedding** | Embed artwork into downloaded files |
| **Speed Limit Control** | Cap download speed (e.g. `2M`, `500K`) |
| **Custom Output Templates** | Full yt-dlp output template support |
| **Live Logs** | Color-coded real-time activity console |
| **Dark / Light / System Theme** | Full theme switching |
| **FFmpeg Auto-Detection** | Finds FFmpeg automatically; can install it via winget |

---

## 🚀 One-Command Install (Windows PowerShell)

Open **Windows PowerShell** (Windows key → type `powershell` → Enter) and run:

```powershell
irm https://raw.githubusercontent.com/DevSajjadAli/youtube-downloader-gui/main/install.ps1 | iex
```

This will:
1. ✅ Check Python 3.10+ is installed
2. ✅ Install all Python dependencies (`yt-dlp`, `customtkinter`, `Pillow`, etc.)
3. ✅ Check/prompt for FFmpeg installation
4. ✅ Create **Desktop shortcut** and **Start Menu entry**
5. ✅ Generate application icons

After install, double-click **YouTube Downloader Pro** on your Desktop.

> **Requires Python 3.10+** — download from [python.org](https://www.python.org/downloads/) if not installed. Make sure "Add Python to PATH" is checked during install.

---

## 🔧 Manual Setup

```bash
# Clone the repository
git clone https://github.com/DevSajjadAli/youtube-downloader-gui.git
cd "youtube-downloader-gui"

# Install dependencies
pip install -r requirements.txt

# Generate icons (first time only)
python assets/generate_icons.py

# Launch the application
python main.py
```

---

## 📸 Screenshots

```
Main Interface           Playlist Manager         Download History
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ YouTube DL       │    │ Playlists & Shows │    │ Download History  │
│ Pro Desktop      │    │                  │    │                  │
├──┬───────────────┤    │ URL: [..........] │    │ ✓ Video Title    │
│🎬│ Single Video  │    │ Folder: [Show]   │    │   720p  2026-11  │
│📋│ Playlists     │    │ Episodes: 1-25   │    │ ✓ Playlist Name  │
│📥│ Queue(3)      │    │ Skip: 1-3        │    │   1080p 2026-11  │
│📖│ History       │    │                  │    │                  │
│📜│ Logs          │    │ [▶ Download]     │    │ [🗑 Clear All]   │
│⚙️│ Settings      │    │ [+ Add to Queue] │    │                  │
└──┴───────────────┘    └──────────────────┘    └──────────────────┘
```

---

## 📋 Quality Presets

| # | Name | Best For |
|---|------|----------|
| 1 | **Best Available (4K/2K/1080p)** | Maximum quality, requires FFmpeg |
| 2 | **1080p Full HD** | Standard HD, great balance |
| 3 | **720p HD** | Fast downloads, good quality |
| 4 | **480p SD** | Data-saving mode |
| 5 | **360p Low** | Minimum storage |
| 6 | **Audio Only MP3** | Music, podcasts, audio extraction |

---

## 🎬 Playlist & Episode Control

| Mode | Input | Effect |
|------|-------|--------|
| All Episodes | — | Downloads every episode |
| Range | `5-15` | Downloads episodes 5 through 15 |
| Skip Range | `1-3` | Downloads all EXCEPT episodes 1–3 |
| Custom List | `1, 3, 5-8, 12` | Downloads only listed episodes |

Playlists are always saved to a **dedicated folder** named after the playlist — never mixed into a generic "show" folder.

---

## ⚙️ System Requirements

- **OS:** Windows 10 / 11
- **Python:** 3.10 or newer
- **FFmpeg:** Optional but recommended for 4K/1080p quality (auto-installable via winget)

### Python Dependencies

```
yt-dlp>=2026.08.19
customtkinter>=6.0.0
Pillow>=10.0.0
imageio-ffmpeg>=0.4.9
darkdetect>=0.8.0
```

---

## 💻 CLI Mode

Run without a display or for scripting:

```bash
python main.py --cli
# or
python cli.py
```

---

## 🔄 Updating

```powershell
# Re-run the installer to get the latest version
irm https://raw.githubusercontent.com/DevSajjadAli/youtube-downloader-gui/main/install.ps1 | iex
```

Or manually:
```bash
cd "C:\Users\YourName\YoutubeDownloaderGUI"
git pull
pip install -r requirements.txt --upgrade
```

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss changes.

1. Fork the repository
2. Create your branch: `git checkout -b feature/amazing-feature`
3. Commit: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Made with ❤️ using Python · CustomTkinter · yt-dlp · Pillow

**[⭐ Star this repo](https://github.com/DevSajjadAli/youtube-downloader-gui)** if it helped you!

</div>
