
# Android Backup & Compress Tool
<img width="512" height="512" alt="IMG_2680" src="https://github.com/user-attachments/assets/28976eeb-afac-4ec8-a2da-59113abd9b28" />

A desktop application to back up photos and videos from an Android device, compress them to save space, and replace the originals on the device.

My wife ran out of space on her Phone. Either buy a new phone or get rid of the memorys in the pocket, or Pay monthly for cloud. All not great. I noticed 1 Minute Video took >300MB, which seemed wasteful. I knew that compression could solve that problem, but I Found no convinient software so I * wrote it: 1 Click to start backup in Full quality, compression and replacing on device while keeping the Metadata for correct sorting in the gallery.
However the setup takes some patience.

\*= Actually 95% was written by Gemini 2.5/GPT5. I just added nuances.
PS: The code is Not perfect, but good enough and since we handle sensitive data: every change is Test intensive. “


## Features

*   **Selective Backup:** Back up the entire camera roll or select specific folders.
*   **Filter by Name:** Use regular expressions to filter and back up only the files you want.
*   **Optional Compression:**
    *   **Videos:** Uses FFmpeg to compress videos, with adjustable CRF (Constant Rate Factor) and resolution.
    *   **Images:** Uses Pillow to compress images, with adjustable quality and resolution.
*   **Metadata Preservation:**  Keeps original metadata (like creation date) to ensure correct sorting in your gallery.
*   **Replace on Device:** (Optional and risky!) Replace the original files on your Android device with the compressed versions.
*   **Dry Run Mode:** See what the script will do without actually modifying any files.
*   **Logging:** Detailed logging of all operations.

## Installation

This application requires Python 3, FFmpeg, ExifTool, and Android Debug Bridge (ADB).

### 1. Install Python and Project Dependencies

1.  **Install Python 3:** If you don't have it, download and install Python from [python.org](https://www.python.org/). Make sure to check the box that says "Add Python to PATH" during installation.
2.  **Clone this repository:**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```
3.  **Install Python packages:**
    ```bash
    pip install -r requirements.txt
    ```

### 2. Install FFmpeg

FFmpeg is a powerful command-line tool for handling video and audio.

1.  Download the latest "full" build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-full.7z).
2.  Extract the `.7z` file (you might need [7-Zip](https://www.7-zip.org/)).
3.  Move the extracted folder to a permanent location, like `C:\ffmpeg`.
4.  Add the `bin` directory from the extracted folder to your system's PATH environment variable.
    *   Search for "Environment Variables" in the Start Menu and select "Edit the system environment variables."
    *   Click "Environment Variables..."
    *   Under "System variables," find and select the "Path" variable, then click "Edit."
    *   Click "New" and add the path to the `bin` directory (e.g., `C:\ffmpeg\bin`).



### 4. Install Android Debug Bridge (ADB)

ADB is a command-line tool for communicating with an Android device.

**1. Enable USB Debugging on Your Phone**

*   Go to **Settings** > **About phone**.
*   Find the **Build number**. On some phones (like Samsung), you may need to go into **Software information** to find it.
*   Tap the **Build number** seven times in a row. You will see a message saying "You are now a developer!"
*   Go back to the main Settings menu and find the new **Developer options** menu.
*   Inside Developer options, find and enable **USB debugging**.
*   When you connect your phone to your computer for the first time after enabling USB debugging, your phone will ask you to authorize the computer. Check the "Always allow from this computer" box and tap **Allow**.

**2. Download and Configure ADB**

1.  **Download ADB:** Download the "SDK Platform-Tools" for your operating system from the [Android developer website](https://developer.android.com/studio/releases/platform-tools).
2.  **Extract the files:**
    *   **Windows:** Extract the zip file to a permanent location, such as `C:\platform-tools`.
    *   **macOS/Linux:** Extract the zip file to a location you can easily remember, like `~/Library/Android/sdk/platform-tools` (macOS) or `~/platform-tools` (Linux).
3.  **Add ADB to your PATH:**
    *   **Windows:** Follow the same steps as for FFmpeg to add the `platform-tools` directory (e.g., `C:\platform-tools`) to your PATH.


## Usage

1.  Connect your Android device to your computer via USB.
2.  Run the application:
    ```bash
    python backup_and_compress.py
    ```
3.  **Configure the settings:**
    *   **Android Path:** The path to your camera roll (usually `/sdcard/DCIM/Camera`).
    *   **Backup to:** The local folder where you want to store the backups.
    *   **Compression:** Enable and configure video and image compression settings.
    *   **Replace on Android:** (Use with caution!) Enable to replace the original files.
4.  Click **Start Process**.

## How to Contribute

Contributions are welcome!

1.  Fork the repository.
2.  Create a new branch: `git checkout -b my-new-feature`
3.  Make your changes.
4.  Commit your changes: `git commit -am 'Add some feature'`
5.  Push to the branch: `git push origin my-new-feature`
6.  Submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
