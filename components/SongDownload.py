import os
import concurrent
import requests
import re
from yt_dlp import YoutubeDL
import configparser
from components.SongInfo import AudioInspector
from components.UiTools import Spinner
from components.MetadataExtractor import SongMetadataFetcher
from components.UiTools import QuietLogger
from dotenv import load_dotenv
from mutagen.mp4 import MP4
from mutagen.id3 import APIC, TIT2, TPE1, TALB, TCON, TDRC, TRCK, TPE2


class MusicDownloader:
    def __init__(self):
        load_dotenv()
        self.open_ai_client = os.getenv("OPEN_AI_KEY")
        config = configparser.ConfigParser()
        config.read("./config.ini")
        self.save_path = config["DEFAULT"].get("DOWNLOAD_PATH", "downloads")
        os.makedirs(self.save_path, exist_ok=True)
        self.spinner = Spinner()

    def fetch_song_metadata(self, url):
        try:
            fetcher = SongMetadataFetcher(openai_key = self.open_ai_client)
            metadata = fetcher.get_complete_metadata(url)
            return metadata
        except Exception as e:
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

            metadata = None
            cover_image_data = None
            downloaded_file = None

            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    metadata_future = executor.submit(self.fetch_song_metadata, url)

                    with YoutubeDL(options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        print()

                self.spinner.stop()

                raw_title = info['title']
                ext = info.get('ext', 'm4a')
                old_path = os.path.join(self.save_path, f"audio.{ext}")

                metadata = metadata_future.result(timeout=20)

                sanitized_title = self.modifyTitle(raw_title)
                filename = self.modifyTitle(metadata.get('title', sanitized_title)) if metadata else sanitized_title
                new_path = os.path.join(self.save_path, f"{filename}.{ext}")

                try:
                    if new_path != old_path:
                        os.rename(old_path, new_path)
                except Exception as e:
                    print(f"Warning: Could not rename file: {e}")
                    new_path = old_path  # fallback

                # Fetch cover in parallel as well
                if metadata and 'cover_image_url' in metadata:
                    cover_image_data = self.fetch_cover_image(metadata['cover_image_url'])

                print("\rDownload completed! File saved in:", new_path)
                downloaded_file = new_path

            except Exception as e:
                self.spinner.stop()
                print("An error occurred during downloading:", e)

            return downloaded_file, metadata, cover_image_data

    def modifyTitle(self,title):
        return re.sub(r'[<>:"/\\|?*]', '', title)
    
    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            self.spinner.stop()
            print(f"\rDownloading Audio : {d['_percent_str']} | Speed: {d['_speed_str']}", end="")
        elif d['status'] == 'finished':
            print("\nDownload finished, converting file...",end='')


    def add_metadata_and_coverimage(self, input_file, cover_image_data, metadata=None):
        if not input_file.endswith(".m4a"):
            print(f"Input file {input_file} is not in M4A format.")
            return
        try:
            audio = MP4(input_file)
            if audio.tags is None:
                audio.add_tags()

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
                    audio["aART"] = metadata['album_artist']
                if 'composer' in metadata:
                    audio["\xa9wrt"] = metadata['composer']
                if 'disk_number' in metadata:
                    audio["disk"] = metadata['disk_number']

            if cover_image_data:
                from mutagen.mp4 import MP4Cover
                audio["covr"] = [MP4Cover(cover_image_data, imageformat=MP4Cover.FORMAT_JPEG)]

            audio.save()

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

