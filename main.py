from components.SongDownload import MusicDownloader

def main():
    downloader = MusicDownloader()
    url = input("Enter the URL : ").strip()
    downloader.process(url)
if __name__ == "__main__":
    main()
