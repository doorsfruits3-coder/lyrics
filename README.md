# 🎵 Discord Lyric Status Sync (v2.0 Pro)

> Tool tự động đổi **Custom Status (Trạng thái tùy chỉnh)** và **Bio (Tiểu sử)** trên tài khoản Discord cá nhân theo thời gian thực đồng bộ với lời bài hát đang phát!

---

## 🌟 Tính Năng Nổi Bật

1. **Đăng nhập linh hoạt (Hỗ trợ Cookie & Token)**:
   - Hỗ trợ nhập trực tiếp User Token Discord.
   - Hỗ trợ dán chuỗi **Cookie / Headers / cURL** từ trình duyệt (tool tự động bóc tách và phân tích).
   - Tích hợp sẵn hướng dẫn 1-click lấy Token / Cookie qua F12 Console trong 5 giây.
   - Hiển thị trực quan Avatar, Tên hiển thị (@handle), ID người dùng và Live Mockup hồ sơ Discord.

2. **Quét lời bài hát thông minh từ Link (Tự động 100%)**:
   - 🔴 **YouTube**: Dán link video/MV hoặc audio (tự động phân tích tiêu đề và tìm lời khớp chuẩn).
   - 🟢 **Spotify**: Dán link track (`open.spotify.com/track/...`).
   - 🟠 **SoundCloud**: Dán link track/bài hát (`soundcloud.com/...` hoặc `on.soundcloud.com/...`).
   - 🟣 **ZingMP3**: Dán link bài hát (`zingmp3.vn/bai-hat/...`).
   - 🌐 **Tìm kiếm trực tiếp**: Gõ tên bài hát (ví dụ: *Nơi Này Có Anh*, *See Tình*, *Die With A Smile*...) - hệ thống tự động tìm bản ghi `.lrc` có đồng bộ từng giây từ cơ sở dữ liệu toàn cầu **LRCLIB**.

3. **Hỗ trợ tải tệp lời bài hát từ máy tính**:
   - Hỗ trợ tệp **`.lrc`** (chuẩn định dạng karaoke `[mm:ss.xx] Lời bài hát`).
   - Hỗ trợ tệp phụ đề **`.srt`** và **`.vtt`**.
   - Hỗ trợ tệp **`.txt`** (tool tự động chia đều thời gian nhịp điệu).
   - Có sẵn các bài hát mẫu chuẩn nhịp để test ngay lập tức.

4. **Đồng bộ thời gian chuẩn xác (Karaoke Sync)**:
   - Giao diện Karaoke sáng bóng: tự động cuộn và làm nổi bật (glow neon) câu hát đang phát.
   - Cho phép click vào bất kỳ câu nào để tua nhanh (Seek) đến thời điểm đó.
   - **Bộ căn chỉnh nhịp (Offset Calibrator)**: Hỗ trợ nút chỉnh `+0.2s`, `+1.0s`, `-0.2s`, `-1.0s` giúp bạn khớp chuẩn xác từng miligiây với nhạc bạn đang tự nghe trên điện thoại/Spotify/YouTube.
   - Cơ chế chống **Rate Limit (429)** thông minh từ Discord API.
   - Tự động dọn dẹp hoặc đặt lại trạng thái khi hết bài.

---

## 🚀 Hướng Dẫn Cài Đặt & Sử Dụng

### Bước 1: Mở Tool
Bạn có 2 chế độ để sử dụng:
- **Chế độ Web Dashboard (Khuyên dùng - Đẹp mắt, dễ chỉnh)**:
  - Nhấp đúp chuột vào file `run.bat` (hoặc mở terminal gõ `python app.py`).
  - Trình duyệt web sẽ tự động mở tại địa chỉ: `http://127.0.0.1:5000`
- **Chế độ Terminal CLI (Dành cho người thích dòng lệnh)**:
  - Nhấp đúp chuột vào file `run_cli.bat` (hoặc gõ `python cli.py`).

---

### Bước 2: Đăng Nhập Discord (Lấy Cookie / Token)

#### Cách lấy siêu nhanh (5 giây):
1. Mở Discord trên trình duyệt web (hoặc ứng dụng Discord Desktop).
2. Nhấn phím `F12` (hoặc `Ctrl + Shift + I`) để mở Developer Tools.
3. Chọn tab **Console**, dán đoạn code sau vào và nhấn **Enter**:
   ```javascript
   (webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
   ```
4. Copy chuỗi token trong ngoặc kép và dán vào ô đăng nhập của Tool, sau đó bấm **⚡ Xác Thực Tài Khoản**.

*(Lưu ý: Nếu bạn có chuỗi Cookie từ extension hoặc cURL Network, bạn cũng có thể dán trực tiếp vào ô, tool sẽ tự động lọc thông tin)*

---

### Bước 3: Nạp Lời Nhạc & Bắt Đầu Đồng Bộ
1. **Qua Link**:
   - Dán link YouTube / Spotify / SoundCloud / ZingMP3 hoặc gõ tên bài hát vào ô tìm kiếm -> Nhấn **🔍 Quét Lời Nhạc**.
2. **Qua File**:
   - Chuyển sang tab **Tải File** -> Kéo thả file `.lrc` hoặc `.srt` vào khung.
3. **Bài mẫu có sẵn**:
   - Nhấn vào tab **Bài Hát Mẫu** và chọn *See Tình* hoặc *Nơi Này Có Anh*.

Sau khi nạp bài hát:
- Nhấn **▶ Bắt Đầu Đồng Bộ**.
- Bạn bật bài nhạc tương ứng trên Spotify/YouTube/điện thoại của bạn cùng lúc.
- Nếu thấy lời trên Discord nhảy nhanh hoặc chậm hơn tiếng hát, chỉ cần nhấn các nút `+0.2s` hoặc `-0.2s` trên thanh điều khiển để khớp nhịp hoàn hảo!

---

## 📁 Cấu Trúc Thư Mục

```text
discord-lyric-status/
├── app.py                   # Máy chủ Web Dashboard (Flask + REST API)
├── cli.py                   # Phiên bản chạy trực tiếp trên Terminal CLI
├── run.bat                  # File chạy 1-click cho Web UI trên Windows
├── run_cli.bat              # File chạy 1-click cho CLI trên Windows
├── requirements.txt         # Danh sách thư viện Python cần thiết
├── core/
│   ├── discord_client.py    # Xử lý xác thực Token/Cookie, update status/bio, rate limit
│   ├── lyrics_engine.py     # Quét link YouTube/Spotify/ZingMP3, LRCLIB API, đọc tệp LRC/SRT
│   └── sync_controller.py   # Bộ đếm giờ, luồng đồng bộ theo thời gian thực, offset calibrator
├── templates/
│   └── index.html           # Giao diện Web Dashboard phong cách Discord Dark Theme
├── static/
│   ├── css/style.css        # CSS phong cách Discord, hiệu ứng Karaoke Neon
│   └── js/app.js            # Logic frontend, karaoke visualizer, live profile preview
└── samples/
    ├── see_tinh.lrc         # File lời mẫu See Tình (Hoàng Thùy Linh)
    └── noi_nay_co_anh.lrc   # File lời mẫu Nơi Này Có Anh (Sơn Tùng M-TP)
```

---

## 🔒 An Toàn & Bảo Mật
- Toàn bộ Token / Cookie chỉ được lưu trong bộ nhớ tạm của máy tính của bạn khi tool đang chạy. Không gửi dữ liệu đi bất kỳ máy chủ bên thứ ba nào.
- Bộ điều khiển có tích hợp giới hạn tần suất gửi yêu cầu tối thiểu (`min_interval = 1.2s - 1.5s`) để giữ tài khoản an toàn, không bị Discord gắn cờ spam.
