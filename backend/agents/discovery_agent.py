"""
Discovery Agent: Scans input folder and archive folders in output, identifies items to process.
"""

from pathlib import Path
from typing import List
from langchain_core.messages import HumanMessage
import logging as log
from utils import INPUT_DIR, OUTPUT_DIR

def is_archive_folder(folder_path: Path) -> bool:
    """
    Check if a folder is a valid archive folder.
    Valid archive folders contain SKILL.md and analysis_report.txt.
    """
    return (
        folder_path.is_dir() and
        (folder_path / "SKILL.md").exists() and
        (folder_path / "analysis_report.txt").exists()
    )

def discover_input_files(state: dict) -> dict:
    """
    Discover all files in the input/ folder and archive folders in output/.
    Input files: .txt (EHR records), .jpg, .jpeg, .png (images)
    Archive folders: timestamped folders with SKILL.md and analysis_report.txt
    """
    input_files = []
    
    # Scan INPUT_DIR for files
    if INPUT_DIR.exists():
        supported_extensions = {".txt", ".jpg", ".jpeg", ".png"}
        input_files = [
            f.name
            for f in INPUT_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in supported_extensions
        ]
        input_files.sort()
    
    # Scan OUTPUT_DIR for archive folders
    archive_folders = []
    if OUTPUT_DIR.exists():
        archive_folders = [
            f.name
            for f in OUTPUT_DIR.iterdir()
            if is_archive_folder(f)
        ]
        archive_folders.sort(reverse=True)  # Most recent first
    
    # Combine both lists
    all_items = input_files + [f"[ARCHIVE] {folder}" for folder in archive_folders]
    
    log.info(f"Discovered {len(input_files)} file(s) in INPUT_DIR")
    if input_files:
        log.info(f"  Files: {input_files}")
    
    log.info(f"Discovered {len(archive_folders)} archive folder(s) in OUTPUT_DIR")
    if archive_folders:
        log.info(f"  Archives: {archive_folders}")
    
    state["input_files"] = all_items
    state["file_results"] = {}
    state["current_file_index"] = 0
    state["messages"] = [
        HumanMessage(content=f"Starting multi-agent processing of {len(all_items)} item(s) ({len(input_files)} file(s), {len(archive_folders)} archive(s)).")
    ]
    
    return state

