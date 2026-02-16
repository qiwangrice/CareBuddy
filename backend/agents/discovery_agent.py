"""
Discovery Agent: Scans input folder and identifies files to process.
"""

from pathlib import Path
from typing import List
from langchain_core.messages import HumanMessage
import logging as log
from utils import INPUT_DIR, OUTPUT_DIR

def discover_input_files(state: dict) -> dict:
    """
    Discover all files in the input/ folder.
    Supported: .txt (EHR records), .jpg, .jpeg, .png (images).
    """
    input_dir = INPUT_DIR
    if not input_dir.exists():
        log.info("No input/ folder found.")
        state["input_files"] = []
        return state

    supported_extensions = {".txt", ".jpg", ".jpeg", ".png"}
    files = [
        f.name
        for f in input_dir.iterdir()
        if f.is_file() and f.suffix.lower() in supported_extensions
    ]

    files.sort()
    num_files = len(files)
    log.info(f"Discovered {num_files} file(s) in {INPUT_DIR}: {files}")
    
    state["input_files"] = files
    state["file_results"] = {}
    state["current_file_index"] = 0
    state["messages"] = [
        HumanMessage(content=f"Starting multi-agent processing of {num_files} file(s).")
    ]
    
    return state
