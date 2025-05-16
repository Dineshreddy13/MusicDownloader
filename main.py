import time
from components.SongDownload import MusicDownloader

def main():
    songs= []
    downloader = MusicDownloader()
    if(len(songs) == 0):
        video_url = input("Enter the YouTube video URL: ").strip()
        songs = video_url.split(" ")
    for i in songs:
        downloader.process(i)
        time.sleep(1)


if __name__ == "__main__":
    main()