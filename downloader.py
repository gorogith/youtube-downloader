import os
import subprocess
import queue
import threading
import time
import yt_dlp

# Inisialisasi antrian
download_queue = queue.Queue()
current_download = {"type": None, "title": None, "progress": None}  # Status download yang sedang berlangsung

# Constants
DEFAULT_DOWNLOAD_PATH = '/media/xru/New Volume/Download'
YES_NO_PROMPT = " (y/n, default: n): "
DEFAULT_SUBTITLE_LANG = 'en'
AUDIO_FORMATS = ['mp3', 'm4a']
COOKIES_FILE = '/path/to/your/actual/cookies.txt'  # Update this path to the correct location of your cookies file

# Fungsi untuk mendapatkan judul video dari URL
def get_video_title(url):
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if not info_dict or 'title' not in info_dict:
                return None
            return info_dict['title']
    except Exception as e:
        print(f"\n[ERROR] Gagal mendapatkan judul dari URL {url}: {e}")
        return None

# Fungsi untuk menormalkan URL
def normalize_url(url):
    if 'youtube.com/watch' in url and 'list=' in url:
        list_id = url.split('list=')[-1].split('&')[0]
        return f'https://www.youtube.com/playlist?list={list_id}'
    return url

# Fungsi untuk mendapatkan informasi playlist
def get_playlist_info(url):
    url = normalize_url(url)  # Normalize the URL
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if 'entries' in info_dict:
                return {
                    'title': info_dict.get('title', 'Unknown Playlist'),
                    'videos': [
                        {'url': entry['url'], 'title': entry.get('title', 'Unknown Title')}
                        for entry in info_dict['entries'] if entry
                    ]
                }
            return None
    except yt_dlp.utils.DownloadError as e:
        print(f"\n[ERROR] Gagal mendapatkan informasi playlist: {e}")
        return None
    except Exception as e:
        print(f"\n[ERROR] Terjadi kesalahan: {e}")
        return None

# Fungsi untuk mendapatkan judul video dan nama channel dari URL
def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'force_generic_extractor': False
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            if not info_dict or 'title' not in info_dict or 'uploader' not in info_dict:
                return None, None
            return info_dict['title'], info_dict['uploader']
    except Exception as e:
        print(f"\n[ERROR] Gagal mendapatkan informasi dari URL {url}: {e}")
        return None, None

# Fungsi untuk mengunduh video
def download_video(url, download_path=DEFAULT_DOWNLOAD_PATH, title=None, channel=None, subtitles=False, subtitle_lang=DEFAULT_SUBTITLE_LANG):
    if channel:
        download_path = os.path.join(download_path, channel)
    os.makedirs(download_path, exist_ok=True)
    try:
        command = [
            "yt-dlp",
            "-q",  # Quiet mode
            "--no-warnings",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4",
            "--merge-output-format", "mp4",
            "-o", os.path.join(download_path, "%(title)s.%(ext)s"),
            url,
        ]
        if os.path.exists(COOKIES_FILE):
            command.extend(["--cookies", COOKIES_FILE])  # Use cookies for authenticated downloads if the file exists
        if subtitles:
            command.extend([
                "--write-sub",  # Unduh subtitle jika tersedia
                "--write-auto-sub",  # Gunakan subtitle otomatis jika tidak ada
                "--sub-lang", subtitle_lang,  # Tentukan bahasa subtitle
                "--embed-subs"  # Sematkan subtitle ke dalam video
            ])

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            current_download['progress'] = line.strip()
            print(line, end='')

        process.wait()
        if process.returncode == 0:
            print(f"\n[INFO] Video '{title}' berhasil diunduh dengan subtitle.")
        else:
            print(f"\n[ERROR] Terjadi kesalahan saat mengunduh video '{title}'.")
    except Exception as e:
        print(f"\n[ERROR] Terjadi kesalahan saat mengunduh video '{title}': {e}")

# Fungsi untuk mengunduh audio
def download_audio(url, download_path=DEFAULT_DOWNLOAD_PATH, format='mp3', title=None, channel=None):
    if channel:
        download_path = os.path.join(download_path, channel)
    os.makedirs(download_path, exist_ok=True)
    try:
        output_template = os.path.join(download_path, f"%(title)s.%(ext)s")
        command = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]",
            "--extract-audio",
            "--audio-format", format,
            "-o", output_template,
            url,
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            current_download['progress'] = line.strip()
            print(line, end='')

        process.wait()
        if process.returncode == 0:
            print(f"\n[INFO] Audio '{title}' berhasil diunduh.")
        else:
            print(f"\n[ERROR] Terjadi kesalahan saat mengunduh audio '{title}'.")
    except Exception as e:
        print(f"\n[ERROR] Terjadi kesalahan saat mengunduh audio '{title}': {e}")

# Fungsi untuk menambahkan unduhan playlist ke antrian
def download_playlist(url, download_path=DEFAULT_DOWNLOAD_PATH, is_audio=False, format='mp3', subtitles=False, subtitle_lang=DEFAULT_SUBTITLE_LANG):
    url = normalize_url(url)  # Normalize the URL
    playlist_info = get_playlist_info(url)
    if not playlist_info:
        print("\n[ERROR] URL bukan merupakan playlist yang valid")
        return

    total_videos = len(playlist_info['videos'])
    print(f"\n[INFO] Menambahkan {total_videos} video/audio dari playlist '{playlist_info['title']}' ke antrian")

    for video in playlist_info['videos']:
        title, channel = get_video_info(video['url'])
        channel_path = os.path.join(download_path, channel)
        os.makedirs(channel_path, exist_ok=True)
        playlist_path = os.path.join(channel_path, playlist_info['title'])
        os.makedirs(playlist_path, exist_ok=True)
        download_queue.put({
            'type': 'audio' if is_audio else 'video',
            'url': video['url'],
            'path': playlist_path,
            'format': format if is_audio else None,
            'title': title,
            'subtitles': subtitles,
            'subtitle_lang': subtitle_lang
        })

# Fungsi untuk memproses antrian
def process_queue():
    while True:
        if not download_queue.empty():
            item = download_queue.get()
            current_download["type"] = item["type"]
            current_download["title"] = item["title"]
            if item["type"] == "video":
                download_video(
                    item["url"],
                    item.get('path', DEFAULT_DOWNLOAD_PATH),
                    title=item["title"],
                    channel=item.get('channel', None),
                    subtitles=item.get('subtitles', False),
                    subtitle_lang=item.get('subtitle_lang', DEFAULT_SUBTITLE_LANG)
                )
            elif item["type"] == "audio":
                download_audio(
                    item["url"],
                    item.get('path', DEFAULT_DOWNLOAD_PATH),
                    format=item.get('format', 'mp3'),
                    title=item["title"],
                    channel=item.get('channel', None)
                )
            current_download["type"] = None
            current_download["title"] = None
            current_download["progress"] = None
            download_queue.task_done()
        else:
            time.sleep(1)

# Fungsi untuk memvalidasi URL YouTube
def is_valid_youtube_url(url):
    if not url or not isinstance(url, str):
        return False
    return any(domain in url.lower() for domain in ['youtube.com/', 'youtu.be/'])

# Fungsi untuk menangani input pengguna
def handle_input():
    while True:
        print("\nPilihan:")
        print("1. Download video")
        print("2. Download audio")
        print("3. Download playlist")
        print("4. Tampilkan status")
        print("5. Keluar")

        choice = input("\nMasukkan pilihan (1-5): ")

        if choice == '5':
            print("\n[INFO] Menutup program...")
            os._exit(0)

        if choice == '4':
            show_status()
            continue

        if choice == '1':
            while True:
                url = input("Masukkan URL YouTube: ").strip()
                if not is_valid_youtube_url(url):
                    print("\n[ERROR] URL tidak valid! Masukkan URL YouTube yang valid.")
                    continue
                if not get_video_title(url):
                    print("\n[ERROR] Tidak dapat mengambil informasi video. Pastikan URL benar.")
                    continue
                break

            download_path = input(f"Masukkan path download (default '{DEFAULT_DOWNLOAD_PATH}'): ") or DEFAULT_DOWNLOAD_PATH
            subtitles = input(f"Download dengan subtitle?{YES_NO_PROMPT}").strip().lower()
            while subtitles not in ['y', 'n', '']:
                print("\n[ERROR] Pilihan tidak valid! Masukkan 'y' atau 'n'.")
                subtitles = input(f"Download dengan subtitle?{YES_NO_PROMPT}").strip().lower()
            subtitles = subtitles == 'y'
            subtitle_lang = DEFAULT_SUBTITLE_LANG
            if subtitles:
                subtitle_lang = input(f"Masukkan kode bahasa subtitle (default '{DEFAULT_SUBTITLE_LANG}'): ") or DEFAULT_SUBTITLE_LANG
            title, channel = get_video_info(url)
            channel_path = os.path.join(download_path, channel)
            os.makedirs(channel_path, exist_ok=True)
            download_queue.put({
                'type': 'video',
                'url': url,
                'path': channel_path,
                'title': title,
                'subtitles': subtitles,
                'subtitle_lang': subtitle_lang
            })
            print(f"\n[INFO] Video '{title}' ditambahkan ke antrian")

        elif choice == '2':
            while True:
                url = input("Masukkan URL YouTube: ").strip()
                if not is_valid_youtube_url(url):
                    print("\n[ERROR] URL tidak valid! Masukkan URL YouTube yang valid.")
                    continue
                if not get_video_title(url):
                    print("\n[ERROR] Tidak dapat mengambil informasi video. Pastikan URL benar.")
                    continue
                break

            download_path = input(f"Masukkan path download (default '{DEFAULT_DOWNLOAD_PATH}'): ") or DEFAULT_DOWNLOAD_PATH
            title = get_video_title(url)
            format = input(f"Masukkan format audio ({'/'.join(AUDIO_FORMATS)}, default: mp3): ") or 'mp3'
            while format not in AUDIO_FORMATS:
                print(f"\n[ERROR] Format tidak valid! Masukkan salah satu dari {', '.join(AUDIO_FORMATS)}.")
                format = input(f"Masukkan format audio ({'/'.join(AUDIO_FORMATS)}, default: mp3): ") or 'mp3'
            download_queue.put({
                'type': 'audio',
                'url': url,
                'path': download_path,
                'format': format,
                'title': title
            })
            print(f"\n[INFO] Audio '{title}' ditambahkan ke antrian")

        elif choice == '3':
            print("\nPilihan:")
            print("1. Download playlist video")
            print("2. Download playlist audio")
            sub_choice = input("\nMasukkan pilihan (1-2): ")

            if sub_choice in ['1', '2']:
                while True:
                    url = input("Masukkan URL YouTube: ").strip()
                    if not is_valid_youtube_url(url):
                        print("\n[ERROR] URL tidak valid! Masukkan URL YouTube yang valid.")
                        continue
                    if not get_playlist_info(url):
                        print("\n[ERROR] Tidak dapat mengambil informasi playlist. Pastikan URL benar.")
                        continue
                    break

                download_path = input(f"Masukkan path download (default '{DEFAULT_DOWNLOAD_PATH}'): ") or DEFAULT_DOWNLOAD_PATH

                if sub_choice == '1':
                    subtitles = input(f"Download dengan subtitle?{YES_NO_PROMPT}").strip().lower()
                    while subtitles not in ['y', 'n', '']:
                        print("\n[ERROR] Pilihan tidak valid! Masukkan 'y' atau 'n'.")
                        subtitles = input(f"Download dengan subtitle?{YES_NO_PROMPT}").strip().lower()
                    subtitles = subtitles == 'y'
                    subtitle_lang = DEFAULT_SUBTITLE_LANG
                    if subtitles:
                        subtitle_lang = input(f"Masukkan kode bahasa subtitle (default '{DEFAULT_SUBTITLE_LANG}'): ") or DEFAULT_SUBTITLE_LANG
                    download_playlist(url, download_path, is_audio=False, subtitles=subtitles, subtitle_lang=subtitle_lang)
                elif sub_choice == '2':
                    format = input(f"Masukkan format audio ({'/'.join(AUDIO_FORMATS)}, default: mp3): ") or 'mp3'
                    while format not in AUDIO_FORMATS:
                        print(f"\n[ERROR] Format tidak valid! Masukkan salah satu dari {', '.join(AUDIO_FORMATS)}.")
                        format = input(f"Masukkan format audio ({'/'.join(AUDIO_FORMATS)}, default: mp3): ") or 'mp3'
                    download_playlist(url, download_path, is_audio=True, format=format)
            else:
                print("\n[ERROR] Pilihan tidak valid!")

        else:
            print("\n[ERROR] Pilihan tidak valid!")

# Fungsi untuk menampilkan status antrian
def show_status():
    if current_download["title"]:
        print(f"\n[STATUS] Sedang mengunduh: {current_download['title']} ({current_download['type']})")
        if current_download['progress']:
            print(f"[PROGRESS] {current_download['progress']}")
    else:
        print("\n[STATUS] Tidak ada unduhan yang sedang berlangsung.")

    if not download_queue.empty():
        print("\n[ANTRIAN] URL yang menunggu:")
        for idx, item in enumerate(list(download_queue.queue), start=1):
            print(f"  {idx}. {item['title']} ({item['type']})")
    else:
        print("\n[ANTRIAN] Tidak ada URL di antrian.")

# Fungsi utama
def main():
    # Menjalankan thread untuk memproses antrian
    threading.Thread(target=process_queue, daemon=True).start()
    # Menjalankan thread untuk menangani input
    threading.Thread(target=handle_input, daemon=False).start()

if __name__ == "__main__":
    main()
