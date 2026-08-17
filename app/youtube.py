import yt_dlp
import threading
import os
import re

class DummyLogger(object):
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def _strip_ansi(text):
    """Remove ANSI escape codes from a string."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', str(text))

# Use tv_embedded client — bypasses most YouTube 403 blocks
# Falls back through ios → web if needed
YT_EXTRACTOR_ARGS = {
    'youtube': {
        'client': ['tv_embedded', 'ios', 'web']
    }
}

def fetch_youtube_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'logger': DummyLogger(),
        'extractor_args': YT_EXTRACTOR_ARGS,
        'noplaylist': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Extract standard video resolutions
            resolutions = set()
            standard_res = [144, 240, 360, 480, 720, 1080, 1440, 2160]

            for f in info.get('formats', []):
                if f.get('vcodec') not in (None, 'none') and f.get('height'):
                    h = f.get('height')
                    closest = min(standard_res, key=lambda x: abs(x - h))
                    if abs(closest - h) <= 100:
                        resolutions.add(f"{closest}p")

            res_list = sorted(list(resolutions), key=lambda x: int(x.replace('p', '')), reverse=True)
            if not res_list:
                res_list = ["best"]

            has_subs = bool(info.get('subtitles') or info.get('automatic_captions'))

            return {
                "title": info.get('title'),
                "resolutions": res_list,
                "has_subtitles": has_subs
            }
    except Exception as e:
        return {"error": _strip_ansi(str(e))}


class YouTubeDownloader:
    def __init__(self, url, task_id, resolution="best", download_subtitles=False,
                 is_subtitle_only=False, download_path=None):
        self.url = url
        self.task_id = task_id
        self.resolution = resolution
        self.download_subtitles = download_subtitles
        self.is_subtitle_only = is_subtitle_only
        self.download_path = download_path or os.path.expanduser("~/Downloads")
        self.filename = "Fetching details..."
        self.status = "waiting"
        self.progress = 0
        self.speed = "0 KB/s"
        self._cancel_flag = False
        self._pause_flag = False
        self._lock = threading.Lock()

    def progress_hook(self, d):
        if self._cancel_flag:
            raise Exception("Canceled")
        if self._pause_flag:
            raise Exception("Paused")

        if d['status'] == 'finished':
            with self._lock:
                self.progress = 100
                self.speed = "0 KB/s"
                self.filename = os.path.basename(d.get('filename', self.filename))
        elif d['status'] == 'downloading':
            with self._lock:
                self.status = "downloading"
                raw_name = d.get('filename', self.filename)
                self.filename = os.path.basename(raw_name) if raw_name else self.filename
                try:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded = d.get('downloaded_bytes', 0)
                    
                    total_str = ""
                    if total:
                        self.progress = int((downloaded / total) * 100)
                        if total >= 1073741824:  # 1 GB
                            total_str = f" / {total / 1073741824:.2f} GB"
                        else:
                            total_str = f" / {total / 1048576:.2f} MB"
                            
                    speed = d.get('speed', 0)
                    if speed:
                        if speed >= 1048576:
                            self.speed = f"{speed / 1048576:.2f} MB/s{total_str}"
                        else:
                            self.speed = f"{speed / 1024:.1f} KB/s{total_str}"
                except Exception:
                    pass

    def start(self):
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            with self._lock:
                self.status = "error: imageio-ffmpeg missing"
            return

        # Ensure download directory exists
        os.makedirs(self.download_path, exist_ok=True)
        base_tmpl = os.path.join(self.download_path, '%(title)s.%(ext)s')

        extractor_args = {'youtube': {'client': ['android']}}

        if self.is_subtitle_only:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en', 'si'],
                'subtitlesformat': 'srt',
                'outtmpl': base_tmpl,
                'progress_hooks': [self.progress_hook],
                'ffmpeg_location': ffmpeg_path,
                'logger': DummyLogger(),
                'extractor_args': extractor_args,
                'noplaylist': True,
                'cachedir': False,
            }
        else:
            if self.resolution == "best":
                fmt = (
                    'best[ext=mp4][vcodec!=none][acodec!=none]'
                    '/bestvideo[ext=mp4]+bestaudio[ext=m4a]'
                    '/best'
                )
            else:
                h = self.resolution.replace('p', '')
                fmt = (
                    f'best[height<={h}][ext=mp4][vcodec!=none][acodec!=none]'
                    f'/bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]'
                    f'/best[height<={h}]'
                )

            ydl_opts = {
                'outtmpl': base_tmpl,
                'progress_hooks': [self.progress_hook],
                'format': fmt,
                'ffmpeg_location': ffmpeg_path,
                'logger': DummyLogger(),
                'extractor_args': extractor_args,
                'noplaylist': True,
                'retries': 10,
                'fragment_retries': 10,
                'cachedir': False,
            }

            if self.download_subtitles:
                ydl_opts.update({
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'si'],
                    'subtitlesformat': 'srt',
                })

        with self._lock:
            self.status = "downloading"
            self._cancel_flag = False
            self._pause_flag = False

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                with self._lock:
                    if self.is_subtitle_only:
                        self.filename = f"{info.get('title', 'Subtitles')} (Subtitles)"
                    else:
                        self.filename = f"{info.get('title', 'Video')}.{info.get('ext', 'mp4')}"
                    self.status = "completed"
                    self.progress = 100
        except Exception as e:
            err_msg = _strip_ansi(str(e))
            with self._lock:
                if err_msg == "Canceled":
                    self.status = "canceled"
                elif err_msg == "Paused":
                    self.status = "paused"
                else:
                    self.status = f"error: {err_msg}"

    def pause(self):
        with self._lock:
            if self.status == "downloading":
                self._pause_flag = True
                self.status = "paused"

    def resume(self):
        with self._lock:
            if self.status != "paused":
                return
            if self._cancel_flag:
                return   # Don't resume a cancelled task
            self._pause_flag = False

        threading.Thread(target=self.start, daemon=True).start()

    def cancel(self):
        with self._lock:
            self._cancel_flag = True
