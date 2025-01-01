import os
import threading
import time
from pyrogram import Client, filters
import pyrogram

# Setup
bot_token = os.environ.get("TOKEN", "") 
api_hash = os.environ.get("HASH", "") 
api_id = os.environ.get("ID", "") 
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
os.system("chmod 777 ./ffmpeg/ffmpeg")  # Ensure ffmpeg has execute permission

# Start command
@app.on_message(filters.command(['start']))
def echo(client, message : pyrogram.types.messages_and_media.message.Message):
    app.send_message(message.chat.id, f"**Welcome** {message.from_user.mention}\n__Just send me a video file to compress.__")

# Upload status
def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)
    
    time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Uploaded__: **{txt}**")
            time.sleep(10)
        except Exception as e:
            print(f"Error updating upload status: {e}")
            time.sleep(5)

# Download status
def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)
    
    time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Downloaded__: **{txt}**")
            time.sleep(10)
        except Exception as e:
            print(f"Error updating download status: {e}")
            time.sleep(5)

# Progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# Compression function with enhanced error handling
def compress(message, msg):
    dowsta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', msg), daemon=True)
    dowsta.start()

    vfile = app.download_media(message, progress=progress, progress_args=[message, "down"])
    if os.path.exists(f'{message.id}downstatus.txt'):
        os.remove(f'{message.id}downstatus.txt')

    name = vfile.split("/")[-1]
    
    # Check if the downloaded video file is valid and not empty
    if os.path.getsize(vfile) == 0:
        app.edit_message_text(message.chat.id, msg.id, "**Error**: Downloaded file is empty.")
        return

    video_size = os.path.getsize(vfile) / (1024 * 1024)  # Size in MB
    # Dynamically set compression ratio for larger files
    if video_size < 50:
        cmd = f'./ffmpeg/ffmpeg -i "{vfile}" -c:v libx264 -crf 28 -preset veryfast output-{message.id}.mp4'
    else:
        cmd = f'./ffmpeg/ffmpeg -i "{vfile}" -c:v libx265 -crf 28 -preset veryfast output-{message.id}.mp4'

    app.edit_message_text(message.chat.id, msg.id, "__Compressing__")

    # Log FFmpeg output (stdout and stderr) to help diagnose the issue
    ffmpeg_log = f'/tmp/ffmpeg_log_{message.id}.txt'
    os.system(f"{cmd} > {ffmpeg_log} 2>&1")

    # Check the FFmpeg log for errors
    with open(ffmpeg_log, 'r') as log_file:
        log_content = log_file.read()
        if "Error" in log_content or "Invalid" in log_content:
            app.edit_message_text(message.chat.id, msg.id, f"**Error during compression**: {log_content}")
            return

    # Validate that the compressed file exists and has non-zero size
    if os.path.exists(f'output-{message.id}.mp4') and os.path.getsize(f'output-{message.id}.mp4') > 0:
        os.remove(vfile)  # Remove original video file
        os.rename(f'output-{message.id}.mp4', name)  # Rename compressed file
    else:
        app.edit_message_text(message.chat.id, msg.id, "**Compression failed or output is empty.**")
        return

    app.edit_message_text(message.chat.id, msg.id, "__Uploading__")

    upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', msg), daemon=True)
    upsta.start()

    try:
        app.send_document(
            message.chat.id,
            document=name,
            force_document=True,
            progress=progress,
            progress_args=[message, "up"],
            reply_to_message_id=message.id
        )
    except Exception as e:
        app.edit_message_text(message.chat.id, msg.id, f"**Error uploading**: {e}")
        return

    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')

    app.delete_messages(message.chat.id, [msg.id])
    os.remove(name)

# Handle document messages
@app.on_message(filters.document)
def document(client, message):
    try:
        mimetype = message.document.mime_type
        if "video" in mimetype:
            msg = app.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
            comp = threading.Thread(target=lambda: compress(message, msg), daemon=True)
            comp.start()
    except Exception as e:
        app.send_message(message.chat.id, f"**Error**: {e}\nPlease send only video files.")

# Handle video messages
@app.on_message(filters.video)
def video(client, message):
    msg = app.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
    comp = threading.Thread(target=lambda: compress(message, msg), daemon=True)
    comp.start()

# Run the bot
app.run()
