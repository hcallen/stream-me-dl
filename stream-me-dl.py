import argparse
import json
import re
import urllib.request
from videos import SourceVideo, CompressedVideo
import sys


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
    video = videos[args.quality]
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


if __name__ == "__main__":
    main()
