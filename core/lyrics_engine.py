import re
import urllib.parse
import json
import requests

class LyricsEngine:
    LRCLIB_API = "https://lrclib.net/api"
    HEADERS = {
        "User-Agent": "DiscordLyricStatus/2.0 (https://github.com/discord-lyric-status)"
    }

    @staticmethod
    def parse_lrc(lrc_text: str):
        """
        Parses LRC content into a sorted list of dicts:
        [{"time": 12.34, "time_str": "00:12", "text": "Lyric text"}, ...]
        Handles multi-timestamp lines like [01:10.00][02:20.00] chorus.
        """
        lyrics = []
        if not lrc_text:
            return lyrics

        # Pattern for timestamp [mm:ss.xx] or [mm:ss.xxx] or [mm:ss]
        time_tag_pattern = re.compile(r'\[(\d{1,3}):(\d{2})(?:[\.:](\d{1,3}))?\]')

        for line in lrc_text.splitlines():
            line = line.strip()
            if not line:
                continue

            # Ignore metadata tags like [ti:Title], [ar:Artist], [al:Album]
            if re.match(r'^\[[a-zA-Z]+:', line):
                continue

            # Find all timestamps in this line
            matches = list(time_tag_pattern.finditer(line))
            if not matches:
                continue

            # The lyric text is everything after the last timestamp tag
            last_match = matches[-1]
            text = line[last_match.end():].strip()

            for match in matches:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                frac_str = match.group(3) or "0"
                if len(frac_str) == 1:
                    fraction = float(f"0.{frac_str}")
                elif len(frac_str) == 2:
                    fraction = float(f"0.{frac_str}")
                else:
                    fraction = float(f"0.{frac_str[:3]}")

                total_seconds = round(minutes * 60 + seconds + fraction, 2)
                time_str = f"{minutes:02d}:{seconds:02d}"

                lyrics.append({
                    "time": total_seconds,
                    "time_str": time_str,
                    "text": text
                })

        # Sort chronologically by time
        lyrics.sort(key=lambda x: x["time"])
        return lyrics

    @staticmethod
    def parse_srt_or_vtt(subtitle_text: str):
        """
        Parses SRT or WebVTT subtitles into synced lyric list.
        """
        lyrics = []
        # Pattern: 00:01:23,456 --> 00:01:25,789 or 01:23.456 --> 01:25.789
        srt_time_pattern = re.compile(
            r'(?:(\d{2}):)?(\d{2}):(\d{2})[,\.](\d{2,3})\s*-->\s*(?:(\d{2}):)?(\d{2}):(\d{2})[,\.](\d{2,3})'
        )

        blocks = subtitle_text.replace('\r\n', '\n').split('\n\n')
        for block in blocks:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if not lines:
                continue

            for i, line in enumerate(lines):
                match = srt_time_pattern.search(line)
                if match:
                    hours = int(match.group(1) or 0)
                    minutes = int(match.group(2))
                    seconds = int(match.group(3))
                    millis = int(match.group(4).ljust(3, '0')[:3])
                    start_time = round(hours * 3600 + minutes * 60 + seconds + millis / 1000.0, 2)
                    
                    text_lines = lines[i+1:]
                    text = " ".join(text_lines).strip()
                    # Strip any HTML tags like <i>, <b>, <c.color>
                    text = re.sub(r'<[^>]+>', '', text).strip()
                    if text:
                        lyrics.append({
                            "time": start_time,
                            "time_str": f"{minutes:02d}:{seconds:02d}",
                            "text": text
                        })
                    break

        lyrics.sort(key=lambda x: x["time"])
        return lyrics

    @staticmethod
    def parse_plain_text(text: str, line_duration: float = 4.0):
        """
        Creates evenly spaced timestamps if user only gives plain lines of text.
        """
        lyrics = []
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        current_time = 0.0
        for line in lines:
            mins = int(current_time // 60)
            secs = int(current_time % 60)
            lyrics.append({
                "time": round(current_time, 2),
                "time_str": f"{mins:02d}:{secs:02d}",
                "text": line
            })
            current_time += line_duration
        return lyrics

    @classmethod
    def clean_song_title(cls, title: str) -> str:
        """
        Cleans video/track titles by removing fluff like:
        [OFFICIAL MUSIC VIDEO], (Lyric Video), M/V, Audio, ft., Prod by...
        """
        if not title:
            return ""
        # Remove bracketed text [Official MV], (Lyrics), etc.
        title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
        # Remove common keywords
        keywords = [
            r'official\s+music\s+video', r'official\s+mv', r'music\s+video',
            r'lyric\s+video', r'official\s+audio', r'audio\s+official',
            r'official\s+video', r'mv\b', r'm\/v\b', r'video\s+lyric',
            r'visualizer', r'prod\.?\s*by.*', r'feat\.?.*', r'ft\.?.*'
        ]
        for kw in keywords:
            title = re.sub(kw, '', title, flags=re.IGNORECASE)

        # Remove extra separators like |, -, / at edges
        title = re.sub(r'[\s\|\-\:\/]+$', '', title)
        title = re.sub(r'^[\s\|\-\:\/]+', '', title)
        title = re.sub(r'\s+', ' ', title).strip()
        return title

    @classmethod
    def extract_info_from_url(cls, url: str):
        """
        Extracts song title and possible artist from YouTube, Spotify, SoundCloud, ZingMP3, etc.
        """
        url = url.strip()
        # 1. YouTube URL
        if "youtube.com" in url or "youtu.be" in url:
            try:
                oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
                resp = requests.get(oembed_url, timeout=6)
                if resp.status_code == 200:
                    raw_title = resp.json().get("title", "")
                    clean_title = cls.clean_song_title(raw_title)
                    author = resp.json().get("author_name", "")
                    return {
                        "type": "youtube",
                        "raw_title": raw_title,
                        "clean_title": clean_title,
                        "query": clean_title or raw_title,
                        "artist": author
                    }
            except Exception:
                pass

        # 2. Spotify URL
        if "spotify.com" in url:
            try:
                oembed_url = f"https://open.spotify.com/oembed?url={urllib.parse.quote(url)}"
                resp = requests.get(oembed_url, timeout=6)
                if resp.status_code == 200:
                    raw_title = resp.json().get("title", "")
                    clean_title = cls.clean_song_title(raw_title)
                    return {
                        "type": "spotify",
                        "raw_title": raw_title,
                        "clean_title": clean_title,
                        "query": raw_title,
                        "artist": ""
                    }
            except Exception:
                pass

        # 3. SoundCloud URL
        if "soundcloud.com" in url:
            clean_url = url
            if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
                clean_url = "https://" + clean_url

            # If it's a short link like on.soundcloud.com/xxx, resolve redirect
            if "on.soundcloud.com" in clean_url:
                try:
                    resolve_resp = requests.get(
                        clean_url,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
                        allow_redirects=True,
                        timeout=5,
                        stream=True
                    )
                    if resolve_resp.url and "soundcloud.com" in resolve_resp.url:
                        clean_url = resolve_resp.url
                except Exception:
                    pass

            # Normalize m.soundcloud.com to soundcloud.com for oEmbed
            oembed_target = re.sub(r'^(https?://)m\.soundcloud\.com', r'\1soundcloud.com', clean_url)

            # Try SoundCloud oEmbed first
            try:
                oembed_url = f"https://soundcloud.com/oembed?url={urllib.parse.quote(oembed_target)}&format=json"
                resp = requests.get(
                    oembed_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
                    timeout=6
                )
                if resp.status_code == 200:
                    data = resp.json()
                    raw_title = data.get("title", "")
                    author = data.get("author_name", "")

                    # Strip "by {author}" at the end of the title if present
                    track_title = raw_title
                    if author:
                        track_title = re.sub(r'\s+by\s+' + re.escape(author) + r'$', '', track_title, flags=re.IGNORECASE)

                    clean_title = cls.clean_song_title(track_title)
                    query = f"{clean_title} {author}".strip() if author and author.lower() not in clean_title.lower() else clean_title
                    return {
                        "type": "soundcloud",
                        "raw_title": raw_title,
                        "clean_title": clean_title or raw_title,
                        "query": query or clean_title or raw_title,
                        "artist": author
                    }
            except Exception:
                pass

            # Fallback: Parse URL path / slug
            try:
                parsed = urllib.parse.urlparse(oembed_target)
                path = parsed.path.strip("/")
                segments = [s for s in path.split("/") if s]
                if len(segments) >= 2 and segments[0].lower() not in ("discover", "stream", "upload", "you", "settings", "search"):
                    raw_artist_slug = segments[0].replace("-", " ").replace("_", " ").strip()
                    # If artist slug is an auto-generated user id like user-12345678, ignore it
                    if re.match(r'^user[-_\s\d]+$', raw_artist_slug, re.IGNORECASE):
                        artist_slug = ""
                    else:
                        cleaned_artist = re.sub(
                            r'(?:official|music|records|audio|channel|prod|production|media)$',
                            '',
                            raw_artist_slug,
                            flags=re.IGNORECASE
                        ).strip()
                        artist_slug = cleaned_artist if cleaned_artist else raw_artist_slug

                    track_slug = segments[-1].replace("-", " ").replace("_", " ")
                    clean_track = cls.clean_song_title(track_slug)
                    query = f"{clean_track} {artist_slug}".strip() if (artist_slug and artist_slug.lower() not in clean_track.lower()) else clean_track
                    return {
                        "type": "soundcloud",
                        "raw_title": track_slug,
                        "clean_title": clean_track or track_slug,
                        "query": query or clean_track or track_slug,
                        "artist": artist_slug
                    }
                elif segments:
                    track_slug = segments[-1].replace("-", " ").replace("_", " ")
                    clean_track = cls.clean_song_title(track_slug)
                    return {
                        "type": "soundcloud",
                        "raw_title": track_slug,
                        "clean_title": clean_track or track_slug,
                        "query": clean_track or track_slug,
                        "artist": ""
                    }
            except Exception:
                pass

        # 4. ZingMP3 URL (e.g. zingmp3.vn/bai-hat/Ten-Bai-Hat-Ca-Si/ID.html)
        if "zingmp3.vn" in url:
            slug_match = re.search(r'/bai-hat/([^/]+)/', url)
            if slug_match:
                slug = slug_match.group(1).replace('-', ' ')
                clean_slug = cls.clean_song_title(slug)
                return {
                    "type": "zingmp3",
                    "raw_title": slug,
                    "clean_title": clean_slug,
                    "query": clean_slug or slug,
                    "artist": ""
                }

        # 5. Fallback: treat whole input as query / song name
        clean_input = cls.clean_song_title(url)
        return {
            "type": "generic",
            "raw_title": url,
            "clean_title": clean_input,
            "query": clean_input or url,
            "artist": ""
        }

    @classmethod
    def rank_candidates(cls, results: list, clean_title: str = "", artist: str = "", query: str = ""):
        """
        Ranks search candidates based on:
        1. Having synced lyrics (+50)
        2. Exact track name match (+40)
        3. Title substring match (+20)
        4. Artist match (+30)
        5. Keyword overlap (+5 per keyword)
        """
        if not results:
            return results

        clean_t = (clean_title or "").lower().strip()
        art = (artist or "").lower().strip()
        art_tokens = set(re.findall(r'\w+', art))
        q_words = set(re.findall(r'\w+', (query or "").lower()))

        def score(item):
            s = 0
            if item.get("has_synced"):
                s += 50

            track_name = (item.get("track_name") or "").lower().strip()
            artist_name = (item.get("artist_name") or "").lower().strip()

            if clean_t:
                if track_name == clean_t:
                    s += 40
                elif clean_t in track_name:
                    s += 20

            if art:
                art_compact = art.replace(" ", "").replace("-", "")
                artist_name_compact = artist_name.replace(" ", "").replace("-", "")
                if art in artist_name or artist_name in art:
                    s += 35
                elif art_compact and len(art_compact) >= 3 and (art_compact in artist_name_compact or artist_name_compact in art_compact):
                    s += 30
                else:
                    item_art_tokens = set(re.findall(r'\w+', artist_name))
                    if art_tokens & item_art_tokens:
                        s += 20

            item_text = f"{track_name} {artist_name}"
            for w in q_words:
                if len(w) > 2 and w in item_text:
                    s += 5

            return s

        return sorted(results, key=score, reverse=True)

    @classmethod
    def search_synced_lyrics(cls, query: str):
        """
        Searches LRCLIB for synced lyrics using query string.
        Returns: (success: bool, results: list)
        """
        if not query:
            return False, []

        try:
            params = {"q": query}
            resp = requests.get(f"{cls.LRCLIB_API}/search", params=params, headers=cls.HEADERS, timeout=8)
            if resp.status_code != 200:
                return False, []

            data = resp.json()
            if not isinstance(data, list):
                return False, []

            results = []
            for item in data:
                has_synced = bool(item.get("syncedLyrics"))
                results.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "track_name": item.get("trackName") or item.get("name"),
                    "artist_name": item.get("artistName"),
                    "album_name": item.get("albumName"),
                    "duration": item.get("duration"),
                    "has_synced": has_synced,
                    "synced_lyrics": item.get("syncedLyrics") or "",
                    "plain_lyrics": item.get("plainLyrics") or ""
                })

            # Prioritize results that actually have synced lyrics
            results.sort(key=lambda x: (not x["has_synced"]))
            return True, results
        except Exception as e:
            return False, []

    @classmethod
    def get_lyrics_from_link_or_query(cls, url_or_query: str):
        """
        High-level helper:
        1. Identifies link type / cleans query
        2. Queries LRCLIB
        3. Parses top matching synced lyrics
        Returns: (success: bool, data: dict)
        """
        info = cls.extract_info_from_url(url_or_query)
        query = info["query"]

        success, results = cls.search_synced_lyrics(query)
        if not success or not results:
            # Try searching with clean_title if different from query
            if info.get("clean_title") and info.get("clean_title") != query:
                success, results = cls.search_synced_lyrics(info["clean_title"])

        if not success or not results:
            # Try searching with artist + clean_title if available
            if info.get("artist") and info.get("clean_title"):
                comb_query = f"{info['artist']} {info['clean_title']}"
                if comb_query != query:
                    success, results = cls.search_synced_lyrics(comb_query)

        if not success or not results:
            # Try searching with raw title if cleaned title didn't yield results
            if info.get("raw_title") and info["raw_title"] != query:
                success, results = cls.search_synced_lyrics(info["raw_title"])

        if not success or not results:
            return False, {
                "message": f"Không tìm thấy lời bài hát đồng bộ cho: '{query}'. Bạn có thể nhập file .lrc hoặc tự dán lời bài hát.",
                "query": query,
                "info": info,
                "candidates": []
            }

        # Rank candidates by relevance
        results = cls.rank_candidates(
            results,
            clean_title=info.get("clean_title", ""),
            artist=info.get("artist", ""),
            query=query
        )

        # Check if first item has synced lyrics
        top_item = results[0]
        artist_name = top_item.get("artist_name") or info.get("artist") or "Không rõ"
        if top_item["has_synced"]:
            parsed_lyrics = cls.parse_lrc(top_item["synced_lyrics"])
            return True, {
                "track_name": top_item["track_name"],
                "artist_name": artist_name,
                "duration": top_item["duration"],
                "lyrics": parsed_lyrics,
                "candidates": results[:5]
            }
        else:
            # We found track, but only plain lyrics
            parsed_lyrics = cls.parse_plain_text(top_item["plain_lyrics"])
            return True, {
                "track_name": top_item["track_name"],
                "artist_name": artist_name,
                "duration": top_item["duration"],
                "lyrics": parsed_lyrics,
                "is_plain_fallback": True,
                "candidates": results[:5]
            }
