# CareBuddy UI Setup & Running Guide

## Architecture

```
CareBuddy/
├── backend/
│   ├── app.py              # FastAPI server
│   ├── agent_orchestrator.py
│   ├── agents/             # Multi-agent system
│   └── input/              # Uploaded files
│
├── frontend/
│   └── index.html          # Web UI (vanilla JS)
│
└── run.sh                  # Startup script
```

## Quick Start

### Option 1: Automated Setup (Linux/macOS)

```bash
cd /Users/qiwang/Downloads/workplace/CareBuddy

# Make run.sh executable
chmod +x run.sh

# Start both backend and frontend
./run.sh
```

### Option 2: Manual Setup

**Terminal 1 - Start Backend API:**
```bash
cd /Users/qiwang/Downloads/workplace/CareBuddy
poetry install --no-root
poetry lock

cd backend
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
poetry run python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Start Frontend Server:**
```bash
cd /Users/qiwang/Downloads/workplace/CareBuddy/frontend
python -m http.server 8080
```

**Terminal 3 - Open in Browser:**
```bash
# Open in your browser
open http://localhost:8080
```

## Usage

### Web Interface Features

1. **📤 Upload Files**
   - Click or drag medical images (.jpg, .png) and EHR records (.txt)
   - Supports multiple file uploads

2. **🚀 Process Files**
   - Click "Process Files" to analyze uploaded files
   - Real-time progress tracking

3. **📊 View Results**
   - See individual file analysis results
   - Comprehensive summary report
   - Download results as JSON or text

4. **🔄 Reset System**
   - Clear all uploaded files and results
   - Start fresh analysis

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | API info |
| POST | `/upload` | Upload files |
| POST | `/process` | Start processing |
| GET | `/status` | Get processing status |
| GET | `/results/{filename}` | Get individual result |
| GET | `/reports/analysis` | Download analysis report |
| GET | `/reports/results.json` | Download results JSON |
| DELETE | `/reset` | Reset system |

### API Documentation

Once running, visit:
```
http://localhost:8000/docs
```

This provides an interactive Swagger UI to test all endpoints.

## Configuration

### Backend Settings

Edit `backend/app.py` to modify:
- Port (default: 8000)
- Input/Output directories
- CORS settings
- Model configuration

### Frontend Settings

Edit `frontend/index.html` to modify:
- API endpoint (default: `http://localhost:8000`)
- Colors and styling
- UI messages

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000

# Kill the process if needed
kill -9 <PID>

# Try different port
poetry run python -m uvicorn app:app --port 8001
```

### Frontend can't connect to backend
- Make sure backend is running on port 8000
- Check CORS settings in `backend/app.py`
- Verify firewall allows localhost connections

### No results displayed
- Check backend logs for processing errors
- Ensure input files are in correct format
- Check that Hugging Face token is set (if needed)

## Performance Tips

1. **Model Loading**: First inference takes longer as model loads
2. **Large Files**: Images are processed in memory; keep under 50MB
3. **Batch Processing**: Process multiple files at once for efficiency
4. **GPU Acceleration**: Uses MPS on macOS, CUDA if available, otherwise CPU

## File Limits

- Maximum file size: 100MB (configurable)
- Maximum files per upload: 10 (configurable)
- Supported image formats: .jpg, .jpeg, .png
- Supported text formats: .txt (UTF-8)

## Security Notes

- Frontend is open to all origins (CORS: *)
- No authentication implemented (add before production)
- Files stored locally in `backend/input/`
- Consider adding rate limiting for production

## Next Steps

1. **Authentication**: Add user login
2. **Database**: Store results persistently
3. **Production Deploy**: Use Docker + cloud hosting
4. **Mobile App**: Create React Native version
5. **Batch API**: Add batch processing endpoints
