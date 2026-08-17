import requests as req_lib
import threading
import time
import os


class Downloader:
    def __init__(self, url, task_id, download_path=None, threads=4):
        self.url = url
        self.task_id = task_id
        self.download_path = download_path or os.path.join(
            os.path.expanduser("~"), "Downloads")
        # Determine filename from URL (deferred full path to start())
        raw_name = url.split('/')[-1].split('?')[0] or f"download_{task_id}.bin"
        self.filename = raw_name          # display name only
        self.status = "waiting"
        self.progress = 0
        self.speed = "0 KB/s"
        self.total_size = 0
        self._downloaded_size = 0
        self._size_lock = threading.Lock()
        self.threads = threads
        self._pause_event = threading.Event()
        self._pause_event.set()           # Set = NOT paused
        self._cancel_flag = False

    @property
    def downloaded_size(self):
        with self._size_lock:
            return self._downloaded_size

    def _add_downloaded(self, amount):
        with self._size_lock:
            self._downloaded_size += amount

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _get_file_size(self):
        try:
            r = req_lib.head(self.url, timeout=8, allow_redirects=True)
            return int(r.headers.get('content-length', 0))
        except Exception:
            return 0

    def _safe_open(self, path, mode):
        """Open a file, creating parent dirs if needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return open(path, mode)

    def _part_path(self, part_num, base):
        return f"{base}.part{part_num}"

    # ── Chunk download ─────────────────────────────────────────────────────────

    def _download_chunk(self, start, end, part_num, base):
        headers = {'Range': f'bytes={start}-{end}'}
        try:
            r = req_lib.get(self.url, headers=headers, stream=True, timeout=30)
            with self._safe_open(self._part_path(part_num, base), "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if self._cancel_flag:
                        return
                    self._pause_event.wait()
                    if chunk:
                        f.write(chunk)
                        self._add_downloaded(len(chunk))
        except Exception:
            pass  # Silently fail; progress won't reach 100% → user can see

    # ── Main start ─────────────────────────────────────────────────────────────

    def start(self):
        self.status = "downloading"
        os.makedirs(self.download_path, exist_ok=True)
        base = os.path.join(self.download_path, self.filename)

        self.total_size = self._get_file_size()

        if self.total_size == 0:
            self._download_single(base)
            return

        chunk_size = self.total_size // self.threads
        threads_list = []

        # Speed / progress monitor
        monitor_stop = threading.Event()

        def speed_monitor():
            prev_dl = 0
            while not monitor_stop.is_set():
                time.sleep(1)
                if self._pause_event.is_set() and not self._cancel_flag:
                    cur = self.downloaded_size
                    speed_bps = (cur - prev_dl)
                    prev_dl = cur
                    if self.total_size:
                        self.progress = min(99, int(cur / self.total_size * 100))
                    if speed_bps >= 1024 * 1024:
                        self.speed = f"{speed_bps / 1024 / 1024:.2f} MB/s"
                    else:
                        self.speed = f"{speed_bps / 1024:.1f} KB/s"

        monitor_thread = threading.Thread(target=speed_monitor, daemon=True)
        monitor_thread.start()

        for i in range(self.threads):
            start_byte = i * chunk_size
            # Fix off-by-one: last byte index is total_size - 1
            end_byte = (start_byte + chunk_size - 1) if i < self.threads - 1 else (self.total_size - 1)
            t = threading.Thread(
                target=self._download_chunk,
                args=(start_byte, end_byte, i, base),
                daemon=True)
            t.start()
            threads_list.append(t)

        for t in threads_list:
            t.join()

        monitor_stop.set()

        if self._cancel_flag:
            self.status = "canceled"
            self._cleanup_parts(base)
        else:
            self._combine_parts(base)
            self.progress = 100
            self.speed = "0 KB/s"
            self.status = "completed"

    # ── Single-thread fallback ─────────────────────────────────────────────────

    def _download_single(self, base):
        try:
            r = req_lib.get(self.url, stream=True, timeout=30)
            total = int(r.headers.get('content-length', 0))
            downloaded = 0
            prev_time = time.time()
            prev_dl = 0

            with self._safe_open(base, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if self._cancel_flag:
                        self.status = "canceled"
                        return
                    self._pause_event.wait()
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self._add_downloaded(len(chunk))

                        if total:
                            self.progress = min(99, int(downloaded / total * 100))

                        now = time.time()
                        if now - prev_time >= 1.0:
                            spd = (downloaded - prev_dl) / (now - prev_time)
                            self.speed = (f"{spd / 1024 / 1024:.2f} MB/s"
                                          if spd >= 1024 * 1024
                                          else f"{spd / 1024:.1f} KB/s")
                            prev_time = now
                            prev_dl = downloaded

            self.progress = 100
            self.speed = "0 KB/s"
            self.status = "completed"
        except Exception as e:
            self.status = f"error: {e}"

    # ── File assembly ──────────────────────────────────────────────────────────

    def _combine_parts(self, base):
        with open(base, "wb") as outfile:
            for i in range(self.threads):
                part = self._part_path(i, base)
                if os.path.exists(part):
                    with open(part, "rb") as infile:
                        outfile.write(infile.read())
                    os.remove(part)

    def _cleanup_parts(self, base):
        for i in range(self.threads):
            part = self._part_path(i, base)
            try:
                if os.path.exists(part):
                    os.remove(part)
            except Exception:
                pass

    # ── Control ────────────────────────────────────────────────────────────────

    def pause(self):
        if self.status == "downloading":
            self.status = "paused"
            self._pause_event.clear()

    def resume(self):
        if self.status == "paused":
            self.status = "downloading"
            self._pause_event.set()

    def cancel(self):
        self._cancel_flag = True
        self._pause_event.set()   # Unblock any waiting thread
