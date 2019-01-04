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
        self.title = f'{self.slug}_source.ts'


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
        self.title = f'{self.slug}_{self.width}x{self.height}.ts'
