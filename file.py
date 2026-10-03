r"""Organize files in a folder into subfolders named by file extension.

Examples:
    python file.py "C:/Users/Alex/Downloads" --dry-run
    python file.py "C:/Users/Alex/Downloads" --log-file "C:/Users/Alex/organizer.log"

Scheduling examples (replace paths/user names with your own):
    Cron (daily at 6 PM):
        0 18 * * * /usr/bin/python3 /path/to/file.py "$HOME/Downloads" --log-file "$HOME/file-organizer.log"

    Windows Task Scheduler:
        Trigger: Daily at 6:00 PM
        Program/script: py.exe
        Add arguments: -3 "C:\path\to\file.py" "C:\Users\Alex\Downloads" --log-file "C:\Users\Alex\file-organizer.log"
        Start in: the folder containing file.py
"""

import argparse
import logging
import os
import shutil
import sys


LOGGER_NAME = "file_organizer"


def configure_logger(log_file=None):
    """Set up console logging and, when requested, a persistent log file."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Keep repeated calls (such as tests) from duplicating log output.
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        expanded_log_file = os.path.abspath(os.path.expanduser(log_file))
        log_directory = os.path.dirname(expanded_log_file)
        if log_directory:
            os.makedirs(log_directory, exist_ok=True)
        file_handler = logging.FileHandler(expanded_log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def unique_destination(destination):
    """Return a free destination path, suffixing collisions with ' (n)'."""
    if not os.path.lexists(destination):
        return destination

    name, extension = os.path.splitext(destination)
    counter = 1
    candidate = f"{name} ({counter}){extension}"
    while os.path.lexists(candidate):
        counter += 1
        candidate = f"{name} ({counter}){extension}"
    return candidate


def organize_folder(folder, dry_run=False, log_file=None):
    """Move top-level files into extension-named subfolders.

    Files without an extension go into ``no_extension``. Directories and
    symbolic links are skipped. In dry-run mode, no files or folders are
    changed; log output is still emitted (and a requested log file is written).

    Returns the number of files moved, or the number that would be moved in
    dry-run mode. Raises ValueError if the source folder does not exist.
    """
    source_folder = os.path.abspath(os.path.expanduser(folder))
    logger = configure_logger(log_file)

    if not os.path.isdir(source_folder):
        raise ValueError(f"Folder does not exist or is not a directory: {source_folder}")

    active_log_path = None
    if log_file:
        active_log_path = os.path.normcase(
            os.path.realpath(os.path.abspath(os.path.expanduser(log_file)))
        )

    with os.scandir(source_folder) as entries:
        files = sorted(entries, key=lambda entry: entry.name.casefold())

    planned_or_moved = 0
    for entry in files:
        try:
            if not entry.is_file(follow_symlinks=False):
                continue

            if active_log_path and os.path.normcase(os.path.realpath(entry.path)) == active_log_path:
                continue

            extension = os.path.splitext(entry.name)[1].lower().lstrip(".")
            category = extension or "no_extension"
            destination_folder = os.path.join(source_folder, category)
            destination = unique_destination(os.path.join(destination_folder, entry.name))

            if dry_run:
                logger.info("DRY RUN: would move %s -> %s", entry.path, destination)
                planned_or_moved += 1
                continue

            os.makedirs(destination_folder, exist_ok=True)
            # Recheck after creating the category folder in case it already
            # contained a file with the same name.
            destination = unique_destination(os.path.join(destination_folder, entry.name))
            shutil.move(entry.path, destination)
            logger.info("Moved %s -> %s", entry.path, destination)
            planned_or_moved += 1
        except OSError as error:
            logger.error("Could not organize %s: %s", entry.path, error)

    action = "would move" if dry_run else "moved"
    logger.info("Finished: %d file(s) %s.", planned_or_moved, action)
    return planned_or_moved


def build_parser():
    parser = argparse.ArgumentParser(
        description="Move files in a folder into subfolders named by extension."
    )
    parser.add_argument("folder", help="Folder to organize (only its top-level files are scanned).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned moves without moving files or creating folders.",
    )
    parser.add_argument(
        "--log-file",
        metavar="PATH",
        help="Also save log messages to PATH (console logging is always enabled).",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        organize_folder(args.folder, dry_run=args.dry_run, log_file=args.log_file)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
