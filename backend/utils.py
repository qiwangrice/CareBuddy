"""
Shared utilities for CareBuddy orchestrator.
Handles device selection, pipeline initialization, and logging.
"""

import logging
import torch
from pathlib import Path
from transformers import pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

INPUT_DIR = Path("./results/input")
OUTPUT_DIR = Path("./results/output")

# Auto-select device
if torch.cuda.is_available():
    DEVICE = "cuda"
elif getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

# Choose safe dtype
if hasattr(torch, "bfloat16") and (DEVICE != "cpu"):
    DTYPE = torch.bfloat16
else:
    DTYPE = torch.float32

log.info(f"Using device={DEVICE}, dtype={DTYPE}")

# Initialize shared model pipeline
PIPE = pipeline(
    "image-text-to-text",
    model="google/medgemma-1.5-4b-it",
    torch_dtype=DTYPE,
    device=DEVICE,
)


def get_pipeline():
    """Get the shared pipeline instance."""
    return PIPE


def get_device():
    """Get the selected device."""
    return DEVICE


def get_dtype():
    """Get the selected dtype."""
    return DTYPE


def get_logger(name: str):
    """Get a logger instance for a module."""
    return logging.getLogger(name)
