import os
import threading
import time
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Setup
bot_token = os.environ.get("TOKEN", "")
api_hash = os.environ.get("HASH", "")
api_id = os.environ.get("ID", "")
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
os.system("chmod 777 ./ffmpeg/ffmpeg")

# Start command
@app.on_message(filters.command(['start']))
def start(client, message: types.Message):
    app.send_message(
        message.chat.id, 
        f"**Welcome** {message.from_user.mention}\n__Send me a video file to compress.__"
    )

# Upload status updater
def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as file:
            progress = file.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Uploaded__: **{progress}**")
        except:
            pass
        time.sleep(5)

# Download status updater
def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as file:
            progress = file.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Downloaded__: **{progress}**")
        except:
            pass
        time.sleep(5)

# Progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as file:
        file.write(f"{current * 100 / total:.1f}%")

# Compression function
def compress_video(message, msg, compression_ratio):
    download_status = threading.Thread(target=downstatus, args=(f'{message.id}downstatus.txt', msg), daemon=True)
    download_status.start()
    
    vfile = app.download_media(message, progress=progress, progress_args=[message, "down"])
    if os.path.exists(f'{message.id}downstatus.txt'):
        os.remove(f'{message.id}downstatus.txt')

    output_file = f'output-{message.id}.mp4'
    compress_cmd = f'./ffmpeg/ffmpeg -i "{vfile}" -b:v {compression_ratio}k -preset veryfast "{output_file}"'

    app.edit_message_text(message.chat.id, msg.id, "__Compressing__")
    try:
        os.system(compress_cmd)
        if os.path.exists(output_file):
            os.remove(vfile)
        else:
            raise Exception("Compression failed")
    except Exception as e:
        app.edit_message_text(message.chat.id, msg.id, f"**Error**: {e}")
        return

    app.edit_message_text(message.chat.id, msg.id, "__Uploading__")
    upload_status = threading.Thread(target=upstatus, args=(f'{message.id}upstatus.txt', msg), daemon=True)
    upload_status.start()
    
    app.send_document(
        message.chat.id, 
        document=output_file, 
        force_document=True, 
        progress=progress, 
        progress_args=[message, "up"], 
        reply_to_message_id=message.id
    )
    
    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    os.remove(output_file)
    app.delete_messages(message.chat.id, [msg.id])

# Handle video and document messages
@app.on_message(filters.video | filters.document)
def handle_video(client, message: types.Message):
    if message.video or (message.document and "video" in message.document.mime_type):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("25%", callback_data="compress_25")],
            [InlineKeyboardButton("50%", callback_data="compress_50")],
            [InlineKeyboardButton("75%", callback_data="compress_75")],
            [InlineKeyboardButton("Custom", callback_data="compress_custom")]
        ])
        app.send_message(
            message.chat.id, 
            "__Choose compression percentage:__", 
            reply_markup=keyboard, 
            reply_to_message_id=message.id
        )
    else:
        app.send_message(message.chat.id, "**Send only videos.**")

# Handle callback queries for compression
@app.on_callback_query(filters.regex(r"compress_\d+"))
def handle_compression(client, callback_query: types.CallbackQuery):
    compression_level = int(callback_query.data.split("_")[1])
    msg = app.send_message(callback_query.message.chat.id, "__Downloading__", reply_to_message_id=callback_query.message.reply_to_message.id)
    
    # Map compression levels to FFmpeg bitrate settings (example: 75% -> 750k)
    bitrate_map = {25: "250k", 50: "500k", 75: "750k"}
    compression_ratio = bitrate_map[compression_level]
    
    compress_thread = threading.Thread(
        target=compress_video, 
        args=(callback_query.message.reply_to_message, msg, compression_ratio), 
        daemon=True
    )
    compress_thread.start()
    callback_query.answer(f"Selected {compression_level}% compression")

# Handle custom compression
@app.on_callback_query(filters.regex(r"compress_custom"))
def handle_custom_compression(client, callback_query: types.CallbackQuery):
    # Get the video size and adjust compression ratio dynamically
    video_file = app.download_media(callback_query.message.reply_to_message)
    video_size = os.path.getsize(video_file) / (1024 * 1024)  # Size in MB
    compression_ratio = "500k" if video_size < 50 else "1000k"  # Dynamic ratio for large files

    msg = app.send_message(callback_query.message.chat.id, "__Downloading__", reply_to_message_id=callback_query.message.reply_to_message.id)
    
    compress_thread = threading.Thread(
        target=compress_video, 
        args=(callback_query.message.reply_to_message, msg, compression_ratio), 
        daemon=True
    )
    compress_thread.start()
    callback_query.answer(f"Selected custom compression for {video_size:.2f}MB video")

# Run the bot
app.run()
