📝 Alaya Lyric Sync: The Pro-Creator Terminal Karaoke
Alaya Lyric Sync is a high-performance, aesthetic terminal-based application designed to bridge the gap between digital entertainment and real-time data processing. It allows users to play any YouTube song via the MPV player while viewing perfectly synced lyrics in a professional, "hacker-style" terminal interface.
🌟 Why this project exists?
In regions like Sri Lanka, many local songs lack high-quality synced lyric data in global databases. This tool solves that by offering a "Live Creator Mode", allowing users to manually sync plain text lyrics from the web to a playing track in real-time.
🚀 Key Features
Smart YouTube Integration: Search and stream high-quality audio/video directly through yt-dlp and MPV.
Deep-Search Lyric Engine: Multi-fallback logic to fetch .lrc (synced) files from the LRCLIB database.
Singlish Transliteration Engine: A custom-built phonetic engine that converts Sinhala Unicode script into readable English letters for a sleek terminal look.
Live-Creator Mode: If no synced data is found, paste plain text from Google, and sync the song yourself by tapping Enter as the singer sings—perfect for creating WhatsApp Status content.
Aesthetic UI: Features centered lyrics, dimming effects for past lines, glowing highlights for the current line, and a real-time progress bar.
Low-Latency Sync: Uses Windows Named Pipes (IPC) to talk directly to the MPV player for millisecond-accurate timing.
🛠️ Technology Stack
Language: Python 3.x
Media Engine: MPV Player & yt-dlp
Real-time Sync: IPC (Inter-Process Communication) via pywin32
API: LRCLIB (REST API)
Styling: ANSI Escape Sequences (for terminal colors and effects)
📦 Setup & Installation
Clone the Repo:
code
Bash
git clone https://github.com/yourusername/alaya-lyric-sync.git
Install Dependencies:
code
Bash
pip install yt-dlp requests pywin32
External Tools:
Download mpv.exe and ffmpeg.exe.
Export your YouTube cookies to cookies.txt using a browser extension.
Run:
code
Bash
python lyric_sync.py
💡 Portfolio Context
This project serves as a "Lab Implementation" of my ability to handle:
Complex String Manipulation (Unicode to Phonetic English).
Process Communication (Talking to external media players).
UI/UX Design in a constrained environment (Terminal).
Community-Driven Solutions (Enabling users to create data where none exists).
