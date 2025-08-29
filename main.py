from components.SongDownload import MusicDownloader

def main():
    songs= []
    downloader = MusicDownloader()
    if(len(songs) == 0):
        video_url = input("Enter the URL: ").strip()
        songs = video_url.split(" ")
    for i in songs:
        downloader.process(i)
if __name__ == "__main__":
    main()
