# TabCapture

Extract guitar tab panels from YouTube tutorials into a printable PDF.

## How it works

1. You paste a YouTube URL from a tab tutorial channel
2. The backend downloads the video, extracts frames at 2fps, and detects when the tab panel jumps to a new set of measures
3. Each unique panel is captured and sent to the frontend
4. You reorder or delete panels in the editor, then download a PDF

> **Note on overlap:** The last visible measure in each panel is a duplicate of the first measure in the next panel (because the panel refreshes when the playhead hits the last barline, which is off-screen). This is intentional — you can delete duplicate panels in the editor.

---

## Running Locally

### Prerequisites

- Python 3.12
- Node.js 18+
- ffmpeg: `brew install ffmpeg`

### Setup

**1. Clone and create the virtual environment**

```bash
git clone <repo-url>
cd getTabs
python3.12 -m venv venv
source venv/bin/activate
```

**2. Install backend dependencies**

```bash
pip install -r backend/requirements.txt
```

**3. Configure the frontend**

```bash
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > frontend/.env.local
```

**4. Terminal 1 — backend**

```bash
source venv/bin/activate   # if not already active
cd backend
uvicorn main:app --reload --port 8000
```

**5. Terminal 2 — frontend**

```bash
cd frontend
npm install
npm run dev
```

Both processes must run simultaneously. Backend is at http://localhost:8000, frontend at http://localhost:3000.

---

## Switching between local and deployed backend

The frontend reads the backend URL from `frontend/.env.local`. Swap the value to point at whichever backend you want:

```bash
# Local backend
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > frontend/.env.local

# Deployed backend (Render)
echo 'NEXT_PUBLIC_API_URL=https://<your-app>.onrender.com' > frontend/.env.local
```

Restart `npm run dev` after changing `.env.local` for Next.js to pick up the new value.

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
