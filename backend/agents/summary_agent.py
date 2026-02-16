"""
Summary Agent: Generates comprehensive analysis report from results.json.
"""

import json
from pathlib import Path
from langchain_core.messages import AIMessage
import logging as log
from utils import get_pipeline, INPUT_DIR, OUTPUT_DIR

def summarize_results(state: dict) -> dict:
    """
    Summary agent: read results.json and generate a comprehensive report.
    """
    log.info("Generating comprehensive summary report...")
    
    results_file = OUTPUT_DIR / "results.json"
    if not results_file.exists():
        log.warning("No results.json found. Skipping summary generation.")
        return state

    # Read results
    summary_data = json.loads(results_file.read_text())
    
    # Generate detailed report
    report_lines = [
        "\n" + "="*80,
        "COMPREHENSIVE ANALYSIS REPORT",
        "="*80,
        f"\nProcessing Summary:",
        f"  • Total files processed: {summary_data['total_files']}",
        f"  • Successfully processed: {summary_data['processed_files']}",
        f"  • Success rate: {(summary_data['processed_files']/max(summary_data['total_files'], 1)*100):.1f}%",
        f"\nDetailed Analysis Results:",
        "-"*80,
    ]

    # summarize the results using the medical model
    pipe = get_pipeline()

    summarize_results = ""

    for filename, result in summary_data["results"].items():
        
        # Truncate long results for readability
        if isinstance(result, dict):
            result_text = json.dumps(result, indent=2)
        else:
            result_text = str(result)
        
        summarize_results += f"  {result_text}"
    
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": summarize_results},
                {"type": "text", "text": "Summarize the overall findings from all processed files in maximum 500 wrods. Highlight any critical insights, common patterns, or notable observations across the dataset. Provide a concise summary that captures the key takeaways from the analysis."}
            ]
        }
    ]

    log.info("Generating summary from results.json using the medical model...")
    
    output = pipe(text=messages, max_new_tokens=2000)
    result = output[0]["generated_text"][-1]["content"]

    report_lines.append(f"\n{result}\n")
    
    report_lines.extend([
        "\n" + "="*80,
        "END OF REPORT",
        "="*80 + "\n"
    ])

    # Log report
    report_text = "\n".join(report_lines)
    log.info(report_text)

    # Save detailed report
    report_file = OUTPUT_DIR / "analysis_report.txt"
    report_file.write_text(report_text)
    log.info(f"Detailed report saved to: {report_file}")

    state["messages"].append(
        AIMessage(content=f"Generated comprehensive analysis report.")
    )

    return state
