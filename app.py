import os
import sys
import webbrowser
import threading
import re
import json
import urllib.parse
import urllib.request

# Fix Windows console encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from core.discord_client import DiscordClient
from core.lyrics_engine import LyricsEngine
from core.sync_controller import SyncController

# Initialize Flask
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
CORS(app)

# Core singletons
discord_client = DiscordClient()
sync_controller = SyncController(discord_client)

@app.route("/")
def index():
    return render_template("index.html")

# --- AUTH ENDPOINTS ---
@app.route("/api/auth/verify", methods=["POST"])
def auth_verify():
    data = request.get_json() or {}
    auth_input = data.get("auth_input", "").strip()
    if not auth_input:
        return jsonify({"success": False, "error": "Vui lòng nhập Token hoặc Cookie!"}), 400

    discord_client.set_credentials(auth_input)
    success, result = discord_client.verify_account()

    if success:
        sync_controller.add_log(f"Đã đăng nhập thành công tài khoản: @{result['username']} ({result['global_name']})", "success")
        return jsonify({
            "success": True, 
            "user": result,
            "has_token": bool(discord_client.token),
            "has_cookies": bool(discord_client.cookies)
        })
    else:
        sync_controller.add_log(f"Xác thực thất bại: {result}", "error")
        return jsonify({"success": False, "error": result}), 400

@app.route("/api/discord/test-status", methods=["POST"])
def test_status():
    if not discord_client.token:
        return jsonify({"success": False, "error": "Chưa kết nối tài khoản Discord!"}), 400
    
    succ, msg = discord_client.update_custom_status("🎵 Đang kiểm tra tool đổi lyric status Discord...")
    if succ:
        return jsonify({"success": True, "message": "Đã đổi trạng thái test thành công! Hãy kiểm tra Discord của bạn."})
    else:
        return jsonify({"success": False, "error": msg}), 400

@app.route("/api/discord/clear-status", methods=["POST"])
def clear_status():
    succ, msg = discord_client.clear_status()
    sync_controller.add_log("Đã yêu cầu xóa trạng thái Discord")
    return jsonify({"success": succ, "message": msg})



# --- SOUNDCLOUD SUPPORT ---
SOUNDCLOUD_RE = re.compile(r"^https?://(?:www\.|m\.|on\.)?soundcloud\.com/\S+", re.I)
_NOISE_RE = re.compile(
    r"[\(\[][^\)\]]*(?:official|lyric|audio|video|mv|visualizer|free download|prod)[^\)\]]*[\)\]]",
    re.I,
)

def is_soundcloud_url(text):
    return bool(SOUNDCLOUD_RE.match(text.strip()))

def _http_get(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=timeout)

def _clean_title(text):
    text = _NOISE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip(" -–—|")

def _strip_feat(text):
    text = re.sub(r"[\(\[]\s*(?:feat|ft)\.?[^\)\]]*[\)\]]", "", text, flags=re.I)
    text = re.sub(r"\s+(?:feat|ft)\.?\s+.*$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip(" -–—|")

def soundcloud_to_queries(url):
    """Đổi link SoundCloud thành danh sách chuỗi tìm kiếm (ưu tiên từ trên xuống)."""
    variants = []

    def add(q):
        q = (q or "").strip()
        if q and q.lower() not in [v.lower() for v in variants]:
            variants.append(q)

    # Cách 1: oEmbed chính thức của SoundCloud (không cần API key)
    try:
        api = "https://soundcloud.com/oembed?format=json&url=" + urllib.parse.quote(url, safe="")
        with _http_get(api) as r:
            info = json.loads(r.read().decode("utf-8", errors="ignore"))
        author = (info.get("author_name") or "").strip()
        title = (info.get("title") or "").strip()
        suffix = f" by {author}"
        if author and title.lower().endswith(suffix.lower()):
            title = title[:-len(suffix)]
        title = _clean_title(title)
        if title:
            if " - " in title:
                artist_part, song_part = title.split(" - ", 1)
                add(title)
                add(_strip_feat(song_part))
                add(f"{_strip_feat(song_part)} {artist_part}")
            else:
                clean = _strip_feat(title)
                add(f"{clean} {author}" if author else clean)
                add(clean)
                add(title)
    except Exception:
        pass

    # Cách 2: lấy từ đường dẫn (soundcloud.com/<ca-si>/<ten-bai>), có xử lý link rút gọn on.soundcloud.com
    if not variants:
        try:
            with _http_get(url) as r:
                final_url = r.geturl()
        except Exception:
            final_url = url
        parts = [p for p in urllib.parse.urlparse(final_url).path.split("/") if p]
        if len(parts) >= 2 and parts[1].lower() not in ("sets", "albums", "likes", "tracks", "reposts"):
            song = parts[1].replace("-", " ")
            artist = parts[0].replace("-", " ")
            add(f"{song} {artist}")
            add(song)
    return variants

# --- LYRICS ENDPOINTS ---
@app.route("/api/lyrics/fetch-url", methods=["POST"])
def fetch_url():
    data = request.get_json() or {}
    url_or_query = data.get("url", "").strip()
    if not url_or_query:
        return jsonify({"success": False, "error": "Vui lòng nhập link bài hát hoặc tên bài hát!"}), 400

    queries = [url_or_query]
    if is_soundcloud_url(url_or_query):
        if "/sets/" in url_or_query.lower():
            return jsonify({"success": False, "error": "Đây là link playlist/album SoundCloud. Hãy dán link của một bài hát cụ thể!"}), 400
        queries = soundcloud_to_queries(url_or_query)
        if not queries:
            return jsonify({"success": False, "error": "Không đọc được thông tin từ link SoundCloud này. Hãy thử nhập tên bài hát!"}), 400
        sync_controller.add_log(f"Đã nhận diện link SoundCloud, đang tìm lời cho: {queries[0]}")

    success, result = False, {}
    for q in queries:
        success, result = LyricsEngine.get_lyrics_from_link_or_query(q)
        if success:
            break
    if not success:
        return jsonify({"success": False, "error": result.get("message", "Không tìm thấy lời bài hát.")}), 404

    # Automatically load into sync controller
    track_info = {
        "track_name": result.get("track_name", "Không rõ"),
        "artist_name": result.get("artist_name", "Không rõ"),
        "duration": result.get("duration", 0),
        "source": url_or_query
    }
    sync_controller.load_song(result["lyrics"], track_info)

    return jsonify({
        "success": True,
        "track_info": track_info,
        "lyrics": result["lyrics"],
        "is_plain_fallback": result.get("is_plain_fallback", False),
        "candidates": result.get("candidates", [])
    })

@app.route("/api/lyrics/search", methods=["GET"])
def search_lyrics():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "results": []})
    queries = soundcloud_to_queries(query) if is_soundcloud_url(query) else [query]
    success, results = False, []
    for q in queries:
        success, results = LyricsEngine.search_synced_lyrics(q)
        if success and results:
            break
    return jsonify({"success": success, "results": results})

@app.route("/api/lyrics/select-candidate", methods=["POST"])
def select_candidate():
    data = request.get_json() or {}
    lrc_content = data.get("synced_lyrics") or data.get("plain_lyrics", "")
    track_name = data.get("track_name", "Bài hát")
    artist_name = data.get("artist_name", "Ca sĩ")

    if not lrc_content:
        return jsonify({"success": False, "error": "Bản ghi không có lời!"}), 400

    if data.get("synced_lyrics"):
        parsed = LyricsEngine.parse_lrc(lrc_content)
    else:
        parsed = LyricsEngine.parse_plain_text(lrc_content)

    track_info = {
        "track_name": track_name,
        "artist_name": artist_name,
        "duration": data.get("duration", 0)
    }
    sync_controller.load_song(parsed, track_info)
    return jsonify({"success": True, "track_info": track_info, "lyrics": parsed})

@app.route("/api/lyrics/upload", methods=["POST"])
def upload_lyrics():
    raw_content = ""
    filename = "custom_lyrics"

    if "file" in request.files:
        f = request.files["file"]
        filename = f.filename
        raw_content = f.read().decode("utf-8", errors="ignore")
    else:
        data = request.get_json() or {}
        raw_content = data.get("content", "")
        filename = data.get("filename", "custom_lyrics.lrc")

    if not raw_content.strip():
        return jsonify({"success": False, "error": "Nội dung tệp trống!"}), 400

    # Auto detect format
    if filename.lower().endswith(".srt") or filename.lower().endswith(".vtt") or "-->" in raw_content:
        parsed = LyricsEngine.parse_srt_or_vtt(raw_content)
    elif "[" in raw_content and "]" in raw_content:
        parsed = LyricsEngine.parse_lrc(raw_content)
    else:
        parsed = LyricsEngine.parse_plain_text(raw_content)

    if not parsed:
        return jsonify({"success": False, "error": "Không thể phân tích dòng thời gian của lời bài hát!"}), 400

    track_title = os.path.splitext(filename)[0].replace("_", " ").title()
    track_info = {
        "track_name": track_title,
        "artist_name": "Tùy chỉnh",
        "duration": parsed[-1]["time"] if parsed else 0
    }
    sync_controller.load_song(parsed, track_info)

    return jsonify({
        "success": True,
        "track_info": track_info,
        "lyrics": parsed
    })

@app.route("/api/lyrics/sample/<sample_name>", methods=["GET"])
def load_sample(sample_name):
    allowed = {
        "see_tinh": "see_tinh.lrc",
        "noi_nay_co_anh": "noi_nay_co_anh.lrc"
    }
    if sample_name not in allowed:
        return jsonify({"success": False, "error": "Mẫu không tồn tại"}), 404

    sample_path = os.path.join(BASE_DIR, "samples", allowed[sample_name])
    try:
        with open(sample_path, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = LyricsEngine.parse_lrc(content)
        title = "See Tình - Hoàng Thùy Linh" if sample_name == "see_tinh" else "Nơi Này Có Anh - Sơn Tùng M-TP"
        track_info = {
            "track_name": title,
            "artist_name": "Sample",
            "duration": parsed[-1]["time"] if parsed else 0
        }
        sync_controller.load_song(parsed, track_info)
        return jsonify({"success": True, "track_info": track_info, "lyrics": parsed})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# --- SYNC CONTROL ENDPOINTS ---
@app.route("/api/sync/start", methods=["POST"])
def sync_start():
    data = request.get_json() or {}
    start_time = float(data.get("start_time", 0.0))
    offset = float(data.get("offset", 0.0))

    if not discord_client.token:
        return jsonify({"success": False, "error": "Bạn chưa đăng nhập tài khoản Discord!"}), 400

    succ, msg = sync_controller.start(start_time, offset)
    return jsonify({"success": succ, "message": msg})

@app.route("/api/sync/pause", methods=["POST"])
def sync_pause():
    succ, msg = sync_controller.pause()
    return jsonify({"success": succ, "message": msg})

@app.route("/api/sync/resume", methods=["POST"])
def sync_resume():
    succ, msg = sync_controller.resume()
    return jsonify({"success": succ, "message": msg})

@app.route("/api/sync/stop", methods=["POST"])
def sync_stop():
    succ, msg = sync_controller.stop()
    return jsonify({"success": succ, "message": msg})

@app.route("/api/sync/seek", methods=["POST"])
def sync_seek():
    data = request.get_json() or {}
    target_time = float(data.get("time", 0.0))
    succ, msg = sync_controller.seek(target_time)
    return jsonify({"success": succ, "message": msg})

@app.route("/api/sync/offset", methods=["POST"])
def sync_offset():
    data = request.get_json() or {}
    delta = float(data.get("delta", 0.0))
    new_offset = sync_controller.adjust_offset(delta)
    return jsonify({"success": True, "offset": new_offset})

@app.route("/api/sync/config", methods=["POST"])
def sync_config():
    data = request.get_json() or {}
    sync_controller.set_config(data)
    return jsonify({"success": True, "config": sync_controller.config})

@app.route("/api/sync/state", methods=["GET"])
def sync_state():
    state = sync_controller.get_state()
    state["user"] = discord_client.user_data
    return jsonify(state)

def open_browser():
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==========================================================")
    print(f"[*] DISCORD LYRIC STATUS SYNC TOOL v2.0")
    print(f"==========================================================")
    print(f"[*] May chu dang chay tai: http://127.0.0.1:{port}")
    print(f"[*] Dang tu dong mo trinh duyet web...")
    print(f"==========================================================\n")
    threading.Timer(1.2, open_browser).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
