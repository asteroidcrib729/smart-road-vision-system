# Smart Road Vision System (SRVS V4) — Final Year Project (FYP)

The **Smart Road Vision System (SRVS V4)** is an advanced computer vision and traffic enforcement system designed to assist traffic police officers. It automatically detects vehicles driven without readable/valid license plates, rickshaws operating without permits, and motorcycle riders who are not wearing helmets.

The system utilizes an asynchronous dual-stream pipeline executing deep learning inference, Re-Identification tracking, super-resolution license plate restoration, local OCR, and cloud-fallback vision validation.

---

## 🏗️ Project Architecture

```
                  ┌────────────────────────────────────────────────────────┐
                  │                 Next.js Dashboard (Vercel)              │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                   Fetch APIs & SSE Events
                                              │
                  ┌───────────────────────────▼────────────────────────────┐
                  │                 FastAPI Wrapper Server                 │
                  └───────────────────────────┬────────────────────────────┘
                                              │
                                  Runs Asynchronous Pipeline
                                              │
     ┌────────────────────────┬───────────────┼────────────────┬────────────────────────┐
     │                        │               │                │                        │
┌────▼────────┐         ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼───────┐         ┌──────▼───────┐
│ YOLOv8      │         │ DeepOCSORT│   │ TransReID │   │ Local OCR    │         │ Gemini API   │
│ Detection   │         │ Tracking  │   │ Module    │   │ (PaddleOCR)  │         │ Fallback     │
└─────────────┘         └───────────┘   └───────────┘   └──────────────┘         └──────────────┘
```

The system is split into two independent codebases:
1. **Frontend (`srvs-frontend-next/`)**: Next.js, React, Tailwind CSS, TypeScript. Interactive canvas telemetry overlay, Real-ESRGAN split slider image comparisons, CSV explorers, and responsive dashboards.
2. **Backend (`srvs-backend-core/`)**: Python, FastAPI, YOLOv8, PyTorch, PaddleOCR, SQLite. Multi-table SQL logging, Server-Sent Events (SSE) live telemetry publisher, and runtime Google Drive video ingestion.

---

## 📁 Repository Directory Structure

```
smart-road-vision-system/
├── srvs-frontend-next/        # Next.js React Dashboard
│   ├── src/
│   │   ├── app/               # Page routers & layouts
│   │   └── components/        # Dashboard layout, LEDGER tabs, slider modal
│   └── package.json           # Node dependencies
├── srvs-backend-core/         # FastAPI Deep Learning Engine
│   ├── core/                  # YOLOv8 and DeepOCSORT tracker handlers
│   ├── models/                # Re-Identification models (TransReID)
│   ├── subtasks/              # Sub-tasks (ANPR license plates, Helmet checks)
│   ├── utils/                 # SQLite database handlers and SSE managers
│   ├── app.py                 # FastAPI Web Server entrypoint
│   ├── pipeline.py            # Asynchronous dual-stream inference pipeline
│   ├── downloader.py          # Google Drive ingestion logic (gdown integration)
│   ├── Dockerfile             # PyTorch + CUDA backend container configuration
│   ├── requirements.txt       # Python environment package pins
│   └── .env                   # Local API keys (GEMINI_API_KEY, HF_API_KEY)
├── docker-compose.yml         # Local/EC2 Docker GPU pass-through orchestrator
├── pyrefly.toml               # Static type checker settings
└── README.md                  # Project overview and setup guidelines
```

---

## 🚀 Local Quick-Start Setup

### 1. Run Frontend (Next.js Dashboard)
Ensure you have **Node.js (v18+)** installed.

```bash
cd srvs-frontend-next
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.
* *Note: When the FastAPI backend is offline, the frontend automatically falls back to a high-fidelity offline simulation loop, allowing you to demonstrate UI functionalities (telemetry logs, slider overlays, database tables) without running the GPU backend.*

### 2. Run Backend (FastAPI Engine)
Ensure you have **Python 3.12** installed.

```bash
cd srvs-backend-core
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file inside `srvs-backend-core/`:
```env
GEMINI_API_KEY=your_gemini_api_key
HF_API_KEY=your_hugging_face_api_token
```

Start the API server:
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
API docs will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 🐋 Production Deployment (Docker + CUDA GPU Pass-Through)

For production deployment on an **AWS EC2 G5 GPU Instance** (`g5.xlarge`), use the pre-configured Docker templates to prevent host dependency issues.

### Prerequisites on the Host VM:
Ensure the host has the **NVIDIA Container Toolkit** installed to pass the physical GPU into the container.

1. **Build and Launch Container**:
   ```bash
   docker-compose up -d --build
   ```
2. **Access API Logs**:
   ```bash
   docker logs -f srvs-backend-container
   ```
3. **Verify CUDA availability** inside the container:
   ```bash
   docker exec -it srvs-backend-container python -c "import torch; print('CUDA Available:', torch.cuda.is_available())"
   ```
