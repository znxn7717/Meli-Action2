import sys
import os
import requests
from moviepy.editor import VideoFileClip

# گرفتن لینک از ورودی اکشن
video_url = sys.argv[1]

# ساخت پوشه downloads اگر وجود نداشت
os.makedirs("downloads", exist_ok=True)

# دانلود فایل
print("Downloading video...")
response = requests.get(video_url, stream=True)
video_path = "downloads/input.mp4"

with open(video_path, "wb") as f:
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            f.write(chunk)

print("Download complete.")

# تبدیل به mp3
print("Converting to mp3...")
video = VideoFileClip(video_path)
audio = video.audio
output_path = "downloads/output.mp3"
audio.write_audiofile(output_path)

print("Conversion complete.")
print(f"Saved to {output_path}")
