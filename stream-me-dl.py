import argparse
import json
import os
import requests
import re
import shutil
import tempfile
from time import sleep
from videos import SourceVideo, CompressedVideo
import sys


def main():
    # define args
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='vod archive url')
    parser.add_argument('-l', '--list', help='list available encodings and exit', action='store_true')
    parser.add_argument('-q', '--quality', help='define which quality of video to download', metavar='#', default=1)
    args = parser.parse_args()

    context = get_context(args.url)
    title_slug = context['vod']['titleSlug']
    manifest_url = context['vod']['_links']['manifest']['href']
    response = requests.get(manifest_url)
    manifest = json.loads(response.text)

    if args.list:
        videos = get_encodings(title_slug, manifest)
        print_qualities(videos)
        sys.exit(0)

    if args.list and args.quality:
        raise Exception('Invalid option combination')

    if args.quality:

        if type(args.quality) is str and args.quality.upper() == 'S':
            video = get_source(title_slug, manifest)
            download_source(video)

        elif args.quality:
            videos = get_encodings(title_slug, manifest)
            try:
                video = videos[int(args.quality) - 1]
            except IndexError:
                raise Exception('Selected quality doesn''t exist')
            ts_urls = get_ts_urls(video.m3u8_location)
            temp_dir = tempfile.TemporaryDirectory()
            print(f'Downloading {video.title}')
            out_files = download_ts_files(temp_dir, ts_urls)
            print('Merging files')
            merge_ts(out_files, video.title)
            temp_dir.cleanup()

    print('Done!')


def download_source(video):
    print(f'Downloading {video.title}')
    response = requests.get(video.location)
    with open(video.title, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


def print_qualities(videos):
    print(f'S - Source')
    for i, video in enumerate(videos):
        print(f'{i + 1} - {video.width}x{video.height}')


def get_source(title, manifest):
    source = manifest['formats']['mp4-http']
    video = SourceVideo(title, source['videoCodec'], source['audioCodec'], source['origin']['location'])
    return video


def get_encodings(title, manifest):
    videos = []
    compressed = manifest['formats']['mp4-hls']
    video_codec = compressed['videoCodec']
    audio_codec = compressed['audioCodec']
    for encoding in compressed['encodings']:
        video_width = encoding['videoWidth']
        video_height = encoding['videoHeight']
        video_kbps = encoding['videoKbps']
        audio_kbps = encoding['audioKbps']
        m3u8_location = encoding['location']
        video = CompressedVideo(title, video_codec, audio_codec, video_width, video_height, video_kbps, audio_kbps,
                                m3u8_location)
        videos.append(video)
    return videos


def get_context(url):
    response = requests.get(url)
    text = response.text.replace('\n', '').replace('\t', '')
    match = re.search('<script>__context\s=\s(.*);</script>', text)
    if match:
        context = match.group(1)
    else:
        raise Exception('Failed to find context')
    return json.loads(context)


def download_ts_files(temp_dir, ts_urls):
    out_files = []
    i = 0
    while i < len(ts_urls):
        try:
            print(f'Downloading part {i + 1} of {len(ts_urls)}', end='\r')
            response = requests.get(ts_urls[i])
            out_file = os.path.join(temp_dir.name, str(i) + '.ts')
            with open(out_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            out_files.append(out_file)
            i += 1

        except requests.ConnectionError:
            print('')
            print(f'Failed to download part {i + 1} of {len(ts_urls)}')
            print(f'Retrying download')
            sleep(3)
    print('')
    return out_files


def get_ts_urls(m3u8_url):
    response = requests.get(m3u8_url)
    ts_files = []
    for line in response.text.splitlines():
        if line.endswith('.ts'):
            ts_files.append(line)
    return ts_files


def merge_ts(ts_list, out_file, out_dir=None):
    if not out_dir:
        out_dir = os.getcwd()
    with open(os.path.join(out_dir, out_file), 'wb') as merged:
        for ts_file in ts_list:
            with open(ts_file, 'rb') as merged_file:
                shutil.copyfileobj(merged_file, merged)


if __name__ == "__main__":
    main()
