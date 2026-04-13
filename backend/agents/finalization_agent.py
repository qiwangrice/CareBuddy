"""
Finalization Agent: Aggregates processing results and saves to patient_records_summary.json.
"""

import json
from pathlib import Path
from langchain_core.messages import AIMessage
import logging as log
from utils import INPUT_DIR, OUTPUT_DIR
from neo4j import GraphDatabase
from typing import List, Dict
import os
from dotenv import load_dotenv
from collections import defaultdict
from difflib import SequenceMatcher
import spacy

load_dotenv()

# Neo4j Configuration (from .env)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


nlp = spacy.load("en_core_web_sm")

def clean_search_query(query: str) -> str:
    """
    Clean the search query by removing adjectives and hyphenated words with adjectives.
    
    This function:
    1. Removes adjectives (ADJ POS tag) - medical descriptors like "severe", "secondary"
    2. Removes words containing hyphens/punctuation if they're connected to adjectives
    3. Removes stop words - common words like "of", "the", "and"
    4. Removes punctuation
    5. Lemmatizes remaining tokens to their base form
    
    Examples:
        "Secondary pancreatitis" -> "pancreatic"
        "Insulin-dependent diabetes mellitus" -> "diabetes mellitus"
        "Acute chronic bronchitis" -> "bronchitis"
    """
    doc = nlp(query)
    cleaned_tokens = []
    
    for i, token in enumerate(doc):
        # Skip stop words and pure punctuation
        if token.is_stop or token.is_punct:
            continue
        
        # Skip adjectives
        if token.pos_ == "ADJ":
            continue
        
        # Skip tokens that contain hyphens/punctuation (like "Insulin-dependent")
        # These are often hyphenated adjectives
        if "-" in token.text or any(c in token.text for c in ".,;:!?'\""):
            continue
        if (i -1 >= 0) and "-" in doc[i-1].text:
            continue
        if (i +1 < len(doc)) and "-" in doc[i+1].text:
            continue
        
        cleaned_tokens.append(token.lemma_)
    
    cleaned_query = " ".join(cleaned_tokens)
    return cleaned_query


def query_diseases_by_symptom(symptom: str) -> List[Dict]:
    """
    Query Neo4j for diseases associated with a given symptom.
    
    Args:
        symptom: Symptom name or query string
        
    Returns:
        List of dictionaries containing disease information with keys:
        - disease_id: ID of the disease
        - disease_label: Human-readable disease name
        - disease_definition: Description of the disease
        - relationship_type: Type of relationship (e.g., RO_0002452)
        - relationship_label: Human-readable relationship label (e.g., "has manifestation")
    """
    driver = None
    session = None
    results = []
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        session = driver.session()
        
        log.debug(f"Querying Neo4j for diseases with symptom: '{symptom}'")
        
        # Query: Find diseases related to symptom
        query = """
            MATCH (disease:Disease)-[rel]->(symptom:Symptom)
            WHERE toLower(symptom.label) CONTAINS toLower($symptom_query)
               OR toLower(symptom.definition) CONTAINS toLower($symptom_query)
            RETURN 
                disease.id as disease_id,
                disease.label as disease_label,
                disease.definition as disease_definition,
                type(rel) as relationship_type,
                rel.relationship_label as relationship_label
            LIMIT 50
        """
        
        result = session.run(query, {"symptom_query": symptom})
        
        for record in result:
            results.append({
                "disease_id": record.get("disease_id"),
                "disease_label": record.get("disease_label"),
                "disease_definition": record.get("disease_definition"),
                "relationship_type": record.get("relationship_type"),
                "relationship_label": record.get("relationship_label")
            })
        
        log.debug(f"Found {len(results)} diseases for symptom '{symptom}'")
        
    except Exception as e:
        log.warning(f"Error querying Neo4j for symptom '{symptom}': {e}")
        
    finally:
        if session:
            session.close()
        if driver:
            driver.close()
    
    return results

def clean_diagnosis(diagnosis: str) -> str:
    """
    Clean diagnosis by removing adjectives and finding closest match in knowledge graph.
    
    This function:
    1. Removes common medical adjectives (severe, mild, acute, chronic, etc.)
    2. Searches Neo4j for exact or fuzzy match with disease labels
    3. Returns the closest disease name from knowledge graph or cleaned diagnosis
    
    Args:
        diagnosis: Raw diagnosis string (e.g., "Severe Pneumonia", "Acute Bronchitis")
        
    Returns:
        Cleaned diagnosis string, preferably from knowledge graph or with adjectives removed
    """
    if not diagnosis or not diagnosis.strip():
        return diagnosis
    
    cleaned_diagnosis = clean_search_query(diagnosis)
    
    log.debug(f"Initial clean: '{diagnosis}' → '{cleaned_diagnosis}'")
    
    driver = None
    session = None
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        session = driver.session()
        
        # Try exact match first
        query = """
            MATCH (d:Disease)
            WHERE toLower(d.label) = toLower($disease_name)
            RETURN d.label
            LIMIT 1
        """
        result = session.run(query, {"disease_name": cleaned_diagnosis})
        record = result.single()
        
        if record:
            matched_label = record["d.label"]
            log.debug(f"Exact match found: '{cleaned_diagnosis}' → '{matched_label}'")
            return matched_label
        
        # Try fuzzy matching with Neo4j (case-insensitive CONTAINS)
        query = """
            MATCH (d:Disease)
            WHERE toLower(d.label) CONTAINS toLower($search_term)
            RETURN d.label
            LIMIT 10
        """
        
        # Search for main noun (usually the last word)
        search_terms = [cleaned_diagnosis] + cleaned_diagnosis.split()[-3:] if len(cleaned_diagnosis.split()) > 1 else [cleaned_diagnosis]
        
        best_match = None
        best_score = 0.0
        
        for search_term in search_terms:
            if not search_term.strip():
                continue
                
            result = session.run(query, {"search_term": search_term})
            records = result.data()
            
            for record in records:
                disease_label = record.get("d.label")
                if disease_label:
                    # Calculate similarity score
                    similarity = SequenceMatcher(None, cleaned_diagnosis.lower(), disease_label.lower()).ratio()
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_match = disease_label
        
        # Use best match if similarity > 0.5, otherwise return cleaned diagnosis
        if best_match and best_score > 0.5:
            log.debug(f"Fuzzy match found (score: {best_score:.2f}): '{cleaned_diagnosis}' → '{best_match}'")
            return best_match
        else:
            log.debug(f"No good match in knowledge graph (best score: {best_score:.2f}), returning cleaned: '{cleaned_diagnosis}'")
            return cleaned_diagnosis
        
    except Exception as e:
        log.warning(f"Error cleaning diagnosis '{diagnosis}': {e}")
        return cleaned_diagnosis
        
    finally:
        if session:
            session.close()
        if driver:
            driver.close()

def validate_diagnosis_against_symptoms(diagnoses: List[str], symptoms: List[str]) -> Dict:
    """
    Validate multiple diagnoses against observed symptoms using Neo4j knowledge graph.
    
    Queries the Disease-Symptom knowledge graph to verify consistency between multiple
    diagnoses and observed symptoms. Returns individual validation scores for each diagnosis
    and an overall consensus score.
    
    Args:
        diagnoses: List of disease names or IDs to validate
        symptoms: List of observed symptoms
        
    Returns:
        Dict with comprehensive validation results:
        - total_diagnoses (int): Number of diagnoses provided
        - validated_count (int): Number of diagnoses found in knowledge graph
        - symptoms_count (int): Number of observed symptoms
        - validations (list): List of dicts, each with:
            - diagnosis (str): The diagnosis being validated
            - match (bool): Whether found in knowledge graph
            - disease_id (str): DOID identifier (if found)
            - disease_label (str): Human-readable name (if found)
            - expected_symptoms (int): Expected symptoms for disease
            - matching_count (int): Symptoms that matched
            - agreement_score (float): Jaccard similarity (0-1)
            - concern (bool): True if agreement < 0.5
            - matching_symptoms (list): List of matched symptoms
            - reason (str): Error message if validation failed
        - consensus_score (float): Average agreement across all diagnoses
        - high_confidence_diagnoses (list): Diagnoses with >70% agreement
        - concern_diagnoses (list): Diagnoses with <50% agreement
    """
    driver = None
    session = None
    validations = []
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        session = driver.session()
        
        # Normalize symptoms once
        symptoms_lower = {s.strip().lower() for s in symptoms if s and s.strip()}
        log.debug(f"Validating {len(diagnoses)} diagnosis/es against {len(symptoms_lower)} observed symptoms")
        
        # Validate each diagnosis
        for diagnosis in diagnoses:
            if not diagnosis or not diagnosis.strip():
                continue
                
            try:
                # Find disease matching diagnosis in knowledge graph
                query = """
                    MATCH (d:Disease)
                    WHERE toLower(d.label) CONTAINS toLower($diagnosis)
                       OR d.id = $disease_id
                    RETURN d.id, d.label
                    LIMIT 1
                """
                
                result = session.run(query, {"diagnosis": diagnosis, "disease_id": diagnosis.upper()})
                disease_record = result.single()
                
                # Handle case where diagnosis not found
                if not disease_record:
                    log.debug(f"Diagnosis '{diagnosis}' not found in knowledge graph")
                    validations.append({
                        "diagnosis": diagnosis,
                        "match": False,
                        "reason": "Diagnosis not found in knowledge graph",
                        "agreement_score": 0.0,
                        "concern": True
                    })
                    continue
                
                disease_id = disease_record["d.id"]
                disease_label = disease_record["d.label"]
                
                # Get all symptoms associated with this disease
                query = """
                    MATCH (d:Disease {id: $disease_id})-[:HAS_SYMPTOM]->(s:Symptom)
                    RETURN s.label
                """
                
                result = session.run(query, {"disease_id": disease_id})
                expected_symptoms = {row["s.label"].lower() for row in result}
                
                # Find matching symptoms
                matching_symptoms = expected_symptoms & symptoms_lower
                
                # Calculate agreement score (Jaccard similarity)
                agreement_score = 0.0
                union_size = len(expected_symptoms | symptoms_lower)
                if union_size > 0:
                    agreement_score = len(matching_symptoms) / union_size
                
                validations.append({
                    "diagnosis": diagnosis,
                    "match": True,
                    "disease_id": disease_id,
                    "disease_label": disease_label,
                    "expected_symptoms": sorted(list(expected_symptoms)),
                    "matching_count": len(matching_symptoms),
                    "agreement_score": round(agreement_score, 3),
                    "matching_symptoms": sorted(list(matching_symptoms)),
                    "concern": agreement_score < 0.5
                })
                
            except Exception as e:
                log.warning(f"Error validating diagnosis '{diagnosis}': {e}")
                validations.append({
                    "diagnosis": diagnosis,
                    "match": False,
                    "reason": f"Validation error: {str(e)}",
                    "agreement_score": 0.0,
                    "concern": True
                })
        
        # Calculate consensus metrics
        matched_validations = [v for v in validations if v.get("match")]
        agreement_scores = [v["agreement_score"] for v in matched_validations] if matched_validations else [0.0]
        consensus_score = sum(agreement_scores) / len(agreement_scores) if agreement_scores else 0.0
        
        high_confidence = [v["diagnosis"] for v in validations if v.get("agreement_score", 0) > 0.7]
        concern_list = [v["diagnosis"] for v in validations if v.get("concern")]
        
        return {
            "total_diagnoses": len(diagnoses),
            "validated_count": len(matched_validations),
            "symptoms_count": len(symptoms_lower),
            "validations": validations,
            "consensus_score": round(consensus_score, 3),
            "high_confidence_diagnoses": high_confidence,
            "concern_diagnoses": concern_list
        }
        
    except Exception as e:
        log.error(f"Critical error in diagnosis validation: {e}")
        return {
            "total_diagnoses": len(diagnoses),
            "validated_count": 0,
            "symptoms_count": len(symptoms),
            "validations": [],
            "consensus_score": 0.0,
            "high_confidence_diagnoses": [],
            "concern_diagnoses": diagnoses,
            "error": str(e)
        }
        
    finally:
        if session:
            session.close()
        if driver:
            driver.close()

def finalize_results(state: dict) -> dict:
    """Aggregate and format final results."""
    log.info("Finalizing results...")
    
    summary = {
        "total_files": len(state["input_files"]),
        "processed_files": len(state["file_results"]),
        "detailed_results": state["file_results"],
        "symptom_disease_associations": {}
    }

    # Log summary
    log.info("\n" + "="*80)
    log.info("MULTI-AGENT PROCESSING SUMMARY")
    log.info("="*80)
    log.info(f"Total files: {summary['total_files']}")
    log.info(f"Successfully processed: {summary['processed_files']}")
    log.info("Detailed Results:")
    log.info("-"*80)

    symptoms = []
    diagnoses = []

    for filename, result in state["file_results"].items():
        # Ensure result is a dict (defensive check)
        if isinstance(result, str):
            log.warning(f"  ✗ {filename}: Invalid result format (string instead of dict)")
            continue
        if not isinstance(result, dict):
            log.warning(f"  ✗ {filename}: Invalid result format (expected dict, got {type(result).__name__})")
            continue
        
        # Log error if processing failed
        if result.get("error"):
            log.warning(f"  ✗ {filename}: {result['error']}")
        else:
            log.info(f"  ✓ {filename}: {result.get('name', 'Processed')}")
        
        # Safely extend symptoms - ensure all items are strings
        raw_symptoms = result.get("symptoms", [])
        if isinstance(raw_symptoms, list):
            for symptom in raw_symptoms:
                if isinstance(symptom, str) and symptom.strip():
                    symptoms.append(symptom.strip())
        
        # Safely extend diagnoses - ensure all items are strings
        raw_diagnoses = result.get("diagnoses", [])
        if isinstance(raw_diagnoses, list):
            for diagnosis in raw_diagnoses:
                if isinstance(diagnosis, str) and diagnosis.strip():
                    diagnoses.append(diagnosis.strip())
    
    # Clean diagnoses by removing adjectives and finding closest match in knowledge graph
    log.info("\nCleaning diagnoses...")
    log.info("-"*80)
    cleaned_diagnoses = []
    for diagnosis in diagnoses:
        cleaned = clean_diagnosis(diagnosis)
        if cleaned != diagnosis:
            log.info(f"  Cleaned: '{diagnosis}' → '{cleaned}'")
        cleaned_diagnoses.append(cleaned)
    diagnoses = cleaned_diagnoses
    
    # Query Neo4j for disease associations with each symptom
    if symptoms:
        log.info("\nQuerying Neo4j for disease-symptom associations...")
        log.info("-"*80)
        disease_count = defaultdict(list)
        
        for symptom in set(symptoms):
            clean_symptom = symptom.strip().lower().split("(")[0].strip()  # Basic cleaning to remove qualifiers
            diseases = query_diseases_by_symptom(clean_symptom)
            
            if diseases:
                for disease in diseases:
                    disease_count[disease['disease_label']].append(symptom)
        
        # only record diseases that are associated with multiple symptoms for better confidence, and log the associations
        for disease, associated_symptoms in disease_count.items():
            if len(associated_symptoms) > 1:
                log.info(f"✓ Disease '{disease}' associated with multiple symptoms: {', '.join(associated_symptoms)}")
                for symptom in associated_symptoms:
                    # Store just the disease label instead of full disease objects for cleaner JSON
                    if symptom not in summary["symptom_disease_associations"]:
                        summary["symptom_disease_associations"][symptom] = []
                    summary["symptom_disease_associations"][symptom].append(disease)
                diagnoses.append(disease)  # disease is already a string (the disease_label)
        for symptom in set(symptoms):
            if symptom not in summary["symptom_disease_associations"]:
                summary["symptom_disease_associations"][symptom] = []
                log.info(f"✗ Symptom '{symptom}' - no diseases found in Neo4j")
    
    # Validate all diagnoses against symptoms
    validation_results = validate_diagnosis_against_symptoms(diagnoses, symptoms)

    log.info("="*80)
    log.info(f"Diagnosis Validation Summary: {validation_results.get('consensus_score', 0):.0%} average agreement")
    
    # Log high confidence and concern diagnoses
    if validation_results.get("high_confidence_diagnoses"):
        log.info(f"✓ High confidence diagnoses: {', '.join(validation_results['high_confidence_diagnoses'])}")
    if validation_results.get("concern_diagnoses"):
        log.warning(f"⚠ Diagnoses with concerns: {', '.join(validation_results['concern_diagnoses'])}")
    
    # Also save a comprehensive patient records file
    patient_records_file = OUTPUT_DIR / "patient_records_summary.json"
    patient_summary = {
        "total_files": len(state["input_files"]),
        "processed_files": summary['processed_files'],
        "total_symptoms_extracted": len(set(symptoms)),
        "total_diagnoses_extracted": len(set(diagnoses)),
        "symptom_disease_associations": summary.get("symptom_disease_associations", {}),
        "detailed_results": summary["detailed_results"]
    }
    # add validation results to patient summary
    patient_summary["diagnosis_validation"] = validation_results
    patient_records_file.write_text(json.dumps(patient_summary, indent=2))
    log.info(f"Patient records summary saved to: {patient_records_file}")

    state["messages"].append(
        AIMessage(content=f"Processing complete. {summary['processed_files']}/{summary['total_files']} files processed successfully.")
    )

    return state
