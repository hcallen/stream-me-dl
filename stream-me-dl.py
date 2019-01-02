import json
import os
import requests
import re
import shutil
import sys
import tempfile
from videos import SourceVideo, CompressedVideo


def main():
    vod_url = sys.argv[1]
    context = get_context(vod_url)
    title_slug = context['vod']['titleSlug']
    manifest_url = context['vod']['_links']['manifest']['href']
    manifest_response = requests.get(manifest_url)
    manifest = json.loads(manifest_response.text)
    videos = get_videos(title_slug, manifest)
    ts_urls = get_ts_urls(videos[1].m3u8_location)
    temp_dir = tempfile.TemporaryDirectory()
    out_files = download_ts_files(temp_dir, ts_urls)
    merge_ts(out_files, title_slug + '.ts')
    temp_dir.cleanup()
    print('Done!')


def get_videos(title, manifest):
    videos = []

    # append source
    source = manifest['formats']['mp4-http']
    video = SourceVideo(title, source['videoCodec'], source['audioCodec'], source['origin']['location'])
    videos.append(video)

    # append compressed videos
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
    for i, url in enumerate(ts_urls):
        print(f'Downloading part {i + 1} of {len(ts_urls)}')
        response = requests.get(url)
        out_file = os.path.join(temp_dir.name, str(i) + '.ts')
        with open(out_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        out_files.append(out_file)
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
    print('Merging files...')
    with open(os.path.join(out_dir, out_file), 'wb') as merged:
        for ts_file in ts_list:
            with open(ts_file, 'rb') as mergefile:
                shutil.copyfileobj(mergefile, merged)


if __name__ == "__main__":
    main()
