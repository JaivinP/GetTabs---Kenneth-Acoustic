# TabCapture

Extract guitar tab panels from YouTube tutorials into a printable PDF.

## How it works

1. You paste a YouTube URL from a tab tutorial channel
2. The backend downloads the video, extracts frames at 2fps, and detects when the tab panel jumps to a new set of measures
3. Each unique panel is captured and sent to the frontend
4. You reorder or delete panels in the editor, then download a PDF

> **Note on overlap:** The last visible measure in each panel is a duplicate of the first measure in the next panel (because the panel refreshes when the playhead hits the last barline, which is off-screen). This is intentional — you can delete duplicate panels in the editor.

---

## Local Development

### Prerequisites

- Node.js 18+
- Python 3.11+
- `ffmpeg` installed on your system (`brew install ffmpeg` on Mac)
- `yt-dlp` installed (`pip install yt-dlp` or `brew install yt-dlp`)

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at http://localhost:8000

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Frontend runs at http://localhost:3000

---

## Deployment

### Backend → Railway

1. Create a new Railway project
2. Connect this repo, set the **root directory** to `backend/`
3. Railway auto-detects the Dockerfile and builds it
4. Note your Railway URL (e.g. `https://tabcapture-backend.up.railway.app`)

### Frontend → Vercel

1. Create a new Vercel project from this repo
2. Set **root directory** to `frontend/`
3. Add environment variable:
   - `NEXT_PUBLIC_API_URL` = your Railway backend URL
4. Deploy

---

## Calibration

The tab region crop is hardcoded to the bottom ~32% of the frame (`TAB_ROW_START = 0.68` in `backend/extractor.py`). This is calibrated for one specific YouTube channel's layout. If panels look wrong, adjust:

- `TAB_ROW_START` — move up if the tab is getting cut off at the top
- `DIFF_THRESHOLD` — lower if panels are being missed, raise if getting false positives
- `DIFF_COL_END` — the chord diagram on the right is excluded from diff detection to avoid false positives; adjust if the channel's chord box is in a different position

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, Tailwind, dnd-kit |
| Backend | FastAPI, OpenCV, yt-dlp, Pillow, ReportLab |
| PDF | ReportLab (3 panels per page, landscape) |
| Hosting | Vercel (frontend) + Railway (backend) |
