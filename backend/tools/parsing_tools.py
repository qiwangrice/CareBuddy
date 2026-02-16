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
        return f"SkillMetadata(archive={self.archive_folder}, success_rate={self.success_rate:.1f}%)"

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
    
    content = skill_md_path.read_text()
    
    try:
        name = re.search(r"name:\s*(.+)", content).group(1).strip()
        description = re.search(r"description:\s*(.+)", content).group(1).strip()
        # Extract archive folder name from file path
        archive_folder = skill_md_path.parent.name
        
        # Extract Generated timestamp
        timestamp_match = re.search(r"Generated:\s*(.+)", content)
        generated_timestamp = timestamp_match.group(1).strip() if timestamp_match else "Unknown"
        
        # Extract Processing Statistics
        total_files_match = re.search(r"Total Files:\s*(\d+)", content)
        total_files = int(total_files_match.group(1)) if total_files_match else 0
        
        processed_match = re.search(r"Successfully Processed:\s*(\d+)", content)
        successfully_processed = int(processed_match.group(1)) if processed_match else 0
        
        success_rate_match = re.search(r"Success Rate:\s*([\d.]+)%", content)
        success_rate = float(success_rate_match.group(1)) if success_rate_match else 0.0
        
        # Extract System Information
        device_match = re.search(r"Device Used:\s*(.+)", content)
        device_used = device_match.group(1).strip() if device_match else "Unknown"
        
        dtype_match = re.search(r"Data Type:\s*(.+)", content)
        data_type = dtype_match.group(1).strip() if dtype_match else "Unknown"
        
        model_match = re.search(r"Model:\s*(.+)", content)
        model = model_match.group(1).strip() if model_match else "Unknown"
        
        # Extract Output Files
        output_files = []
        files_section = re.search(r"Output Files\n((?:- `.+?`\n?)*)", content)
        if files_section:
            file_lines = files_section.group(1).splitlines()
            output_files = [
                line.replace("- `", "").replace("`", "").strip() 
                for line in file_lines if line.strip().startswith("-")
            ]
        
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
            output_files=output_files
        )
    
    except Exception as e:
        print(f"Error parsing SKILL.md at {skill_md_path}: {e}")
        return None

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