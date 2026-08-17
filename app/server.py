import json
import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
from downloader import Downloader
from youtube import YouTubeDownloader, fetch_youtube_info

app = Flask(__name__)
CORS(app)

# Thread-safe downloads dict
downloads = {}
downloads_lock = threading.Lock()

# Load config
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
app_config = {"download_path": os.path.join(os.path.expanduser("~"), "Downloads")}
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            app_config.update(json.load(f))
    except Exception:
        pass


@app.route('/set_config', methods=['POST'])
def set_config():
    data = request.json or {}
    if 'download_path' in data:
        app_config['download_path'] = data['download_path']
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(app_config, f)
        except Exception:
            pass
    return jsonify({"status": "success"})


@app.route('/fetch_info', methods=['POST'])
def fetch_info():
    data = request.json or {}
    url = data.get('url', '')
    if 'youtube.com' in url or 'youtu.be' in url:
        info = fetch_youtube_info(url)
        return jsonify(info)
    return jsonify({"error": "Not a YouTube URL"})


def _new_task_id():
    """Generate a unique task ID."""
    return str(uuid.uuid4())[:8]


@app.route('/add', methods=['POST'])
def add_download():
    data = request.json or {}
    url = data.get('url', '')
    dl_type = data.get('type', 'file')
    dl_path = app_config['download_path']

    if dl_type == 'youtube':
        resolution = data.get('resolution', 'best')
        sep_subs = data.get('separate_subs', False)

        # Add video task
        task_id = _new_task_id()
        task = YouTubeDownloader(url, task_id, resolution=resolution,
                                 download_subtitles=False, download_path=dl_path)
        with downloads_lock:
            downloads[task_id] = task
        threading.Thread(target=task.start, daemon=True).start()

        if sep_subs:
            sub_task_id = _new_task_id()
            sub_task = YouTubeDownloader(url, sub_task_id, is_subtitle_only=True,
                                         download_path=dl_path)
            with downloads_lock:
                downloads[sub_task_id] = sub_task
            threading.Thread(target=sub_task.start, daemon=True).start()

        return jsonify({"status": "added", "task_id": task_id})
    else:
        task_id = _new_task_id()
        task = Downloader(url, task_id, download_path=dl_path)
        with downloads_lock:
            downloads[task_id] = task
        threading.Thread(target=task.start, daemon=True).start()
        return jsonify({"status": "added", "task_id": task_id})


@app.route('/status', methods=['GET'])
def get_status():
    with downloads_lock:
        snap = list(downloads.items())
    status_list = []
    for task_id, task in snap:
        status_list.append({
            "task_id": task_id,
            "filename": task.filename,
            "progress": task.progress,
            "status": task.status,
            "speed": task.speed,
        })
    return jsonify(status_list)


@app.route('/pause', methods=['POST'])
def pause_download():
    data = request.json or {}
    task_id = data.get('task_id')
    with downloads_lock:
        task = downloads.get(task_id)
    if task:
        task.pause()
        return jsonify({"status": "paused"})
    return jsonify({"error": "not found"}), 404


@app.route('/resume', methods=['POST'])
def resume_download():
    data = request.json or {}
    task_id = data.get('task_id')
    with downloads_lock:
        task = downloads.get(task_id)
    if task:
        task.resume()
        return jsonify({"status": "resumed"})
    return jsonify({"error": "not found"}), 404


@app.route('/cancel', methods=['POST'])
def cancel_download():
    data = request.json or {}
    task_id = data.get('task_id')
    with downloads_lock:
        task = downloads.get(task_id)
    if task:
        task.cancel()
        return jsonify({"status": "canceled"})
    return jsonify({"error": "not found"}), 404


@app.route('/clear_done', methods=['POST'])
def clear_done():
    done_states = ('completed', 'canceled', 'error')
    to_remove = []
    with downloads_lock:
        for tid, task in downloads.items():
            if any(task.status.startswith(s) for s in done_states):
                to_remove.append(tid)
        for tid in to_remove:
            downloads.pop(tid)
    return jsonify({"status": "cleared", "count": len(to_remove)})


def run_server():
    app.run(port=6578, debug=False, use_reloader=False)


if __name__ == '__main__':
    run_server()
