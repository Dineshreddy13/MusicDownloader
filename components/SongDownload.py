import os
import concurrent
import requests
import time
import re
from yt_dlp import YoutubeDL
import configparser
from components.SongInfo import AudioInspector
from components.UiTools import Spinner
from components.MetadataExtractor import SongMetadataFetcher
from components.UiTools import QuietLogger
from mutagen.mp4 import MP4
from mutagen.id3 import APIC, TIT2, TPE1, TALB, TCON, TDRC, TRCK, TPE2


class MusicDownloader:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read("./config.ini")
        self.save_path = config["DEFAULT"].get("DOWNLOAD_PATH", "downloads")
        os.makedirs(self.save_path, exist_ok=True)
        self.spinner = Spinner()

    def fetch_song_metadata(self, url):
        try:
            fetcher = SongMetadataFetcher()
            metadata = fetcher.get_complete_metadata(url)
            return metadata
        except Exception as e:
            return None

    def downloadAudio(self, url):
        self.spinner.start()
        base_options = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'outtmpl': os.path.join(self.save_path, '%(id)s.%(ext)s'),
            'logger': QuietLogger(),
        }

        downloaded_files = []
        all_metadata = []

        try:
            with YoutubeDL(base_options) as ydl:
                info = ydl.extract_info(url, download=False)  # only structure

            # Handle single vs playlist
            if "entries" in info:
                entries = info["entries"]
            else:
                entries = [info]

            def process_entry(entry):
                video_url = entry["webpage_url"]

                # Run metadata fetch in parallel
                with concurrent.futures.ThreadPoolExecutor() as meta_executor:
                    meta_future = meta_executor.submit(self.fetch_song_metadata, video_url)

                    # Step 2: download this entry
                    with YoutubeDL(base_options) as ydl:
                        entry_info = ydl.extract_info(video_url, download=True)

                    raw_title = entry_info['title']
                    ext = entry_info.get('ext', 'm4a')
                    song_id = entry_info['id']
                    old_path = os.path.join(self.save_path, f"{song_id}.{ext}")

                    # Wait for metadata result (download + metadata now overlap in time)
                    metadata = None
                    try:
                        metadata = meta_future.result(timeout=20)
                    except Exception as e:
                        print(f"⚠️ Metadata fetch failed for {video_url}: {e}")

                    # Step 3: sanitize + rename
                    safe_title = self.modifyTitle(raw_title)
                    final_name = safe_title
                    if metadata and 'title' in metadata:
                        final_name = self.modifyTitle(metadata['title'])

                    new_path = os.path.join(self.save_path, f"{final_name}.{ext}")

                    try:
                        if old_path != new_path:
                            os.rename(old_path, new_path)
                    except Exception as e:
                        print(f"Could not rename {old_path} → {new_path}: {e}")
                        new_path = old_path

                    # Step 4: cover image
                    cover_image_data = None
                    if metadata and 'cover_image_url' in metadata:
                        cover_image_data = self.fetch_cover_image(metadata['cover_image_url'])

                    # Step 5: embed metadata
                    self.add_metadata_and_coverimage(new_path, cover_image_data, metadata=metadata)
                    
                    print("\r\033[92mDownloaded: \033[0m", end="")

                    print(f"\033[94m{metadata['title']}.\033[0m")
                    return new_path, metadata

            # Step 6: run all songs in parallel
            if len(entries) > 1:
                print(f"\rDownloading songs from -> ({info.get('title')})")
            else:
                print("\rDownloading Song:")
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(process_entry, entries))

            for file_path, metadata in results:
                if file_path:
                    downloaded_files.append(file_path)
                    all_metadata.append(metadata)
            self.spinner.stop()


        except Exception as e:
            self.spinner.stop()
            print("An error occurred during downloading:", e)

        return downloaded_files, all_metadata


    def modifyTitle(self,title):
        return re.sub(r'[<>:"/\\|?*]', '', title)
    

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

            if cover_image_data:
                from mutagen.mp4 import MP4Cover
                audio["covr"] = [MP4Cover(cover_image_data, imageformat=MP4Cover.FORMAT_JPEG)]

            audio.save()

        except Exception as e:
            print("Error updating the audio file with metadata and cover image :", e)


    def fetch_cover_image(self, url):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Failed to fetch cover image: {e}")
            return None

    def process(self, video_url):
        start = time.time()
        downloaded_files, all_metadata = self.downloadAudio(video_url)

        if downloaded_files:
            print("\r\nDownload Summary:")
            for i, f in enumerate(downloaded_files, 1):
                meta_title = all_metadata[i-1].get("title") if all_metadata[i-1] else None
                display_name = meta_title if meta_title else os.path.basename(f)
                print(f"{i:02d}. {display_name} -> {f}")
                AudioInspector(f).display_properties()

        end = time.time()
        elapsed = round(end - start)
        print("Elapsed time : ", elapsed//60 ,"min", elapsed%60, "sec")

