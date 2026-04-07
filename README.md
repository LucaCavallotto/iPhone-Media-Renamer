# iPhone Media Renamer

A simple, robust Python CLI tool designed to automatically rename iPhone photos and videos based on their actual creation date and time from embedded metadata.

Perfect for organizing cluttered media folders into a human-readable, chronological format like `2024-07-15_14-32-05.jpg`.

---

## Features

- **Photo Support**: Extracts `DateTimeOriginal` from EXIF data (supports JPG, HEIC, PNG, etc.).
- **Video Support**: Extracts creation dates from video metadata (supports MOV, MP4, etc.).
- **Collision Handling**: Automatically adds suffixes (e.g., `_b`, `_c`) for bursts or files taken in the same second.
- **Instant Restore**: Not happy with the result? Use the built-in restore feature to revert to original filenames before exiting.
- **Smart Fallback**: Uses file modification time if metadata is missing or unreadable.
- **Timezone Aware**: Handles UTC-to-local conversion for MOV files.

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- For photo metadata: [Pillow](https://python-pillow.org/)
- For video metadata: [hachoir](https://hachoir.readthedocs.io/)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/lucacavallotto/rename-iphone-media.git
   cd rename-iphone-media
   ```

2. **Install dependencies**:
   ```bash
   pip install Pillow hachoir
   ```

---

## Usage

1. Run the script:
   ```bash
   python rename_iphone_media.py
   ```
2. Enter the path to your media folder when prompted.
3. Review the file list and confirm the rename operation.
4. After inspection, choose to keep the changes or restore the original names.

### Example

**Before:**
```
IMG_1234.JPG
IMG_1235.JPG
VID_5678.MOV
```

**After:**
```
2024-07-15_14-32-05.jpg
2024-07-15_14-32-07.jpg
2024-07-15_14-35-10.mov
```

---

## Important Disclaimer

> [!WARNING]
> This tool performs file renaming operations. While it includes a restore feature, you should ALWAYS **backup your media files** before using this script.

### Potential Failure Points & Limitations

1.  **Metadata Accuracy**:
    - Renaming depends entirely on the accuracy of the stored metadata.
    - If EXIF or video metadata is missing, the tool falls back to the **file modification date**, which may not reflect the actual capture time if the file has been copied or moved incorrectly.
2.  **Timezone Shifts**:
    - Apple `.mov` files store timestamps in UTC. The script attempts to convert these to your local system time. If your system timezone is incorrect or the files were recorded in a different timezone than your current one, timestamps might be offset.
3.  **Third-Party Apps**:
    - Photos or videos saved from apps like WhatsApp, Instagram, or Telegram often strip metadata. These will likely default to the file modification date.
4.  **No Persistent Undo**:
    - The "Restore" feature only works **during the active session**. Once you exit the script and confirm the changes, there is no automatic way to undo the renaming.

**Use this tool at your own risk. The author is not responsible for any data loss or metadata inaccuracies.**

---

## License

MIT License - feel free to use and modify for your own needs.