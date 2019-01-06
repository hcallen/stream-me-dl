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
    parser.add_argument('-q', '--quality', help='define which quality of video to download', type=int, metavar='#',
                        default=1)
    args = parser.parse_args()

    context = get_context(args.url)
    title_slug = context['vod']['titleSlug']
    manifest_url = context['vod']['_links']['manifest']['href']
    response = requests.get(manifest_url)
    manifest = json.loads(response.text)

    if args.list:
        videos = get_videos(title_slug, manifest)
        print_qualities(videos)
        sys.exit(0)

    if args.list and args.quality:
        raise Exception('Invalid option combination')

    if args.quality >= 0:
        videos = get_videos(title_slug, manifest)
        if args.quality == 0:
            download_source(videos[0])
            print('Done!')
        else:
            try:
                video = videos[args.quality]
            except IndexError:
                raise Exception('Selected quality doesn''t exist')
            download_compressed(video)
            print('Done!')
    else:
        raise Exception('Selected quality doesn''t exist')


def download_source(video):
    print(f'Downloading {video.title}')
    response = requests.get(video.location)
    with open(video.title, 'wb') as f:
        complete = 0
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                complete += 1024
                f.write(chunk)


def download_compressed(video):
    temp_dir = tempfile.TemporaryDirectory()
    out_files = download_ts_files(temp_dir, video)
    merge_ts(out_files, video.title)
    temp_dir.cleanup()


def get_mb_str(size):
    mbs = size / 1000000
    return f'{mbs:0.2f} MB'


def print_qualities(videos):
    # sources
    print('0 - Source')
    # compressed videos
    for i, video in enumerate(videos[1:]):
        print(f'{i + 1} - {video.width}x{video.height}')


def get_videos(title, manifest):
    videos = []

    # add source
    source = manifest['formats']['mp4-http']
    source_video = SourceVideo(title, source['videoCodec'], source['audioCodec'], source['origin']['location'])
    videos.append(source_video)

    # add compressed
    compressed = manifest['formats']['mp4-hls']
    video_codec = compressed['videoCodec']
    audio_codec = compressed['audioCodec']
    for encoding in compressed['encodings']:
        video_width = encoding['videoWidth']
        video_height = encoding['videoHeight']
        video_kbps = encoding['videoKbps']
        audio_kbps = encoding['audioKbps']
        m3u8_location = encoding['location']
        compressed_video = CompressedVideo(title, video_codec, audio_codec, video_width, video_height, video_kbps,
                                           audio_kbps,
                                           m3u8_location)
        videos.append(compressed_video)
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


def download_ts_files(temp_dir, video):
    print(f'Downloading {video.title}')
    out_files = []
    i = 0
    while i < len(video.ts_urls):
        try:
            percent = ((i + 1) / len(video.ts_urls)) * 100
            print(f'Downloading part {i + 1} of {len(video.ts_urls)} - {percent:0.2f}% Complete', end='\r')
            response = requests.get(video.ts_urls[i])
            out_file = os.path.join(temp_dir.name, str(i) + '.ts')
            with open(out_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            out_files.append(out_file)
            i += 1

        except requests.ConnectionError:
            print('')
            print(f'Failed to download part {i + 1} of {len(video.ts_urls)}')
            print(f'Retrying download')
            sleep(3)
    print('')
    return out_files


def merge_ts(ts_list, out_file, out_dir=None):
    print('Merging files')
    if not out_dir:
        out_dir = os.getcwd()
    with open(os.path.join(out_dir, out_file), 'wb') as merged:
        for ts_file in ts_list:
            with open(ts_file, 'rb') as merged_file:
                shutil.copyfileobj(merged_file, merged)


def get_length(m3u8_location):
    response = requests.get(m3u8_location)
    length = 0
    for line in response.text.splitlines():
        match = re.search('^#EXTINF:(\d*.\d*),', line)
        if match:
            length += float(match.group(1))
    return length


if __name__ == "__main__":
    main()
