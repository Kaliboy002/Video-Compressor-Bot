import os
import subprocess
import threading
from pyrogram import Client, filters
from pyrogram.types import Message

# Setup
bot_token = os.environ.get("TOKEN", "")
api_id = os.environ.get("ID", "")
api_hash = os.environ.get("HASH", "")
app = Client("video_compressor_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Start Command
@app.on_message(filters.command("start"))
def start(client, message: Message):
    message.reply_text(
        f"Hello {message.from_user.first_name}! 👋\n"
        "Send me a video, and I'll compress it for you."
    )

# Progress Tracker
def progress(current, total, message: Message, task: str):
    percent = current * 100 / total
    try:
        message.edit_text(f"{task}: {percent:.2f}%")
    except:
        pass

# Compression Function
def compress_video(input_file, output_file, crf=28):
    cmd = [
        "./ffmpeg/ffmpeg",
        "-i", input_file,
        "-c:v", "libx265",
        "-preset", "medium",
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "128k",
        output_file
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Handler for Video Files
@app.on_message(filters.video | filters.document)
def handle_video(client, message: Message):
    if message.video or (message.document and "video" in message.document.mime_type):
        # Start download
        msg = message.reply_text("Downloading...")
        file_path = app.download_media(message, progress=progress, progress_args=(msg, "Downloading"))

        # Compress video
        msg.edit_text("Compressing...")
        output_path = f"compressed-{message.id}.mp4"
        compress_video(file_path, output_path)

        # Check if compression succeeded
        if os.path.exists(output_path):
            msg.edit_text("Uploading...")
            app.send_document(
                message.chat.id,
                output_path,
                caption="Here is your compressed video!",
                reply_to_message_id=message.id
            )
            os.remove(output_path)
        else:
            msg.edit_text("❌ Compression failed. Check FFmpeg logs.")
        
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
    else:
        message.reply_text("Please send a valid video file.")

# Run the Bot
app.run()
