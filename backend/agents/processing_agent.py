"""
Processing Agent: Routes and processes individual files (images or EHR records).
"""

from pathlib import Path
from PIL import Image
from langchain_core.messages import AIMessage
from utils import get_pipeline, INPUT_DIR, OUTPUT_DIR
import logging as log


def process_file_worker(state: dict) -> dict:
    """
    Worker agent: process the current file (image or EHR record).
    Routes based on file type.
    """
    files = state["input_files"]
    idx = state["current_file_index"]

    if idx >= len(files):
        log.info(f"No more files to process (idx={idx}, total={len(files)})")
        return state

    filename = files[idx]
    filepath = INPUT_DIR / filename
    file_ext = filepath.suffix.lower()

    log.info(f"Processing {idx+1}/{len(files)}: {filename}")

    try:
        if file_ext == ".txt":
            # Process EHR record
            result = process_ehr_file(filepath)
        elif file_ext in {".jpg", ".jpeg", ".png"}:
            # Process image
            result = process_image_file(filepath)
        else:
            result = f"Unsupported file type: {file_ext}"

        state["file_results"][filename] = result
        log.info(f"✓ Completed: {filename}")

    except Exception as e:
        error_msg = f"Error processing {filename}: {str(e)}"
        log.error(error_msg)
        state["file_results"][filename] = error_msg

    # Move to next file
    state["current_file_index"] += 1
    state["messages"].append(
        AIMessage(content=f"Processed file {idx+1}: {filename}")
    )

    return state


def process_image_file(filepath: Path) -> str:
    """Analyze image using the medical model."""
    pipe = get_pipeline()
    
    log.info(f"Loading image: {filepath}")
    image = Image.open(filepath)

    prompt = "Describe the image type and any abnormalities you see."
    log.info("Analyzing image with model...")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt}
            ]
        }
    ]

    output = pipe(text=messages, max_new_tokens=2000)
    result = output[0]["generated_text"][-1]["content"]

    log.info("Image analysis complete.")
    return result


def process_ehr_file(filepath: Path) -> str:
    """Analyze EHR record using the medical model."""
    pipe = get_pipeline()
    
    log.info(f"Loading EHR record: {filepath}")
    record_text = filepath.read_text()

    prompt = "Summarize the patient's medical history and current condition based on this EHR record."
    log.info("Analyzing EHR with model...")

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": record_text},
                {"type": "text", "text": prompt}
            ]
        }
    ]

    output = pipe(text=messages, max_new_tokens=2000)
    result = output[0]["generated_text"][-1]["content"]

    log.info("EHR analysis complete.")
    return result


def should_continue_processing(state: dict) -> str:
    """Decide whether to process another file or finish."""
    if state["current_file_index"] < len(state["input_files"]):
        return "process_file"
    else:
        return "finalize"
