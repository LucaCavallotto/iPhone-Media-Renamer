#!/usr/bin/env python3
"""
iPhone Media Renamer
Renames photos and videos from an iPhone folder using their creation date and time.

Usage:
  python imr.py                   # will prompt for folder
  python imr.py /path/to/folder   # folder passed directly
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timezone

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
    HACHOIR_AVAILABLE = True
except ImportError:
    HACHOIR_AVAILABLE = False

PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.heic', '.heif', '.png', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mov', '.mp4', '.m4v', '.avi'}
ALL_EXTENSIONS   = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS


# ── Date extraction ────────────────────────────────────────────────────────────

def get_exif_date(filepath: Path) -> datetime | None:
    if not PIL_AVAILABLE or filepath.suffix.lower() not in PHOTO_EXTENSIONS:
        return None
    try:
        exif = Image.open(filepath)._getexif()
        if exif:
            for tag in (36867, 36868, 306):   # DateTimeOriginal, Digitized, DateTime
                if tag in exif:
                    return datetime.strptime(exif[tag], "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None


def get_video_date(filepath: Path) -> datetime | None:
    if not HACHOIR_AVAILABLE or filepath.suffix.lower() not in VIDEO_EXTENSIONS:
        return None
    try:
        parser = createParser(str(filepath))
        if parser:
            with parser:
                metadata = extractMetadata(parser)
            if metadata:
                for key in ('creation_date', 'date_time_original'):
                    value = metadata.get(key)
                    if value and isinstance(value, datetime):
                        if filepath.suffix.lower() == '.mov':
                            # MOV timestamps are UTC — convert to local time
                            value = value.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)
                        return value
    except Exception:
        pass
    return None


def get_creation_date(filepath: Path) -> datetime | None:
    """Read the filesystem creation date (macOS birthtime via st_birthtime)."""
    try:
        birthtime = filepath.stat().st_birthtime
        return datetime.fromtimestamp(birthtime)
    except AttributeError:
        # st_birthtime is macOS-only; not available on Linux
        return None


def get_file_date(filepath: Path) -> datetime:
    return (
        get_exif_date(filepath)
        or get_video_date(filepath)
        or get_creation_date(filepath)
        or datetime.fromtimestamp(filepath.stat().st_mtime)
    )


# ── Naming ─────────────────────────────────────────────────────────────────────

def build_new_name(filepath: Path, date: datetime, taken: set[str]) -> str:
    """
    2024-07-15_14-32-05.jpg
    Same-second collisions: 2024-07-15_14-32-05_b.jpg, _c.jpg, …
    Works across different extensions (burst + live photo pairs).
    """
    base = date.strftime("%Y-%m-%d_%H-%M-%S")
    ext  = filepath.suffix.lower()

    candidate = base + ext
    if candidate not in taken:
        return candidate

    for i in range(1, 702):   # _b … _zz — more than enough
        if i < 26:
            suffix = chr(ord('b') + i - 1)
        else:
            suffix = chr(ord('a') + (i - 26) // 26) + chr(ord('a') + (i - 26) % 26)
        candidate = f"{base}_{suffix}{ext}"
        if candidate not in taken:
            return candidate

    raise RuntimeError(f"Could not generate a unique name for {filepath.name}")


# ── Already-renamed detection ──────────────────────────────────────────────────

# Matches filenames produced by this script: 2024-07-15_14-32-05.jpg
#                                         or 2024-07-15_14-32-05_b.jpg
RENAMED_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(_[a-z]{1,2})?$'
)

def is_already_renamed(filepath: Path) -> bool:
    return bool(RENAMED_PATTERN.match(filepath.stem))


def count_distinct_groups(files: list[Path]) -> int:
    """
    Count distinct images by grouping files that share the same stem
    (e.g. IMG_1234.JPG + IMG_1234.MOV = 1 distinct image).
    """
    return len({f.stem.upper() for f in files})


# ── File collection ────────────────────────────────────────────────────────────

def collect_media_files(folder: Path) -> tuple[list[Path], list[Path]]:
    """
    Returns (to_rename, already_renamed) — two separate lists.
    Files matching the renamed pattern are skipped.
    """
    to_rename: list[Path] = []
    already:   list[Path] = []
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in ALL_EXTENSIONS:
            if is_already_renamed(f):
                already.append(f)
            else:
                to_rename.append(f)
    return to_rename, already


# ── I/O helpers ────────────────────────────────────────────────────────────────

W = 60  # header width

def header(title: str) -> None:
    print(f"\n{'─' * W}")
    print(f"  {title}")
    print(f"{'─' * W}")

def subheader(title: str) -> None:
    print(f"\n  {title}")
    print(f"  {'·' * (W - 2)}")

def validate_folder(path: str) -> tuple[Path, list[Path], list[Path]] | None:
    """Validate a path string and return (folder, to_rename, already) or None."""
    folder = Path(path.strip().strip('"').strip("'"))
    if not folder.exists() or not folder.is_dir():
        return None
    to_rename, already = collect_media_files(folder)
    if not to_rename and not already:
        return None
    return folder, to_rename, already

def ask_folder() -> tuple[Path, list[Path], list[Path]]:
    while True:
        raw = input("\n  Folder path: ").strip()
        result = validate_folder(raw)
        if result is None:
            folder = Path(raw.strip().strip('"').strip("'"))
            if not folder.exists() or not folder.is_dir():
                print("  ! Invalid path. Try again.")
            else:
                print("  ! No media files found (JPG, HEIC, MOV, MP4 …). Try another folder.")
            continue
        return result


def ask_yes_no(prompt: str) -> bool:
    while True:
        a = input(f"  {prompt} ").strip().lower()
        if a in ('y', 'yes'): return True
        if a in ('n', 'no'):  return False
        print("  Answer y or n.")


# ── Core logic ─────────────────────────────────────────────────────────────────

def rename_files(files: list[Path]) -> list[tuple[Path, Path]]:
    folder = files[0].parent
    taken  = {f.name for f in folder.iterdir() if f.is_file()}
    log: list[tuple[Path, Path]] = []
    errors = 0

    subheader("Renaming")
    for filepath in files:
        date     = get_file_date(filepath)
        new_name = build_new_name(filepath, date, taken - {filepath.name})
        new_path = folder / new_name
        try:
            filepath.rename(new_path)
            log.append((new_path, filepath))
            taken.discard(filepath.name)
            taken.add(new_name)
            print(f"  {filepath.name:<45}  →  {new_name}")
        except Exception as exc:
            print(f"  {filepath.name:<45}  error: {exc}")
            errors += 1

    print(f"\n  {len(log)} renamed, {errors} errors.")
    return log


def restore_files(log: list[tuple[Path, Path]]) -> None:
    errors = 0
    subheader("Restoring")
    for current, original in log:
        if not current.exists():
            print(f"  {current.name:<45}  not found, skipped.")
            errors += 1
            continue
        try:
            current.rename(original)
            print(f"  {current.name:<45}  →  {original.name}")
        except Exception as exc:
            print(f"  {current.name:<45}  error: {exc}")
            errors += 1
    print(f"\n  {len(log) - errors} restored, {errors} errors.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    header("iPhone Media Renamer")

    if not PIL_AVAILABLE:
        print("  ! Pillow not installed — photo EXIF dates unavailable  (pip install Pillow)")
    if not HACHOIR_AVAILABLE:
        print("  ! hachoir not installed — video metadata unavailable   (pip install hachoir)")

    # Accept folder from command-line argument or prompt
    if len(sys.argv) > 1:
        result = validate_folder(sys.argv[1])
        if result is None:
            folder_path = Path(sys.argv[1])
            if not folder_path.exists() or not folder_path.is_dir():
                print(f"\n  ! Invalid path: {sys.argv[1]}")
            else:
                print(f"\n  ! No media files found in: {sys.argv[1]}")
            print("  Falling back to manual input.")
            folder, files, already = ask_folder()
        else:
            folder, files, already = result
            print(f"\n  Folder: {folder}")
    else:
        folder, files, already = ask_folder()

    # ── Pre-rename summary ─────────────────────────────────────────────────────
    photos   = sum(1 for f in files if f.suffix.lower() in PHOTO_EXTENSIONS)
    videos   = sum(1 for f in files if f.suffix.lower() in VIDEO_EXTENSIONS)
    distinct = count_distinct_groups(files)

    if already:
        subheader(f"Already renamed — skipped ({len(already)} files)")
        for f in already:
            print(f"  {f.name}")

    if not files:
        print("\n  Nothing left to rename.")
        sys.exit(0)

    subheader(f"Files to rename ({len(files)} total  ·  {photos} photos  ·  {videos} videos  ·  {distinct} distinct)")
    for f in files:
        print(f"  {f.name}")

    print()
    if not ask_yes_no(f"Rename {len(files)} files? [y/n]:"):
        print("\n  Cancelled. Nothing was changed.")
        sys.exit(0)

    log = rename_files(files)

    if not log:
        sys.exit(0)

    # ── Post-rename summary ────────────────────────────────────────────────────
    header("Done")
    print(f"  Folder   {folder}")
    print(f"  Renamed  {len(log)} files  ·  {photos} photos  ·  {videos} videos  ·  {distinct} distinct")

    print()
    if ask_yes_no("Happy with the result? [y/n]:"):
        sys.exit(0)
    else:
        restore_files(log)
        print()
        header("Restored")
        print(f"  All {len(log)} files have been restored to their original names.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted.")
        sys.exit(0)
