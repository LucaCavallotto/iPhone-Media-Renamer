# iPhone Media Renamer

Renames photos and videos exported from an iPhone — replacing original filenames like `IMG_1234.JPG` with the actual capture date and time: `2024-07-15_14-32-05.jpg`.

## Requirements

**Python 3.10+** and two optional packages for best results:

```bash
pip install Pillow hachoir
```

Without them, the script falls back to the filesystem creation date, which is usually correct but less reliable than embedded metadata.

## Usage

```bash
python imr.py                              # prompts for folder
python imr.py /path/to/folder             # folder as argument
python imr.py "/path/with spaces/folder"  # quote paths with spaces
```

The script will list all files it intends to rename and ask for confirmation before doing anything. If you are not satisfied with the result, answering `n` at the end restores every file to its original name.

## Output format

| Situation | Result |
|---|---|
| Single photo | `2024-07-15_14-32-05.jpg` |
| Live Photo pair | `2024-07-15_14-32-05.jpg` + `2024-07-15_14-32-05.mov` |
| Burst / same second | `2024-07-15_14-32-05.jpg`, `…_b.jpg`, `…_c.jpg` |

## How the date is determined

1. EXIF `DateTimeOriginal` (photos)
2. Video metadata `creation_date` (MOV/MP4, automatically converted from UTC to local time)
3. Filesystem creation date — `birthtime` on macOS; useful for apps like Snapchat that strip metadata
4. Filesystem modification date — last resort fallback

## Personal Backup Workflow (iPhone to HDD)

1. In the Photos app (on your iPhone or Mac), create an album with the photos you want to export.
2. Open the Photos app on your Mac (ensuring iCloud synchronization is active), open the album, select the photos, and go to **File > Export > Export Unmodified Original For X Items...**.
3. In the export dialog, uncheck **Export IPTC as XMP**, set **File Name** to **Use File Name** (instead of Title), and set **Subfolder Format** to **None**.
4. Rename the exported photos using this `iPhone-Media-Renamer` script.
5. Transfer the renamed folder to your external Hard Drive (HDD).

## Notes

- Only renames files. Nothing is deleted or moved.
- Only processes the top-level folder. Subfolders are ignored.
- Files already matching the output pattern are automatically skipped, so running the script twice on the same folder is safe.
- On macOS, you can drag and drop a folder onto the Terminal window to paste its path.

## ⚠️ Disclaimer

This script renames files directly on disk. While it only performs rename operations and offers a rollback option, **unexpected errors can occur** — including filesystem issues, permission errors, or edge cases in metadata reading that could result in incorrect dates or, in rare circumstances, filename conflicts.

**Always keep a backup of your files before running this script.** The author takes no responsibility for any data loss or corruption that may occur. Use at your own risk.