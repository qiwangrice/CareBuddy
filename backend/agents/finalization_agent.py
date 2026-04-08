"""
Finalization Agent: Aggregates processing results and saves to results.json.
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

load_dotenv()

# Neo4j Configuration (from .env)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


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
        symptoms.extend(result.get("symptoms", []))
        diagnoses.extend(result.get("diagnoses", []))
    
    # Query Neo4j for disease associations with each symptom
    if symptoms:
        log.info("\nQuerying Neo4j for disease-symptom associations...")
        log.info("-"*80)
        
        for symptom in set(symptoms):
            diseases = query_diseases_by_symptom(symptom)
            
            if diseases:
                summary["symptom_disease_associations"][symptom] = diseases
                log.info(f"✓ Symptom '{symptom}' associated with {len(diseases)} disease(s)")
                for disease in diseases:
                    log.info(f"    - {disease['disease_label']} ({disease['disease_id']})")
                    if disease.get('relationship_label'):
                        log.info(f"      Relationship: {disease['relationship_label']}")
            else:
                summary["symptom_disease_associations"][symptom] = []
                log.info(f"✗ Symptom '{symptom}' - no diseases found in Neo4j")

    log.info("="*80)

    # Save to results.json
    results_file = OUTPUT_DIR / "results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    results_file.write_text(json.dumps(summary, indent=2))
    log.info(f"Results saved to: {results_file}")
    
    # Also save a comprehensive patient records file
    patient_records_file = OUTPUT_DIR / "patient_records_summary.json"
    patient_summary = {
        "total_files_processed": summary['processed_files'],
        "total_symptoms_extracted": len(set(symptoms)),
        "total_diagnoses_extracted": len(set(diagnoses)),
        "symptom_disease_associations": summary.get("symptom_disease_associations", {}),
        "detailed_results": summary["detailed_results"]
    }
    patient_records_file.write_text(json.dumps(patient_summary, indent=2))
    log.info(f"Patient records summary saved to: {patient_records_file}")

    state["messages"].append(
        AIMessage(content=f"Processing complete. {summary['processed_files']}/{summary['total_files']} files processed successfully.")
    )

    return state
