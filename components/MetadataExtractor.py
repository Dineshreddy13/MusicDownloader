from urllib.parse import urlparse, parse_qs
from ytmusicapi import YTMusic
import itunespy


class SongMetadataFetcher:
    def __init__(self):
        self.ytmusic = YTMusic()

    def extract_video_id(self, url):
        """Extract videoId from a YouTube Music link"""
        parsed = urlparse(url)
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if not video_id:
            raise ValueError("Invalid YouTube Music link: no videoId found")
        return video_id

    def fetch_base_metadata(self, url):
        """Fetch initial metadata from YouTube Music"""
        video_id = self.extract_video_id(url)
        song_info = self.ytmusic.get_song(video_id)
        video_details = song_info.get("videoDetails", {})

        return {
            "title": video_details.get("title", "Unknown"),
            "artist": video_details.get("author", "Unknown"),
            "cover_image_url": video_details.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "N/A"),
        }

    def fill_with_itunes(self, metadata):
        """Try to fill metadata using iTunes API"""
        try:
            results = itunespy.search_track(f"{metadata['title']} {metadata['artist']}")
            if results:
                r = results[0]
                metadata["album"] = metadata.get("album") or r.collection_name
                metadata["album_artist"] = metadata.get("album_artist") or r.artist_name
                metadata["year"] = metadata.get("year") or r.release_date[:4]
                metadata["track_number"] = metadata.get("track_number") or r.track_number
                metadata["genre"] = metadata.get("genre") or r.primary_genre_name
        except Exception as e:
            print("iTunes lookup failed:", e)
        return metadata

    def get_complete_metadata(self, url):
        """Return metadata using YT Music + iTunes"""
        base_metadata = self.fetch_base_metadata(url)

        # Enrich with iTunes
        enriched_metadata = self.fill_with_itunes(base_metadata)

        return enriched_metadata
