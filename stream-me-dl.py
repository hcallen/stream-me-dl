import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.request


def main():
    # define args
    # TODO: add out dir
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='vod archive url')
    parser.add_argument('-l', '--list', help='list available encodings and exit', action='store_true')
    parser.add_argument('-q', '--quality', help='define which quality of video to download', type=int, metavar='#',
                        default=1)
    args = parser.parse_args()

    # parse html
    context = get_context(args.url)
    title_slug = context['vod']['titleSlug']
    user_slug = context['vod']['userSlug']
    manifest_url = context['vod']['_links']['manifest']['href']
    manifest_r = urllib.request.urlopen(manifest_url)
    manifest_read = manifest_r.read().decode('utf-8')
    manifest = json.loads(manifest_read)

    videos = get_videos(user_slug, title_slug, manifest)

    if args.list:
        print_qualities(videos)
        sys.exit(0)

    if args.quality > len(videos) or args.quality < 0:
        raise Exception('Selected quality doesn\'t exist')

    # download video
    try:
        video = videos[args.quality]
    except IndexError:
        video = videos[0]
    video.download()
    sys.exit(0)


def get_context(url):
    response = urllib.request.urlopen(url)
    html = response.read().decode('utf-8')
    text = html.replace('\n', '').replace('\t', '')
    match = re.search('<script>__context\s=\s(.*);</script>', text)
    if not match:
        raise Exception('Failed to find context')
    context = match.group(1)
    return json.loads(context)


def get_videos(user, title, manifest):
    videos = []

    # add source
    source = manifest['formats']['mp4-http']
    source_video = SourceVideo(user, title, source['videoCodec'], source['audioCodec'], source['origin']['location'])
    videos.append(source_video)

    # add compressed
    if 'mp4-hls' in manifest['formats'].keys():
        compressed = manifest['formats']['mp4-hls']
        video_codec = compressed['videoCodec']
        audio_codec = compressed['audioCodec']
        for encoding in compressed['encodings']:
            video_width = encoding['videoWidth']
            video_height = encoding['videoHeight']
            video_kbps = encoding['videoKbps']
            audio_kbps = encoding['audioKbps']
            m3u8_location = encoding['location']
            compressed_video = CompressedVideo(user, title, video_codec, audio_codec, video_width, video_height,
                                               video_kbps,
                                               audio_kbps, m3u8_location)
            videos.append(compressed_video)
    return videos


def print_qualities(videos):
    # source
    print(f'0 - Source - {videos[0].size:0.2f} MB')
    # compressed videos
    for i, video in enumerate(videos[1:]):
        print(f'{i + 1} - {video.width}x{video.height} - ~{video.size:0.2f} MB')


class Video(object):
    def __init__(self, user_slug, title_slug, video_codec, audio_codec):
        self.user_slug = user_slug
        self.title_slug = title_slug
        self.video_codec = video_codec
        self.audio_codec = audio_codec


class SourceVideo(Video):

    def __init__(self, user_slug, title_slug, video_codec, audio_codec, location):
        Video.__init__(self, user_slug, title_slug, video_codec, audio_codec)
        self.location = location
        self.title = f'{self.user_slug}-{self.title_slug}-source.mp4'
        self._content_length = None
        self.size = self.content_length / 1000000

    def download(self, out_dir=None):
        if not out_dir:
            out_dir = os.getcwd()
        complete = 0
        out_file = os.path.join(out_dir, self.title)
        with open(out_file, 'wb') as f:
            try:
                response = urllib.request.urlopen(self.location)
                block_size = 1024
                while True:
                    buffer = response.read(block_size)
                    if not buffer:
                        break
                    complete += 1024
                    f.write(buffer)
                    percent = (complete / self.content_length) * 100
                    print(f'Downloading {self.title} - {percent:0.2f}%', end='\r')
            except ConnectionResetError:
                print(f'Download failed {self.title} - {percent:0.2f}%', end='\r')
                print('\nRetrying download')
        print('\nDone!')

    @property
    def content_length(self):
        if self._content_length:
            return self._content_length
        response = urllib.request.urlopen(self.location)
        self._content_length = int(response.getheader('Content-Length'))
        return self._content_length


class CompressedVideo(Video):

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

    def download(self, out_dir=None):
        if not out_dir:
            out_dir = os.getcwd()
        temp_dir = tempfile.TemporaryDirectory()
        ts_files = self._download_ts_files(temp_dir)
        self._merge_ts_files(ts_files, out_dir)
        temp_dir.cleanup()
        print('\nDone!')

    def _download_ts_files(self, temp_dir):
        out_files = []
        i = 0
        while i < len(self.ts_urls):
            percent = ((i + 1) / len(self.ts_urls)) * 100
            print(f'Downloading {self.title} - part {i + 1} of {len(self.ts_urls)} - {percent:0.2f}%', end='\r')
            out_file = os.path.join(temp_dir.name, str(i) + '.ts')
            block_size = 1024
            try:
                response = urllib.request.urlopen(self.ts_urls[i])
                with open(out_file, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                out_files.append(out_file)
                i += 1
            except ConnectionResetError:
                print(f'Failed to download {self.title} - part {i + 1} of '
                      f'{len(self.ts_urls)} - {percent:0.2f}%', end='\r')
                print('\nRetrying download')

        print('')
        return out_files

    def _merge_ts_files(self, ts_list, out_dir):
        with open(os.path.join(out_dir, self.title), 'wb') as merged:
            for i, ts_file in enumerate(ts_list):
                percent = ((i + 1) / len(ts_list) * 100)
                with open(ts_file, 'rb') as merged_file:
                    shutil.copyfileobj(merged_file, merged)
                print(f'Merging files - {percent:0.2f}%', end='\r')

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
        self._m3u8 = urllib.request.urlopen(self.m3u8_location).read().decode('utf-8')
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
        # convert to MBs
        self._size = (self.video_kbps + self.audio_kbps) * (self.duration / 60) * 0.0075
        return self._size


if __name__ == "__main__":
    main()
