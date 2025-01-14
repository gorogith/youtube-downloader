#!/data/data/com.termux/files/usr/bin/bash

# Update package list
pkg update -y

# Install required packages
pkg install -y python ffmpeg

# Install pip if not already installed
pkg install -y python-pip

# Install required Python packages
pip install yt-dlp

echo "Setup completed! You can now run the YouTube downloader."
