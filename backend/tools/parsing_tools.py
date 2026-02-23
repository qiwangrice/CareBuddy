import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path
from datetime import datetime

@dataclass
class SkillMetadata:
    """Parsed SKILL.md metadata from archive folders."""
    name: str
    description: str
    archive_folder: str
    generated_timestamp: str
    total_files: int
    successfully_processed: int
    success_rate: float
    device_used: str
    data_type: str
    model: str
    output_files: List[str]
    
    def __str__(self) -> str:
        rate_str = f"{self.success_rate:.1f}%" if self.success_rate is not None else "N/A"
        return f"SkillMetadata(archive={self.archive_folder}, success_rate={rate_str})"

def parse_skill_md(skill_md_path: Path) -> Optional[SkillMetadata]:
    """
    Parse a single SKILL.md file and extract metadata.
    
    Args:
        skill_md_path: Path to SKILL.md file
        
    Returns:
        SkillMetadata object or None if parsing fails
    """
    if not skill_md_path.exists():
        return None

    name = description = archive_folder = generated_timestamp = device_used = data_type = model = success_rate = total_files = successfully_processed = None
    tab= ": "
    file1 = open(skill_md_path, 'r')
    for line in file1:
        line = line.strip()
        tmp = line.strip().split(tab)
        if len(tmp) < 2:
            continue  # Skip lines that don't have the expected format
        if tmp[0].startswith("name"):
            name = tmp[1]
        elif tmp[0].startswith("description"):
            description = tmp[1].strip()
        elif "Archive Folder" in line:
            archive_folder = tmp[1].strip()
        elif "Generated" in line:
            generated_timestamp = tmp[1].strip()
        elif "Total Files" in line:
            total_files = int(tmp[1])
        elif "Successfully Processed" in line:
            successfully_processed = int(tmp[1])
        elif "Success Rate" in line:
            success_rate = float(tmp[1].replace("%", ""))
        elif "Device Used" in line:
            device_used = tmp[1].strip()
        elif "Data Type" in line:
            data_type = tmp[1].strip()
        elif "Model" in line:
            model = tmp[1].strip()
    success_rate_str = f"{success_rate:.1f}%" if success_rate is not None else "N/A"

    return SkillMetadata(
        name=name,
        description=description,
            archive_folder=archive_folder,
            generated_timestamp=generated_timestamp,
            total_files=total_files,
            successfully_processed=successfully_processed,
            success_rate=success_rate,
            device_used=device_used,
            data_type=data_type,
            model=model,
            output_files=['results.json', 'analysis_report.txt'] # default
        )

def parse_all_skill_md(output_dir: Path) -> Dict[str, SkillMetadata]:
    """
    Parse all SKILL.md files from archive folders in output directory.
    
    Args:
        output_dir: Path to results/output directory
        
    Returns:
        Dictionary mapping archive folder names to SkillMetadata objects
    """
    skills_metadata: Dict[str, SkillMetadata] = {}
    
    if not output_dir.exists():
        return skills_metadata
    
    # Find all SKILL.md files in archive folders
    for skill_file in output_dir.glob("*/SKILL.md"):
        metadata = parse_skill_md(skill_file)
        if metadata:
            skills_metadata[metadata.archive_folder] = metadata
    
    return skills_metadata