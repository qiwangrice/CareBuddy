"""
Build a Neo4j graph of Disease-Symptom relationships from ddss.xrdf.

Parses the DOID/SYMP ontology, extracts Disease and Symptom nodes with
their labels/definitions, and creates HAS_SYMPTOM edges between them.

Usage:
    python build_disease_symptom_graph.py                  # parse + load to Neo4j
    python build_disease_symptom_graph.py --dry-run        # parse only, print stats
    python build_disease_symptom_graph.py --clear           # clear existing Disease/Symptom nodes first
    python build_disease_symptom_graph.py --export-json     # also export to JSON
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rdflib import Graph, Namespace, RDF, RDFS, OWL

load_dotenv()

# Namespaces
OBO = Namespace("http://purl.obolibrary.org/obo/")
PREDIBIONTO = Namespace("https://w3id.org/def/predibionto#")
OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")

# Neo4j config
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")

XRDF_PATH = Path(__file__).parent / "ddss.xrdf"
BATCH_SIZE = 500


def parse_xrdf(filepath: Path):
    """Parse ddss.xrdf and extract diseases, symptoms, and has_symptom relationships."""
    print(f"Parsing {filepath} ...")
    g = Graph()
    g.parse(str(filepath), format="xml")
    print(f"  Loaded {len(g)} triples")

    # --- Extract Disease nodes (DOID_*) ---
    diseases = {}
    for subj in g.subjects(RDF.type, OWL.Class):
        uri = str(subj)
        if "/DOID_" not in uri:
            continue
        doid = uri.split("/")[-1]
        label = None
        definition = None
        for lbl in g.objects(subj, RDFS.label):
            label = str(lbl)
        for defn in g.objects(subj, OBO["IAO_0000115"]):
            definition = str(defn)
        diseases[uri] = {"id": doid, "label": label, "definition": definition}

    # --- Extract Symptom nodes (SYMP_*) ---
    symptoms = {}
    for subj in g.subjects(RDF.type, OWL.Class):
        uri = str(subj)
        if "/SYMP_" not in uri:
            continue
        symp_id = uri.split("/")[-1]
        label = None
        definition = None
        icd9 = []
        umls = []
        for lbl in g.objects(subj, RDFS.label):
            label = str(lbl)
        for defn in g.objects(subj, OBO["IAO_0000115"]):
            definition = str(defn)
        for xref in g.objects(subj, OBOINOWL["hasDbXref"]):
            xref_str = str(xref)
            if xref_str.startswith("ICD9"):
                icd9.append(xref_str)
            elif xref_str.startswith("UMLS_CUI"):
                umls.append(xref_str.replace("UMLS_CUI:", ""))
        symptoms[uri] = {
            "id": symp_id,
            "label": label,
            "definition": definition,
            "icd9": icd9,
            "umls_cui": umls,
        }

    # --- Extract has_symptom relationships ---
    has_symptom_uri = PREDIBIONTO["has_symptom"]
    relationships = []
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        # Check if this property is a sub-property of has_symptom
        if (prop, RDFS.subPropertyOf, has_symptom_uri) not in g:
            continue
        domain_uri = None
        range_uri = None
        for d in g.objects(prop, RDFS.domain):
            domain_uri = str(d)
        for r in g.objects(prop, RDFS.range):
            range_uri = str(r)
        if domain_uri and range_uri and "/DOID_" in domain_uri and "/SYMP_" in range_uri:
            relationships.append((domain_uri, range_uri))

    print(f"  Diseases:      {len(diseases)}")
    print(f"  Symptoms:      {len(symptoms)}")
    print(f"  Relationships: {len(relationships)}")
    return diseases, symptoms, relationships


def load_to_neo4j(diseases, symptoms, relationships, clear=False):
    """Load extracted data into Neo4j."""
    from neo4j import GraphDatabase

    print(f"\nConnecting to Neo4j at {NEO4J_URI} ...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()

    with driver.session() as session:
        if clear:
            print("  Clearing existing Disease/Symptom nodes ...")
            session.run("MATCH (n:Disease) DETACH DELETE n")
            session.run("MATCH (n:Symptom) DETACH DELETE n")

        # Create constraints/indexes
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Disease) REQUIRE d.id IS UNIQUE")
        session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:Symptom) REQUIRE s.id IS UNIQUE")

        # Batch-insert diseases
        disease_list = list(diseases.values())
        for i in range(0, len(disease_list), BATCH_SIZE):
            batch = disease_list[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS d
                MERGE (n:Disease {id: d.id})
                SET n.label = d.label, n.definition = d.definition
                """,
                batch=batch,
            )
        print(f"  Loaded {len(disease_list)} Disease nodes")

        # Batch-insert symptoms
        symptom_list = list(symptoms.values())
        for i in range(0, len(symptom_list), BATCH_SIZE):
            batch = symptom_list[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS s
                MERGE (n:Symptom {id: s.id})
                SET n.label = s.label,
                    n.definition = s.definition,
                    n.icd9 = s.icd9,
                    n.umls_cui = s.umls_cui
                """,
                batch=batch,
            )
        print(f"  Loaded {len(symptom_list)} Symptom nodes")

        # Batch-insert relationships
        rel_batch = [
            {"disease_id": d.split("/")[-1], "symptom_id": s.split("/")[-1]}
            for d, s in relationships
        ]
        for i in range(0, len(rel_batch), BATCH_SIZE):
            batch = rel_batch[i : i + BATCH_SIZE]
            session.run(
                """
                UNWIND $batch AS r
                MATCH (d:Disease {id: r.disease_id})
                MATCH (s:Symptom {id: r.symptom_id})
                MERGE (d)-[:HAS_SYMPTOM]->(s)
                """,
                batch=batch,
            )
        print(f"  Created {len(rel_batch)} HAS_SYMPTOM relationships")

    driver.close()
    print("Done.")


def export_json(diseases, symptoms, relationships, output_path: Path):
    """Export extracted data to JSON."""
    data = {
        "diseases": list(diseases.values()),
        "symptoms": list(symptoms.values()),
        "relationships": [
            {"disease": d.split("/")[-1], "symptom": s.split("/")[-1]}
            for d, s in relationships
        ],
    }
    output_path.write_text(json.dumps(data, indent=2))
    print(f"Exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Build Disease-Symptom Neo4j graph from ddss.xrdf")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, do not load to Neo4j")
    parser.add_argument("--clear", action="store_true", help="Clear existing Disease/Symptom nodes before loading")
    parser.add_argument("--export-json", action="store_true", help="Export extracted data to JSON")
    parser.add_argument("--xrdf", type=str, default=str(XRDF_PATH), help="Path to ddss.xrdf")
    args = parser.parse_args()

    xrdf_path = Path(args.xrdf)
    if not xrdf_path.exists():
        print(f"Error: {xrdf_path} not found", file=sys.stderr)
        sys.exit(1)

    diseases, symptoms, relationships = parse_xrdf(xrdf_path)

    if args.export_json:
        export_json(diseases, symptoms, relationships, xrdf_path.parent / "disease_symptom_graph.json")

    if not args.dry_run:
        load_to_neo4j(diseases, symptoms, relationships, clear=args.clear)
    else:
        print("\nDry run — skipping Neo4j load.")


if __name__ == "__main__":
    main()
