from tkinter import filedialog
import customtkinter as ctk
import requests
import threading
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SERVER = "http://localhost:6578"

# File type icons based on extension
def get_file_icon(filename: str) -> str:
    fn = filename.lower()
    if any(fn.endswith(x) for x in ['.mp4', '.mkv', '.webm', '.avi', '.mov']):
        return "🎬"
    if any(fn.endswith(x) for x in ['.mp3', '.aac', '.flac', '.wav', '.ogg']):
        return "🎵"
    if any(fn.endswith(x) for x in ['.srt', '.vtt', '.ass']):
        return "💬"
    if any(fn.endswith(x) for x in ['.zip', '.rar', '.7z', '.tar', '.gz']):
        return "🗜️"
    if any(fn.endswith(x) for x in ['.pdf']):
        return "📄"
    if any(fn.endswith(x) for x in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
        return "🖼️"
    if 'subtitle' in fn or '(subtitles)' in fn.lower():
        return "💬"
    return "📥"

# Status badge colors
STATUS_COLORS = {
    "completed":   ("#1a6b3c", "#2ecc71"),   # dark bg, text
    "downloading": ("#0a3d62", "#3498db"),
    "paused":      ("#5d4037", "#f39c12"),
    "waiting":     ("#2c2c2c", "#aaaaaa"),
    "canceled":    ("#3c1414", "#e74c3c"),
}

def get_status_color(status: str):
    if status.startswith("error"):
        return ("#4a0e0e", "#e74c3c")
    for key, val in STATUS_COLORS.items():
        if status.startswith(key):
            return val
    return ("#2c2c2c", "#aaaaaa")


class IDMCloneGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("EasyDownloader")
        self.geometry("900x640")
        self.minsize(720, 440)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        try:
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass

        self._build_toolbar()
        self._build_offline_banner()
        self._build_list()

        self.download_widgets: dict = {}
        self._server_was_offline = False

        threading.Thread(target=self._load_saved_folder, daemon=True).start()
        self.after(800, self.update_status)
        self.after(1000, self._check_first_run)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = ctk.CTkFrame(self, height=64, corner_radius=0, fg_color="#1a1a2e")
        tb.pack(side="top", fill="x")
        tb.pack_propagate(False)

        ctk.CTkButton(
            tb, text="➕  Add URL",
            command=self.add_url_dialog,
            width=120, height=36,
            fg_color="#00ADB5", hover_color="#008c94",
            font=("Roboto", 13, "bold")
        ).pack(side="left", padx=12, pady=14)

        ctk.CTkButton(
            tb, text="📂  Folder",
            command=lambda: threading.Thread(
                target=self._do_set_folder, daemon=True).start(),
            width=110, height=36,
            fg_color="#2c3e50", hover_color="#1a252f",
            font=("Roboto", 13)
        ).pack(side="left", padx=4, pady=14)

        self.folder_lbl = ctk.CTkLabel(
            tb, text="", font=("Roboto", 11), text_color="#7f8c8d")
        self.folder_lbl.pack(side="left", padx=8)

        # Feedback button
        ctk.CTkButton(
            tb, text="🐛  Feedback",
            command=self._show_feedback_dialog,
            width=110, height=36,
            fg_color="#8e44ad", hover_color="#732d91",
            font=("Roboto", 12)
        ).pack(side="right", padx=12, pady=14)

        # Clear completed button
        ctk.CTkButton(
            tb, text="🗑  Clear Done",
            command=self._clear_done,
            width=120, height=36,
            fg_color="#2c2c2c", hover_color="#3d3d3d",
            font=("Roboto", 12)
        ).pack(side="right", padx=4, pady=14)

        ctk.CTkLabel(
            tb, text="EasyDownloader",
            font=("Roboto", 20, "bold"), text_color="#00ADB5"
        ).pack(side="right", padx=12)

    def _build_offline_banner(self):
        self.offline_banner = ctk.CTkFrame(
            self, height=30, corner_radius=0, fg_color="#6b1010")
        self.offline_lbl = ctk.CTkLabel(
            self.offline_banner,
            text="⚠️  Cannot connect to server — is main.py running?",
            font=("Roboto", 12), text_color="#ffaaaa")
        self.offline_lbl.pack(pady=4)
        # Don't pack yet — shown only when offline

    def _build_list(self):
        self.scroll_frame = ctk.CTkScrollableFrame(
            self, corner_radius=0, fg_color="#16213e")
        self.scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _load_saved_folder(self):
        default = os.path.join(os.path.expanduser("~"), "Downloads")
        self.after(0, lambda: self.folder_lbl.configure(text=default))

    def _do_set_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            try:
                requests.post(f'{SERVER}/set_config',
                              json={'download_path': folder}, timeout=3)
                self.after(0, lambda: self.folder_lbl.configure(text=folder))
            except Exception:
                pass

    def _clear_done(self):
        threading.Thread(target=self._do_clear_done, daemon=True).start()

    def _do_clear_done(self):
        try:
            requests.post(f'{SERVER}/clear_done', timeout=3)
        except Exception:
            pass

    def _set_online(self):
        if self._server_was_offline:
            self._server_was_offline = False
            self.offline_banner.pack_forget()

    def _set_offline(self):
        if not self._server_was_offline:
            self._server_was_offline = True
            self.offline_banner.pack(side="top", fill="x", after=self.winfo_children()[0])

    def _check_first_run(self):
        config_dir = os.path.join(os.path.expanduser("~"), ".easydownloader")
        os.makedirs(config_dir, exist_ok=True)
        marker = os.path.join(config_dir, "extension_prompted.txt")
        
        if not os.path.exists(marker):
            self._show_extension_guide()
            try:
                with open(marker, "w") as f:
                    f.write("1")
            except Exception:
                pass

    def _show_extension_guide(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Install Chrome Extension")
        dialog.geometry("600x350")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Welcome to EasyDownloader! 🎉", font=("Roboto", 20, "bold"), text_color="#00ADB5").pack(pady=(20, 10))
        
        instructions = (
            "To catch downloads automatically from your browser, please add the extension:\n\n"
            "1. Click the button below to open Chrome Extensions.\n"
            "2. Turn on 'Developer mode' (top right corner).\n"
            "3. Click 'Load unpacked' (top left corner).\n"
            "4. Select the 'extension' folder located in the EasyDownloader folder.\n"
            "   (Usually: C:\\Program Files\\EasyDownloader\\extension)"
        )
        
        ctk.CTkLabel(dialog, text=instructions, font=("Roboto", 13), justify="left").pack(padx=20, pady=10)

        import webbrowser
        def open_chrome():
            webbrowser.open("chrome://extensions/")
            
        ctk.CTkButton(dialog, text="Open Chrome Extensions", command=open_chrome, fg_color="#00ADB5", hover_color="#008c94", font=("Roboto", 14, "bold"), height=40).pack(pady=20)

    def _show_feedback_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Send Feedback / Report Bug")
        dialog.geometry("500x370")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="We value your feedback!", font=("Roboto", 16, "bold"), text_color="#00ADB5").pack(pady=(15, 5))
        ctk.CTkLabel(dialog, text="Tell us about a bug you found or a feature you want.", font=("Roboto", 12)).pack(pady=(0, 15))

        textbox = ctk.CTkTextbox(dialog, width=440, height=160)
        textbox.pack(pady=5)
        
        status_lbl = ctk.CTkLabel(dialog, text="", font=("Roboto", 12))
        status_lbl.pack(pady=2)

        def _send():
            msg = textbox.get("1.0", "end-1c").strip()
            if not msg:
                return
            status_lbl.configure(text="Sending...", text_color="#aaaaaa")
            dialog.update()
            
            def _do_send():
                try:
                    # Obfuscated email to avoid direct scraping
                    # target = thiwasan2002@gmail.com
                    target = "thiwasan2002" + "@" + "gmail" + ".com"
                    requests.post(
                        f"https://formsubmit.co/ajax/{target}",
                        data={"Feedback": msg, "_subject": "EasyDownloader Feedback"},
                        headers={"Accept": "application/json", "Referer": "https://github.com/Thiwanka-work/py-idm-clone"},
                        timeout=10
                    )
                    self.after(0, lambda: status_lbl.configure(text="✅ Feedback sent successfully! Thank you.", text_color="#2ecc71"))
                    self.after(2000, dialog.destroy)
                except Exception as e:
                    self.after(0, lambda: status_lbl.configure(text="❌ Failed to send feedback. Check your connection.", text_color="#e74c3c"))
                    
            threading.Thread(target=_do_send, daemon=True).start()
            
        ctk.CTkButton(dialog, text="Send", command=_send, fg_color="#8e44ad", hover_color="#732d91", font=("Roboto", 13, "bold"), width=120).pack(pady=10)

    # ── Add URL dialog ─────────────────────────────────────────────────────────

    def add_url_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Download URL")
        dialog.geometry("540x175")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        try:
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except Exception:
            pass

        ctk.CTkLabel(dialog, text="Paste a URL to download:",
                     font=("Roboto", 13)).pack(pady=(18, 6))

        url_entry = ctk.CTkEntry(dialog, width=460, placeholder_text="https://...")
        url_entry.pack(pady=4)
        url_entry.focus()

        status_lbl = ctk.CTkLabel(dialog, text="", font=("Roboto", 11),
                                   text_color="#aaaaaa")
        status_lbl.pack()

        def _submit():
            url = url_entry.get().strip()
            if not url:
                return
            dl_type = ('youtube' if ('youtube.com' in url or 'youtu.be' in url)
                       else 'file')
            status_lbl.configure(text="⏳ Sending to queue…", text_color="#aaaaaa")
            dialog.update()
            threading.Thread(
                target=_do_submit, args=(url, dl_type), daemon=True).start()

        def _do_submit(url, dl_type):
            try:
                requests.post(f'{SERVER}/add',
                              json={'url': url, 'type': dl_type,
                                    'resolution': 'best', 'separate_subs': True},
                              timeout=5)
                self.after(0, dialog.destroy)
            except Exception as e:
                self.after(0, lambda: status_lbl.configure(
                    text=f"❌ {e}", text_color="#e74c3c"))

        btn = ctk.CTkButton(dialog, text="⬇  Download", command=_submit,
                            fg_color="#00ADB5", hover_color="#008c94",
                            font=("Roboto", 13, "bold"))
        btn.pack(pady=(6, 15))
        dialog.bind("<Return>", lambda _: _submit())

    # ── Download card ──────────────────────────────────────────────────────────

    def create_download_card(self, task):
        task_id = str(task['task_id'])
        st = task.get('status', 'waiting')
        bg, fg = get_status_color(st)

        card = ctk.CTkFrame(
            self.scroll_frame, corner_radius=10,
            border_width=1, border_color="#2a2a4a",
            fg_color="#1e2040")
        card.pack(fill="x", pady=6, padx=14)

        # ── Row 1: icon + filename + status badge ──────────────────────────────
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", padx=14, pady=(10, 3))

        icon_lbl = ctk.CTkLabel(row1, text=get_file_icon(task['filename']),
                                 font=("Roboto", 22))
        icon_lbl.pack(side="left", padx=(0, 8))

        name_lbl = ctk.CTkLabel(row1, text=self._short(task['filename']),
                                  font=("Roboto", 13, "bold"), anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True)

        badge = ctk.CTkLabel(row1, text=f" {st.title()} ",
                              font=("Roboto", 11, "bold"),
                              fg_color=bg, text_color=fg,
                              corner_radius=6)
        badge.pack(side="right", padx=4)

        # ── Row 2: progress bar ────────────────────────────────────────────────
        prog_bar = ctk.CTkProgressBar(card, height=7, corner_radius=4,
                                       progress_color="#00ADB5")
        prog_bar.pack(fill="x", padx=14, pady=3)
        prog_bar.set(0)

        # ── Row 3: speed/percent + buttons ────────────────────────────────────
        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=14, pady=(3, 10))

        details_lbl = ctk.CTkLabel(row3, text="0 KB/s | 0%",
                                    font=("Roboto", 11), text_color="#7f8c8d")
        details_lbl.pack(side="left")

        btn_cancel = ctk.CTkButton(
            row3, text="✕", width=34, height=28,
            command=lambda: self.action(task_id, 'cancel'),
            fg_color="#4a1010", hover_color="#7b1010",
            font=("Roboto", 13, "bold"))
        btn_resume = ctk.CTkButton(
            row3, text="▶", width=34, height=28,
            command=lambda: self.action(task_id, 'resume'),
            fg_color="#0a3d0a", hover_color="#1a5c1a",
            font=("Roboto", 13))
        btn_pause = ctk.CTkButton(
            row3, text="⏸", width=34, height=28,
            command=lambda: self.action(task_id, 'pause'),
            fg_color="#4a3a00", hover_color="#6b5400",
            font=("Roboto", 13))

        btn_cancel.pack(side="right", padx=(4, 0))
        btn_resume.pack(side="right", padx=4)
        btn_pause.pack(side="right", padx=4)

        self.download_widgets[task_id] = {
            'frame': card,
            'icon': icon_lbl,
            'name': name_lbl,
            'badge': badge,
            'progress_bar': prog_bar,
            'details': details_lbl,
            'btn_pause': btn_pause,
            'btn_resume': btn_resume,
            'btn_cancel': btn_cancel,
            '_status': st,
        }
        return self.download_widgets[task_id]

    @staticmethod
    def _short(text, maxlen=70):
        return text if len(text) <= maxlen else text[:maxlen - 1] + "…"

    def action(self, task_id, action_type):
        threading.Thread(
            target=lambda: self._do_action(task_id, action_type),
            daemon=True).start()

    def _do_action(self, task_id, action_type):
        try:
            requests.post(f'{SERVER}/{action_type}',
                          json={'task_id': str(task_id)}, timeout=3)
        except Exception:
            pass

    # ── Status polling ─────────────────────────────────────────────────────────

    def update_status(self):
        threading.Thread(target=self._fetch_status, daemon=True).start()
        self.after(1500, self.update_status)

    def _fetch_status(self):
        try:
            r = requests.get(f'{SERVER}/status', timeout=2)
            if r.status_code == 200:
                self.after(0, lambda data=r.json(): self._apply_update(data))
                self.after(0, self._set_online)
            else:
                self.after(0, self._set_offline)
        except Exception:
            self.after(0, self._set_offline)

    def _apply_update(self, data):
        # Keep track of active task IDs from server
        active_ids = set()

        for task in data:
            t_id = str(task['task_id'])
            active_ids.add(t_id)

            if t_id not in self.download_widgets:
                self.create_download_card(task)
            w = self.download_widgets[t_id]

            st = task['status']
            w['_status'] = st

            # Filename + icon
            fname = task['filename']
            w['icon'].configure(text=get_file_icon(fname))
            w['name'].configure(text=self._short(fname))

            # Progress bar
            pct = float(task['progress'])
            w['progress_bar'].set(pct / 100.0)

            # Speed / details
            if st.startswith('error'):
                err_msg = st[6:].strip() if len(st) > 6 else "Unknown error"
                if err_msg.lower().startswith("error:"):
                    err_msg = err_msg[6:].strip()
                w['details'].configure(text=self._short(err_msg, maxlen=110), text_color="#e74c3c")
                badge_text = " Error "
            else:
                w['details'].configure(text=f"{task['speed']} | {int(pct)}%", text_color="#7f8c8d")
                badge_text = f" {st.title()} "

            # Badge
            bg, fg = get_status_color(st)
            w['badge'].configure(text=badge_text,
                                  fg_color=bg, text_color=fg)

            # Card border colour
            done = st in ('completed', 'canceled') or st.startswith('error')
            if st == 'completed':
                w['frame'].configure(border_color="#1a6b3c")
                w['progress_bar'].configure(progress_color="#2ecc71")
            elif st.startswith('error'):
                w['frame'].configure(border_color="#7b1010")
            elif st == 'paused':
                w['frame'].configure(border_color="#6b5400")
            else:
                w['frame'].configure(border_color="#2a2a4a")

            # Button states
            if done:
                w['btn_pause'].configure(state="disabled")
                w['btn_resume'].configure(state="disabled")
                w['btn_cancel'].configure(state="disabled")
            elif st == 'paused':
                w['btn_pause'].configure(state="disabled")
                w['btn_resume'].configure(state="normal")
                w['btn_cancel'].configure(state="normal")
            else:
                w['btn_pause'].configure(state="normal")
                w['btn_resume'].configure(state="disabled")
                w['btn_cancel'].configure(state="normal")

        # Remove any cards for tasks no longer on the server
        to_remove = [tid for tid in self.download_widgets if tid not in active_ids]
        for tid in to_remove:
            w = self.download_widgets.pop(tid)
            try:
                w['frame'].destroy()
            except Exception:
                pass


if __name__ == '__main__':
    app = IDMCloneGUI()
    app.mainloop()
