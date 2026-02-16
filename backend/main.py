"""
CareBuddy: Medical Image & EHR Analysis System
Entry point for the LangGraph multi-agent orchestrator.
"""

from agent_orchestrator import run_orchestrator


if __name__ == "__main__":
    final_state = run_orchestrator()
