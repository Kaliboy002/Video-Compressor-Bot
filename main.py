import os
import threading
import time
from pyrogram import Client
from pyrogram import filters
import pyrogram


# Setup
bot_token = os.environ.get("TOKEN", "")
api_hash = os.environ.get("HASH", "")
api_id = os.environ.get("ID", "")
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)
os.system("chmod 777 ./ffmpeg/ffmpeg")


# Start command
@app.on_message(filters.command(['start']))
def echo(client, message: pyrogram.types.messages_and_media.message.Message):
    app.send_message(message.chat.id, f"**Welcome** {message.from_user.mention}\n__Just send me a video file, and I'll compress it for you!__")


# Upload status
def upstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break

    time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Uploading__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)


# Download status
def downstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break

    time.sleep(3)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Downloading__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)


# Progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")


# Compress function with enhancements for speed and error handling
def compress(message, msg):
    dowsta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', msg), daemon=True)
    dowsta.start()
    
    # Download video file
    vfile = app.download_media(message, progress=progress, progress_args=[message, "down"])
    if os.path.exists(f'{message.id}downstatus.txt'):
        os.remove(f'{message.id}downstatus.txt')

    name = vfile.split("/")[-1]

    # Optimize speed: Use libx264 codec with faster settings
    cmd = f'./ffmpeg/ffmpeg -i {vfile} -c:v libx264 -preset veryfast -crf 23 -c:a aac -b:a 128k output-{message.id}.mp4'
    
    # Indicate compression
    app.edit_message_text(message.chat.id, msg.id, "__Compressing__")
    try:
        os.system(cmd)
    except Exception as e:
        app.edit_message_text(message.chat.id, msg.id, f"**Error**: {str(e)}")
        return

    # Check if the file was successfully created
    if not os.path.exists(f'output-{message.id}.mp4'):
        app.edit_message_text(message.chat.id, msg.id, "**Error: Compression failed or incomplete file**")
        return

    # Clean up the original video file
    os.remove(vfile)

    # Rename the output file to match the original filename
    os.rename(f'output-{message.id}.mp4', name)
    app.edit_message_text(message.chat.id, msg.id, "__Uploading__")

    # Upload the compressed video
    upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', msg), daemon=True)
    upsta.start()
    app.send_document(message.chat.id, document=name, force_document=True, progress=progress, progress_args=[message, "up"], reply_to_message_id=message.id)

    if os.path.exists(f'{message.id}upstatus.txt'):
        os.remove(f'{message.id}upstatus.txt')
    
    # Delete the message after uploading
    app.delete_messages(message.chat.id, [msg.id])
    os.remove(name)


# Handle document uploads
@app.on_message(filters.document)
def document(client, message):
    try:
        mimetype = message.document.mime_type
        if "video" in mimetype:
            msg = app.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
            comp = threading.Thread(target=lambda: compress(message, msg), daemon=True)
            comp.start()
    except Exception as e:
        app.send_message(message.chat.id, f"**Send only Videos**: {str(e)}")


# Handle video uploads
@app.on_message(filters.video)
def video(client, message):
    msg = app.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
    comp = threading.Thread(target=lambda: compress(message, msg), daemon=True)
    comp.start()


# Infinity polling
app.run()
