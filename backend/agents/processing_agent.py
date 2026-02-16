"""
Processing Agent: Routes and processes individual files (images or EHR records) and archive folders.
"""

import json
from pathlib import Path
from PIL import Image
from langchain_core.messages import AIMessage
from utils import get_pipeline, INPUT_DIR, OUTPUT_DIR
from tools.parsing_tools import parse_skill_md
import logging as log


def process_file_worker(state: dict) -> dict:
    """
    Worker agent: process the current item (file or archive folder).
    Routes based on type (file or archive).
    """
    items = state["input_files"]
    idx = state["current_file_index"]

    if idx >= len(items):
        log.info(f"No more items to process (idx={idx}, total={len(items)})")
        return state

    item = items[idx]
    log.info(f"Processing {idx+1}/{len(items)}: {item}")

    try:
        if item.startswith("[ARCHIVE] "):
            # Process archive folder
            archive_name = item.replace("[ARCHIVE] ", "")
            result = process_archive_folder(archive_name)
        else:
            # Process regular file
            filepath = INPUT_DIR / item
            file_ext = filepath.suffix.lower()
            
            if file_ext == ".txt":
                # Process EHR record
                result = process_ehr_file(filepath)
            elif file_ext in {".jpg", ".jpeg", ".png"}:
                # Process image
                result = process_image_file(filepath)
            else:
                result = f"Unsupported file type: {file_ext}"

        state["file_results"][item] = result
        log.info(f"✓ Completed: {item}")

    except Exception as e:
        error_msg = f"Error processing {item}: {str(e)}"
        log.error(error_msg)
        state["file_results"][item] = error_msg

    # Move to next item
    state["current_file_index"] += 1
    state["messages"].append(
        AIMessage(content=f"Processed item {idx+1}: {item}")
    )

    return state


def process_archive_folder(archive_name: str) -> str:
    """
    Intelligently analyze archive folder based on SKILL.md metadata.
    
    Decision logic:
    1. Always read SKILL.md first (lightweight, has key stats)
    2. If success_rate < 100%, read analysis_report.txt for context
    3. Only read results.json if detailed per-file info is needed
    4. Generate insights using the compiled information
    """
    archive_path = OUTPUT_DIR / archive_name
    log.info(f"Processing archive folder: {archive_path}")
    
    if not archive_path.exists():
        return f"Archive folder not found: {archive_name}"
    
    skill_file = archive_path / "SKILL.md"
    report_file = archive_path / "analysis_report.txt"
    results_file = archive_path / "results.json"
    
    # STEP 1: Always parse SKILL.md first
    log.info(f"Reading SKILL.md for archive: {archive_name}")
    metadata = parse_skill_md(skill_file)
    
    if not metadata:
        return f"Invalid archive folder: {archive_name} (SKILL.md not found or invalid)"
    
    archive_info = f"Archive Analysis: {archive_name}\n"
    archive_info += "="*80 + "\n\n"
    archive_info += "SKILL METADATA:\n"
    archive_info += f"  Name: {metadata.name}\n"
    archive_info += f"  Description: {metadata.description}\n"
    archive_info += f"  Generated: {metadata.generated_timestamp}\n"
    archive_info += f"  Total Files: {metadata.total_files}\n"
    archive_info += f"  Successfully Processed: {metadata.successfully_processed}\n"
    archive_info += f"  Success Rate: {metadata.success_rate:.1f}%\n"
    archive_info += f"  Device: {metadata.device_used}\n"
    archive_info += f"  Model: {metadata.model}\n\n"
    
    # STEP 2: Decide whether to read analysis_report.txt based on success rate
    should_read_report = metadata.success_rate < 100.0
    
    if should_read_report:
        log.info(f"Success rate {metadata.success_rate:.1f}% < 100%, reading analysis_report.txt for context")
        if report_file.exists():
            report_content = report_file.read_text()
            archive_info += "ANALYSIS REPORT (Read due to incomplete success):\n"
            archive_info += report_content + "\n"
        else:
            log.warning(f"Analysis report not found for archive: {archive_name}")
    else:
        log.info(f"Success rate is {metadata.success_rate:.1f}% (100%), skipping detailed report")
        archive_info += "Note: All files processed successfully. Detailed report skipped.\n\n"
    
    # STEP 3: Only read results.json if we need detailed information (TODO: define criteria for when detailed results are needed, e.g. if total_files > 3 or if there were any failures)
    need_detailed_results = metadata.total_files > 3 or metadata.success_rate < 100.0
    
    if need_detailed_results:
        log.info(f"Reading results.json for detailed analysis (total_files={metadata.total_files}, success_rate={metadata.success_rate:.1f}%)")
        if results_file.exists():
            try:
                results_data = json.loads(results_file.read_text())
                archive_info += "DETAILED PROCESSING RESULTS:\n"
                
                if "results" in results_data and results_data["results"]:
                    archive_info += f"  Total result records: {len(results_data['results'])}\n"
                    # Summarize results (don't include full text to keep context bounded)
                    for filename, result in results_data.get("results", {}).items():
                        result_preview = str(result)[:150]
                        archive_info += f"  - {filename}: {result_preview}...\n"
                else:
                    archive_info += "  No detailed results available\n"
            except Exception as e:
                log.warning(f"Could not read results.json: {e}")
        else:
            log.warning(f"Results file not found for archive: {archive_name}")
    else:
        log.info("Skipping detailed results.json (small number of files and 100% success rate)")
    
    archive_info += "\n"
    
    # STEP 4: Generate insights using the model with the compiled information
    pipe = get_pipeline()
    
    prompt = (
        "Analyze this archive report and generate concise key insights, patterns, and recommendations. "
        "Focus on critical findings and actionable insights. "
        "If success rate is 100%, highlight what worked well. "
        "If there were failures, analyze the root causes and suggest improvements."
    )
    
    log.info(f"Generating insights from archive metadata and selective content")
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": archive_info},
                {"type": "text", "text": prompt}
            ]
        }
    ]
    
    try:
        output = pipe(text=messages, max_new_tokens=2000)
        insights = output[0]["generated_text"][-1]["content"]
        log.info("Archive analysis complete.")
        
        return f"Archive Analysis Insights:\n\n{insights}"
    except Exception as e:
        log.warning(f"Could not generate model insights for archive: {e}")
        return f"Archive processed successfully.\n{archive_info}"



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
    """Decide whether to process another item or finish."""
    if state["current_file_index"] < len(state["input_files"]):
        return "process_file"
    else:
        return "finalize"
