"""
LangGraph-based multi-agent orchestrator for processing medical images and EHR records.
Dynamically spawns subagents based on files in the input folder.

Architecture:
- Discovery Agent: Scans input/ folder
- Processing Agent: Routes and processes files (images/EHR)
- Finalization Agent: Aggregates results
- Summary Agent: Generates comprehensive report
"""

from typing import List, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage
import logging as log

from agents import (
    discover_input_files,
    process_file_worker,
    should_continue_processing,
    finalize_results,
    summarize_results,
)
from utils import DEVICE, DTYPE, PIPE


class AgentState(TypedDict):
    """State shared across all agents in the graph."""
    input_files: List[str]
    file_results: dict  # Maps filename to analysis result
    current_file_index: int
    messages: List[BaseMessage]


def build_orchestrator_graph() -> StateGraph:
    """Build the LangGraph orchestrator."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("discover", discover_input_files)
    graph.add_node("process_file", process_file_worker)
    graph.add_node("finalize", finalize_results)
    graph.add_node("summarize", summarize_results)

    # Add edges
    graph.add_edge("discover", "process_file")
    graph.add_conditional_edges(
        "process_file",
        should_continue_processing,
        {
            "process_file": "process_file",
            "finalize": "finalize"
        }
    )
    graph.add_edge("finalize", "summarize")
    graph.add_edge("summarize", END)

    # Set entry point
    graph.set_entry_point("discover")

    return graph


def run_orchestrator():
    """Execute the multi-agent orchestrator."""
    log.info("\n" + "="*80)
    log.info("CAREBUDDY: LangGraph Multi-Agent Medical Image & EHR Analyzer")
    log.info("="*80)
    log.info(f"Configuration: device={DEVICE}, dtype={DTYPE}")
    log.info("="*80 + "\n")

    # Build graph
    graph = build_orchestrator_graph()
    runnable = graph.compile()

    # Initial state
    initial_state = {
        "input_files": [],
        "file_results": {},
        "current_file_index": 0,
        "messages": []
    }

    # Execute
    final_state = runnable.invoke(initial_state)

    return final_state


if __name__ == "__main__":
    final_state = run_orchestrator()
