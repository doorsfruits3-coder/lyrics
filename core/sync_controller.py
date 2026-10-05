import time
import threading
from typing import List, Dict, Any
from .discord_client import DiscordClient

class SyncController:
    def __init__(self, discord_client: DiscordClient):
        self.discord = discord_client
        self.lock = threading.Lock()

        # Session state
        self.state = "stopped"  # "stopped", "playing", "paused", "finished"
        self.lyrics: List[Dict[str, Any]] = []
        self.track_info: Dict[str, Any] = {}
        
        # Timing
        self.start_epoch = 0.0
        self.paused_at_time = 0.0
        self.offset = 0.0
        self.current_time = 0.0
        self.current_line_idx = -1
        self.current_line_text = ""
        self.last_sent_text = ""
        self.last_api_call_time = 0.0

        # Configuration
        self.config = {
            "emoji": "🎵",
            "format": "{emoji} {lyric}",
            "target": "custom_status",  # "custom_status", "bio", "both"
            "clear_on_finish": True,
            "min_interval": 1.5,
            "intro_text": "🎧 Đang nghe: {track}"
        }

        # Event log for UI
        self.logs: List[Dict[str, Any]] = []
        self._worker_thread = None
        self._stop_event = threading.Event()

    def add_log(self, message: str, level: str = "info"):
        with self.lock:
            log_item = {
                "timestamp": time.strftime("%H:%M:%S"),
                "message": message,
                "level": level
            }
            self.logs.append(log_item)
            if len(self.logs) > 60:
                self.logs.pop(0)

    def set_config(self, new_config: dict):
        with self.lock:
            self.config.update(new_config)

    def load_song(self, lyrics: List[Dict[str, Any]], track_info: Dict[str, Any] = None):
        with self.lock:
            self.stop_internal()
            self.lyrics = lyrics
            self.track_info = track_info or {}
            self.current_line_idx = -1
            self.current_line_text = ""
            self.current_time = 0.0
            self.paused_at_time = 0.0
            self.state = "ready"
        self.add_log(f"Đã nạp bài hát: {self.track_info.get('track_name', 'Không rõ')} ({len(lyrics)} câu hát)")

    def start(self, start_from_time: float = 0.0, offset: float = 0.0):
        with self.lock:
            if not self.lyrics:
                return False, "Chưa có lời bài hát nào được nạp!"
            
            self.stop_internal()
            self.offset = offset
            self.current_time = start_from_time
            self.start_epoch = time.time() - start_from_time
            self.state = "playing"
            self.current_line_idx = -1
            self.current_line_text = ""
            self.last_sent_text = ""
            self._stop_event.clear()

            self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._worker_thread.start()

        self.add_log(f"Bắt đầu đồng bộ lời nhạc vào Discord từ {start_from_time:.1f}s")
        return True, "Bắt đầu thành công"

    def pause(self):
        with self.lock:
            if self.state == "playing":
                self.state = "paused"
                self.paused_at_time = self.current_time
                self.add_log("Tạm dừng đồng bộ")
                return True, "Đã tạm dừng"
        return False, "Không thể tạm dừng khi chưa phát"

    def resume(self):
        with self.lock:
            if self.state == "paused":
                self.start_epoch = time.time() - self.paused_at_time
                self.state = "playing"
                self.add_log("Tiếp tục đồng bộ")
                return True, "Đã tiếp tục"
        return False, "Không ở trạng thái tạm dừng"

    def stop(self):
        with self.lock:
            self.stop_internal()
            self.state = "stopped"
            if self.config.get("clear_on_finish", True):
                threading.Thread(target=self.discord.clear_status, daemon=True).start()
        self.add_log("Đã dừng đồng bộ và xóa trạng thái")
        return True, "Đã dừng"

    def stop_internal(self):
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            # Wait briefly
            self._worker_thread.join(timeout=0.2)
        self._stop_event.clear()

    def seek(self, target_time: float):
        with self.lock:
            target_time = max(0.0, float(target_time))
            self.current_time = target_time
            if self.state == "playing":
                self.start_epoch = time.time() - target_time
                self.current_line_idx = -1
            elif self.state == "paused":
                self.paused_at_time = target_time
                self.current_line_idx = -1
        self.add_log(f"Tua đến {target_time:.1f}s")
        return True, f"Đã tua đến {target_time}s"

    def adjust_offset(self, delta: float):
        with self.lock:
            self.offset += delta
            # Adjust start epoch accordingly
            self.start_epoch -= delta
        self.add_log(f"Cân chỉnh độ lệch (Offset): {self.offset:+.2f}s")
        return self.offset

    def _format_status(self, lyric_text: str) -> str:
        emoji = self.config.get("emoji", "🎵")
        fmt = self.config.get("format", "{emoji} {lyric}")
        text = fmt.replace("{emoji}", emoji).replace("{lyric}", lyric_text)
        return text.strip()

    def _send_to_discord(self, text: str):
        now = time.time()
        # Prevent rapid spamming
        min_int = self.config.get("min_interval", 1.5)
        if now - self.last_api_call_time < min_int:
            time.sleep(min_int - (now - self.last_api_call_time))

        target = self.config.get("target", "custom_status")
        emoji = self.config.get("emoji", "🎵")

        if target in ("custom_status", "both"):
            succ, msg = self.discord.update_custom_status(text=text, emoji_name=emoji)
            if not succ:
                self.add_log(f"[Discord Error] {msg}", "error")

        if target in ("bio", "both"):
            succ, msg = self.discord.update_bio(bio_text=text)
            if not succ:
                self.add_log(f"[Discord Bio Error] {msg}", "error")

        self.last_api_call_time = time.time()
        self.last_sent_text = text
        self.add_log(f"Discord Status ➔ \"{text}\"", "success")

    def _run_loop(self):
        intro_sent = False
        track_name = self.track_info.get("track_name", "Bài hát")

        while not self._stop_event.is_set():
            with self.lock:
                if self.state != "playing":
                    time.sleep(0.1)
                    continue

                now = time.time()
                self.current_time = now - self.start_epoch

            current_t = self.current_time

            # Find matching lyric line
            active_idx = -1
            for i, line in enumerate(self.lyrics):
                if current_t >= line["time"]:
                    active_idx = i
                else:
                    break

            # Handle intro before first lyric
            if active_idx == -1:
                if not intro_sent and current_t < 10.0:
                    intro_template = self.config.get("intro_text", "🎧 Đang nghe: {track}")
                    intro_text = intro_template.replace("{track}", track_name)
                    intro_text = self._format_status(intro_text)
                    threading.Thread(target=self._send_to_discord, args=(intro_text,), daemon=True).start()
                    intro_sent = True
            elif active_idx != self.current_line_idx:
                # We have entered a new lyric line!
                self.current_line_idx = active_idx
                line_data = self.lyrics[active_idx]
                self.current_line_text = line_data["text"]

                # Send update to Discord in background thread to avoid blocking loop
                status_text = self._format_status(self.current_line_text)
                if status_text != self.last_sent_text:
                    threading.Thread(target=self._send_to_discord, args=(status_text,), daemon=True).start()

            # Check if song ended (past last lyric + 8 seconds)
            if self.lyrics and current_t > (self.lyrics[-1]["time"] + 8.0):
                self.add_log("Bài hát đã hoàn thành!", "success")
                with self.lock:
                    self.state = "finished"
                    if self.config.get("clear_on_finish", True):
                        threading.Thread(target=self.discord.clear_status, daemon=True).start()
                break

            time.sleep(0.05)  # 50ms precision loop

    def get_state(self):
        with self.lock:
            return {
                "state": self.state,
                "current_time": round(self.current_time, 2),
                "offset": round(self.offset, 2),
                "current_line_idx": self.current_line_idx,
                "current_line_text": self.current_line_text,
                "last_sent_text": self.last_sent_text,
                "track_info": self.track_info,
                "total_lines": len(self.lyrics),
                "config": self.config,
                "logs": list(self.logs[-25:])
            }
