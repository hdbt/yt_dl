import os
import sys
import datetime
import threading
import requests
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
from tkinter import PhotoImage
from yt_dlp import YoutubeDL



############################################
# 1) Helper: Determine ffmpeg.exe location
############################################
def get_ffmpeg_path():
    """
    If running under PyInstaller --onefile, ffmpeg.exe may be unpacked to sys._MEIPASS.
    Otherwise, assume ffmpeg.exe is in the same folder as this script.
    """
    if hasattr(sys, '_MEIPASS'):
        # This is the temp folder where PyInstaller unpacked files
        return os.path.join(sys._MEIPASS, 'ffmpeg.exe')
    else:
        # For normal Python execution, assume ffmpeg.exe is in the same directory
        return os.path.join(os.path.dirname(__file__), 'ffmpeg.exe')

def get_path(filename):
    """
    If you bundle with PyInstaller, this ensures we can load files from
    the correct location at runtime (sys._MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    else:
        return filename

############################################
# 2) Threaded Download Logic
############################################
def download_videos_threaded():
    """
    Spawn a separate thread so the GUI stays responsive
    while multiple downloads/conversions happen.
    """
    thread = threading.Thread(target=bulk_download)
    thread.start()

def bulk_download():
    """
    Reads multiple lines (URLs) from the Text widget.
    Depending on the selected radio button, downloads:
      - MP3 audio only
      - MP4 video
    Displays progress, animated GIF for conversion, etc.
    """
    links = links_text.get("1.0", tk.END).splitlines()
    links = [url.strip() for url in links if url.strip()]

    if not links:
        messagebox.showwarning("No Links", "Please enter at least one YouTube link (one per line).")
        return

    # Disable the "Download & Convert" button so user doesn't spam-click
    download_button.config(state=tk.DISABLED)

    # Determine if user wants audio or video
    mode = download_mode.get()  # "audio" or "video"

    # ---- OPTIONAL: Show the overlay GIF on top of the progress bar right away ----
    # For example, let's say we always show it during downloads
    # You can decide exactly when you'd like to place it.
    overlay_label.place(x=progress_bar.winfo_x()+ 400 ,
                        y=progress_bar.winfo_y() + 30 )  # Adjust offsets as needed
    start_overlay_gif()

    for index, url in enumerate(links, start=1):
        try:
            # Reset progress bar and label
            progress_label.config(text=f"Processing {index}/{len(links)}...")
            progress_bar["value"] = 0
            progress_bar.config(mode="determinate")
            progress_bar.pack(pady=5)
            loading_label.pack_forget()  # Hide the big 'loading.gif' if visible

            # -----------------------------------------------------------
            # 2A) Build yt-dlp options, specifying ffmpeg_location
            # -----------------------------------------------------------
            if mode == "audio":
                # Audio (MP3) mode
                ydl_opts = {
                    'ffmpeg_location': get_ffmpeg_path(),
                    'format': 'bestaudio/best',
                    'outtmpl': '%(title)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '128',
                    }],
                    'progress_hooks': [download_hook],
                    'postprocessor_hooks': [postprocessor_hook],
                }
            else:
                # Video (MP4) mode
                ydl_opts = {
                    'ffmpeg_location': get_ffmpeg_path(),
                    'format': 'bestvideo[height<=720]+bestaudio/best',
                    'outtmpl': '%(title)s.%(ext)s',
                    'merge_output_format': 'mp4',  # Merge into MP4 container
                    'progress_hooks': [download_hook],
                    'postprocessor_hooks': [postprocessor_hook],
                }

            # -----------------------------------------------------------
            # 2B) Download & Convert (yt-dlp)
            # -----------------------------------------------------------
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "video")

                if mode == "audio":
                    progress_label.config(text=f"Done: {title}.mp3")
                else:
                    progress_label.config(text=f"Done: {title}.mp4")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to process:\n{url}\n\n{e}")
            progress_label.config(text="")

    # Re-enable the button
    download_button.config(state=tk.NORMAL)
    progress_label.config(text="Alle Downloads fertig, Babylein!")

    # Stop/hide the overlay GIF after all downloads
    stop_overlay_gif()
    overlay_label.place_forget()

############################################
# 3) Download/Conversion Hooks
############################################
def download_hook(d):
    """
    Called during the 'downloading' phase.
    Updates our determinate progress bar based on total bytes.
    """
    if d['status'] == 'downloading':
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
        if total_bytes:
            fraction = d['downloaded_bytes'] / total_bytes
            percent = fraction * 100
            progress_bar["value"] = percent

        # Force UI to update
        root.update_idletasks()

    elif d['status'] == 'finished':
        progress_label.config(text="Download finished. Converting...")

def postprocessor_hook(d):
    """
    Called during post-processing (FFmpeg conversion or merging).
    We'll show an animated GIF to indicate 'work in progress' (the main big loading.gif).
    """
    if d['status'] == 'started':
        # Hide the determinate progress bar
        progress_bar.pack_forget()

        # Show the animated GIF label (the big one)
        loading_label.pack(pady=5)
        loading_label.lift()
        start_loading_gif()

    elif d['status'] == 'processing':
        # Still converting/merging
        pass

    elif d['status'] == 'finished':
        # Stop the animation and hide the big GIF
        stop_loading_gif()
        loading_label.pack_forget()


        # Re-show the progress bar (fully complete)
        progress_bar.pack(pady=5)
        progress_bar.config(mode='determinate', value=100)
        progress_label.config(text="Conversion/merge finished!")
        root.update_idletasks()

############################################
# 4) Animated GIF Support (for loading.gif)
############################################
frames = []
gif_index = 0
gif_running = False

def load_gif_frames():
    """
    Load the frames of loading.gif into a list of PhotoImages.
    """
    global frames
    try:
        gif = PhotoImage(file=get_path("loading.gif") )
        frames.append(gif)
        i = 1
        while True:
            gif2 = PhotoImage(file=get_path("loading.gif"), format=f"gif -index {i}")
            frames.append(gif2)
            i += 1
    except:
        pass

def start_loading_gif():
    """Start animating the loaded frames in loading_label."""
    global gif_running
    gif_running = True
    animate_gif()

def stop_loading_gif():
    """Stop the GIF animation."""
    global gif_running
    gif_running = False

def animate_gif():
    """Cycle through each frame of the loading.gif."""
    global gif_index
    if not gif_running or not frames:
        return

    frame = frames[gif_index]
    gif_index = (gif_index + 1) % len(frames)
    loading_label.config(image=frame)

    # Schedule the next frame
    root.after(100, animate_gif)  # Adjust speed as needed (100 ms)

############################################
# 5) SECOND GIF: Overlay (on top of progress bar)
############################################
overlay_frames = []
overlay_gif_index = 0
overlay_gif_running = False

def load_overlay_gif_frames():
    """
    Load frames for overlay.gif into a list of PhotoImages.
    """
    global overlay_frames
    try:
        gif = PhotoImage(file=get_path("overlay.gif"))
        overlay_frames.append(gif)
        i = 1
        while True:
            gif2 = PhotoImage(file=get_path("overlay.gif"), format=f"gif -index {i}")
            overlay_frames.append(gif2)
            i += 1
    except:
        pass

def start_overlay_gif():
    """Start animating the overlay.gif on top of the progress bar."""
    global overlay_gif_running
    overlay_gif_running = True
    animate_overlay_gif()

def stop_overlay_gif():
    """Stop the overlay GIF animation."""
    global overlay_gif_running
    overlay_gif_running = False

def animate_overlay_gif():
    """Cycle through each frame of the overlay.gif."""
    global overlay_gif_index
    if not overlay_gif_running or not overlay_frames:
        return

    frame = overlay_frames[overlay_gif_index]
    overlay_gif_index = (overlay_gif_index + 1) % len(overlay_frames)
    overlay_label.config(image=frame)

    # Schedule the next frame
    root.after(100, animate_overlay_gif)  # Adjust speed as needed (100 ms)

# ------------------------------------
#  GitHub Update Logic
# ------------------------------------
GITHUB_USER = "hdbt"
GITHUB_REPO = "yt_dl"
ASSET_NAME = "youtube_to_mp3.exe"  # The name of the release asset on GitHub
def check_for_update():
    """
    Checks the latest release on GitHub, downloads the .exe, and saves it
    as youtube_to_mp3_new.exe. Then prompts the user to replace the old file.
    """
    try:
        # 1. Get latest release info via GitHub API
        api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases/latest"
        headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        release_data = response.json()

        # 2. Locate the .exe asset in the release
        assets = release_data.get("assets", [])
        download_url = None
        for asset in assets:
            if asset.get("name") == ASSET_NAME:
                download_url = asset.get("browser_download_url")
                break

        if not download_url:
            messagebox.showerror("Update Error", f"No asset named {ASSET_NAME} found in latest release.")
            return

        # 3. Download the new .exe
        lbl = str(datetime.datetime.today()).split()[0]
        new_filename = f"youtube_to_mp3_{lbl}.exe"
        message_label.config(text="Downloading update...")
        with requests.get(download_url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(new_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

        # 4. Let the user know
        message_label.config(text="Download kompletto.")
        messagebox.showinfo("Update gedownloaded",
                            f"Neue version wurde als {new_filename} gespeichert.\n\n"
                            "Schließe das Programm und nutze die neue Exe "
                            f"{new_filename}.")

    except Exception as e:
        messagebox.showerror("Update Error", f"Failed to update:\n{e}")


############################################
# 6) GUI Setup (tkinter)
############################################
root = tk.Tk()
root.title("YouTube Downloader für das Bebe")
root.geometry("600x600")
root.resizable(False, False)
# Add an "Update" button
update_button = tk.Button(root, text="🌐", command=check_for_update)
update_button.pack(anchor = "e", side = "top")

instruction_label = tk.Label(root, text="Ein YouTube link pro Zeile:")
instruction_label.pack(pady=(10, 5))

links_text = tk.Text(root, height=10, width=60)
links_text.pack(pady=5)
sample_links = "https://www.youtube.com/watch?v=nEZj-ZKqgUw" # sample link
links_text.insert("1.0", sample_links)

# Radio buttons to select "Audio" or "Video"
download_mode = tk.StringVar(value="audio")  # default to audio
audio_radiobutton = tk.Radiobutton(root, text="Download als MP3 (Audio)", variable=download_mode, value="audio")
video_radiobutton = tk.Radiobutton(root, text="Download als MP4 (Video)", variable=download_mode, value="video")
audio_radiobutton.pack()
video_radiobutton.pack()

download_button = tk.Button(root, text="Download & Konvertieren", command=download_videos_threaded)
download_button.pack(pady=10)

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=5)

progress_label = tk.Label(root, text="", fg="blue")
progress_label.pack(pady=5)

# Label to hold the main "loading.gif" (hidden initially)
loading_label = tk.Label(root)
loading_label.pack_forget()

# Label for the overlay.gif. We'll place() it on top of progress_bar
overlay_label = tk.Label(root)
overlay_label.place_forget()  # Hide initially

# Load both sets of GIF frames at startup
load_gif_frames()
load_overlay_gif_frames()

message_label = tk.Label(root, text="", fg="purple")
message_label.pack(pady=10)

icon_img = PhotoImage(file=get_path("overlay.gif") )   # or "my_icon.gif"
root.iconphoto(False, icon_img)

root.mainloop()
