from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
from typing import Callable, Iterable

import cv2

from .models import Student
from .utils import file_sha256, safe_component

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


@dataclass
class SortSummary:
    sorted: int = 0
    review: int = 0
    already_copied: int = 0
    errors: int = 0
    cancelled: bool = False
    report_csv: str = ""


def _decode_qr(path: Path) -> list[str]:
    image = cv2.imread(str(path))
    if image is None:
        return []
    detector = cv2.QRCodeDetector()
    values: list[str] = []
    try:
        ok, decoded_info, _points, _straight = detector.detectAndDecodeMulti(image)
        if ok:
            values.extend(v.strip() for v in decoded_info if v and v.strip())
    except Exception:
        pass
    if not values:
        try:
            value, _points, _straight = detector.detectAndDecode(image)
            if value and value.strip():
                values.append(value.strip())
        except Exception:
            pass
    return list(dict.fromkeys(values))


def _candidate_from_payload(payload: str, students: dict[str, Student]) -> str | None:
    payload = payload.strip()
    if payload in students:
        return payload
    parts = payload.split("|")
    if len(parts) == 3 and parts[0].upper() == "NEA":
        candidate = parts[2].strip()
        if candidate in students:
            return candidate
    return None


def _iter_images(source_folders: Iterable[str | Path], output_folder: Path):
    output_resolved = output_folder.resolve()
    seen: set[Path] = set()
    for source in source_folders:
        source_path = Path(source).expanduser().resolve()
        if not source_path.exists():
            continue
        candidates = [source_path] if source_path.is_file() else source_path.rglob("*")
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen or not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            if resolved == output_resolved or output_resolved in resolved.parents:
                continue
            seen.add(resolved)
            yield path


def _student_folder(output_folder: Path, student: Student) -> Path:
    group = safe_component(student.group_code, "Ungrouped")
    student_name = safe_component(student.student_name)
    candidate = safe_component(student.candidate_number)
    return output_folder / group / f"{student_name} - {candidate}"


def _copy_idempotent(source: Path, destination_dir: Path) -> tuple[Path, bool]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / source.name
    source_hash = None

    if destination.exists():
        try:
            source_hash = file_sha256(source)
            if file_sha256(destination) == source_hash:
                return destination, True
        except OSError:
            pass
        stem, suffix = source.stem, source.suffix
        counter = 2
        while True:
            candidate = destination_dir / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                destination = candidate
                break
            try:
                if source_hash is None:
                    source_hash = file_sha256(source)
                if file_sha256(candidate) == source_hash:
                    return candidate, True
            except OSError:
                pass
            counter += 1

    shutil.copy2(source, destination)
    return destination, False


def sort_photos(source_folders: Iterable[str | Path], output_folder: str | Path, students: Iterable[Student], progress: Callable[[int, int, str], None] | None = None, should_cancel: Callable[[], bool] | None = None) -> SortSummary:
    output = Path(output_folder).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    review_folder = output / "Manual_Check_Required"
    review_folder.mkdir(parents=True, exist_ok=True)

    student_map = {s.candidate_number: s for s in students}
    images = list(_iter_images(source_folders, output))
    summary = SortSummary()
    report_rows: list[dict[str, str]] = []

    for index, source in enumerate(images, 1):
        if should_cancel and should_cancel():
            summary.cancelled = True
            break
        status = "error"
        candidate = ""
        destination = ""
        detail = ""
        try:
            payloads = _decode_qr(source)
            candidates = {_candidate_from_payload(p, student_map) for p in payloads}
            candidates.discard(None)
            if len(candidates) == 1:
                candidate = next(iter(candidates))
                student = student_map[candidate]
                dest, existed = _copy_idempotent(source, _student_folder(output, student))
                destination = str(dest)
                if existed:
                    status = "already_copied"
                    summary.already_copied += 1
                else:
                    status = "sorted"
                    summary.sorted += 1
            else:
                if not payloads:
                    detail = "No readable QR code"
                elif not candidates:
                    detail = "QR code does not match the loaded roster"
                else:
                    detail = "More than one student QR code was detected"
                dest, existed = _copy_idempotent(source, review_folder)
                destination = str(dest)
                if existed:
                    status = "already_copied"
                    summary.already_copied += 1
                else:
                    status = "review"
                    summary.review += 1
        except Exception as exc:
            detail = str(exc)
            summary.errors += 1

        report_rows.append({"source": str(source), "status": status, "candidate_number": candidate, "destination": destination, "detail": detail})
        if progress:
            progress(index, len(images), source.name)

    reports = output / "Reports"
    reports.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports / f"photo_sort_{stamp}.csv"
    with report_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "status", "candidate_number", "destination", "detail"])
        writer.writeheader()
        writer.writerows(report_rows)
    summary.report_csv = str(report_path)
    return summary


def assign_review_photo(review_photo: str | Path, output_folder: str | Path, student: Student) -> Path:
    review_photo = Path(review_photo)
    output = Path(output_folder)
    destination, _ = _copy_idempotent(review_photo, _student_folder(output, student))
    reports = output / "Reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / "manual_assignments.csv"
    new_file = not report_path.exists()
    with report_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        if new_file:
            writer.writerow(["timestamp", "review_photo", "candidate_number", "student_name", "destination"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), str(review_photo), student.candidate_number, student.student_name, str(destination)])
    return destination
