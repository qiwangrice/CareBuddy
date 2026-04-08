# CareBuddy: AI-Powered Medical Analysis System

## 🏥 Overview

CareBuddy is a sophisticated multi-agent medical image and EHR (Electronic Health Record) analysis system that combines:

- **LangGraph Multi-Agent Orchestrator**: Dynamically spawns agents based on input files
- **Medical AI Model**: `google/medgemma-1.5-4b-it` for analyzing medical images and records
- **FastAPI Backend**: RESTful API for processing and result management
- **Modern Web UI**: Beautiful, responsive interface for easy interaction

## 🎬 Demo Video

Watch the CareBuddy system in action: https://www.youtube.com/watch?v=h8AVXXA1_YU

## ✨ Features

### Backend (LangGraph Multi-Agent System)
- ✅ **Discovery Agent**: Scans both input files AND archive folders
  - Identifies medical images (.jpg, .png) and EHR records (.txt)
  - Detects previous archive folders with SKILL.md metadata
- ✅ **Processing Agents**: Intelligent routing based on content type
  - Image Analyzer: Detects abnormalities in medical images
  - EHR Summarizer: Analyzes patient health records
  - Archive Analyzer: Reads SKILL.md to decide if detailed report/results needed
- ✅ **Archive System**: Timestamped result storage with metadata
  - Automatic archiving to `YYYY-MM-DD_HH-MM-SS` folders
  - SKILL.md: Metadata with success rate, device, model used
  - Re-processable: Archives can be fed back as input for comparative analysis
- ✅ **Finalization Agent**: Aggregates results into structured JSON
- ✅ **Summary Agent**: Generates comprehensive analysis reports & archives
- ✅ **Intelligent Archive Processing**: 
  - Always reads SKILL.md (lightweight metadata)
  - Reads analysis_report.txt only if success < 100%
  - Reads results.json only if needed for detailed insights
- ✅ **Logging**: Structured logging throughout the pipeline
- ✅ **Device Auto-Detection**: Automatically uses CUDA, MPS (macOS), or CPU

### Frontend (Web UI)
- ✅ **File Upload**: Drag-and-drop or click to upload medical files
- ✅ **Real-time Progress**: Track processing status with progress bar
- ✅ **Results Display**: View individual file analyses with formatted output
- ✅ **Summary Reports**: Comprehensive analysis report generation
- ✅ **Download**: Export results as JSON or formatted text
- ✅ **Responsive Design**: Works on desktop and tablets
- ✅ **Modern UI**: Beautiful gradient design with smooth animations

### API (RESTful Endpoints)
- ✅ **File Processing**: Upload, process, and retrieve results
- ✅ **Archive Management**: List and query archive SKILL metadata
- ✅ **SKILL Parsing**: Parse and aggregate archive metadata across system

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd CareBuddy
poetry install --no-root
poetry lock
```

### 2. Start Backend API
```bash
cd backend
poetry run python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

Backend: `http://localhost:8000`
API Docs: `http://localhost:8000/docs`

### 3. Start Frontend (new terminal)
```bash
cd frontend
python -m http.server 8080
```

Frontend: `http://localhost:8080`

## � Multi-Agent Workflow

```
Input Files + Archive Folders
           ↓
    [DISCOVERY AGENT]
    - Scans results/input/ for files
    - Scans results/output/ for archives
           ↓
    [CONDITIONAL ROUTING]
           ↓
    ┌─────────────────┬──────────────────┐
    ↓                 ↓                  ↓
[IMAGE ANALYSIS]  [EHR ANALYSIS]  [ARCHIVE ANALYSIS]
- Abnormalities   - Patient History   - Read SKILL.md
- Medical Type    - Conditions        - Smart file reading
- Findings        - Recommendations   - Generate insights
    │                 │                  │
    └─────────────────┴──────────────────┘
           ↓
    [FINALIZATION AGENT]
    - Aggregate results
    - Save to results.json
           ↓
    [SUMMARY AGENT]
    - Generate analysis_report.txt
    - Create SKILL.md
    - Archive to timestamped folder
           ↓
    results/output/YYYY-MM-DD_HH-MM-SS/
    ├── results.json
    ├── analysis_report.txt
    └── SKILL.md
```

### Archive System Workflow
1. **Generation**: Every analysis run creates timestamped archive with metadata
2. **Discovery**: Next run automatically detects and includes archives as input
3. **Re-analysis**: Archives are intelligently re-processed to find patterns
4. **Metadata**: SKILL.md contains execution metadata for decision-making
5. **Comparison**: Multiple archives enable longitudinal analysis

## 📁 Project Structure

```
CareBuddy/
├── main.py                      # Entry point (backward compatible)
├── agent_orchestrator.py        # LangGraph orchestrator & state machine
├── backend/
│   ├── app.py                   # FastAPI service with REST endpoints
│   ├── utils.py                 # Device detection, logging, archiving
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── discovery_agent.py   # File & archive discovery
│   │   ├── processing_agent.py  # Intelligent file/archive processing
│   │   ├── finalization_agent.py# Result aggregation
│   │   └── summary_agent.py     # Report generation & archiving
│   └── tools/
│       ├── __init__.py
│       └── parsing_tools.py     # SKILL.md parsing utilities
├── frontend/
│   ├── index.html               # Single-page app
│   └── styles/
├── KAG/
│   ├── ddss.xrdf              # Disease-Ontology/Symptom-Ontology RDF file
│   ├── build_disease_symptom_graph.py  # Parse RDF & load Disease-Symptom graph to Neo4j
│   ├── search_neo4j.py        # Search Disease-Symptom graph in Neo4j
│   └── database/
│       └── disease_symptom_graph.json  # Exported disease-symptom relationships
├── results/
│   ├── input/                   # Upload directory
│   └── output/                  # Archives & current results
│       ├── 2026-02-15_18-30-45/ # Timestamped archive
│       │   ├── SKILL.md
│       │   ├── results.json
│       │   └── analysis_report.txt
│       ├── results.json         # Latest results
│       └── analysis_report.txt  # Latest report
├── README.md
└── pyproject.toml
```

## 🧬 Knowledge Graph (KAG) - Disease-Symptom Database

CareBuddy includes a comprehensive Disease-Symptom knowledge graph built from the Disease Ontology (DOID) and Symptom Ontology (SYMP), loaded into Neo4j for efficient querying.

### Graph Statistics
- **~12,000+** Disease-Symptom relationships
- **~8,800** Unique diseases (DOID_*)
- **~21,800** Unique symptoms (SYMP_*)
- **Cross-references**: ICD9, UMLS CUI, and more

### Graph Tools

#### 1. Build Disease-Symptom Graph
Parse the RDF ontology and load relationships into Neo4j.

```bash
# Load graph (parse ddss.xrdf and populate Neo4j)
python KAG/build_disease_symptom_graph.py

# Parse only, don't load (see statistics)
python KAG/build_disease_symptom_graph.py --dry-run

# Clear existing graph before loading
python KAG/build_disease_symptom_graph.py --clear

# Export extracted data to JSON
python KAG/build_disease_symptom_graph.py --export-json
```

#### 2. Search the Graph
Query diseases and symptoms interactively.

```bash
# Find diseases with a specific symptom
python KAG/search_neo4j.py --symptom "fever" --limit 20

# Find all symptoms for a disease
python KAG/search_neo4j.py --disease "angiosarcoma" --limit 10

# Find related diseases (sharing symptoms)
python KAG/search_neo4j.py --related-to DOID_0001816 --limit 15

# Get full disease details with all symptoms
python KAG/search_neo4j.py --detail-disease "angiosarcoma"

# Get full symptom details with all associated diseases
python KAG/search_neo4j.py --detail-symptom "fever"

# View graph statistics
python KAG/search_neo4j.py --stats
```

### Query Examples

**Find all diseases with symptom "fever":**
```bash
python KAG/search_neo4j.py --symptom "fever"
```

**Get comprehensive disease profile:**
```bash
python KAG/search_neo4j.py --detail-disease "angiosarcoma"
```

### Integration with Medical Analysis

The Disease-Symptom graph is automatically queried during EHR analysis to:
- **Validate extracted conditions** against known disease-symptom patterns
- **Suggest related diseases** when symptoms align with multiple conditions
- **Cross-reference** findings with standardized medical ontologies (ICD9, UMLS)
- **Identify symptom clusters** indicating complex conditions

## 📚 Documentation

- [Frontend Setup Guide](./FRONTEND_SETUP.md) - Detailed UI setup and usage
- [Poetry Installation](./POETRY_INSTALL.md) - Dependency management
- [Neo4j Setup Guide](./NEO4J_STARTUP_GUIDE.md) - Database configuration
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI

### Key API Endpoints

#### File Processing
- `POST /upload` - Upload medical files
- `POST /process` - Start multi-agent processing
- `GET /status` - Get current processing status
- `GET /reports/analysis/content` - Get analysis report as JSON
- `GET /reports/results.json` - Download results.json
- `DELETE /reset` - Clear uploaded files and reset state

#### Archive & SKILL Metadata
- `GET /archives/skill/summary` - Aggregate stats from all archives
- `GET /archives/skill` - List all archive SKILL metadata
- `GET /archives/skill/{archive_name}` - Get specific archive metadata

#### Health & Info
- `GET /health` - System health and device info
- `GET /` - API information

## � SKILL.md Metadata System

Every analysis run automatically creates a timestamped archive with `SKILL.md` containing:

```markdown
# Analysis Skill Report

## Processing Metadata
- Generated: 2026-02-15 18:30:45
- Archive Folder: 2026-02-15_18-30-45

## Processing Statistics
- Total Files: 5
- Successfully Processed: 5
- Success Rate: 100.0%

## System Information
- Device Used: mps
- Data Type: bfloat16
- Model: google/medgemma-1.5-4b-it
```

### Archive Processing Logic

The system intelligently reads archive files based on content:

| Condition | SKILL.md | Report | Results.json |
|-----------|----------|--------|--------------|
| 100% success, ≤3 files | ✅ Read | ❌ Skip | ❌ Skip |
| 100% success, >3 files | ✅ Read | ❌ Skip | ✅ Read |
| <100% success (any) | ✅ Read | ✅ Read | ✅ Read |

This minimizes context usage while maintaining sufficient information for analysis.

## �🔒 Security

⚠️ **Note**: Current implementation is for development. For production:
- Add user authentication  
- Implement rate limiting
- Set specific CORS origins
- Add input validation
- Use HTTPS/TLS encryption

## 📞 Support

Check [FRONTEND_SETUP.md](./FRONTEND_SETUP.md) for troubleshooting and detailed guides.


---

**Made with ❤️ for better healthcare through AI**
