"""
Processing Agent: Routes and processes individual files (images or EHR records) and archive folders.
"""

import json
from pathlib import Path
from typing import Union
from PIL import Image
from langchain_core.messages import AIMessage
from utils import get_pipeline, INPUT_DIR, OUTPUT_DIR
from tools.parsing_tools import parse_skill_md
import logging as log
import pydantic
from pydantic import Field
import re

def deduplicate_critical_info(info_list: list[str]) -> list[str]:
    """
    Deduplicate critical info items using a more robust approach.
    
    This function normalizes the text by:
    - Stripping whitespace
    - Converting to lowercase for comparison
    - Removing common prefixes like "History of"
    - Removing punctuation for comparison
    
    Args:
        info_list: List of critical info strings (potentially with duplicates)
    Returns:
        List of unique critical info strings, preserving original formatting of the first occurrence.
    """
    seen = set()
    deduplicated = []
    
    for item in info_list:
        normalized = item.strip().lower()
        normalized = re.sub(r'^(history of|history, of)\s+', '', normalized)  # Remove "History of" prefix
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        
        if normalized not in seen:
            seen.add(normalized)
            deduplicated.append(item.strip())
    
    return deduplicated

def save_patient_record_to_json(patient_record: dict, filename: str = None) -> Path:
    """
    Save a patient record to a JSON file in OUTPUT_DIR.
    
    Args:
        patient_record: Dictionary containing patient data
        filename: Optional filename (default: <patient_id>.json)
        
    Returns:
        Path to the saved JSON file
    """
    if filename is None:
        patient_id = patient_record.get("patient_id", "UNKNOWN")
        filename = f"{patient_id}.json"
    
    # Clean and normalize the record before saving
    cleaned_record = clean_patient_record(patient_record)
    
    output_file = OUTPUT_DIR / filename
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(cleaned_record, f, indent=2, ensure_ascii=False)
    
    log.info(f"✓ Saved patient record to: {output_file}")
    log.info(f"  - Contains {len(cleaned_record.get('symptoms', []))} unique symptoms")
    log.info(f"  - Contains {len(cleaned_record.get('critical_info', []))} unique critical items")
    
    return output_file


def clean_patient_record(patient_record: dict) -> dict:
    """
    Clean and normalize a patient record before saving.
    
    Performs:
    - Deduplication of all list fields
    - Removal of empty strings
    - Trimming of whitespace
    - Case normalization where appropriate
    
    Args:
        patient_record: Raw patient record dictionary
        
    Returns:
        Cleaned patient record dictionary
    """
    cleaned = {}
    
    # Simple string fields
    for field in ["patient_id", "name"]:
        value = patient_record.get(field, "")
        cleaned[field] = str(value).strip() if value else ""
    
    # List fields with deduplication
    for field in ["symptoms", "diagnoses", "medications", "critical_info"]:
        raw_list = patient_record.get(field, [])
        if not isinstance(raw_list, list):
            raw_list = [raw_list]
        
        # Filter empty items and strip whitespace
        cleaned_items = [str(item).strip() for item in raw_list if item and str(item).strip()]
        
        # Deduplicate
        if field == "critical_info":
            cleaned[field] = deduplicate_critical_info(cleaned_items)
        else:
            # For other lists, use simple deduplication preserving order
            seen = set()
            deduplicated = []
            for item in cleaned_items:
                normalized = item.lower()
                if normalized not in seen:
                    seen.add(normalized)
                    deduplicated.append(item)
            cleaned[field] = deduplicated
    
    return cleaned


def export_batch_results(results: dict, batch_filename: str = "patient_records.json") -> Path:
    """
    Export all patient records from a batch of file processing to a single JSON file.
    
    Args:
        results: Dictionary of filename -> patient_record mappings
        batch_filename: Name of the output batch file
        
    Returns:
        Path to the saved batch JSON file
    """
    output_file = OUTPUT_DIR / batch_filename
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Aggregate results with metadata
    batch_data = {
        "total_records": len(results),
        "records": results,
        "export_timestamp": str(Path.ctime(Path.cwd()))
    }
    
    with open(output_file, 'w') as f:
        json.dump(batch_data, f, indent=2)
    
    log.info(f"✓ Exported batch results to: {output_file}")
    log.info(f"  - Total records: {batch_data['total_records']}")
    return output_file

class PatientRecord(pydantic.BaseModel):
    """Structured representation of a patient's medical record."""
    patient_id: str = Field(default_factory=lambda: "UNKNOWN")
    name: str = Field(default_factory=lambda: "")  # Optional name field, can be empty
    symptoms: list[str]
    diagnoses: list[str]
    medications: list[str]
    critical_info: list[str]


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
                result = {
                    "patient_id": "UNKNOWN",
                    "name": "Unsupported File Type",
                    "error": f"Unsupported file type: {file_ext}",
                    "symptoms": [],
                    "diagnoses": [],
                    "medications": [],
                    "critical_info": []
                }

        state["file_results"][item] = result
        log.info(f"✓ Completed: {item}")

    except Exception as e:
        error_msg = f"Error processing {item}: {str(e)}"
        log.error(error_msg)
        state["file_results"][item] = {
            "patient_id": "UNKNOWN",
            "name": "Processing Error",
            "error": error_msg,
            "symptoms": [],
            "diagnoses": [],
            "medications": [],
            "critical_info": []
        }

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
    3. Only read patient_records_summary.json if detailed per-file info is needed
    4. Generate insights using the compiled information
    """
    archive_path = OUTPUT_DIR / archive_name
    log.info(f"Processing archive folder: {archive_path}")
    
    if not archive_path.exists():
        return f"Archive folder not found: {archive_name}"
    
    skill_file = archive_path / "SKILL.md"
    report_file = archive_path / "analysis_report.txt"
    results_file = archive_path / "patient_records_summary.json"
    
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
    
    # STEP 3: Only read patient_records_summary.json if we need detailed information (TODO: define criteria for when detailed results are needed, e.g. if total_files > 3 or if there were any failures)
    need_detailed_results = metadata.total_files > 3 or metadata.success_rate < 100.0
    
    if need_detailed_results:
        log.info(f"Reading patient_records_summary.json for detailed analysis (total_files={metadata.total_files}, success_rate={metadata.success_rate:.1f}%)")
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
                log.warning(f"Could not read patient_records_summary.json: {e}")
        else:
            log.warning(f"Patient records summary file not found for archive: {archive_name}")
    else:
        log.info("Skipping patient_records_summary.json (small number of files and 100% success rate)")
    
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



def process_image_file(filepath: Path) -> Union[PatientRecord, dict]:
    """Analyze medical image and extract findings into PatientRecord format."""
    pipe = get_pipeline()
    
    log.info(f"Loading image: {filepath}")
    image = Image.open(filepath)

    prompt = """Analyze this medical image and structure the findings into JSON format:
    {
        "patient_id": "IMAGE_<filename>",
        "name": "Image Analysis Result",
        "symptoms": ["list of clinical signs/symptoms observed"],
        "diagnoses": ["list of potential diagnoses or pathologies identified"],
        "medications": ["list of recommended treatments or interventions"],
        "critical_info": ["list of critical findings, alerts, or abnormalities"]
    }
    
    Return ONLY valid JSON, no other text.
    Include confidence levels or severity where relevant in the descriptions."""
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

    output = pipe(text=messages, max_new_tokens=2000,response_format=PatientRecord.schema())
    result_text = output[0]["generated_text"][-1]["content"]
    print("Model output for image analysis:", result_text)
    cleaned_result_text = clean_llm_json_output(result_text)
    print("Cleaned JSON text for parsing:", cleaned_result_text)

    log.info("Image analysis complete. Parsing into PatientRecord format...")
    
    try:
        # Parse JSON output from model using robust parser
        result_data = json.loads(cleaned_result_text)
        
        if not result_data:
            raise ValueError("JSON parsing returned empty dict")
        
        # Deduplicate critical_info
        critical_info = result_data.get("critical_info", [])
        if critical_info:
            critical_info = deduplicate_critical_info(critical_info)
            result_data["critical_info"] = critical_info
        
        # Validate and create PatientRecord
        patient_record = PatientRecord(
            patient_id=result_data.get("patient_id", f"IMAGE_{filepath.stem}"),
            name=result_data.get("name", "Image Analysis"),
            symptoms=result_data.get("symptoms", []),
            diagnoses=result_data.get("diagnoses", []),
            medications=result_data.get("medications", []),
            critical_info=critical_info
        )
        log.info(f"✓ Created PatientRecord from image: {filepath.name}")
        log.info(f"  - Symptoms: {len(patient_record.symptoms)}")
        log.info(f"  - Diagnoses: {len(patient_record.diagnoses)}")
        log.info(f"  - Medications: {len(patient_record.medications)}")
        log.info(f"  - Critical Info: {len(patient_record.critical_info)}")
        
        # Save to JSON file
        result_dict = patient_record.model_dump()
        save_patient_record_to_json(result_dict, f"IMAGE_{filepath.stem}.json")
        
        return result_dict
        
    except (json.JSONDecodeError, ValueError) as e:
        log.warning(f"Failed to parse model output as JSON: {e}. Attempting fallback extraction...")
        # Fallback: create record with raw result
        return PatientRecord(
            patient_id=f"IMAGE_{filepath.stem}",
            name="Image Analysis",
            symptoms=[],
            diagnoses=[],
            medications=[],
            critical_info=[result_text]  # Store raw analysis in critical_info
        ).model_dump()


def clean_llm_json_output(result_text: str) -> str:
    """
    Clean raw LLM output into parseable JSON string.
    
    Steps:
    1. Remove markdown code fences (```json ... ```)
    2. Truncate at the last complete string entry
    3. Remove trailing comma, close unclosed array and object
    
    Args:
        result_text: Raw text output from the LLM
        
    Returns:
        Cleaned JSON string ready for parsing
    """
    cleaned = result_text.strip()
    
    # 1. Remove markdown fence properly (substring, not chars)
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    
    # 2. Truncate at the last complete string entry
    last_quote = cleaned.rfind('"')
    if last_quote > 0:
        cleaned = cleaned[:last_quote + 1]
    
    # 3. Remove trailing comma, then close the array and object
    cleaned = cleaned.rstrip().rstrip(',') + ']}'
    
    return cleaned


def process_ehr_file(filepath: Path) -> Union[PatientRecord, dict]:
    """Analyze EHR record and extract into PatientRecord Pydantic format."""
    pipe = get_pipeline()
    
    log.info(f"Loading EHR record: {filepath}")
    record_text = filepath.read_text()

    prompt = """Extract and structure this EHR record into JSON format with these fields:
    - patient_id: string
    - name: string  
    - symptoms: list of symptom strings
    - diagnoses: list of diagnosis strings
    - medications: list of medication strings   
    - critical_info: list of critical information strings
    
    Return ONLY valid JSON, no other text."""
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
    result_text = output[0]["generated_text"][-1]["content"]
    log.debug(f"Raw model output: {result_text}...")
    
    cleaned = clean_llm_json_output(result_text)
    print("Cleaned JSON text for parsing:", cleaned)
    
    log.info("EHR analysis complete. Parsing into PatientRecord format...")
    
    try:
        # Parse JSON output from model using robust parser
        result_data = json.loads(cleaned)
        
        if not result_data:
            raise ValueError("JSON parsing returned empty dict")
        
        # Deduplicate critical_info to remove repetitive entries
        critical_info = result_data.get("critical_info", [])
        if critical_info:
            critical_info = deduplicate_critical_info(critical_info)
            result_data["critical_info"] = critical_info
        
        # Validate and create PatientRecord
        patient_record = PatientRecord(
            patient_id=result_data.get("patient_id", "UNKNOWN"),
            name=result_data.get("name", ""),
            symptoms=result_data.get("symptoms", []),
            diagnoses=result_data.get("diagnoses", []),
            medications=result_data.get("medications", []),
            critical_info=critical_info
        )
        log.info(f"✓ Created PatientRecord for {patient_record.patient_id}")
        log.info(f"  - Symptoms: {len(patient_record.symptoms)}")
        log.info(f"  - Diagnoses: {len(patient_record.diagnoses)}")
        log.info(f"  - Medications: {len(patient_record.medications)}")
        log.info(f"  - Critical Info: {len(patient_record.critical_info)} (deduplicated)")
        
        # Save to JSON file
        result_dict = patient_record.model_dump()
        save_patient_record_to_json(result_dict, f"{patient_record.patient_id}_ehr.json")
        
        return result_dict
        
    except (json.JSONDecodeError, ValueError) as e:
        log.warning(f"Failed to parse model output as JSON: {e}. Attempting fallback extraction...")
        # Fallback: create empty record if parsing fails
        return PatientRecord(
            patient_id="UNKNOWN",
            name="",
            symptoms=[],
            diagnoses=[],
            medications=[],
            critical_info=[result_text]  # Store raw result in critical_info
        ).model_dump()


def should_continue_processing(state: dict) -> str:
    """Decide whether to process another item or finish."""
    if state["current_file_index"] < len(state["input_files"]):
        return "process_file"
    else:
        return "finalize"
