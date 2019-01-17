import argparse
import json
import os
import re
import shutil
import tempfile
import urllib.request
from videos import SourceVideo, CompressedVideo
import sys


def main():
    # define args
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='vod archive url')
    parser.add_argument('-l', '--list', help='list available encodings and exit', action='store_true')
    parser.add_argument('-q', '--quality', help='define which quality of video to download', type=int, metavar='#',
                        default=1)
    args = parser.parse_args()

    context = get_context(args.url)
    title_slug = context['vod']['titleSlug']
    user_slug = context['vod']['userSlug']
    manifest_url = context['vod']['_links']['manifest']['href']
    manifest_r = urllib.request.urlopen(manifest_url)
    manifest = manifest_r.read().decode('utf-8')
    manifest = json.loads(manifest)

    if args.list:
        videos = get_videos(user_slug, title_slug, manifest)
        print_qualities(videos)
        sys.exit(0)

    if args.list and args.quality:
        raise Exception('Invalid option combination')

    if args.quality >= 0:
        videos = get_videos(user_slug, title_slug, manifest)
        if args.quality == 0:
            download_source(videos[0])
            print('\nDone!')
        else:
            try:
                video = videos[args.quality]
            except IndexError:
                raise Exception('Selected quality doesn''t exist')

            # download compressed video
            temp_dir = tempfile.TemporaryDirectory()
            out_files = download_ts_files(temp_dir, video)
            merge_ts(out_files, video.title)
            temp_dir.cleanup()
            print('\nDone!')
    else:
        raise Exception('Selected quality doesn''t exist')


def download_source(video):
    complete = 0
    with open(video.title, 'wb') as f:
        response = urllib.request.urlopen(video.location)
        block_size = 1024
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break
            complete += 1024
            f.write(buffer)
            percent = (complete / video.content_length) * 100
            print(f'Downloading {video.title} - {percent:0.2f}%', end='\r')


def print_qualities(videos):
    # sources
    print(f'0 - Source - {videos[0].size:0.2f} MB')
    # compressed videos
    for i, video in enumerate(videos[1:]):
        print(f'{i + 1} - {video.width}x{video.height} - ~{video.size:0.2f} MB')


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
            compressed_video = CompressedVideo(user, title, video_codec, audio_codec, video_width, video_height, video_kbps,
                                               audio_kbps, m3u8_location)
            videos.append(compressed_video)
    return videos


def get_context(url):
    response = urllib.request.urlopen(url)
    html = response.read().decode('utf-8')
    text = html.replace('\n', '').replace('\t', '')
    match = re.search('<script>__context\s=\s(.*);</script>', text)
    if match:
        context = match.group(1)
    else:
        raise Exception('Failed to find context')
    return json.loads(context)


def download_ts_files(temp_dir, video):
    out_files = []
    i = 0
    while i < len(video.ts_urls):
        percent = ((i + 1) / len(video.ts_urls)) * 100
        print(f'Downloading {video.title} - part {i + 1} of {len(video.ts_urls)} - {percent:0.2f}%', end='\r')
        out_file = os.path.join(temp_dir.name, str(i) + '.ts')
        block_size = 1024
        response = urllib.request.urlopen(video.ts_urls[i])
        with open(out_file, 'wb') as f:
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                f.write(buffer)
        out_files.append(out_file)
        i += 1

    print('')
    return out_files


def merge_ts(ts_list, out_file, out_dir=None):
    if not out_dir:
        out_dir = os.getcwd()
    with open(os.path.join(out_dir, out_file), 'wb') as merged:
        for i, ts_file in enumerate(ts_list):
            percent = ((i + 1) / len(ts_list) * 100)
            with open(ts_file, 'rb') as merged_file:
                shutil.copyfileobj(merged_file, merged)
            print(f'Merging files - {percent:0.2f}%', end='\r')


if __name__ == "__main__":
    main()
