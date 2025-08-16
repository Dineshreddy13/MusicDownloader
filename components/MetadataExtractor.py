import json
from urllib.parse import urlparse, parse_qs
from ytmusicapi import YTMusic
from openai import OpenAI
from datetime import date


class SongMetadataFetcher:
    def __init__(self, openai_key: str):
        self.ytmusic = YTMusic()
        self.client = OpenAI(api_key=openai_key)

    def extract_video_id(self, url: str) -> str:
        """Extract videoId from a YouTube Music link"""
        parsed = urlparse(url)
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if not video_id:
            raise ValueError("Invalid YouTube Music link: no videoId found")
        return video_id

    def fetch_base_metadata(self, url: str) -> dict:
        """Fetch initial metadata from YouTube Music"""
        video_id = self.extract_video_id(url)
        song_info = self.ytmusic.get_song(video_id)
        video_details = song_info.get("videoDetails", {})

        return {
            "title": video_details.get("title", "Unknown"),
            "artist": video_details.get("author", "Unknown"),
            "cover_image_url": video_details.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "N/A"),
        }

    def fill_missing_with_ai(self, metadata: dict) -> dict:
        """Ask AI to complete missing metadata fields"""
        prompt = f"""
        You are a meticulous music metadata assistant. Today's date is {date.today()}.
        Task: Fill ONLY the missing fields for this track's metadata using authoritative, up-to-date sources.
        Some song metadata is missing. 
        Current data: {metadata}
        Fill in missing fields (album, album_artist, year, genre, track_number, composer) based on up-to-date music sources like spotify, apple music, youtube music.
        Return JSON only.
        """
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    def get_complete_metadata(self, url: str) -> dict:
        """Return merged metadata (YT Music + AI filled)"""
        base_metadata = self.fetch_base_metadata(url)
        ai_metadata = self.fill_missing_with_ai(base_metadata)

        # Merge base + AI (AI fields overwrite if same keys)
        complete_metadata = {**base_metadata, **ai_metadata}
        return complete_metadata
