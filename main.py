import os
import logging
import tempfile
import threading
import time
from queue import Queue
from pyrogram import Client, filters
import pyrogram
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("VideoCompressorBot")

# Environment variables
bot_token = os.getenv("TOKEN", "")
api_hash = os.getenv("HASH", "")
api_id = os.getenv("ID", "")

# Initialize the bot
app = Client("video_compressor_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Check for FFmpeg binary
if not os.path.exists("./ffmpeg/ffmpeg"):
    raise FileNotFoundError("FFmpeg binary not found in the ./ffmpeg directory.")
os.system("chmod 777 ./ffmpeg/ffmpeg")

# Task queue for threading
task_queue = Queue()

# Worker function for task queue
def worker():
    while True:
        task = task_queue.get()
        if task is None:
            break
        try:
            task()
        except Exception as e:
            logger.error(f"Error processing task: {e}")
        task_queue.task_done()

# Start worker threads
for _ in range(8):  # Adjust based on server capacity
    threading.Thread(target=worker, daemon=True).start()

# Start command
@app.on_message(filters.command(["start"]))
def start_command(client, message: pyrogram.types.Message):
    app.send_message(
        message.chat.id,
        f"**Welcome, {message.from_user.first_name}!**\n\n"
        f"Send me a video, and I'll compress it for you with **high speed** and **best quality!**\n\n"
        "Note: Large files may take longer to process."
    )

# Progress tracker for downloads/uploads
def progress(current, total, message, stage):
    percentage = int((current / total) * 100)
    if percentage % 10 == 0:  # Update every 10%
        app.edit_message_text(
            message.chat.id, message.id,
            f"__{stage.capitalize()}__: **{percentage}%**"
        )

# Function to compress video
def compress_video(message, temp_dir, output_name):
    input_path = os.path.join(temp_dir, "input.mp4")
    output_path = os.path.join(temp_dir, output_name)
    cmd = (
        f"./ffmpeg/ffmpeg -i \"{input_path}\" "
        f"-c:v libx265 -preset ultrafast -crf 28 -c:a aac -b:a 128k \"{output_path}\""
    )
    logger.info(f"Running FFmpeg command: {cmd}")
    result = os.system(cmd)
    if result != 0 or not os.path.exists(output_path):
        raise RuntimeError("FFmpeg compression failed.")
    return output_path

# Compression task handler
def handle_compression(message: pyrogram.types.Message, msg: pyrogram.types.Message):
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            app.edit_message_text(message.chat.id, msg.id, "__Downloading video...__")
            
            # Download video
            input_file = app.download_media(
                message, file_name=os.path.join(temp_dir, "input.mp4"),
                progress=progress, progress_args=[message, "Downloading"]
            )
            if not input_file:
                raise RuntimeError("Video download failed.")
            
            app.edit_message_text(message.chat.id, msg.id, "__Compressing video...__")
            
            # Compress video
            compressed_file = compress_video(message, temp_dir, "compressed.mp4")
            
            app.edit_message_text(message.chat.id, msg.id, "__Uploading video...__")
            
            # Upload compressed video
            app.send_document(
                chat_id=message.chat.id,
                document=compressed_file,
                file_name=f"compressed_{os.path.basename(input_file)}",
                caption="✅ **Video successfully compressed!**",
                progress=progress, progress_args=[message, "Uploading"]
            )
            app.delete_messages(message.chat.id, [msg.id])
    except Exception as e:
        logger.error(f"Error in compression: {e}")
        app.edit_message_text(message.chat.id, msg.id, f"❌ **Error:** {str(e)}")

# Handle document uploads
@app.on_message(filters.document)
def document_handler(client, message: pyrogram.types.Message):
    if "video" in message.document.mime_type:
        msg = app.send_message(message.chat.id, "__Processing your video...__", reply_to_message_id=message.id)
        task_queue.put(lambda: handle_compression(message, msg))
    else:
        app.send_message(message.chat.id, "⚠️ **Please send a valid video file.**")

# Handle video uploads
@app.on_message(filters.video)
def video_handler(client, message: pyrogram.types.Message):
    msg = app.send_message(message.chat.id, "__Processing your video...__", reply_to_message_id=message.id)
    task_queue.put(lambda: handle_compression(message, msg))

# About command
@app.on_message(filters.command(["about"]))
def about_command(client, message: pyrogram.types.Message):
    app.send_message(
        message.chat.id,
        "**About This Bot**\n\n"
        "- This bot compresses videos using the H.265 (HEVC) codec for better quality and smaller size.\n"
        "- Built with [Pyrogram](https://docs.pyrogram.org/) and FFmpeg.\n"
        "- Open source and customizable for your needs!"
    )

# Help command
@app.on_message(filters.command(["help"]))
def help_command(client, message: pyrogram.types.Message):
    app.send_message(
        message.chat.id,
        "**Help Menu**\n\n"
        "1. Send a video file directly or as a document.\n"
        "2. The bot will compress and return the file to you.\n\n"
        "⚠️ **Note:**\n- Larger files may take more time.\n- Ensure the file format is supported."
    )

# Shutdown gracefully
@app.on_message(filters.command(["shutdown"]) & filters.user([123456789]))  # Replace with admin user ID
def shutdown(client, message: pyrogram.types.Message):
    app.send_message(message.chat.id, "🔄 **Shutting down...**")
    os._exit(0)

# Run the bot
if __name__ == "__main__":
    logger.info("Starting Video Compressor Bot...")
    app.run()
