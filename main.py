import os
import threading
import time
from pyrogram import Client, filters
import pyrogram

# Setup
bot_token = os.environ.get("TOKEN", "") 
api_hash = os.environ.get("HASH", "") 
api_id = os.environ.get("ID", "") 
app = Client("video_compressor_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

# Ensure ffmpeg permissions
os.system("chmod +x ./ffmpeg/ffmpeg")

# Start Command
@app.on_message(filters.command(['start']))
def start_command(client, message: pyrogram.types.messages_and_media.message.Message):
    app.send_message(
        message.chat.id,
        f"**Welcome** {message.from_user.mention}\n"
        f"__Send me a video file, and I'll compress it for you.__"
    )

# Status Updater
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
        time.sleep(3)

# Progress Writer
def progress_callback(current, total, message, stage):
    progress = f"{current * 100 / total:.1f}%"
    with open(f"{message.id}_{stage}.txt", "w") as f:
        f.write(progress)

# Compress Video
def compress_video(message, status_msg):
    try:
        # Downloading
        download_status_file = f"{message.id}_download.txt"
        download_thread = threading.Thread(
            target=update_status, args=(download_status_file, status_msg, "Downloading"), daemon=True
        )
        download_thread.start()

        video_file = app.download_media(
            message,
            progress=progress_callback,
            progress_args=[message, "download"]
        )

        if os.path.exists(download_status_file):
            os.remove(download_status_file)

        if not video_file:
            app.edit_message_text(message.chat.id, status_msg.id, "❌ Failed to download the video.")
            return

        # Compressing
        app.edit_message_text(message.chat.id, status_msg.id, "⚙️ Compressing the video...")

        output_file = f"compressed-{message.id}.mp4"
        ffmpeg_command = f"./ffmpeg/ffmpeg -i {video_file} -c:v libx265 -preset medium -crf 28 -c:a aac {output_file} -y"

        compression_status = os.system(ffmpeg_command)

        if compression_status != 0 or not os.path.exists(output_file):
            app.edit_message_text(message.chat.id, status_msg.id, "❌ Compression failed.")
            return

        # Cleanup original file
        os.remove(video_file)

        # Uploading
        upload_status_file = f"{message.id}_upload.txt"
        upload_thread = threading.Thread(
            target=update_status, args=(upload_status_file, status_msg, "Uploading"), daemon=True
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

        if os.path.exists(upload_status_file):
            os.remove(upload_status_file)

        # Cleanup compressed file
        os.remove(output_file)
        app.delete_messages(message.chat.id, [status_msg.id])

    except Exception as e:
        app.edit_message_text(message.chat.id, status_msg.id, f"❌ Error: {str(e)}")
        return

# Handle Document
@app.on_message(filters.document)
def handle_document(client, message):
    try:
        mimetype = message.document.mime_type
        if "video" in mimetype:
            status_msg = app.send_message(message.chat.id, "📥 Downloading...", reply_to_message_id=message.id)
            threading.Thread(target=compress_video, args=(message, status_msg), daemon=True).start()
        else:
            app.send_message(message.chat.id, "❌ Please send a valid video file.")
    except Exception as e:
        app.send_message(message.chat.id, f"❌ Error: {str(e)}")

# Handle Video
@app.on_message(filters.video)
def handle_video(client, message):
    try:
        status_msg = app.send_message(message.chat.id, "📥 Downloading...", reply_to_message_id=message.id)
        threading.Thread(target=compress_video, args=(message, status_msg), daemon=True).start()
    except Exception as e:
        app.send_message(message.chat.id, f"❌ Error: {str(e)}")

# Run the bot
app.run()
