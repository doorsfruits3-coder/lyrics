import unittest
from core.lyrics_engine import LyricsEngine

class TestLyricsEngine(unittest.TestCase):
    def test_clean_song_title(self):
        self.assertEqual(LyricsEngine.clean_song_title("See Tình [Official Music Video]"), "See Tình")
        self.assertEqual(LyricsEngine.clean_song_title("Nơi Này Có Anh (Lyric Video)"), "Nơi Này Có Anh")
        self.assertEqual(LyricsEngine.clean_song_title("Alone (Original Mix)"), "Alone")

    def test_extract_soundcloud_urls(self):
        # 1. Desktop URL
        sc_url = "https://soundcloud.com/marshmellomusic/alone"
        info = LyricsEngine.extract_info_from_url(sc_url)
        self.assertEqual(info["type"], "soundcloud")
        self.assertIn("alone", info["query"].lower())

        # 2. Mobile URL
        m_sc_url = "https://m.soundcloud.com/postmalone/circles"
        info_m = LyricsEngine.extract_info_from_url(m_sc_url)
        self.assertEqual(info_m["type"], "soundcloud")
        self.assertIn("circles", info_m["query"].lower())

        # 3. Slug parsing fallback
        slug_url = "https://soundcloud.com/charlie-puth/see-you-again-feat-wiz-khalifa"
        info_slug = LyricsEngine.extract_info_from_url(slug_url)
        self.assertEqual(info_slug["type"], "soundcloud")
        self.assertIn("see you again", info_slug["query"].lower())

    def test_parse_lrc(self):
        sample_lrc = "[00:12.34] Câu hát đầu tiên\n[00:18.50] Câu hát thứ hai"
        parsed = LyricsEngine.parse_lrc(sample_lrc)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["time"], 12.34)
        self.assertEqual(parsed[0]["text"], "Câu hát đầu tiên")
        self.assertEqual(parsed[1]["time"], 18.50)

    def test_soundcloud_lyrics_integration(self):
        succ, res = LyricsEngine.get_lyrics_from_link_or_query("https://soundcloud.com/marshmellomusic/alone")
        self.assertTrue(succ)
        self.assertIn("alone", res["track_name"].lower())
        self.assertGreater(len(res["lyrics"]), 0)

if __name__ == "__main__":
    unittest.main()
