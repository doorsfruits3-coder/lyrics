import re
import time
import requests
import json

class DiscordClient:
    API_BASE = "https://discord.com/api/v9"
    DEFAULT_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    def __init__(self, raw_auth_input=""):
        self.token = ""
        self.cookies = ""
        self.user_data = None
        self.last_request_time = 0
        self.min_interval = 1.2  # minimum interval between status updates
        if raw_auth_input:
            self.set_credentials(raw_auth_input)

    @classmethod
    def parse_auth_string(cls, input_str: str):
        """
        Parses token and cookies from various user input formats:
        - Pure token
        - Cookie string containing token=...
        - Full cURL or HTTP headers containing Authorization / Cookie
        - JSON string
        """
        token = ""
        cookies = ""

        if not input_str:
            return token, cookies

        input_str = input_str.strip()

        # Try JSON
        if input_str.startswith("{") and input_str.endswith("}"):
            try:
                data = json.loads(input_str)
                token = data.get("token") or data.get("authorization") or ""
                cookies = data.get("cookies") or data.get("cookie") or ""
            except Exception:
                pass

        # Try cURL / Headers
        if not token:
            auth_match = re.search(r'(?:authorization|auth|token)\s*[:=]\s*["\']?([A-Za-z0-9_\-\.]{40,120})["\']?', input_str, re.IGNORECASE)
            if auth_match:
                token = auth_match.group(1)

        # Extract Cookies if present
        cookie_match = re.search(r'(?:cookie\s*:\s*)([^\r\n]+)', input_str, re.IGNORECASE)
        if cookie_match:
            cookies = cookie_match.group(1).strip()
        elif "__dcfduid=" in input_str or "__sdcfduid=" in input_str or "locale=" in input_str:
            cookies = input_str.strip()

        # If token was inside cookie string (e.g. token=xyz)
        if not token:
            token_cookie = re.search(r'(?:^|;\s*)(?:token|auth_token)=([A-Za-z0-9_\-\.]{40,120})', input_str, re.IGNORECASE)
            if token_cookie:
                token = token_cookie.group(1)

        # Regex fallback for standard Discord token pattern: [A-Za-z0-9_\-]{24,28}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,}
        if not token:
            direct_token_match = re.search(r'[A-Za-z0-9_\-]{24,28}\.[A-Za-z0-9_\-]{6}\.[A-Za-z0-9_\-]{27,}', input_str)
            if direct_token_match:
                token = direct_token_match.group(0)

        # Or if user just pasted token directly without spaces
        if not token and len(input_str) >= 50 and " " not in input_str and ";" not in input_str:
            token = input_str

        return token, cookies

    def set_credentials(self, raw_input: str):
        self.token, self.cookies = self.parse_auth_string(raw_input)

    def get_headers(self):
        headers = {
            "User-Agent": self.DEFAULT_UA,
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
        }
        if self.token:
            headers["Authorization"] = self.token
        if self.cookies:
            headers["Cookie"] = self.cookies
        return headers

    def verify_account(self):
        """
        Tests if the credentials are valid and fetches user profile.
        Returns: (success: bool, data_or_error_msg: dict/str)
        """
        if not self.token:
            if self.cookies and not self.token:
                return False, (
                    "Đã nhận diện Cookie trình duyệt, nhưng Discord yêu cầu User Token để xác thực API. "
                    "Hãy dán Token tài khoản hoặc dùng hướng dẫn F12 để lấy Token!"
                )
            return False, "Chưa cung cấp Token hoặc Cookie hợp lệ!"

        try:
            url = f"{self.API_BASE}/users/@me"
            resp = requests.get(url, headers=self.get_headers(), timeout=10)

            if resp.status_code == 200:
                user = resp.json()
                avatar_id = user.get("avatar")
                user_id = user.get("id")
                avatar_url = "https://cdn.discordapp.com/embed/avatars/0.png"
                if avatar_id:
                    ext = "gif" if avatar_id.startswith("a_") else "png"
                    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.{ext}"

                self.user_data = {
                    "id": user_id,
                    "username": user.get("username"),
                    "global_name": user.get("global_name") or user.get("username"),
                    "discriminator": user.get("discriminator", "0"),
                    "avatar_url": avatar_url,
                    "bio": user.get("bio", "")
                }
                return True, self.user_data
            elif resp.status_code == 401:
                return False, "Token không hợp lệ hoặc đã hết hạn (401 Unauthorized)."
            elif resp.status_code == 403:
                return False, "Tài khoản bị hạn chế hoặc Cloudflare chặn yêu cầu (403 Forbidden)."
            else:
                return False, f"Lỗi HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            return False, f"Lỗi kết nối tới Discord API: {str(e)}"

    def update_custom_status(self, text: str, emoji_name: str = "🎵", emoji_id: str = None):
        """
        Updates Discord custom status via PATCH /users/@me/settings.
        """
        if not self.token:
            return False, "Chưa thiết lập token"

        # Rate-limiting check
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        url = f"{self.API_BASE}/users/@me/settings"
        
        status_payload = {
            "text": text[:128], # Discord max length is 128 characters
            "expires_at": None
        }
        if emoji_name:
            status_payload["emoji_name"] = emoji_name
        if emoji_id:
            status_payload["emoji_id"] = emoji_id

        payload = {
            "custom_status": status_payload
        }

        try:
            resp = requests.patch(url, headers=self.get_headers(), json=payload, timeout=8)
            self.last_request_time = time.time()

            if resp.status_code == 200:
                return True, "Cập nhật trạng thái thành công"
            elif resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 2.0)
                return False, f"Bị giới hạn tốc độ (Rate Limited), đợi {retry_after}s"
            else:
                return False, f"Lỗi HTTP {resp.status_code}: {resp.text[:150]}"
        except Exception as e:
            return False, f"Lỗi mạng: {str(e)}"

    def update_bio(self, bio_text: str):
        """
        Updates Discord profile bio / about me.
        """
        if not self.token:
            return False, "Chưa thiết lập token"

        url = f"{self.API_BASE}/users/@me/profile"
        payload = {"bio": bio_text[:190]}

        try:
            resp = requests.patch(url, headers=self.get_headers(), json=payload, timeout=8)
            if resp.status_code == 200:
                return True, "Cập nhật bio thành công"
            elif resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 2.0)
                return False, f"Rate limited: đợi {retry_after}s"
            else:
                return False, f"Lỗi HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)

    def clear_status(self):
        """
        Clears custom status.
        """
        if not self.token:
            return False, "Chưa thiết lập token"

        url = f"{self.API_BASE}/users/@me/settings"
        try:
            resp = requests.patch(url, headers=self.get_headers(), json={"custom_status": None}, timeout=8)
            return resp.status_code == 200, "Đã xóa trạng thái"
        except Exception as e:
            return False, str(e)
