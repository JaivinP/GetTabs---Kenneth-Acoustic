import base64
import io
from typing import List
from PIL import Image
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER


PANELS_PER_PAGE = 3
PAGE_MARGIN = 0.4 * inch


def generate_pdf(panels: list, title: str = "Guitar Tab") -> bytes:
    """
    Stitch panel images into a compact multi-panel-per-page PDF.
    panels: list of PanelImage(id, image) where image is base64 PNG
    """
    buf = io.BytesIO()
    page_size = landscape(letter)
    page_w, page_h = page_size

    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=PAGE_MARGIN,
        rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,
        bottomMargin=PAGE_MARGIN,
        title=title,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TabTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=colors.HexColor("#1a1a1a"),
        alignment=TA_CENTER,
        spaceAfter=6,
    )
    label_style = ParagraphStyle(
        "PanelLabel",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=colors.HexColor("#888888"),
        alignment=TA_CENTER,
        spaceAfter=2,
    )

    usable_w = page_w - 2 * PAGE_MARGIN
    # Each panel gets full usable width; height is proportional to the crop
    # We'll compute per-panel after decoding the first image

    story = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.1 * inch))

    for i, panel in enumerate(panels):
        # Decode base64 → PIL → get aspect ratio
        img_bytes = base64.b64decode(panel.image)
        pil_img = Image.open(io.BytesIO(img_bytes))
        orig_w, orig_h = pil_img.size
        aspect = orig_h / orig_w

        panel_w = usable_w
        panel_h = panel_w * aspect

        # Cap height so we fit PANELS_PER_PAGE panels per page
        max_panel_h = (page_h - 2 * PAGE_MARGIN - 0.5 * inch) / PANELS_PER_PAGE
        if panel_h > max_panel_h:
            panel_h = max_panel_h
            panel_w = panel_h / aspect

        rl_img = RLImage(io.BytesIO(img_bytes), width=panel_w, height=panel_h)
        story.append(Paragraph(f"Panel {i + 1}", label_style))
        story.append(rl_img)
        story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    return buf.getvalue()
