# Quick Start: Neo4j with CareBuddy

## 30-Second Setup

```bash
# 1. Navigate to CareBuddy
cd CareBuddy

# 2. Start Neo4j
./neo4j.sh start

# 3. View data in browser
./neo4j.sh open
```

---

## Available Commands

### Neo4j Management (`./neo4j.sh`)
```bash
./neo4j.sh start      # Start container
./neo4j.sh stop       # Stop container  
./neo4j.sh restart    # Restart container
./neo4j.sh status     # Check if running
./neo4j.sh logs       # View logs
./neo4j.sh open       # Open browser (http://localhost:7474)
./neo4j.sh reset      # Full wipe (delete all data)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Connection refused | Run `./neo4j.sh start` and wait 10s |
| Port already in use | `./neo4j.sh reset` or `lsof -i :7687` |
| Slow data loading | Increase memory in docker-compose.yml |

---

## File Locations

```
CareBuddy/
├── docker-compose.yml         ← Neo4j container config
├── neo4j.sh                   ← Management script
├── NEO4J_STARTUP_GUIDE.md    ← Full documentation
├── resources/
│   └── ddss.xrdf             ← Bring your own database 
└── KAG/
    ├── ddss.xrdf                          ← Disease-Symptom RDF ontology
    ├── build_disease_symptom_graph.py     ← Parse & load Disease-Symptom graph to Neo4j
    ├── search_neo4j.py                    ← Interactive graph search tool
    └── database/
        └── disease_symptom_graph.json     ← Exported relationships
```

---

## Next Steps

### 1. Start Neo4j
```bash
./neo4j.sh start
```

### 2. Build Disease-Symptom Knowledge Graph
```bash
# Parse RDF and load to Neo4j (one-time setup)
python KAG/build_disease_symptom_graph.py
# or with options:
python KAG/build_disease_symptom_graph.py --clear  # Clear existing first
python KAG/build_disease_symptom_graph.py --export-json  # Also export JSON
```

### 3. Search the Graph
```bash
# Find diseases with a symptom
python KAG/search_neo4j.py --symptom "fever"

# Find symptoms for a disease
python KAG/search_neo4j.py --disease "angiosarcoma"

# Get full disease profile
python KAG/search_neo4j.py --detail-disease "influenza"

# View graph statistics
python KAG/search_neo4j.py --stats
```

### 4. Verify Setup
```bash
# Check Neo4j connection and view graph stats
python KAG/search_neo4j.py --stats
```

---

**Last Updated**: April 8, 2026  
**Status**: ✅ Ready for Production
