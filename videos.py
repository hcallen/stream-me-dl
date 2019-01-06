import requests
import re

class Video(object):
    def __init__(self, slug, video_codec, audio_codec):
        self.slug = slug
        self.video_codec = video_codec
        self.audio_codec = audio_codec



class SourceVideo(Video):
    source = True

    def __init__(self, slug, video_codec, audio_codec, location):
        Video.__init__(self, slug, video_codec, audio_codec)
        self.location = location
        self.title = f'{self.slug}_source.mp4'
        self._size = None

    @property
    def size(self):
        if self._size:
            return self._size
        content_length = requests.head(self.location).headers['Content-length']
        self._size = int(content_length)
        return self._size


class CompressedVideo(Video):
    source = False

    def __init__(self, slug, video_codec, audio_codec, video_width, video_height, video_kbps, audio_kbps,
                 m3u8_location):
        Video.__init__(self, slug, video_codec, audio_codec)
        self.width = video_width
        self.height = video_height
        self.video_kbps = video_kbps
        self.audio_kbps = audio_kbps
        self.m3u8_location = m3u8_location
        self.title = f'{self.slug}_{self.width}x{self.height}.mp4'
        self.ts_urls = self.get_ts_urls(self.m3u8_location)
        self.size = None

    @staticmethod
    def get_ts_urls(m3u8_location):
        response = requests.get(m3u8_location)
        ts_files = []
        for line in response.text.splitlines():
            if line.endswith('.ts'):
                ts_files.append(line)
        return ts_files

