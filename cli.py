import os
import sys
import time
import getpass
from colorama import init, Fore, Style

from core.discord_client import DiscordClient
from core.lyrics_engine import LyricsEngine
from core.sync_controller import SyncController

# Init colorama for Windows console UTF-8 & color support
init(autoreset=True)
sys.stdout.reconfigure(encoding='utf-8')

BANNER = f"""{Fore.MAGENTA}
  ╔═══════════════════════════════════════════════════════════════╗
  ║            🎵 DISCORD LYRIC STATUS SYNC CLI 🎵                ║
  ║      Đổi trạng thái Discord cá nhân đồng bộ theo lời nhạc     ║
  ╚═══════════════════════════════════════════════════════════════╝
{Style.RESET_ALL}"""

def main():
    print(BANNER)

    # 1. AUTHENTICATION
    print(f"{Fore.CYAN}[1] ĐĂNG NHẬP DISCORD{Style.RESET_ALL}")
    print(f"Nhập Token hoặc chuỗi Cookie từ trình duyệt:")
    auth_input = input(f"{Fore.YELLOW}➔ Token / Cookie: {Style.RESET_ALL}").strip()

    if not auth_input:
        print(f"{Fore.RED}[!] Bạn chưa nhập thông tin đăng nhập!{Style.RESET_ALL}")
        return

    client = DiscordClient(auth_input)
    print(f"{Fore.BLUE}[*] Đang xác thực tài khoản với Discord API...{Style.RESET_ALL}")
    success, result = client.verify_account()

    if not success:
        print(f"{Fore.RED}[X] Lỗi xác thực: {result}{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}[✔] Đã đăng nhập: @{result['username']} ({result['global_name']}) | ID: {result['id']}{Style.RESET_ALL}\n")

    # 2. CHOOSE SOURCE
    print(f"{Fore.CYAN}[2] CHỌN NGUỒN LỜI BÀI HÁT{Style.RESET_ALL}")
    print("1. Nhập link YouTube, Spotify, ZingMP3 hoặc tên bài hát")
    print("2. Nhập đường dẫn tệp lời bài hát (.lrc, .srt, .txt)")
    print("3. Dùng bài hát mẫu (1: See Tình, 2: Nơi Này Có Anh)")

    choice = input(f"{Fore.YELLOW}➔ Chọn [1/2/3]: {Style.RESET_ALL}").strip()
    lyrics = []
    track_info = {}

    if choice == "1":
        query = input(f"{Fore.YELLOW}➔ Nhập link hoặc tên bài hát: {Style.RESET_ALL}").strip()
        print(f"{Fore.BLUE}[*] Đang quét lời bài hát và thời gian đồng bộ...{Style.RESET_ALL}")
        succ, res = LyricsEngine.get_lyrics_from_link_or_query(query)
        if not succ:
            print(f"{Fore.RED}[X] {res.get('message', 'Không tìm thấy lời bài hát!')}{Style.RESET_ALL}")
            return
        lyrics = res["lyrics"]
        track_info = {
            "track_name": res.get("track_name", "Không rõ"),
            "artist_name": res.get("artist_name", "Không rõ")
        }
    elif choice == "2":
        path = input(f"{Fore.YELLOW}➔ Nhập đường dẫn tệp (.lrc/.srt): {Style.RESET_ALL}").strip(' "\'')
        if not os.path.exists(path):
            print(f"{Fore.RED}[X] Tệp không tồn tại: {path}{Style.RESET_ALL}")
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        if path.endswith(".srt") or "-->" in content:
            lyrics = LyricsEngine.parse_srt_or_vtt(content)
        else:
            lyrics = LyricsEngine.parse_lrc(content)
        track_info = {
            "track_name": os.path.splitext(os.path.basename(path))[0],
            "artist_name": "Tùy chỉnh"
        }
    elif choice == "3":
        sample_choice = input(f"{Fore.YELLOW}➔ Chọn mẫu [1: See Tình / 2: Nơi Này Có Anh]: {Style.RESET_ALL}").strip()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        fname = "see_tinh.lrc" if sample_choice == "1" else "noi_nay_co_anh.lrc"
        sample_path = os.path.join(base_dir, "samples", fname)
        with open(sample_path, "r", encoding="utf-8") as f:
            content = f.read()
        lyrics = LyricsEngine.parse_lrc(content)
        track_info = {
            "track_name": "See Tình" if sample_choice == "1" else "Nơi Này Có Anh",
            "artist_name": "Sample"
        }
    else:
        print(f"{Fore.RED}[!] Lựa chọn không hợp lệ.{Style.RESET_ALL}")
        return

    if not lyrics:
        print(f"{Fore.RED}[X] Danh sách lời bài hát trống!{Style.RESET_ALL}")
        return

    print(f"\n{Fore.GREEN}[✔] Đã nạp: {track_info.get('track_name')} ({len(lyrics)} câu hát){Style.RESET_ALL}")
    print(f"Thời lượng: {lyrics[-1]['time_str']} ({lyrics[-1]['time']}s)")

    # 3. SETTINGS
    print(f"\n{Fore.CYAN}[3] TÙY CHỌN HIỂN THỊ{Style.RESET_ALL}")
    emoji = input(f"{Fore.YELLOW}➔ Emoji đi kèm [Mặc định: 🎵]: {Style.RESET_ALL}").strip() or "🎵"
    
    # 4. START SYNC
    print(f"\n{Fore.GREEN}===================================================={Style.RESET_ALL}")
    print(f"Nhấn {Fore.YELLOW}[ENTER]{Style.RESET_ALL} để bắt đầu phát nhạc và đồng bộ lời status...")
    print(f"Nhấn {Fore.RED}Ctrl + C{Style.RESET_ALL} bất kỳ lúc nào để dừng lại.")
    print(f"{Fore.GREEN}===================================================={Style.RESET_ALL}\n")
    input()

    controller = SyncController(client)
    controller.set_config({"emoji": emoji, "clear_on_finish": True})
    controller.load_song(lyrics, track_info)
    controller.start(0.0)

    try:
        current_idx = -1
        while controller.state == "playing":
            state = controller.get_state()
            active_idx = state["current_line_idx"]
            t = state["current_time"]

            mins = int(t // 60)
            secs = int(t % 60)
            time_str = f"{mins:02d}:{secs:02d}"

            if active_idx != current_idx and active_idx >= 0:
                current_idx = active_idx
                line = lyrics[active_idx]
                print(f"{Fore.CYAN}[{time_str}]{Style.RESET_ALL} {Fore.GREEN}▶ {emoji} {line['text']}{Style.RESET_ALL}")

            time.sleep(0.1)

        print(f"\n{Fore.GREEN}[✔] Bài hát đã kết thúc! Đã tự động dọn dẹp trạng thái.{Style.RESET_ALL}")

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Đang dừng lại và xóa trạng thái Discord...{Style.RESET_ALL}")
        controller.stop()
        print(f"{Fore.GREEN}[✔] Đã dừng thành công!{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
