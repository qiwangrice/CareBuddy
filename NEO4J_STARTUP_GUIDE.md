# Neo4j Setup & TTL Loading Guide

Quick start guide for running Neo4j with CareBuddy and loading RDF/Turtle files.

## Prerequisites

- Docker and Docker Compose installed
- TTL files in `resources/` or `KAG/` directory
- Python environment with neo4j and rdflib installed

## Quick Start

### 1. Start Neo4j Container

```bash
cd /Users/qiwang/Downloads/workplace/CareBuddy

# Using the management script
./neo4j.sh start

# OR manually
docker-compose up -d neo4j
```

### 2. Verify Neo4j is Running

```bash
# Check container status
./neo4j.sh status

# Visit browser interface
./neo4j.sh open
# Or manually: http://localhost:7474
# Login: neo4j / carebuddy_password
```

### 3. Load TTL Files into Neo4j

```bash
# From CareBuddy directory
cd /Users/qiwang/Downloads/workplace/CareBuddy

# Option A: Load specific TTL file
python KAG/ttl_to_neo4j.py

# Option B: Load from Python (advanced)
python << 'EOF'
from KAG.ttl_to_neo4j import TTLToNeo4jLoader

loader = TTLToNeo4jLoader(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="carebuddy_password"
)

# Load a TTL file
loader.load_ttl("path/to/your/file.ttl")

# Get statistics
stats = loader.get_statistics()
print(f"Loaded {stats['nodes']} nodes and {stats['relationships']} relationships")
EOF
```

### 4. Query Data

```bash
# Test connection and query
python << 'EOF'
from KAG.ttl_to_neo4j import TTLToNeo4jLoader

loader = TTLToNeo4jLoader()
loader.connect()

# Search for a term
results = loader.search_by_label("DNA")
print(f"Found {len(results)} results containing 'DNA'")

# Get neighbors of a node
neighbors = loader.get_neighbors("node_id", hops=2)
print(f"Found {len(neighbors)} neighbors")

loader.close()
EOF
```

## Management Commands

Use the `neo4j.sh` script for common operations:

```bash
./neo4j.sh start      # Start Neo4j
./neo4j.sh stop       # Stop Neo4j
./neo4j.sh restart    # Restart Neo4j
./neo4j.sh status     # Check status
./neo4j.sh logs       # View logs (follow mode)
./neo4j.sh open       # Open browser
./neo4j.sh reset      # Full wipe and restart
./neo4j.sh help       # Show help
```

## Configuration

### Connection Details

- **Browser URL**: http://localhost:7474
- **Bolt Protocol**: bolt://localhost:7687
- **Default Credentials**: 
  - Username: `neo4j`
  - Password: `carebuddy_password`

### Customize Credentials

Edit `docker-compose.yml`:

```yaml
environment:
  NEO4J_AUTH: neo4j/your_new_password  # Change password here
```

Then restart:
```bash
./neo4j.sh restart
```

### Memory Configuration

Default memory limits in `docker-compose.yml`:
- Initial heap: 2GB
- Max heap: 4GB

To increase, edit:
```yaml
environment:
  NEO4J_dbms_memory_heap_initial__size: 4G
  NEO4J_dbms_memory_heap_max__size: 8G
```

## TTL File Locations

### Available TTL Files

1. **GO Ontology** (Gene Ontology)
   - Generated from: `go-basic.json`
   - File: `resources/go-basic.ttl` (2.62 MB)
   - Contains: 52,003 GO terms with relationships

2. **MESH Sample**
   - File: `resources/MESH_sample.ttl`
   - Contains: 16 medical descriptors for testing

### Generate New TTL Files

```bash
cd /Users/qiwang/Downloads/workplace/discovery-agent

# Generate from utilities
python << 'EOF'
from knowledge_query.ttl_utils import create_sample_mesh_ttl, convert_go_json_to_ttl

# Create MESH sample
create_sample_mesh_ttl("output_path.ttl")

# Convert GO JSON to TTL (limit to 5000 terms for faster processing)
convert_go_json_to_ttl("resources/go-basic.json", max_terms=5000)
EOF
```

## Troubleshooting

### Neo4j Won't Start

```bash
# Check if port is already in use
lsof -i :7687
lsof -i :7474

# Kill existing process
kill -9 <PID>

# Restart
./neo4j.sh restart
```

### Connection Refused

```bash
# Ensure container is running
docker ps | grep carebuddy-neo4j

# Check logs
./neo4j.sh logs

# Verify port mapping
docker port carebuddy-neo4j
```

### Out of Memory Errors

```bash
# Increase heap in docker-compose.yml
NEO4J_dbms_memory_heap_max__size: 8G

# Restart
./neo4j.sh restart
```

### TTL File Won't Load

```bash
# Verify file exists and is readable
ls -lh resources/*.ttl

# Check TTL file syntax (first few lines)
head -20 resources/go-basic.ttl

# Enable debug logging
python << 'EOF'
import logging
logging.basicConfig(level=logging.DEBUG)

from KAG.ttl_to_neo4j import TTLToNeo4jLoader
loader = TTLToNeo4jLoader()
loader.load_ttl("resources/go-basic.ttl")
EOF
```

### Clear All Data

```bash
# WARNING: This deletes all Neo4j data
./neo4j.sh reset
```

## Performance Tips

1. **Batch Loading**: TTL files are loaded in batches (default 1000 triples)
2. **Indexing**: Create indexes on frequently searched properties
3. **Memory**: Allocate enough heap for your dataset size
4. **Timeout**: Increase if loading large files takes too long

```python
# Adjust batch size in ttl_to_neo4j.py
BATCH_SIZE = 5000  # Larger batches = faster loading (higher memory)
```

## Integration with BackendAPI

```python
# In backend API endpoint
from KAG.ttl_to_neo4j import TTLToNeo4jLoader

# Create singleton for connection pooling
neo4j_loader = TTLToNeo4jLoader(
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="carebuddy_password"
)

# Use in endpoint
@app.get("/api/search")
async def search_graph(query: str):
    results = neo4j_loader.search_by_label(query)
    return {"results": results}
```

## Advanced Usage

### Run Cypher Queries Directly

```python
from KAG.ttl_to_neo4j import TTLToNeo4jLoader

loader = TTLToNeo4jLoader()
loader.connect()

# Count all nodes
result = loader.query("MATCH (n) RETURN count(n) as count")

# Find all relationships
result = loader.query("""
    MATCH (n1)-[r]->(n2)
    RETURN type(r) as relationship, count(*) as count
    ORDER BY count DESC
""")

loader.close()
```

### Export Data

```python
loader = TTLToNeo4jLoader()
loader.connect()

# Export statistics
loader.export_to_file("neo4j_stats.json")

# Export query results
result = loader.query("MATCH (n) RETURN n LIMIT 1000")
# Result can be saved to JSON/CSV as needed

loader.close()
```

## Monitoring

### View Real-Time Logs

```bash
./neo4j.sh logs
```

### Container Resource Usage

```bash
docker stats carebuddy-neo4j
```

### Neo4j Metrics (in browser CLI)

```
:sysinfo           # System information
CALL dbms.info()   # Database info
```

## Cleanup

### Stop All Services

```bash
cd /Users/qiwang/Downloads/workplace/CareBuddy
docker-compose down
```

### Remove Data (Keep Container)

```bash
docker-compose down
docker volume rm carebuddy_neo4j_data carebuddy_neo4j_logs
```

### Full Cleanup

```bash
docker-compose down -v  # Removes containers, volumes, networks
```

## Knowledge Graph (KAG) - Disease-Symptom Database

CareBuddy includes specialized tools for building and searching a comprehensive Disease-Symptom knowledge graph sourced from the Disease Ontology (DOID) and Symptom Ontology (SYMP).

### Quick Start

```bash
# 1. Start Neo4j (from the main CareBuddy directory)
./neo4j.sh start

# 2. Build and load the Disease-Symptom graph
python KAG/build_disease_symptom_graph.py

# 3. Search the graph
python KAG/search_neo4j.py --symptom "fever"
```

### Build Disease-Symptom Graph

Parse the RDF ontology file (`ddss.xrdf`) and load Disease-Symptom relationships into Neo4j.

```bash
# Parse and load (default)
python KAG/build_disease_symptom_graph.py

# Parse only (view statistics without loading)
python KAG/build_disease_symptom_graph.py --dry-run

# Clear existing nodes before loading
python KAG/build_disease_symptom_graph.py --clear

# Export graph to JSON
python KAG/build_disease_symptom_graph.py --export-json
```

**Output Graph Statistics:**
- ~12,000+ Disease-Symptom relationships
- ~8,800 unique diseases (DOID_*)
- ~21,800 unique symptoms (SYMP_*)
- ICD9 and UMLS CUI cross-references included

### Search the Disease-Symptom Graph

Interactive search tool to query loaded relationships.

```bash
# Find all diseases with a symptom
python KAG/search_neo4j.py --symptom "fever" --limit 20

# Find all symptoms for a disease
python KAG/search_neo4j.py --disease "angiosarcoma" --limit 10

# Find related diseases (sharing symptoms)
python KAG/search_neo4j.py --related-to DOID_0001816 --limit 10

# Get full disease profile with all symptoms
python KAG/search_neo4j.py --detail-disease "influenza"

# Get full symptom profile with all associated diseases
python KAG/search_neo4j.py --detail-symptom "fever"

# View graph statistics
python KAG/search_neo4j.py --stats
```

### Query Examples

**Find all diseases with "fever" symptom:**
```bash
python KAG/search_neo4j.py --symptom "fever"

# Output:
# === Diseases with symptom 'fever' ===
# ┌─────────────┬──────────────────────────┬────────────────────────────┐
# │ id          │ label                    │ definition                 │
# ├─────────────┼──────────────────────────┼────────────────────────────┤
# │ DOID_0001589│ Human immunodeficiency.. │ A retroviral infection...  │
# │ DOID_0007193│ Influenza A              │ An influenza caused by...  │
# └─────────────┴──────────────────────────┴────────────────────────────┘
```

**Get complete disease profile:**
```bash
python KAG/search_neo4j.py --detail-disease "angiosarcoma"

# Output shows:
# - Disease ID and definition
# - Total symptom count
# - List of all symptoms with ICD9/UMLS codes
```

### Graph Schema

**Node Types:**
- `Disease`: DOID identifiers with label and definition
- `Symptom`: SYMP identifiers with label, definition, ICD9, and UMLS CUI codes

**Relationship Types:**
- `[:HAS_SYMPTOM]`: Connects Disease → Symptom

### Cypher Query Examples

Access Neo4j directly for advanced queries:

```cypher
# Count total nodes
MATCH (n) RETURN COUNT(*) as total_nodes

# Find top 10 symptoms by disease count
MATCH (s:Symptom)<-[:HAS_SYMPTOM]-(d:Disease)
RETURN s.label, COUNT(d) as disease_count
ORDER BY disease_count DESC
LIMIT 10

# Find all diseases with multiple common symptoms
MATCH (d1:Disease)-[:HAS_SYMPTOM]->(s:Symptom)<-[:HAS_SYMPTOM]-(d2:Disease)
WHERE d1.id < d2.id
RETURN d1.label, d2.label, COUNT(s) as shared_symptoms
ORDER BY shared_symptoms DESC
LIMIT 20
```

## Reference

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/)
- [RDFlib Documentation](https://rdflib.readthedocs.io/)
