import os
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, USLT, Encoding
from mutagen.mp4 import MP4, MP4Tags
import syncedlyrics

class LyricsEmbedder:
    def __init__(self, audio_path: str):
        self.audio_path = audio_path
        self.extension = os.path.splitext(audio_path)[1].lower()

        if self.extension == '.mp3':
            self.audio = MP3(audio_path, ID3=ID3)
            if self.audio.tags is None:
                self.audio.add_tags()
        elif self.extension == '.m4a':
            self.audio = MP4(audio_path)
            if self.audio.tags is None:
                self.audio.add_tags()
        else:
            raise ValueError("Unsupported audio format. Only .mp3 and .m4a are supported.")

    def fetch_lyrics(self, title: str, artist: str) -> str:
        print(f"🔍 Searching lyrics for: {title} by {artist}")
        try:
            lyrics = syncedlyrics.search(f"[{title}] [{artist}]")
            if not lyrics:
                raise ValueError("Lyrics not found.")
            print("🎵 Lyrics fetched successfully.")
            return lyrics
        except Exception as e:
            print(f"❌ Failed to fetch lyrics: {e}")
            return ""

    def embed_lyrics(self, lyrics_text: str):
        if not lyrics_text:
            print("⚠️ No lyrics to embed.")
            return

        if self.extension == '.mp3':
            self.audio.tags.delall("USLT")
            uslt = USLT(encoding=Encoding.UTF8, lang='eng', desc='', text=lyrics_text)
            self.audio.tags.add(uslt)
            self.audio.save(v2_version=3)
        elif self.extension == '.m4a':
            self.audio.tags["©lyr"] = [lyrics_text]
            self.audio.save()

        print(f"✅ Lyrics embedded successfully in {self.extension} file.")
