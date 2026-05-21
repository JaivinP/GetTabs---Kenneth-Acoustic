from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
import io
import traceback

from extractor import extract_panels, extract_panels_from_file
from pdf_generator import generate_pdf

app = FastAPI(title="TabCapture API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in prod
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExtractRequest(BaseModel):
    url: str


class PanelImage(BaseModel):
    id: str
    image: str  # base64 PNG


class GeneratePDFRequest(BaseModel):
    panels: List[PanelImage]
    title: str = "Guitar Tab"


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
async def extract(req: ExtractRequest):
    try:
        panels = extract_panels(req.url)
        return {"panels": panels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract-file")
async def extract_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        panels = extract_panels_from_file(content)
        return {"panels": panels}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-pdf")
async def gen_pdf(req: GeneratePDFRequest):
    try:
        pdf_bytes = generate_pdf(req.panels, req.title)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{req.title}.pdf"'},
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
