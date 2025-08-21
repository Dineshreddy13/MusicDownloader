import time
from components.SongDownload import MusicDownloader

def main():
    songs= []
    start = time.time()
    downloader = MusicDownloader()
    if(len(songs) == 0):
        video_url = input("Enter the YouTube video URL: ").strip()
        songs = video_url.split(" ")
    for i in songs:
        downloader.process(i)
    end = time.time()
    elapsed = end - start
    min = int(elapsed // 60)
    sec = int(elapsed % 60)
    print("Elapsed Time: ", min, "min", sec, "sec")
if __name__ == "__main__":
    main()
