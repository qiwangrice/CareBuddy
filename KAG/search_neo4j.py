"""
Search and query the Neo4j Disease-Symptom graph.

Provides CLI interface to:
  - Find diseases by symptom
  - Find symptoms by disease
  - Find related diseases (share symptoms)
  - Explore symptom chains
  - Get disease/symptom details

Usage:
    python search_neo4j.py --disease "angiosarcoma"
    python search_neo4j.py --symptom "fever"
    python search_neo4j.py --related-to "DOID_0001816"
    python search_neo4j.py --stats
"""

import argparse
import os
import sys
from typing import Dict, List

from dotenv import load_dotenv
from neo4j import GraphDatabase
from tabulate import tabulate

load_dotenv()

# Neo4j config
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


class DiseaseSymptomSearcher:
    """Query and search the Disease-Symptom Neo4j graph."""

    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        try:
            self.driver.verify_connectivity()
        except Exception as e:
            print(f"Error connecting to Neo4j at {NEO4J_URI}: {e}", file=sys.stderr)
            sys.exit(1)

    def close(self):
        self.driver.close()

    def find_diseases_by_symptom(self, symptom_query: str, limit: int = 50) -> List[Dict]:
        """Find all diseases associated with a symptom (by label or ID)."""
        with self.driver.session() as session:
            # Try matching by label first, then by ID
            result = session.run(
                """
                MATCH (s:Symptom)-[:HAS_SYMPTOM*0..1]-(symptom:Symptom)
                WHERE s.label CONTAINS $query OR s.id = $id_query
                WITH symptom
                MATCH (d:Disease)-[:HAS_SYMPTOM]->(symptom)
                RETURN d.id, d.label, d.definition
                LIMIT $limit
                """,
                {
                    "query": symptom_query,
                    "id_query": symptom_query.upper(),
                    "limit": limit,
                },
            )
            records = [
                {"id": r["d.id"], "label": r["d.label"] or "N/A", "definition": r["d.definition"] or "N/A"}
                for r in result
            ]
            return records

    def find_symptoms_by_disease(self, disease_query: str, limit: int = 50) -> List[Dict]:
        """Find all symptoms for a disease (by label or ID)."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Disease)
                WHERE d.label CONTAINS $query OR d.id = $id_query
                WITH d
                MATCH (d)-[:HAS_SYMPTOM]->(s:Symptom)
                RETURN s.id, s.label, s.definition, s.icd9, s.umls_cui
                LIMIT $limit
                """,
                {
                    "query": disease_query,
                    "id_query": disease_query.upper(),
                    "limit": limit,
                },
            )
            records = [
                {
                    "id": r["s.id"],
                    "label": r["s.label"] or "N/A",
                    "definition": r["s.definition"] or "N/A",
                    "icd9": ", ".join(r["s.icd9"] or []),
                    "umls_cui": ", ".join(r["s.umls_cui"] or []),
                }
                for r in result
            ]
            return records

    def find_related_diseases(self, disease_id: str, limit: int = 20) -> List[Dict]:
        """Find diseases that share symptoms with a given disease."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d1:Disease {id: $disease_id})-[:HAS_SYMPTOM]->(s:Symptom)
                WITH s
                MATCH (s)<-[:HAS_SYMPTOM]-(d2:Disease)
                WHERE d2.id <> $disease_id
                RETURN d2.id, d2.label, COUNT(s) as shared_symptom_count
                ORDER BY shared_symptom_count DESC
                LIMIT $limit
                """,
                disease_id=disease_id,
                limit=limit,
            )
            records = [
                {"id": r["d2.id"], "label": r["d2.label"] or "N/A", "shared_symptoms": r["shared_symptom_count"]}
                for r in result
            ]
            return records

    def get_disease_detail(self, disease_query: str) -> Dict:
        """Get full details for a disease including all symptoms."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Disease)
                WHERE d.label CONTAINS $query OR d.id = $id_query
                RETURN d.id, d.label, d.definition
                LIMIT 1
                """,
                {
                    "query": disease_query,
                    "id_query": disease_query.upper(),
                },
            )
            disease = result.single()
            if not disease:
                return None

            d_id, d_label, d_def = disease["d.id"], disease["d.label"], disease["d.definition"]

            # Get symptoms
            result = session.run(
                """
                MATCH (d:Disease {id: $disease_id})-[:HAS_SYMPTOM]->(s:Symptom)
                RETURN s.id, s.label, s.definition
                ORDER BY s.label
                """,
                disease_id=d_id,
            )
            symptoms = [
                {"id": r["s.id"], "label": r["s.label"] or "N/A", "definition": r["s.definition"] or "N/A"}
                for r in result
            ]

            return {
                "id": d_id,
                "label": d_label or "N/A",
                "definition": d_def or "N/A",
                "symptom_count": len(symptoms),
                "symptoms": symptoms,
            }

    def get_symptom_detail(self, symptom_query: str) -> Dict:
        """Get full details for a symptom including all diseases."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (s:Symptom)
                WHERE s.label CONTAINS $query OR s.id = $id_query
                RETURN s.id, s.label, s.definition, s.icd9, s.umls_cui
                LIMIT 1
                """,
                {
                    "query": symptom_query,
                    "id_query": symptom_query.upper(),
                },
            )
            symptom = result.single()
            if not symptom:
                return None

            s_id = symptom["s.id"]
            s_label = symptom["s.label"]
            s_def = symptom["s.definition"]
            s_icd9 = symptom["s.icd9"] or []
            s_umls = symptom["s.umls_cui"] or []

            # Get diseases
            result = session.run(
                """
                MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom {id: $symptom_id})
                RETURN d.id, d.label
                ORDER BY d.label
                """,
                symptom_id=s_id,
            )
            diseases = [{"id": r["d.id"], "label": r["d.label"] or "N/A"} for r in result]

            return {
                "id": s_id,
                "label": s_label or "N/A",
                "definition": s_def or "N/A",
                "icd9": s_icd9,
                "umls_cui": s_umls,
                "disease_count": len(diseases),
                "diseases": diseases,
            }

    def get_stats(self) -> Dict:
        """Get overall graph statistics."""
        with self.driver.session() as session:
            result = session.run(
                """
                RETURN 
                  (SELECT COUNT(*) FROM (MATCH (d:Disease) RETURN d)) as disease_count,
                  (SELECT COUNT(*) FROM (MATCH (s:Symptom) RETURN s)) as symptom_count,
                  (SELECT COUNT(*) FROM (MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom) RETURN d)) as relationship_count
                """
            )
            stats = result.single()

            result = session.run(
                """
                MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
                RETURN COUNT(*) as total_relationships
                """
            )
            total_rels = result.single()["total_relationships"]

            result = session.run(
                """
                MATCH (d:Disease)-[:HAS_SYMPTOM]->(s:Symptom)
                WITH d, COUNT(s) as symptom_count
                RETURN AVG(symptom_count) as avg_symptoms_per_disease
                """
            )
            avg_symp = result.single()["avg_symptoms_per_disease"]

            return {
                "total_diseases": stats["disease_count"] if stats["disease_count"] else 0,
                "total_symptoms": stats["symptom_count"] if stats["symptom_count"] else 0,
                "total_relationships": total_rels,
                "avg_symptoms_per_disease": round(avg_symp, 2) if avg_symp else 0,
            }


def print_table(records: List[Dict], title: str = ""):
    """Pretty-print results as a table."""
    if not records:
        print(f"  No results found.")
        return
    if title:
        print(f"\n{title}:")
    if records:
        print(tabulate(records, headers="keys", tablefmt="grid"))


def main():
    parser = argparse.ArgumentParser(description="Search Disease-Symptom Neo4j graph")
    parser.add_argument("--disease", type=str, help="Search for diseases by name/ID")
    parser.add_argument("--symptom", type=str, help="Search for symptoms by name/ID")
    parser.add_argument("--related-to", type=str, metavar="DISEASE_ID", help="Find diseases related to a disease")
    parser.add_argument("--detail-disease", type=str, metavar="QUERY", help="Get full disease details")
    parser.add_argument("--detail-symptom", type=str, metavar="QUERY", help="Get full symptom details")
    parser.add_argument("--stats", action="store_true", help="Show graph statistics")
    parser.add_argument("--limit", type=int, default=50, help="Max results (default: 50)")

    args = parser.parse_args()

    if not any([args.disease, args.symptom, args.related_to, args.detail_disease, args.detail_symptom, args.stats]):
        parser.print_help()
        sys.exit(1)

    searcher = DiseaseSymptomSearcher()

    try:
        if args.stats:
            stats = searcher.get_stats()
            print("\n=== Graph Statistics ===")
            for key, value in stats.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
            print()

        if args.disease:
            print(f"\n=== Symptoms of disease '{args.disease}' ===")
            results = searcher.find_symptoms_by_disease(args.disease, limit=args.limit)
            print_table(results)

        if args.symptom:
            print(f"\n=== Diseases with symptom '{args.symptom}' ===")
            results = searcher.find_diseases_by_symptom(args.symptom, limit=args.limit)
            print_table(results)

        if args.related_to:
            print(f"\n=== Diseases related to {args.related_to} ===")
            results = searcher.find_related_diseases(args.related_to, limit=args.limit)
            print_table(results)

        if args.detail_disease:
            detail = searcher.get_disease_detail(args.detail_disease)
            if detail:
                print(f"\n=== Disease: {detail['label']} ({detail['id']}) ===")
                print(f"Definition: {detail['definition']}")
                print(f"Total Symptoms: {detail['symptom_count']}\n")
                print_table(detail["symptoms"], "Symptoms")
            else:
                print(f"Disease '{args.detail_disease}' not found.")

        if args.detail_symptom:
            detail = searcher.get_symptom_detail(args.detail_symptom)
            if detail:
                print(f"\n=== Symptom: {detail['label']} ({detail['id']}) ===")
                print(f"Definition: {detail['definition']}")
                if detail["icd9"]:
                    print(f"ICD9: {', '.join(detail['icd9'])}")
                if detail["umls_cui"]:
                    print(f"UMLS CUI: {', '.join(detail['umls_cui'])}")
                print(f"Total Diseases: {detail['disease_count']}\n")
                print_table(detail["diseases"], "Associated Diseases")
            else:
                print(f"Symptom '{args.detail_symptom}' not found.")

    finally:
        searcher.close()


if __name__ == "__main__":
    main()
