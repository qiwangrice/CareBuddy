# CareBuddy: AI-Powered Medical Analysis System

## 🏥 Overview

CareBuddy is a sophisticated multi-agent medical image and EHR (Electronic Health Record) analysis system that combines:

- **LangGraph Multi-Agent Orchestrator**: Dynamically spawns agents based on input files
- **Medical AI Model**: `google/medgemma-1.5-4b-it` for analyzing medical images and records
- **FastAPI Backend**: RESTful API for processing and result management
- **Modern Web UI**: Beautiful, responsive interface for easy interaction

## ✨ Features

### Backend (LangGraph Multi-Agent System)
- ✅ **Discovery Agent**: Automatically scans input folder for images (.jpg, .png) and EHR records (.txt)
- ✅ **Processing Agents**: Routes files to specialized processors (image analyzer, EHR summarizer)
- ✅ **Finalization Agent**: Aggregates results into structured JSON
- ✅ **Summary Agent**: Generates comprehensive analysis reports
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

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd /Users/qiwang/Downloads/workplace/CareBuddy
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

## 📁 Project Structure

```
CareBuddy/
├── main.py                   # Entry point
├── agent_orchestrator.py     # LangGraph orchestrator
├── utils.py                  # Shared utils & logging
├── agents/                   # Multi-agent modules
├── backend/                  # FastAPI service
└── frontend/                 # Web UI
```

## 📚 Documentation

- [Frontend Setup Guide](./FRONTEND_SETUP.md) - Detailed UI setup and usage
- [Poetry Installation](./POETRY_INSTALL.md) - Dependency management
- [API Documentation](http://localhost:8000/docs) - Interactive Swagger UI

## 🔒 Security

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
