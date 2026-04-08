"""
Pytest tests for clean_llm_json_output function.
"""

import json
import sys
import pytest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from agents.processing_agent import clean_llm_json_output


class TestCleanLlmJsonOutput:
    """Tests for clean_llm_json_output()."""

    def test_removes_markdown_fence(self):
        """Should strip ```json and ``` wrappers."""
        raw = '```json\n{"patient_id": "P001", "symptoms": ["fever"]}\n```'
        cleaned = clean_llm_json_output(raw)
        data = json.loads(cleaned)
        assert data["patient_id"] == "P001"

    def test_valid_json_passthrough(self):
        """Already-valid JSON should still parse after cleaning."""
        raw = '{"patient_id": "P002", "name": "Jane", "symptoms": [], "critical_info": ["alert"]}'
        cleaned = clean_llm_json_output(raw)
        data = json.loads(cleaned)
        assert data["patient_id"] == "P002"
        assert data["name"] == "Jane"

    def test_truncated_json_gets_closed(self):
        """Incomplete JSON cut mid-array should be closed with ]}."""
        raw = '```json\n{"patient_id": "P003", "critical_info": ["item1", "item2", "item3'
        cleaned = clean_llm_json_output(raw)
        print("Cleaned JSON text for parsing:", cleaned)
        data = json.loads(cleaned)
        assert data["patient_id"] == "P003"
        assert "item2" in data["critical_info"]

    def test_trailing_comma_removed(self):
        """Trailing comma before closure should not break parsing."""
        raw = '```json\n{"patient_id": "P004", "symptoms": ["cough", "fever",]}\n```'
        cleaned = clean_llm_json_output(raw)
        data = json.loads(cleaned)
        assert len(data["symptoms"]) == 2

    def test_truncated_mid_entry_with_duplicates(self):
        """Real-world case: duplicate entries, JSON truncated mid-string."""
        raw = (
            '```json\n'
            '{\n'
            '  "patient_id": "P0012345",\n'
            '  "name": "Mr. John Doe",\n'
            '  "symptoms": ["Tinnitus", "Epigastric pain"],\n'
            '  "diagnoses": ["Pancreatitis"],\n'
            '  "medications": ["Insulin"],\n'
            '  "critical_info": [\n'
            '    "History of Whipple procedure",\n'
            '    "History of high CA 19-9",\n'
            '    "History of epigastric pain prompting contrast CT",\n'
            '    "History of epigastric pain prompting contrast CT",\n'
            '    "History of abdominal pain (low abdomen, crampy, 4 hours duration, resolved)'
        )
        cleaned = clean_llm_json_output(raw)
        print("Cleaned JSON text for parsing:", cleaned)
        data = json.loads(cleaned)
        assert data["patient_id"] == "P0012345"
        assert data["name"] == "Mr. John Doe"
        assert len(data["critical_info"]) >= 2

    def test_only_closing_fence(self):
        """JSON with only trailing ``` fence."""
        raw = '{"patient_id": "P005", "symptoms": ["headache"]}\n```'
        cleaned = clean_llm_json_output(raw)
        data = json.loads(cleaned)
        assert data["patient_id"] == "P005"

    def test_empty_string(self):
        """Empty input should not raise."""
        cleaned = clean_llm_json_output("")
        assert isinstance(cleaned, str)

    def test_no_quotes_in_input(self):
        """Input with no quotes should not crash."""
        cleaned = clean_llm_json_output("no json here")
        assert isinstance(cleaned, str)

    def test_preserves_all_fields(self):
        """All PatientRecord fields should survive cleaning."""
        raw = (
            '```json\n'
            '{\n'
            '  "patient_id": "P006",\n'
            '  "name": "Test Patient",\n'
            '  "symptoms": ["fever", "cough"],\n'
            '  "diagnoses": ["flu"],\n'
            '  "medications": ["acetaminophen"],\n'
            '  "critical_info": ["allergic to penicillin"]\n'
            '}\n'
            '```'
        )
        cleaned = clean_llm_json_output(raw)
        data = json.loads(cleaned)
        assert data["patient_id"] == "P006"
        assert data["symptoms"] == ["fever", "cough"]
        assert data["diagnoses"] == ["flu"]
        assert data["medications"] == ["acetaminophen"]
        assert data["critical_info"] == ["allergic to penicillin"]
