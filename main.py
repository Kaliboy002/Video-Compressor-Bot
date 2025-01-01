import os
import threading
import time
from pyrogram import Client, filters
from pyrogram.types import Message
import subprocess

# Bot Setup
bot_token = os.environ.get("TOKEN", "")
api_hash = os.environ.get("HASH", "")
api_id = os.environ.get("ID", "")
app = Client("video_compressor_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Ensure ffmpeg permissions
os.system("chmod +x ./ffmpeg/ffmpeg")

# Start Command
@app.on_message(filters.command(["start"]))
def start_command(client, message: Message):
    app.send_message(
        message.chat.id,
        f"**Welcome, {message.from_user.mention}!**\n"
        f"__Send me a video file, and I'll compress it for you.__\n"
        f"**Note:** This bot works best for videos up to ~2GB (Railway limitations apply)."
    )

# Progress Writer
def progress_callback(current, total, message, stage):
    progress = f"{(current / total) * 100:.1f}%"
    with open(f"{message.id}_{stage}_progress.txt", "w") as f:
        f.write(progress)

# Status Update Thread
def update_status(file_path, message, prefix):
    while not os.path.exists(file_path):
        time.sleep(1)
    while os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                progress = f.read()
            app.edit_message_text(message.chat.id, message.id, f"{prefix}: **{progress}**")
        except:
            pass
        time.sleep(5)

# Compress Video
def compress_video(message, status_msg):
    try:
        # Downloading Video
        download_progress_file = f"{message.id}_download_progress.txt"
        download_thread = threading.Thread(
            target=update_status, args=(download_progress_file, status_msg, "Downloading"), daemon=True
        )
        download_thread.start()

        input_file = app.download_media(
            message,
            progress=progress_callback,
            progress_args=[message, "download"]
        )
        if not input_file:
            app.edit_message_text(message.chat.id, status_msg.id, "❌ Failed to download the video.")
            return

        # Remove Download Progress File
        if os.path.exists(download_progress_file):
            os.remove(download_progress_file)

        # Compressing Video
        app.edit_message_text(message.chat.id, status_msg.id, "⚙️ Compressing the video...")
        output_file = f"compressed-{message.id}.mp4"

        # Adjusted for older FFmpeg versions
        ffmpeg_command = [
            "./ffmpeg/ffmpeg",
            "-i", input_file,
            "-c:v", "libx264",  # libx264 for compatibility
            "-preset", "medium",  # Standard preset
            "-crf", "28",  # Compression level
            "-c:a", "aac",  # Audio codec
            output_file
        ]

        process = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode != 0 or not os.path.exists(output_file):
            app.edit_message_text(message.chat.id, status_msg.id, "❌ Compression failed.")
            return

        # Remove Original File to Save Space
        os.remove(input_file)

        # Uploading Video
        upload_progress_file = f"{message.id}_upload_progress.txt"
        upload_thread = threading.Thread(
            target=update_status, args=(upload_progress_file, status_msg, "Uploading"), daemon=True
        )
        upload_thread.start()

        app.send_document(
            message.chat.id,
            document=output_file,
            caption="✅ Video compressed successfully!",
            progress=progress_callback,
            progress_args=[message, "upload"],
            reply_to_message_id=message.id
        )

        # Cleanup
        if os.path.exists(upload_progress_file):
            os.remove(upload_progress_file)
        os.remove(output_file)

        app.delete_messages(message.chat.id, [status_msg.id])

    except Exception as e:
        app.edit_message_text(message.chat.id, status_msg.id, f"❌ Error: {str(e)}")
        return

# Document Handler
@app.on_message(filters.document)
def handle_document(client, message: Message):
    try:
        mime_type = message.document.mime_type
        if "video" in mime_type:
            status_msg = app.send_message(message.chat.id, "📥 Downloading...", reply_to_message_id=message.id)
            threading.Thread(target=compress_video, args=(message, status_msg), daemon=True).start()
        else:
            app.send_message(message.chat.id, "❌ Please send a valid video file.")
    except Exception as e:
        app.send_message(message.chat.id, f"❌ Error: {str(e)}")

# Video Handler
@app.on_message(filters.video)
def handle_video(client, message: Message):
    try:
        status_msg = app.send_message(message.chat.id, "📥 Downloading...", reply_to_message_id=message.id)
        threading.Thread(target=compress_video, args=(message, status_msg), daemon=True).start()
    except Exception as e:
        app.send_message(message.chat.id, f"❌ Error: {str(e)}")

# Run the Bot
app.run()
