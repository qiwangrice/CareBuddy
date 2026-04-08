"""
Unit tests for processing_agent.py - specifically the process_ehr_file function.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Import the function and model to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from agents.processing_agent import process_ehr_file, PatientRecord


class TestProcessEhrFile:
    """Test suite for process_ehr_file function."""

    @pytest.fixture
    def mock_pipeline(self):
        """Mock the get_pipeline function."""
        with patch("agents.processing_agent.get_pipeline") as mock:
            yield mock

    @pytest.fixture
    def sample_ehr_content(self):
        """Sample EHR record content."""
        return """
        Patient ID: P12345
        Patient Name: John Smith
        DOB: 01/15/1975
        
        Chief Complaint: Severe headache and fever for 3 days
        
        Symptoms:
        - High fever (101.5°F)
        - Severe headache
        - Sensitivity to light
        - Neck stiffness
        
        Medical History:
        - Hypertension (diagnosed 2010)
        - Type 2 Diabetes
        
        Current Medications:
        - Lisinopril 10mg daily
        - Metformin 500mg twice daily
        - Aspirin 81mg daily
        
        Physical Examination:
        - Blood pressure: 140/90 mmHg
        - Heart rate: 92 bpm
        - Temperature: 101.8°F
        - Positive Kernig's and Brudzinski's signs
        
        Assessment and Plan:
        Suspected meningitis. Urgent admission needed.
        """

    @pytest.fixture
    def sample_model_response(self):
        """Sample structured JSON response from model."""
        return {
            "patient_id": "P12345",
            "name": "John Smith",
            "symptoms": ["high fever", "severe headache", "sensitivity to light", "neck stiffness"],
            "diagnoses": ["suspected meningitis"],
            "medications": ["Lisinopril 10mg daily", "Metformin 500mg twice daily", "Aspirin 81mg daily"],
            "critical_info": ["positive Kernig's and Brudzinski's signs", "urgent admission needed"]
        }

    def test_process_ehr_file_success(self, mock_pipeline, sample_ehr_content, sample_model_response):
        """Test successful EHR file processing with valid JSON output."""
        # Setup mock
        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        mock_pipe.return_value = [
            {
                "generated_text": [
                    {},
                    {"content": json.dumps(sample_model_response)}
                ]
            }
        ]

        # Create temporary EHR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_ehr_content)
            temp_file = Path(f.name)

        try:
            # Execute
            result = process_ehr_file(temp_file)

            # Assertions
            assert isinstance(result, dict), "Result should be a dictionary"
            assert result['patient_id'] == "P12345"
            assert result['name'] == "John Smith"
            assert len(result['symptoms']) == 4
            assert "high fever" in result['symptoms']
            assert len(result['medications']) == 3
            assert "suspected meningitis" in result['diagnoses']
            assert len(result['critical_info']) == 2

        finally:
            temp_file.unlink()

    def test_process_ehr_file_valid_patient_record(self, mock_pipeline, sample_ehr_content, sample_model_response):
        """Test that output conforms to PatientRecord schema."""
        # Setup mock
        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        mock_pipe.return_value = [
            {
                "generated_text": [
                    {},
                    {"content": json.dumps(sample_model_response)}
                ]
            }
        ]

        # Create temporary EHR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_ehr_content)
            temp_file = Path(f.name)

        try:
            # Execute
            result = process_ehr_file(temp_file)

            # Validate that result can be instantiated as PatientRecord
            patient_record = PatientRecord(**result)
            assert patient_record.patient_id == "P12345"
            assert isinstance(patient_record.symptoms, list)
            assert isinstance(patient_record.diagnoses, list)
            assert isinstance(patient_record.medications, list)
            assert isinstance(patient_record.critical_info, list)

        finally:
            temp_file.unlink()

    def test_process_ehr_file_invalid_json_fallback(self, mock_pipeline, sample_ehr_content):
        """Test fallback behavior when model returns invalid JSON."""
        # Setup mock to return invalid JSON
        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        invalid_response = "This is not valid JSON - the model failed to parse"
        mock_pipe.return_value = [
            {
                "generated_text": [
                    {},
                    {"content": invalid_response}
                ]
            }
        ]

        # Create temporary EHR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_ehr_content)
            temp_file = Path(f.name)

        try:
            # Execute
            result = process_ehr_file(temp_file)

            # Assertions - should create fallback record
            assert isinstance(result, dict)
            assert result['patient_id'] == "UNKNOWN"
            assert result['name'] == ""
            assert result['symptoms'] == []
            assert result['diagnoses'] == []
            assert result['medications'] == []
            # Invalid response should be stored in critical_info
            assert len(result['critical_info']) > 0
            assert invalid_response in result['critical_info']

        finally:
            temp_file.unlink()

    def test_process_ehr_file_missing_fields(self, mock_pipeline, sample_ehr_content):
        """Test handling of missing fields in model response."""
        # Model returns partial JSON
        partial_response = {
            "patient_id": "P99999",
            "name": "Jane Doe"
            # Missing symptoms, diagnoses, medications, critical_info
        }

        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        mock_pipe.return_value = [
            {
                "generated_text": [
                    {},
                    {"content": json.dumps(partial_response)}
                ]
            }
        ]

        # Create temporary EHR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_ehr_content)
            temp_file = Path(f.name)

        try:
            # Execute
            result = process_ehr_file(temp_file)

            # Assertions - should fill in defaults
            assert result['patient_id'] == "P99999"
            assert result['name'] == "Jane Doe"
            assert result['symptoms'] == []
            assert result['diagnoses'] == []
            assert result['medications'] == []
            assert result['critical_info'] == []

        finally:
            temp_file.unlink()

    def test_process_ehr_file_with_special_characters(self, mock_pipeline, sample_ehr_content):
        """Test processing EHR with special characters and unicode."""
        # Response with special characters
        response_with_special_chars = {
            "patient_id": "P12345",
            "name": "José García-López",
            "symptoms": ["fever (101.5°F)", "Körper-schmerz"],
            "diagnoses": ["Influenza A (H3N2)"],
            "medications": ["Ibuprofen 400mg"],
            "critical_info": ["Patient requires 24/7 monitoring. Do NOT discharge until fever subsides."]
        }

        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        mock_pipe.return_value = [
            {
                "generated_text": [
                    {},
                    {"content": json.dumps(response_with_special_chars)}
                ]
            }
        ]

        # Create temporary EHR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_ehr_content)
            temp_file = Path(f.name)

        try:
            # Execute
            result = process_ehr_file(temp_file)

            # Assertions
            assert result['name'] == "José García-López"
            assert "fever (101.5°F)" in result['symptoms']
            assert "Influenza A (H3N2)" in result['diagnoses']

        finally:
            temp_file.unlink()

    def test_process_ehr_file_empty_lists(self, mock_pipeline, sample_ehr_content):
        """Test handling of empty lists in response."""
        response_with_empty_lists = {
            "patient_id": "P55555",
            "name": "Test Patient",
            "symptoms": [],
            "diagnoses": [],
            "medications": [],
            "critical_info": []
        }

        mock_pipe = Mock()
        mock_pipeline.return_value = mock_pipe
        mock_pipe.return_value = [
            {
                "generated_text": [
                    {},
                    {"content": json.dumps(response_with_empty_lists)}
                ]
            }
        ]

        # Create temporary EHR file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(sample_ehr_content)
            temp_file = Path(f.name)

        try:
            # Execute
            result = process_ehr_file(temp_file)

            # Assertions - should accept empty lists
            assert result['symptoms'] == []
            assert result['diagnoses'] == []
            assert result['medications'] == []
            assert result['critical_info'] == []
            assert result['patient_id'] == "P55555"

        finally:
            temp_file.unlink()


class TestPatientRecordModel:
    """Test suite for PatientRecord Pydantic model."""

    def test_patient_record_creation(self):
        """Test basic PatientRecord instantiation."""
        record = PatientRecord(
            patient_id="P001",
            name="Test User",
            symptoms=["fever", "cough"],
            diagnoses=["flu"],
            medications=["tamiflu"],
            critical_info=["allergy to penicillin"]
        )
        assert record.patient_id == "P001"
        assert record.name == "Test User"
        assert len(record.symptoms) == 2

    def test_patient_record_model_dump(self):
        """Test model_dump() method for serialization."""
        record = PatientRecord(
            patient_id="P002",
            name="Another User",
            symptoms=["headache"],
            diagnoses=["migraine"],
            medications=["ibuprofen"],
            critical_info=[]
        )
        dumped = record.model_dump()
        assert isinstance(dumped, dict)
        assert dumped['patient_id'] == "P002"
        assert dumped['name'] == "Another User"

    def test_patient_record_validation_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            PatientRecord(
                patient_id="P003"
                # Missing required fields
            )

    def test_patient_record_json_serialization(self):
        """Test JSON serialization of PatientRecord."""
        record = PatientRecord(
            patient_id="P004",
            name="JSON Test",
            symptoms=["rash", "itching"],
            diagnoses=["eczema"],
            medications=["hydrocortisone cream"],
            critical_info=["avoid contact with allergen"]
        )
        dumped = record.model_dump()
        json_str = json.dumps(dumped)
        loaded = json.loads(json_str)
        assert loaded['patient_id'] == "P004"
        assert "rash" in loaded['symptoms']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
