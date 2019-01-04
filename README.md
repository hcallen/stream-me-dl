# Stream.me VOD Downloader
A script to download Stream.me VODs.

## Requirements

[Python 3.6+](python.org)  
[Requests](http://docs.python-requests.org/en/master/)

## Usage
```console

# Download highest quality compressed video available
$ python3 stream-me-dl.py https://www.stream.me/archive/username/video_title/vod_id

# List available video qualities
$ python3 stream-me-dl.py --l https://www.stream.me/archive/username/video_title/vod_id

S - Source
1 - 854x480
2 - 370x208

# Download second listed quality
$ python3 stream-me-dl.py -q 2 https://www.stream.me/archive/username/video_title/vod_id

# Download source quality
$ python3 stream-me-dl.py -q S https://www.stream.me/archive/username/video_title/vod_id

```