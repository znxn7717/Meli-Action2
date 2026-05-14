import sys
import os
import requests
from urllib.parse import urlparse, unquote
from moviepy.editor import VideoFileClip
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_filename_from_url(url, default_name="file.mp4"):
    path = urlparse(url).path
    filename = os.path.basename(path)
    filename = unquote(filename)

    if not filename:
        filename = default_name

    return filename


def download_file(url, output_path):
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)


def convert_to_mp3(video_path, mp3_path):
    video = VideoFileClip(video_path)
    audio = video.audio

    if audio is None:
        raise ValueError(f"No audio stream found in: {video_path}")

    audio.write_audiofile(mp3_path)
    audio.close()
    video.close()


def process_url(url, index):
    print(f"\nProcessing URL {index}: {url}")

    filename = get_filename_from_url(url, default_name=f"video_{index}.mp4")
    base_name, _ = os.path.splitext(filename)

    video_path = os.path.join(DOWNLOAD_DIR, filename)
    mp3_path = os.path.join(DOWNLOAD_DIR, f"{base_name}.mp3")

    print(f"Downloading to: {video_path}")
    download_file(url, video_path)

    print(f"Converting to: {mp3_path}")
    convert_to_mp3(video_path, mp3_path)

    print(f"Done: {mp3_path}")


def main():
    urls = [arg.strip() for arg in sys.argv[1:] if arg.strip()]

    if not urls:
        raise ValueError("At least one video URL is required.")

    for i, url in enumerate(urls, start=1):
        try:
            process_url(url, i)
        except Exception as e:
            print(f"Failed for URL {i}: {url}")
            print(f"Error: {e}")


if __name__ == "__main__":
    main()
