"""
Summary Agent: Generates comprehensive analysis report from results.json.
"""

import json
from pathlib import Path
from langchain_core.messages import AIMessage
import logging as log
from utils import get_pipeline, INPUT_DIR, OUTPUT_DIR, archive_results
from pydantic import BaseModel
from typing import List

summary_prompt_template = """You are a primary care physician. 
Based on the comprehensive analysis results provided in the input JSON, generate a brief summary highlighting   the key insights, patterns, and observations derived from the analysis of the dataset in less than 10 sentences. 

Input:
{{INPUT_JSON}} 
"""

concern_prompt_template = """You are a primary care physician. Based on the comprehensive analysis results provided in the input JSON, identify any potential concerns or red flags in less than 5 sentences.
Input:
{{INPUT_JSON}}
"""

key_insights_prompt_template = """You are a primary care physician. Based on the comprehensive analysis results provided in the input JSON, identify the key insights and patterns in less than 5 sentences.
Input:
{{INPUT_JSON}}
"""
recommendation_prompt_template = """You are a primary care physician. Based on the comprehensive analysis results provided in the input JSON, provide recommendations for next steps in patient care in less than 5 sentences.
Input:
{{INPUT_SUMMARY}}
"""

class SummaryRecord(BaseModel):
    summary: str
    key_insights: str
    concern: str
    recommendation: str

def summarize_results(state: dict) -> dict:
    """
    Summary agent: read patient_records_summary.json and generate a comprehensive report.
    """
    log.info("Generating comprehensive summary report...")
    
    results_file = OUTPUT_DIR / "patient_records_summary.json"
    if not results_file.exists():
        log.warning("No patient_records_summary.json found. Skipping summary generation.")
        return state

    # Read results
    INPUT_JSON = json.loads(results_file.read_text())

    print("=" * 80)
    print("Input JSON:")
    print(json.dumps(INPUT_JSON, indent=2))

    # summarize the results using the medical model
    pipe = get_pipeline()
    
    summary_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": summary_prompt_template.replace("{{INPUT_JSON}}", json.dumps(INPUT_JSON))}
            ]
        }
    ]

    log.info("Generating summary from results.json using the medical model...")
    
    output = pipe(text=summary_messages, max_new_tokens=20000)
    summary = output[0]["generated_text"][-1]["content"]

    print("=" * 80)
    print(summary)

    concern_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": concern_prompt_template.replace("{{INPUT_JSON}}", json.dumps(INPUT_JSON["diagnosis_validation"]))}
            ]
        }
    ]
    concern_output = pipe(text=concern_messages, max_new_tokens=20000)
    concern = concern_output[0]["generated_text"][-1]["content"]

    print("=" * 80)
    print(concern)

    key_insights_messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": key_insights_prompt_template.replace("{{INPUT_JSON}}", json.dumps(INPUT_JSON["detailed_results"]))}
            ]
        }   
    ]
    key_insights_output = pipe(text=key_insights_messages, max_new_tokens=20000)    
    key_insights = key_insights_output[0]["generated_text"][-1]["content"]

    print("=" * 80)
    print(key_insights)

    recommendation_messages = [
        {
            "role": "user",
            "content": [           
                {"type": "text", "text": recommendation_prompt_template.replace("{{INPUT_SUMMARY}}", summary)}
            ]
        }
    ]
    recommendation_output = pipe(text=recommendation_messages, max_new_tokens=20000)
    recommendation = recommendation_output[0]["generated_text"][-1]["content"]

    print("=" * 80)
    print(recommendation)

    cleaned_result = {
        "summary": summary,
        "key_insights": key_insights,
        "concern": concern,
        "recommendation": recommendation
    }

    print("=" * 80)
    print("Cleaned Result:")
    print(cleaned_result)

    cleaned_result["symptoms"] = list(INPUT_JSON.get("symptom_disease_associations", {}).keys())
    cleaned_result["high_confidence_diagnosis"] = INPUT_JSON.get("diagnosis_validation", {}).get("high_confidence_diagnoses", [])
    cleaned_result["diagnosis_with_uncertainty"] = INPUT_JSON.get("diagnosis_validation", {}).get("concern_diagnoses", [])
    
    print("=" * 80)
    print("Final Result with Additional Fields:")
    print(cleaned_result)

    # Save detailed report
    report_file = OUTPUT_DIR / "analysis_report.json"
    report_file.write_text(json.dumps(cleaned_result, indent=2))
    log.info(f"Detailed report saved to: {report_file}")

    # Archive results to timestamped folder with SKILL.md
    archive_results(
        total_files=INPUT_JSON['total_files'],
        processed_files=INPUT_JSON['processed_files'],
        description=cleaned_result.get("summary", "" )
    )

    return state
