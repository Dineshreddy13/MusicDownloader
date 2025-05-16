import os
import requests
import re
from yt_dlp import YoutubeDL
import time
import sys
import configparser
from TokenManager import SpotifyTokenManager
from LyricsEmbedor import LyricsEmbedder
from SongInfo import AudioInspector
from UiTools import Spinner
from UiTools import QuietLogger
from dotenv import load_dotenv
from mutagen.mp4 import MP4
from mutagen.id3 import APIC, TIT2, TPE1, TALB, TCON, TDRC, TRCK, TPE2


class MusicDownloader:
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        config = configparser.ConfigParser()
        config.read("./config.ini")
        self.save_path = config["DEFAULT"].get("DOWNLOAD_PATH", "downloads")
        os.makedirs(self.save_path, exist_ok=True)

        self.spotify_token = None
        self.spinner = Spinner()


    def get_spotify_access_token(self):
        try:
            token_manager = SpotifyTokenManager(self.client_id, self.client_secret)
            self.spotify_token = token_manager.getToken();  
            return self.spotify_token
        except Exception as e:
            print("Failed to get Spotify access token:", e)
            return None

    def fetch_song_metadata(self, song_name):
        if not self.spotify_token:
            self.get_spotify_access_token()
        if not self.spotify_token:
            return None 

        url = "https://api.spotify.com/v1/search"
        headers = {"Authorization": f"Bearer {self.spotify_token}"}
        params = {"q": song_name, "type": "track", "limit": 10}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            track = response.json()["tracks"]["items"][0]

            if not track:
                print("No tracks found...")
                return None

            # print("Top 10 tracks:")
            # for idx, track in enumerate(tracks, start=1):
            #     track_artists = ", ".join(artist["name"] for artist in track["artists"])
            #     print(f"{idx}. {track['name']} by {track_artists}")

            # while True:
            #     try:
            #         choice = int(input("Select a track (1-10): "))
            #         if 1 <= choice <= len(tracks):
            #             selected_track = tracks[choice - 1]
            #             break
            #         else:
            #             print("Please choose a valid option between 1 and 10.")
            #     except ValueError:
            #         print("Invalid input. Please enter a number between 1 and 10.")

            artist_id = track["artists"][0]["id"]
            artist_url = f"https://api.spotify.com/v1/artists/{artist_id}"
            artist_response = requests.get(artist_url, headers=headers)
            artist_response.raise_for_status()
            artist_data = artist_response.json()
            genres = ", ".join(artist_data.get("genres", []))
            album = track["album"]
            album_artists = ", ".join(artist["name"] for artist in album["artists"])
            album_images = track["album"]["images"]
            cover_image_url = album_images[0]["url"] if album_images else None

            metadata = {
                "title": track["name"],
                "artist": ", ".join(artist["name"] for artist in track["artists"]),
                "album": album["name"],
                "album_artist": album_artists,
                "year": album["release_date"].split("-")[0],
                "genre": genres,
                "track_id": track["id"],
                "popularity": track.get("popularity", "N/A"),
                "track_number": track["track_number"],
                "duration_ms": track["duration_ms"],
                "cover_image_url": cover_image_url,
            }

            print("Metadata fetched successfully...")
            return metadata
        except Exception as e:
            print("Failed to fetch song metadata:", e)
            return None

    def downloadAudio(self, url):
        self.spinner.start()
        options = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best', 
            'outtmpl': os.path.join(self.save_path, 'audio.%(ext)s'),
            'noplaylist': True,
            'logger': QuietLogger(),
            'progress_hooks': [self._progress_hook],
        }

        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                print()
            self.spinner.stop()
            raw_title = info['title']
            ext = info.get('ext', 'm4a')
            old_path = os.path.join(self.save_path, f"audio.{ext}")

            sanitized_title = self.modifyTitle(raw_title)
            metadata = self.fetch_song_metadata(sanitized_title)
            if not metadata:
                proceed = input("Proceed without metadata (y/n): ")
                if proceed.lower() != 'y':
                    sys.exit()

            filename = self.modifyTitle(metadata.get('title', sanitized_title))
            new_path = os.path.join(self.save_path, f"{filename}.{ext}")

            try:
                if new_path != old_path:
                    os.rename(old_path, new_path)
            except Exception as e:
                print(f"Warning: Could not rename file: {e}")
                new_path = old_path  # fallback

            cover_image_data = None
            if metadata and 'cover_image_url' in metadata:
                cover_image_data = self.fetch_cover_image(metadata['cover_image_url'])
            if not cover_image_data:
                proceed = input("Proceed without cover image (y/n): ")
                if proceed.lower() != 'y':
                    sys.exit()

            print("\rDownload completed! File saved in:", new_path)
            return new_path, metadata, cover_image_data

        except Exception as e:
            self.spinner.stop()
            print("An error occurred during downloading:", e)
            return None, None, None


    def modifyTitle(self,title):
        return re.sub(r'[<>:"/\\|?*]', '', title)
    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            self.spinner.stop()
            print(f"\rDownloading Audio : {d['_percent_str']} | Speed: {d['_speed_str']}", end="")
        elif d['status'] == 'finished':
            print("\nDownload finished, converting file...")
            self.spinner.start()

    def add_metadata_and_coverimage(self, input_file, cover_image_data, metadata=None):
        if not input_file.endswith(".m4a"):
            print(f"Input file {input_file} is not in M4A format.")
            return
        try:
            audio = MP4(input_file)
            if not audio.tags:
                audio.tags = {}

            if metadata:
                if 'title' in metadata:
                    audio["\xa9nam"] = metadata['title']  
                if 'artist' in metadata:
                    audio["\xa9ART"] = metadata['artist']  
                if 'album' in metadata:
                    audio["\xa9alb"] = metadata['album']  
                if 'genre' in metadata:
                    audio["\xa9gen"] = metadata['genre']  
                if 'year' in metadata:
                    audio["\xa9day"] = str(metadata['year'])  
                if 'track_number' in metadata:
                    audio["trkn"] = [(metadata['track_number'], 0)]  
                if 'album_artist' in metadata:
                    audio["\xa9wrt"] = metadata['album_artist']

            if cover_image_data:
                audio["covr"] = [cover_image_data]  

            audio.save()

            # Embed lyrics if available
            embedder = LyricsEmbedder(input_file)
            lyrics = embedder.fetch_lyrics(metadata["title"], metadata["artist"].split(",")[0])
            if lyrics:
                embedder.embed_lyrics(lyrics)

            AudioInspector(input_file).display_properties()

            print(f"✅ Metadata and cover image embedded successfully : {input_file}")
        except Exception as e:
            print("Error updating the audio file with metadata and cover image :", e)

    def fetch_cover_image(self, url):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            print("Cover image fetched successfully.")
            return response.content
        except Exception as e:
            print(f"Failed to fetch cover image: {e}")
            return None

    def process(self, video_url):
        downloaded_file, metadata, cover_image_data = self.downloadAudio(video_url)
        if downloaded_file:
            self.add_metadata_and_coverimage(downloaded_file, cover_image_data, metadata=metadata)



# def main():
#     songs= []
#     downloader = MusicDownloader()
#     if(len(songs) == 0):
#         video_url = input("Enter the YouTube video URL: ").strip()
#         songs = video_url.split(" ")
#     for i in songs:
#         downloader.process(i)
#         time.sleep(1)



# if __name__ == "__main__":
#     main()
