# Stream.me VOD Downloader
A script to download Stream.me VODs.

## Requirements

[Python 3.6+](http://python.org)  

## Usage

Show help
```console
$ python3 stream-me-dl.py -h 
usage: stream-me-dl.py [-h] [-l] [-q] url

positional arguments:
  url            vod archive url

optional arguments:
  -h, --help     show this help message and exit
  -l, --list     list available encodings
  -q, --quality  define which quality of video to download

```

Download highest quality compressed video available (quality '1')
```console
$ python3 stream-me-dl.py https://www.stream.me/archive/username/video_title/vod_id
```
List available video qualities
```console
$ python3 stream-me-dl.py -l https://www.stream.me/archive/username/video_title/vod_id

0 - Source - 5422.16 MB
1 - 854x480 - ~1578.18 MB
2 - 370x208 - ~215.99 MB
```
Download second listed quality
```console
$ python3 stream-me-dl.py -q 2 https://www.stream.me/archive/username/video_title/vod_id
```