from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
import qrcode

from .models import Student
from .utils import safe_component


def _font(size: int, bold: bool = False):
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_font(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int, bold: bool = False):
    for size in range(start_size, 13, -1):
        font = _font(size, bold)
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return _font(13, bold)


def render_card(student: Student, demo: bool = False) -> Image.Image:
    width, height = 1180, 740
    card = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(card)
    margin = 42
    draw.rounded_rectangle((6, 6, width - 6, height - 6), radius=24, outline="black", width=4)

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=12, border=4)
    qr.add_data(student.qr_payload)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((520, 520), Image.Resampling.NEAREST)
    card.paste(qr_img, (620, 105))

    left_width = 530
    centre_font = _font(32, True)
    small_font = _font(28)
    number_font = _font(55, True)
    name_font = _fit_font(draw, student.student_name, left_width - 50, 52, True)

    draw.text((margin, 75), f"Centre {student.centre_number}", fill="black", font=centre_font)
    draw.text((margin, 185), "Candidate", fill="black", font=small_font)
    draw.text((margin, 225), student.candidate_number, fill="black", font=number_font)
    draw.text((margin, 340), "Student", fill="black", font=small_font)
    draw.multiline_text((margin, 380), student.student_name, fill="black", font=name_font, spacing=8)
    if student.group_code:
        draw.text((margin, 555), f"Group {student.group_code}", fill="black", font=small_font)
    if demo:
        draw.text((margin, 655), "DEMONSTRATION", fill="black", font=_font(24, True))
    return card


def generate_qr_cards(students: Iterable[Student], output_folder: str | Path, demo: bool = False) -> dict[str, Path]:
    students = list(students)
    if not students:
        raise ValueError("No students selected.")

    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    images_folder = output_folder / "Individual_Cards"
    images_folder.mkdir(exist_ok=True)

    rendered: list[Image.Image] = []
    for student in students:
        card = render_card(student, demo=demo)
        rendered.append(card)
        card.save(images_folder / f"{safe_component(student.group_code)}_{safe_component(student.candidate_number)}.png")

    a4_w, a4_h = 3508, 2480
    pages: list[Image.Image] = []
    for i in range(0, len(rendered), 2):
        page = Image.new("RGB", (a4_w, a4_h), "white")
        for slot, card in enumerate(rendered[i:i+2]):
            scale = min((a4_w - 280) / card.width, (a4_h / 2 - 190) / card.height)
            size = (int(card.width * scale), int(card.height * scale))
            resized = card.resize(size, Image.Resampling.LANCZOS)
            x = (a4_w - resized.width) // 2
            y = 90 + slot * (a4_h // 2)
            page.paste(resized, (x, y))
        pages.append(page)

    pdf_path = output_folder / "Student_QR_Cards.pdf"
    pages[0].save(pdf_path, "PDF", resolution=300, save_all=True, append_images=pages[1:])
    return {"pdf": pdf_path, "images": images_folder}
