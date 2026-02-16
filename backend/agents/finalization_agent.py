"""
Finalization Agent: Aggregates processing results and saves to results.json.
"""

import json
from pathlib import Path
from langchain_core.messages import AIMessage
import logging as log
from utils import INPUT_DIR, OUTPUT_DIR


def finalize_results(state: dict) -> dict:
    """Aggregate and format final results."""
    log.info("Finalizing results...")
    
    summary = {
        "total_files": len(state["input_files"]),
        "processed_files": len(state["file_results"]),
        "results": state["file_results"]
    }

    # Log summary
    log.info("\n" + "="*80)
    log.info("MULTI-AGENT PROCESSING SUMMARY")
    log.info("="*80)
    log.info(f"Total files: {summary['total_files']}")
    log.info(f"Successfully processed: {summary['processed_files']}")
    log.info("Detailed Results:")
    log.info("-"*80)

    for filename, result in state["file_results"].items():
        log.info(f"📄 {filename}:")
        log.info(f"  {result[:200]}..." if len(result) > 200 else f"  {result}")

    log.info("="*80)

    # Save to results.json
    results_file = OUTPUT_DIR / "results.json"
    results_file.write_text(json.dumps(summary, indent=2))
    log.info(f"Results saved to: {results_file}")

    state["messages"].append(
        AIMessage(content=f"Processing complete. {summary['processed_files']}/{summary['total_files']} files processed successfully.")
    )

    return state
