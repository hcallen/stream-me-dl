import requests
import re


class Video(object):
    def __init__(self, user_slug, title_slug, video_codec, audio_codec):
        self.user_slug = user_slug
        self.title_slug = title_slug
        self.video_codec = video_codec
        self.audio_codec = audio_codec


class SourceVideo(Video):
    source = True

    def __init__(self, user_slug, title_slug, video_codec, audio_codec, location):
        Video.__init__(self, user_slug, title_slug, video_codec, audio_codec)
        self.location = location
        self.title = f'{self.user_slug}-{self.title_slug}-source.mp4'
        self._size = None

    @property
    def size(self):
        if self._size:
            return self._size
        content_length = requests.head(self.location).headers['Content-length']
        # convert to MBs
        self._size = int(content_length) / 1000000
        return self._size


class CompressedVideo(Video):
    source = False

    def __init__(self, user_slug, title_slug, video_codec, audio_codec, video_width, video_height, video_kbps,
                 audio_kbps, m3u8_location):
        Video.__init__(self, user_slug, title_slug, video_codec, audio_codec)
        self.width = video_width
        self.height = video_height
        self.video_kbps = video_kbps
        self.audio_kbps = audio_kbps
        self.m3u8_location = m3u8_location
        self.title = f'{self.user_slug}-{self.title_slug}-{self.width}x{self.height}.mp4'
        self._ts_urls = None
        self._duration = None
        self._m3u8 = None
        self._size = None

    @property
    def ts_urls(self):
        if self._ts_urls:
            return self._ts_urls
        self._ts_urls = []
        for line in self.m3u8.splitlines():
            if line.endswith('.ts'):
                self._ts_urls.append(line)
        return self._ts_urls

    @property
    def m3u8(self):
        if self._m3u8:
            return self._m3u8
        self._m3u8 = requests.get(self.m3u8_location).text
        return self._m3u8

    @property
    def duration(self):
        if self._duration:
            return self._duration
        self._duration = 0
        for line in self.m3u8.splitlines():
            match = re.search('^#EXTINF:(\d*.\d*),', line)
            if match:
                self._duration += float(match.group(1))
        return self._duration

    @property
    def size(self):
        if self._size:
            return self._size
        # minutes
        min = self.duration / 60
        # convert to MBs
        self._size = (self.video_kbps + self.audio_kbps) * min * 0.0075
        return self._size
