import subprocess
import requests
import time
import re
import os
import sys
import json
import msvcrt 
import win32pipe, win32file, pywintypes # Requires: pip install pywin32
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURATION ---
# Ensure this points to your mpv.exe
MPV_PATH = r"C:\songs lyrics preview\mpv-x86_64-v3-20260419-git-06f4ce7\mpv.exe"
COOKIE_FILE = "cookies.txt" 
SEARCH_CACHE_FILE = "search_cache.json"
LYRIC_OFFSET = 0.8  # Slightly increased offset for better reading
# ---------------------

def get_cache():
    if os.path.exists(SEARCH_CACHE_FILE):
        try:
            with open(SEARCH_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {}

def save_cache(cache):
    try:
        with open(SEARCH_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except: pass

def contains_sinhala(text):
    """Checks if the text contains Sinhala characters"""
    return any('\u0d80' <= char <= '\u0dff' for char in text)

def transliterate_sinhala(text):
    """Refined Singlish Engine for exact phonetic sounds"""
    if not text or not contains_sinhala(text): return text
    vowels = {
        'අ': 'a', 'ආ': 'aa', 'ඇ': 'ae', 'ඈ': 'aae', 'ඉ': 'i', 'ඊ': 'ii', 
        'උ': 'u', 'ඌ': 'uu', 'එ': 'e', 'ඒ': 'ee', 'ඔ': 'o', 'ඕ': 'oo'
    }
    consonants = {
        'ක': 'k', 'ඛ': 'kh', 'ග': 'g', 'ඝ': 'gh', 'ඞ': 'ng', 'ඟ': 'ng',
        'ච': 'ch', 'ඡ': 'chh', 'ජ': 'j', 'ඣ': 'jh', 'ඤ': 'ny', 'ඥ': 'gn', 'ඦ': 'nj',
        'ට': 't', 'ඨ': 'th', 'ඩ': 'd', 'ඪ': 'dh', 'ණ': 'n', 'ඬ': 'nd',
        'ත': 'th', 'ථ': 'thh', 'ද': 'd', 'ධ': 'dh', 'න': 'n', 'ඳ': 'nd',
        'ප': 'p', 'ඵ': 'ph', 'බ': 'b', 'භ': 'bh', 'ම': 'm', 'ඹ': 'mb',
        'ය': 'y', 'ර': 'r', 'ල': 'l', 'ව': 'w', 'ශ': 'sha', 'ෂ': 'sha', 'ස': 'sa', 
        'හ': 'h', 'ළ': 'l', 'ෆ': 'f'
    }
    modifiers = {
        'ා': 'aa', 'ැ': 'ae', 'ෑ': 'aae', 'ි': 'i', 'ී': 'ii', 'ු': 'u', 'ූ': 'uu', 
        'ෙ': 'e', 'ේ': 'ee', 'ො': 'o', 'ෝ': 'oo', 'ෞ': 'au'
    }
    hal_kireema = '්'
    res, i = "", 0
    while i < len(text):
        char = text[i]
        if char in vowels:
            res += vowels[char]
            i += 1
        elif char in consonants:
            base = consonants[char]
            next_c = text[i+1] if i+1 < len(text) else None
            if next_c == hal_kireema:
                res += base
                i += 2
            elif next_c in modifiers:
                res += base + modifiers[next_c]
                i += 2
            else:
                res += base + "a"
                i += 1
        elif char == 'ං':
            res += "ng"
            i += 1
        else:
            res += char
            i += 1
    # Cleanup for natural Singlish look
    res = res.replace('aa', 'a').replace('ii', 'i').replace('uu', 'u').replace('ee', 'e').replace('oo', 'o')
    return res.title().strip()

if sys.platform == "win32":
    os.system('chcp 65001 > nul')

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_term_width():
    try: return os.get_terminal_size().columns
    except: return 65

def clean_title(title):
    # Removes junk text that prevents API matches
    junk = [r'\(Official.*?\)', r'\[Official.*?\]', r'Music Video', r'Lyric Video', r'HD', r'4K', r'\(Lyrics\)', r'Lyrics', r'Official Video', r'Video Song', r'- \d{4}']
    for pattern in junk:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    return title.strip()

def get_lyrics_from_db(yt_title, user_query):
    """
    Search international synced database with retries and better timeout.
    """
    cleaned_yt = clean_title(yt_title)
    search_list = [cleaned_yt, user_query]
    search_list = [q for q in dict.fromkeys(search_list) if q and len(q) >= 3]
    
    session = requests.Session()
    for query in search_list:
        url = "https://lrclib.net/api/search"
        # Try up to 2 times for each query if it times out
        for attempt in range(2):
            try:
                response = session.get(url, params={'q': query}, timeout=10).json()
                if response and isinstance(response, list):
                    for result in response:
                        if result.get('syncedLyrics'):
                            track = result.get('trackName', '').lower()
                            # Validation: track name should be in the title or query
                            if track and (track in cleaned_yt.lower() or track in user_query.lower()):
                                return result['syncedLyrics']
                    
                    # Fallback to the very first synced result if it exists
                    if response[0].get('syncedLyrics'):
                        return response[0]['syncedLyrics']
                break # Success (even if no lyrics), move to next query in search_list
            except requests.exceptions.Timeout:
                if attempt == 0: 
                    time.sleep(1) # Short wait before retry
                    continue
            except: break
    return None

def draw_ui(title, current_lyric, past_lyrics, progress=0):
    clear_screen()
    w = get_term_width()
    print("\033[1;33m" + "━"*w)
    print("  SINHALA SMART TRANS-LYRIC SYSTEM (PRO)  ".center(w))
    print("━"*w + "\033[0m")
    display_title = (title[:w-20] + '..') if len(title) > w-20 else title
    print(f"\n\033[1;36m" + f" 🎵 {display_title.upper()} ".center(w) + "\033[0m")
    print("\n" * 2)
    for old_lyric in past_lyrics[-2:]:
        print(f"\033[2;37m{old_lyric.center(w)}\033[0m")
    if current_lyric:
        print(f"\n\033[1;93m▶ ♪ {current_lyric.upper()} ♪ ◀\033[0m".center(w + 10))
    else:
        print("\n" + "...".center(w))
    print("\n" * 3)
    bar_width = 30
    filled = int(bar_width * progress)
    bar = "█" * filled + "░" * (bar_width - filled)
    print("\033[1;33m━"*w + f"\n\033[1;37m [q] Quit | {bar} | [←/→] Seek\033[0m".center(w+15))

def parse_lrc(lrc_text):
    lyrics = []
    if not lrc_text: return []
    for line in lrc_text.splitlines():
        if ']' in line:
            try:
                parts = line.split(']', 1)
                time_str = parts[0][1:].strip()
                text = parts[1].strip() if len(parts) > 1 else ""
                
                # Handle cases with multiple timestamps like [00:01.00][00:05.00] Text
                while text.startswith('['):
                    more_parts = text.split(']', 1)
                    text = more_parts[1].strip() if len(more_parts) > 1 else ""

                if ":" in time_str:
                    m, s = time_str.split(':')
                    total_seconds = int(m) * 60 + float(s)
                    rom_text = transliterate_sinhala(text)
                    lyrics.append({'time': total_seconds, 'text': rom_text})
            except: continue
    return sorted(lyrics, key=lambda x: x['time'])

def search_youtube_and_check(query):
    clear_screen()
    
    # Check cache first
    cache = get_cache()
    if query.lower() in cache:
        cached_data = cache[query.lower()]
        if any(v.get('has_lyrics') for v in cached_data):
            print(f"\033[1;32m🚀 Loading cached results for: '{query}'...\033[0m")
            return cached_data

    print(f"\033[1;32m🔍 Searching YouTube for: '{query}'...\033[0m")
    cmd = ['yt-dlp', f'ytsearch5:{query}', '--dump-json', '--flat-playlist', '--no-warnings']
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        raw_results = []
        for line in result.stdout.splitlines():
            try:
                data = json.loads(line)
                if data.get('_type') == 'url' or data.get('id'):
                    raw_results.append(data)
            except: continue
        
        if not raw_results:
            print("\033[1;31m⚠ No results found on YouTube.\033[0m")
            time.sleep(2)
            return []

        print("\n\033[1;33m--- SEARCH RESULTS ---\033[0m")
        final_videos = []
        for i, data in enumerate(raw_results, 1):
            title = data.get('title', 'Unknown Title')
            v_id = data.get('id')
            
            # Real-time feedback with "WAITING" status for slower API
            print(f"{i}. \033[1;33m[⏳ WAITING] {title[:60]}...\033[0m", end='\r')
            
            lrc_text = get_lyrics_from_db(title, query)
            has_lrc = True if lrc_text else False
            
            status = "\033[1;32m[✔ LYRICS FOUND]\033[0m" if has_lrc else "\033[1;31m[✖ NO SYNC DATA]\033[0m"
            print("\033[K" + f"{i}. {status} \033[1;37m{title}\033[0m")
            
            final_videos.append({
                'title': title, 
                'url': f"https://www.youtube.com/watch?v={v_id}", 
                'has_lyrics': has_lrc,
                'lrc_data': lrc_text,
                'duration': data.get('duration', 0)
            })
            # Respectful delay between checks
            time.sleep(0.5) 
        
        # Save to cache if we found lyrics
        if any(v['has_lyrics'] for v in final_videos):
            cache[query.lower()] = final_videos
            save_cache(cache)
            
        return final_videos
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)
        return []

def play_with_mpv(vid_data, user_query):
    # Ensure we try one last time for lyrics if not found during search
    lrc_text = vid_data['lrc_data']
    if not lrc_text:
        lrc_text = get_lyrics_from_db(vid_data['title'], user_query)
    
    synced_lyrics = parse_lrc(lrc_text)

    ipc_pipe = r"\\.\pipe\mpv-lyric-pipe"
    mpv_cmd = [MPV_PATH, vid_data['url'], f"--input-ipc-server={ipc_pipe}", "--geometry=450x320-10+10", "--ontop", "--no-terminal"]
    if os.path.exists(COOKIE_FILE): mpv_cmd.append(f"--ytdl-raw-options=cookies={COOKIE_FILE}")

    mpv_proc = subprocess.Popen(mpv_cmd)
    print(f"\033[1;32m🚀 MPV Started. Connecting to sync engine...\033[0m")
    time.sleep(3) 

    last_idx, past_lyrics, duration = -1, [], vid_data['duration']
    try:
        handle = win32file.CreateFile(ipc_pipe, win32file.GENERIC_READ | win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, 0, None)
        print(f"\033[1;32m🔗 Connected to MPV! Playing lyrics...\033[0m")
        while mpv_proc.poll() is None:
            if msvcrt.kbhit() and msvcrt.getch().decode('utf-8').lower() == 'q': break
            
            # Ask MPV for current time position
            req = json.dumps({"command": ["get_property", "time-pos"], "request_id": 1}) + "\n"
            win32file.WriteFile(handle, req.encode())
            
            # Robust IPC reading
            try:
                _, resp = win32file.ReadFile(handle, 4096)
                for line in resp.decode().splitlines():
                    data = json.loads(line)
                    if data.get('request_id') == 1:
                        current_time = data.get('data')
                        if current_time is not None:
                            prog_percent = current_time / duration if duration > 0 else 0
                            adjusted_time = current_time + LYRIC_OFFSET
                            
                            # Find correct lyric line (Seek-friendly)
                            new_idx = -1
                            for i, l in enumerate(synced_lyrics):
                                if adjusted_time >= l['time']: new_idx = i
                                else: break
                            
                            if new_idx != last_idx:
                                # Reset view if seeking backwards
                                if new_idx < last_idx: past_lyrics = []
                                
                                if new_idx != -1 and new_idx > last_idx and last_idx != -1: 
                                    past_lyrics.append(synced_lyrics[last_idx]['text'])
                                    
                                curr_text = synced_lyrics[new_idx]['text'] if new_idx != -1 else ""
                                draw_ui(vid_data['title'], curr_text, past_lyrics, prog_percent)
                                last_idx = new_idx
            except Exception as e:
                # print(f"IPC Error: {e}") # Keep quiet in UI but handle it
                pass
            time.sleep(0.05)
    except Exception as e:
        print(f"\033[1;31m❌ Connection Error: {e}\033[0m")
        time.sleep(2)
    finally:
        mpv_proc.terminate()
        clear_screen()

if __name__ == "__main__":
    while True:
        clear_screen()
        query = input("\033[1;37mEnter Song Name (or 'q' to quit): \033[0m").strip()
        if not query or query.lower() == 'q': break
        results = search_youtube_and_check(query)
        if results:
            print("\n\033[1;33m--- SEARCH RESULTS ---\033[0m")
            for i, v in enumerate(results, 1):
                status = "\033[1;32m[✔ LYRICS FOUND]\033[0m" if v['has_lyrics'] else "\033[1;31m[✖ NO SYNC DATA]\033[0m"
                print(f"{i}. {status} \033[1;37m{v['title']}\033[0m")
            c_raw = input("\nChoice (1-5), 's' for new search: ").strip().lower()
            if c_raw == 's': continue
            try:
                choice = int(c_raw) - 1
                if 0 <= choice < len(results): play_with_mpv(results[choice], query)
            except: pass
//add git repo
