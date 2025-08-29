from mutagen import File

class AudioInspector:
    def __init__(self, file_path):
        self.file_path = file_path
        self.audio = File(file_path)
        self.properties = {}

    def get_codec_name(self, info_class_name):
        codec_map = {
            "MP3Info": "MP3",
            "MP4Info": "M4A",
            "FLACInfo": "FLAC",
            "OggVorbisInfo": "OGG",
        }
        return codec_map.get(info_class_name, info_class_name)

    def analyze(self):
        if self.audio is None:
            print("❌ Unsupported or corrupted audio file.")
            return

        info = self.audio.info
        codec_class = type(info).__name__
        channel_count = getattr(info, 'channels', 'Unknown')
        channel_map = {1: "Mono", 2: "Stereo"}
        self.properties = {
            'codec': self.get_codec_name(codec_class),
            'bitrate': getattr(info, 'bitrate', 0) // 1000 if hasattr(info, 'bitrate') else 'Unknown',
            'channels': channel_map.get(channel_count, f"{channel_count} channels"),
            'sampling_rate': getattr(info, 'sample_rate', 'Unknown'),
            'bit_depth': getattr(info, 'bits_per_sample', 'Unknown') if hasattr(info, 'bits_per_sample') else 'N/A'
        }

    def display_properties(self):
        if not self.properties:
            self.analyze()

        print("🎧 Audio Details :")
        print("Codec          :", self.properties.get('codec', 'Unknown'))
        print("Bitrate        :", self.properties.get('bitrate', 'Unknown'), "kb/s")
        print("Channels       :", self.properties.get('channels', 'Unknown'))
        print("Sampling Rate  :", self.properties.get('sampling_rate', 'Unknown'), "Hz")
        print("Bit Depth      :", self.properties.get('bit_depth', 'N/A'))
