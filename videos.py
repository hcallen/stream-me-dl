class Video(object):
    def __init__(self, title, video_codec, audio_codec):
        self.title = title
        self.video_codec = video_codec
        self.audio_codec = audio_codec


class SourceVideo(Video):
    compressed = False

    def __init__(self, title, video_codec, audio_codec, location):
        Video.__init__(self, title, video_codec, audio_codec)
        self.location = location


class CompressedVideo(Video):
    compressed = True

    def __init__(self, title, video_codec, audio_codec, video_width, video_height, video_kbps, audio_kbps,
                 m3u8_location):
        Video.__init__(self, title, video_codec, audio_codec)
        self.video_width = video_width
        self.video_height = video_height
        self.video_kbps = video_kbps
        self.audio_kbps = audio_kbps
        self.m3u8_location = m3u8_location
