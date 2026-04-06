#!/bin/bash
# Batch Instagram Video Downloader
# Install yt-dlp first: pip install yt-dlp

mkdir -p downloads
cd downloads

echo "🚀 Starting Instagram video downloads..."

echo "Downloading DRt0DAPEcv1..."
/Users/ariankalantari/senpai-reel/venv/bin/python -m yt_dlp "https://www.instagram.com/p/DRt0DAPEcv1/" -o "DRt0DAPEcv1.%(ext)s"
echo "✅ Done: DRt0DAPEcv1"

echo "🎉 All downloads complete!"
