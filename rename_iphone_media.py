#!/usr/bin/env python3
"""
iPhone Media Renamer
Renames photos and videos from an iPhone folder using their creation date and time.
"""

import sys
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


def get_file_date(filepath: Path) -> datetime:
    return (
        get_exif_date(filepath)
        or get_video_date(filepath)
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


# ── File collection ────────────────────────────────────────────────────────────

def collect_media_files(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in ALL_EXTENSIONS
    )


# ── I/O helpers ────────────────────────────────────────────────────────────────

def ask_folder() -> tuple[Path, list[Path]]:
    while True:
        raw = input("\nFolder path: ").strip().strip('"').strip("'")
        folder = Path(raw)
        if not folder.exists() or not folder.is_dir():
            print("  Invalid path. Try again.")
            continue
        files = collect_media_files(folder)
        if not files:
            print("  No media files found (JPG, HEIC, MOV, MP4 …). Try another folder.")
            continue
        return folder, files


def ask_yes_no(prompt: str) -> bool:
    while True:
        a = input(prompt).strip().lower()
        if a in ('y', 'yes'): return True
        if a in ('n', 'no'):  return False
        print("  Answer y or n.")


# ── Core logic ─────────────────────────────────────────────────────────────────

def rename_files(files: list[Path]) -> list[tuple[Path, Path]]:
    folder = files[0].parent
    taken  = {f.name for f in folder.iterdir() if f.is_file()}
    log: list[tuple[Path, Path]] = []
    errors = 0

    print()
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
    print()
    for current, original in log:
        if not current.exists():
            print(f"  {current.name}  not found, skipped.")
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
    print("iPhone Media Renamer")

    if not PIL_AVAILABLE:
        print("  ! Pillow not installed — photo EXIF dates unavailable  (pip install Pillow)")
    if not HACHOIR_AVAILABLE:
        print("  ! hachoir not installed — video metadata unavailable   (pip install hachoir)")

    folder, files = ask_folder()

    photos = sum(1 for f in files if f.suffix.lower() in PHOTO_EXTENSIONS)
    videos = sum(1 for f in files if f.suffix.lower() in VIDEO_EXTENSIONS)
    print(f"\n  {len(files)} files  ({photos} photos, {videos} videos)\n")
    for f in files:
        print(f"    {f.name}")

    if not ask_yes_no(f"\nRename {len(files)} files? [y/n]: "):
        print("  Cancelled.")
        sys.exit(0)

    log = rename_files(files)

    if not log:
        sys.exit(0)

    print(f"\n  Check: {folder}")

    if ask_yes_no("  Happy with the result? [y/n]: "):
        sys.exit(0)
    else:
        print("  Restoring…")
        restore_files(log)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Interrupted.")
        sys.exit(0)
