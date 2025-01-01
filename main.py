import os
import logging
import threading
import time
from queue import Queue
from pyrogram import Client, filters
import pyrogram

# Configure loggingg
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
bot_token = os.environ.get("TOKEN", "")
api_hash = os.environ.get("HASH", "")
api_id = os.environ.get("ID", "")

# Initialize the bot
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

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
for _ in range(4):  # Adjust the number of workers based on server capacity
    threading.Thread(target=worker, daemon=True).start()

# Start command
@app.on_message(filters.command(['start']))
def start_command(client, message):
    app.send_message(message.chat.id, f"**Welcome** {message.from_user.mention}\n__Send me a video file, and I will compress it for you!__")


# Download progress tracker
def progress(current, total, message, type):
    percentage = int((current / total) * 100)
    if percentage % 20 == 0:  # Update every 20%
        with open(f'{message.id}{type}status.txt', "w") as fileup:
            fileup.write(f"{percentage}%")


# Upload status updater
def upstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
        except Exception:
            pass
        time.sleep(5)


# Download status updater
def downstatus(statusfile, message):
    while not os.path.exists(statusfile):
        time.sleep(1)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            app.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
        except Exception:
            pass
        time.sleep(5)


# Compress video
def compress(message, msg):
    try:
        # Start time tracking
        start_time = time.time()

        # Download video
        dowsta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', msg), daemon=True)
        dowsta.start()
        vfile = app.download_media(message, progress=progress, progress_args=[message, "down"])
        os.remove(f'{message.id}downstatus.txt')

        # Prepare FFmpeg command
        name = vfile.split("/")[-1]
        output_file = f"output-{message.id}.mp4"  # Change to .mp4 for better compatibility

        # Improved compression command for speed (libx264 for faster compression)
        cmd = f'./ffmpeg/ffmpeg -i "{vfile}" -c:v libx264 -preset veryfast -crf 28 -c:a aac -b:a 128k "{output_file}"'
        app.edit_message_text(message.chat.id, msg.id, "__Compressing__")
        logger.info(f"Running command: {cmd}")
        os.system(cmd)

        # Check for compression success
        if not os.path.exists(output_file):
            app.edit_message_text(message.chat.id, msg.id, "**Error during compression**")
            return

        os.rename(output_file, name)
        os.remove(vfile)

        # Upload compressed video
        upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', msg), daemon=True)
        upsta.start()
        app.send_document(message.chat.id, document=name, force_document=True, progress=progress, progress_args=[message, "up"], reply_to_message_id=message.id)
        os.remove(f'{message.id}upstatus.txt')
        os.remove(name)
        app.delete_messages(message.chat.id, [msg.id])

        # Time taken for the whole process
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Total time for download, compress, and upload: {duration:.2f} seconds")

        # Send user the time taken
        app.send_message(message.chat.id, f"**Compression complete!**\nTotal time: {duration:.2f} seconds")

    except Exception as e:
        logger.error(f"Error in compression: {e}")
        app.edit_message_text(message.chat.id, msg.id, f"**Error:** {str(e)}")


# Handle document uploads
@app.on_message(filters.document)
def document_handler(client, message):
    try:
        mimetype = message.document.mime_type
        if "video" in mimetype:
            msg = app.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
            task_queue.put(lambda: compress(message, msg))
        else:
            app.send_message(message.chat.id, "**Please send a valid video file.**")
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        app.send_message(message.chat.id, "**Send only videos.**")


# Handle video uploads
@app.on_message(filters.video)
def video_handler(client, message):
    msg = app.send_message(message.chat.id, "__Downloading__", reply_to_message_id=message.id)
    task_queue.put(lambda: compress(message, msg))


# Run the bot
app.run()
