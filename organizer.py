from os import scandir, makedirs
from os.path import splitext, exists, join
from shutil import move
from time import sleep
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mutagen import File
from pathlib import Path


# ! FILL IN BELOW IF YOU WANT TO TRACK DIFFRENT FOLDER
# ? folder to track e.g. Windows: "C:\\Users\\UserName\\Downloads"
SOURCE_DIR = str(Path.home() / "Downloads")
if not exists(SOURCE_DIR):
    print(f"Directory \"{SOURCE_DIR}\" has not been found")
    print("Please update SOURCE_DIR to a valid folder.")
    raise SystemExit

DEST_DIR = str(Path.home() / "Organized Downloads")
DEST_DIR_DOCUMENTS = rf"{DEST_DIR}/Downloaded Documents"
DEST_DIR_MUSIC = rf"{DEST_DIR}/Downloaded Music"
DEST_DIR_SFX = rf"{DEST_DIR_MUSIC}/SFX Sounds"
DEST_DIR_VIDEO = rf"{DEST_DIR}/Downloaded Videos"
DEST_DIR_IMAGE = rf"{DEST_DIR}/Downloaded Images"

DIRECTORIES = [DEST_DIR, DEST_DIR_SFX, DEST_DIR_MUSIC,
                DEST_DIR_VIDEO, DEST_DIR_IMAGE, DEST_DIR_DOCUMENTS
]

for directory in DIRECTORIES:
    makedirs(directory, exist_ok=True)

# ! BELOW are supported file types. Please Feel Free to add another file extension if not included
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".jpe", ".jif", ".jfif", ".jfi", ".png", ".gif", ".webp", ".tiff",
                    ".tif", ".psd", ".raw", ".arw", ".cr2", ".nrw", ".k25", ".bmp", ".dib", ".heif",
                    ".heic", ".ind", ".indd", ".indt", ".jp2", ".j2k", ".jpf", ".jpx", ".jpm",
                    ".mj2", ".svg", ".svgz", ".ai", ".eps", ".ico")

VIDEO_EXTENSIONS = (".webm", ".mpg", ".mp2", ".mpeg", ".mpe", ".mpv", ".ogg",
                    ".mp4", ".mp4v", ".m4v", ".avi", ".wmv", ".mov", ".qt", ".flv", ".swf", ".avchd")

AUDIO_EXTENSIONS = (".m4a", ".flac", ".mp3", ".wav", ".wma", ".aac")

DOCUMENT_EXTENSIONS = (".doc", ".docx", ".odt",
                       ".pdf", ".xls", ".xlsx", ".ppt", ".pptx")

SFX_MAX_DURATION = 30

SFX_KEYWORDS = (
    "sfx",
    "sound effect",
    "whoosh",
    "impact",
    "explosion",
    "click",
    "notification",
    "ui",
)

def make_unique_name(dest, name):
    filename, extension = splitext(name)
    counter = 1
    while exists(join(dest, name)):
        name = f"{filename}({str(counter)}){extension}"
        counter += 1
    return name

def move_file(dest, entry, name):
    try:
        unique_name = make_unique_name(dest, name)
        destination = join(dest, unique_name)
        move(entry.path, destination)
        return True
    except PermissionError:
        logging.warning(f"File is currently in use: {name}")
        return False
    except FileNotFoundError:
        logging.warning(f"File disappeared before it could be moved: {name}")
        return False
    except Exception as e:
        logging.error(f"Failed to move '{name}': {e}")
        return False
    
class MoverHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return

        with scandir(SOURCE_DIR) as entries:
            for entry in entries:
                if not entry.is_file():
                    continue

                name = entry.name
                lower_name = name.lower()

                if lower_name.endswith((".crdownload", ".part", ".tmp")):
                    continue

                self.check_files(entry, name, IMAGE_EXTENSIONS, DEST_DIR_IMAGE, "image")
                self.check_files(entry, name, VIDEO_EXTENSIONS, DEST_DIR_VIDEO, "video")
                self.check_files(entry, name, DOCUMENT_EXTENSIONS, DEST_DIR_DOCUMENTS, "document")
                self.check_audio_files(entry, name)

    def check_audio_files(self, entry, name):
        lower_name = name.lower()

        for audio_extension in AUDIO_EXTENSIONS:
            if lower_name.endswith(audio_extension):

                try:
                    audio = File(entry.path)
                    if audio is None or not hasattr(audio, "info"):
                        logging.warning(f"Couldn't read audio metadata: {name}")
                        return
                    length = audio.info.length
                except Exception:
                    logging.warning(f"Couldn't read audio metadata: {name}")
                    return         

                if length < SFX_MAX_DURATION or any(keyword in lower_name for keyword in SFX_KEYWORDS):
                    dest = DEST_DIR_SFX
                else:
                    dest = DEST_DIR_MUSIC
                if move_file(dest, entry, name):
                    logging.info(f"Moved audio file: {name}")
                break

    def check_files(self, entry, name, extensions, destination, file_type):
        lower_name = name.lower()
        if lower_name.endswith(extensions):
            if move_file(destination, entry, name):
                logging.info(f"Moved {file_type} file: {name}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    event_handler = MoverHandler()
    observer = Observer()
    observer.schedule(event_handler, SOURCE_DIR, recursive=True)
    observer.start()
    try:
        while True:
            sleep(10)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()