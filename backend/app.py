"""
FastAPI backend service for CareBuddy.
Provides REST API endpoints for medical image and EHR analysis.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from utils import get_logger
from tools.parsing_tools import parse_skill_md, parse_all_skill_md, SkillMetadata

from agent_orchestrator import run_orchestrator

log = get_logger(__name__)

app = FastAPI(
    title="CareBuddy API",
    description="Medical Image & EHR Analysis System",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure input/output directories exist
INPUT_DIR = Path("./results/input")
OUTPUT_DIR = Path("./results/output")
INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Pydantic models
class AnalysisResult(BaseModel):
    filename: str
    result: str
    status: str = "success"
    error: Optional[str] = None


class ProcessingStatus(BaseModel):
    status: str
    total_files: int
    processed_files: int
    results: List[AnalysisResult]
    summary_report: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    device: str
    model: str


# Global state
processing_state = {
    "is_processing": False,
    "results": [],
    "total_files": 0,
    "processed_files": 0,
}


@app.get("/health", response_model=HealthResponse)
async def health():
    """Device health check endpoint."""
    from utils import get_device, get_dtype
    
    return HealthResponse(
        status="healthy",
        device=str(get_device()),
        model="google/medgemma-1.5-4b-it"
    )


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload medical images or EHR records for processing."""
    log.info(f"Received {len(files)} file(s) for upload")
    
    uploaded = []
    for file in files:
        try:
            file_path = INPUT_DIR / file.filename
            content = await file.read()
            file_path.write_bytes(content)
            log.info(f"Uploaded: {file.filename}")
            uploaded.append({
                "filename": file.filename,
                "size": len(content),
                "status": "uploaded"
            })
        except Exception as e:
            log.error(f"Error uploading {file.filename}: {str(e)}")
            uploaded.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "total_uploaded": len(uploaded),
        "files": uploaded
    }


@app.post("/process")
async def process_files():
    """Start processing uploaded files. a) Run the multi-agent orchestrator, b) Parse summary report."""
    if processing_state["is_processing"]:
        raise HTTPException(status_code=409, detail="Processing already in progress")
    
    log.info("Starting file processing...")
    processing_state["is_processing"] = True
    processing_state["results"] = []
    
    try:
        
        # Run orchestrator
        final_state = run_orchestrator()
        
        # Parse results
        results_file = OUTPUT_DIR / "patient_records_summary.json"
        if results_file.exists():
            results_data = json.loads(results_file.read_text())
            processing_state["total_files"] = results_data.get("total_files", 0)
            processing_state["processed_files"] = results_data.get("processed_files", 0)
            
            # Extract results - key is "detailed_results" in patient_records_summary.json
            for filename, result in results_data.get("detailed_results", {}).items():
                # Convert dict results to JSON string for AnalysisResult model
                result_str = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
                processing_state["results"].append({
                    "filename": filename,
                    "result": result_str,
                    "status": "success"
                })
        
        log.info("Processing completed successfully")
        return {
            "status": "completed",
            "total_files": processing_state["total_files"],
            "processed_files": processing_state["processed_files"],
            "results": processing_state["results"]
        }
        
    except Exception as e:
        log.error(f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        processing_state["is_processing"] = False


@app.get("/status", response_model=ProcessingStatus)
async def get_status():
    """Get current processing status."""
    report = None
    report_file = OUTPUT_DIR / "analysis_report.json"
    if report_file.exists():
        report = report_file.read_text()
    
    return ProcessingStatus(
        status="processing" if processing_state["is_processing"] else "idle",
        total_files=processing_state["total_files"],
        processed_files=processing_state["processed_files"],
        results=[
            AnalysisResult(
                filename=r["filename"],
                result=r.get("result", ""),
                status=r.get("status", "success"),
                error=r.get("error")
            )
            for r in processing_state["results"]
        ],
        summary_report=report
    )


@app.get("/results/{filename}")
async def get_result(filename: str):
    """Get individual file analysis result."""
    for result in processing_state["results"]:
        if result["filename"] == filename:
            return result
    
    raise HTTPException(status_code=404, detail=f"Result not found for {filename}")


@app.get("/reports/analysis")
async def get_analysis_report():
    """Download the analysis report as text or JSON."""
    # Try JSON first, then fall back to txt
    report_json = OUTPUT_DIR / "analysis_report.json"
    report_txt = OUTPUT_DIR / "analysis_report.txt"
    
    if report_json.exists():
        # Convert JSON to readable text format
        content = json.loads(report_json.read_text())
        
        # Format the report as plain text
        text_report = f"""COMPREHENSIVE ANALYSIS REPORT
{'='*50}

SUMMARY
{'-'*50}
{content.get('summary', 'Not available')}

HIGH CONFIDENCE DIAGNOSES
{'-'*50}
{json.dumps(content.get('high_confidence_diagnosis', []), indent=2) if content.get('high_confidence_diagnosis') else 'None identified'}

DIAGNOSES WITH UNCERTAINTY
{'-'*50}
{json.dumps(content.get('diagnosis_with_uncertainty', []), indent=2) if content.get('diagnosis_with_uncertainty') else 'None identified'}

SYMPTOMS
{'-'*50}
{json.dumps(content.get('symptoms', []), indent=2) if content.get('symptoms') else 'None identified'}

CONCERNS
{'-'*50}
{content.get('concern', 'Not available')}

RECOMMENDATIONS
{'-'*50}
{content.get('recommendation', 'Not available')}
"""
        return {
            "status": "success",
            "content": text_report,
            "filename": "analysis_report.txt"
        }
    elif report_txt.exists():
        return FileResponse(
            report_txt,
            media_type="text/plain",
            filename="analysis_report.txt"
        )
    else:
        raise HTTPException(status_code=404, detail="Report not available yet")


@app.get("/reports/analysis/content")
async def get_analysis_report_content():
    """Get the analysis report content as JSON with all sections."""
    report_file = OUTPUT_DIR / "analysis_report.json"
    if not report_file.exists():
        raise HTTPException(status_code=404, detail="Report not available yet")
    
    content = json.loads(report_file.read_text())
    log.info("Retrieved analysis report content")

    log.info(json.dumps(content, indent=2)[:500] + "..." if len(json.dumps(content, indent=2)) > 500 else json.dumps(content, indent=2))
    
    return {
        "status": "success",
        "filename": "analysis_report.json",
        "summary": content.get('summary', ''),
        "high_confidence_diagnosis": content.get('high_confidence_diagnosis', []),
        "diagnosis_with_uncertainty": content.get('diagnosis_with_uncertainty', []),
        "concern": content.get('concern', ''),
        "recommendation": content.get('recommendation', ''),
        "symptoms": content.get('symptoms', [])
    }


@app.get("/reports/patient_records_summary.json")
async def get_patient_records_summary_json():
    """Download the patient records summary JSON."""
    summary_file = OUTPUT_DIR / "patient_records_summary.json"
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Patient records summary not available yet")
    
    return FileResponse(
        summary_file,
        media_type="application/json",
        filename="patient_records_summary.json"
    )


@app.delete("/reset")
async def reset():
    """Reset processing state and clear uploaded files."""
    log.info("Resetting system state...")
    
    # Clear input files
    for file in INPUT_DIR.glob("*"):
        if file.is_file():
            file.unlink()
    
    # Reset state
    processing_state["is_processing"] = False
    processing_state["results"] = []
    processing_state["total_files"] = 0
    processing_state["processed_files"] = 0
    
    log.info("System reset completed")
    return {"status": "reset"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "CareBuddy API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/archives/skill")
async def list_all_archives_skill():
    """List all SKILL metadata from all archive folders."""
    try:
        all_metadata = parse_all_skill_md(OUTPUT_DIR)
        metadata_list = [
            {
                "archive_folder": m.archive_folder,
                "generated_timestamp": m.generated_timestamp,
                "total_files": m.total_files,
                "successfully_processed": m.successfully_processed,
                "success_rate": m.success_rate,
                "device_used": m.device_used,
                "data_type": m.data_type,
                "model": m.model,
                "output_files": m.output_files
            }
            for m in all_metadata.values()
        ]
        log.info(f"Retrieved {len(metadata_list)} archive SKILL metadata")
        return {
            "status": "success",
            "total_archives": len(metadata_list),
            "archives": sorted(metadata_list, key=lambda x: x["archive_folder"], reverse=True)
        }
    except Exception as e:
        log.error(f"Error listing archives SKILL: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/archives/skill/{archive_name}")
async def get_archive_skill(archive_name: str):
    """Get SKILL metadata for a specific archive folder."""
    try:
        skill_file = OUTPUT_DIR / archive_name / "SKILL.md"
        metadata = parse_skill_md(skill_file)
        
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Archive '{archive_name}' not found or invalid")
        
        log.info(f"Retrieved SKILL metadata for archive: {archive_name}")
        return {
            "status": "success",
            "archive_folder": metadata.archive_folder,
            "generated_timestamp": metadata.generated_timestamp,
            "total_files": metadata.total_files,
            "successfully_processed": metadata.successfully_processed,
            "success_rate": metadata.success_rate,
            "device_used": metadata.device_used,
            "data_type": metadata.data_type,
            "model": metadata.model,
            "output_files": metadata.output_files
        }
    except Exception as e:
        log.error(f"Error getting archive SKILL {archive_name}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
