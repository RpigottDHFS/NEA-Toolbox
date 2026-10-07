from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import json
from typing import Callable, Iterable

import cv2

from .models import Student
from .utils import file_sha256, safe_component

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".heif", ".dng", ".cr2", ".cr3", ".nef", ".arw", ".raf", ".orf", ".rw2"}


@dataclass
class SortSummary:
    sorted: int = 0
    review: int = 0
    already_copied: int = 0
    errors: int = 0
    cancelled: bool = False
    report_csv: str = ""
    originals_copied: int = 0
    originals_already_copied: int = 0
    student_copies: int = 0
    matched_example: str = ""


def _decode_qr(path: Path) -> list[str]:
    import numpy as np
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return []
    detector = cv2.QRCodeDetector()
    values = set()
    max_detected = 0
    height, width = image.shape[:2]
    # Different scales and overlapping tiles recover codes missed in group photos.
    probes = [image, cv2.resize(image, None, fx=.75, fy=.75), cv2.resize(image, None, fx=1.5, fy=1.5)]
    if min(height, width) > 300:
        for y0, y1 in [(0, int(height*.65)), (int(height*.35), height)]:
            for x0, x1 in [(0, int(width*.65)), (int(width*.35), width)]:
                probes.append(image[y0:y1, x0:x1])
    for probe in probes:
        try:
            _ok, decoded, points, _straight = detector.detectAndDecodeMulti(probe)
            if points is not None:
                max_detected = max(max_detected, len(points))
            values.update(v.strip() for v in decoded if v and v.strip())
            value, _points, _straight = detector.detectAndDecode(probe)
            if value and value.strip():
                values.add(value.strip())
        except cv2.error:
            continue
    if max_detected > len(values):
        values.add("UNREADABLE_DETECTED_QR")
    return sorted(values)


def _candidate_from_payload(payload: str, students: dict[str, Student]) -> str | None:
    payload = payload.strip()
    if payload in students:
        return payload
    parts = payload.split("|")
    if len(parts) == 3 and parts[0].upper() in {"NEA", "NEA1"}:
        candidate = parts[2].strip()
        if candidate in students and students[candidate].centre_number == parts[1].strip():
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

    # Exclusive create protects existing photos even if two calls race.
    try:
        with destination.open("xb") as target, source.open("rb") as original:
            shutil.copyfileobj(original, target)
    except FileExistsError:
        return _copy_idempotent(source, destination_dir)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    if file_sha256(source) != file_sha256(destination):
        destination.unlink(missing_ok=True)
        raise OSError("Copy verification failed; original source retained")
    shutil.copystat(source, destination)
    return destination, False


def sort_photos(source_folders: Iterable[str | Path], output_folder: str | Path, students: Iterable[Student], progress: Callable[[int, int, str], None] | None = None, should_cancel: Callable[[], bool] | None = None) -> SortSummary:
    output = Path(output_folder).expanduser().resolve()
    sources = list(source_folders)
    for source in sources:
        src = Path(source).expanduser().resolve()
        if not src.exists():
            raise ValueError(f"Photo source is unavailable: {src}")
        if src == output or src in output.parents or output in src.parents:
            raise ValueError("Choose separate source and output folders, neither inside the other.")
    student_map = {}
    for student in students:
        if student.candidate_number in student_map:
            raise ValueError("Duplicate candidate numbers in roster; correct the roster before sorting.")
        student_map[student.candidate_number] = student
    if not student_map:
        raise ValueError("Load a valid student roster before sorting.")
    images = sorted(_iter_images(sources, output), key=lambda p: str(p).casefold())
    if not images:
        raise ValueError("No supported photos found in the selected sources.")
    summary = SortSummary()
    decoded = {}
    # Validate identity before copying. An unreadable/unknown first photo is skipped.
    for index, source in enumerate(images, 1):
        if should_cancel and should_cancel():
            summary.cancelled = True
            return summary
        if progress:
            progress(0, len(images), f"Checking roster: photo {index}/{len(images)} - {source.name}")
        try:
            payloads = _decode_qr(source)
        except Exception:
            payloads = []
        decoded[source] = payloads
        matches = [_candidate_from_payload(p, student_map) for p in payloads]
        if any(matches):
            summary.matched_example = str(source)
            break
    if not summary.matched_example:
        raise ValueError("No readable student QR code matches this roster. No photos were copied. "
                         "Check the centre and candidate numbers, load the correct current Excel file, "
                         "and check the headings Name, Candidate number and Group Code. "
                         "Inserted columns are supported; changed candidate numbers require corrected data or new tags.")

    output.mkdir(parents=True, exist_ok=True)
    review_folder = output / "Manual_Check_Required"
    originals_folder = output / "All_Original_Images"
    reports = output / "Reports"
    reports.mkdir(exist_ok=True)
    report_path = reports / f"photo_sort_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.csv"
    fields = ["source", "status", "candidate_number", "destination", "original_destination", "detail"]
    summary.report_csv = str(report_path)
    with report_path.open("x", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, source in enumerate(images, 1):
            if should_cancel and should_cancel():
                summary.cancelled = True
                break
            row = dict.fromkeys(fields, "")
            row["source"] = str(source)
            destinations, failures = [], []
            new_student = False
            review_needed = False
            all_existed = True
            try:
                original, existed = _copy_idempotent(source, originals_folder)
                row["original_destination"] = str(original)
                if existed:
                    summary.originals_already_copied += 1
                else:
                    summary.originals_copied += 1
                payloads = decoded[source] if source in decoded else _decode_qr(source)
                matches = {_candidate_from_payload(p, student_map) for p in payloads}
                unknown = None in matches
                matches.discard(None)
                review_needed = not matches or unknown
                row["candidate_number"] = ";".join(sorted(matches))
                for candidate in sorted(matches):
                    try:
                        dest, existed = _copy_idempotent(source, _student_folder(output, student_map[candidate]))
                        destinations.append(str(dest))
                        all_existed = all_existed and existed
                        if not existed:
                            new_student = True
                            summary.student_copies += 1
                    except Exception as exc:
                        failures.append(f"Candidate {candidate}: {exc}")
                if new_student:
                    summary.sorted += 1
                if review_needed:
                    detail = "No readable QR code" if not payloads else "One or more QR codes do not match the roster"
                    row["detail"] = detail
                    try:
                        dest, existed = _copy_idempotent(source, review_folder)
                        destinations.append(str(dest))
                        all_existed = all_existed and existed
                        if not existed:
                            summary.review += 1
                    except Exception as exc:
                        failures.append(f"Manual review: {exc}")
                if failures:
                    raise OSError("; ".join(failures))
                if all_existed:
                    summary.already_copied += 1
                    row["status"] = "already_copied"
                else:
                    row["status"] = "sorted_and_review" if matches and review_needed else ("sorted" if matches else "review")
            except Exception as exc:
                row["status"] = "error"
                row["detail"] = str(exc)
                summary.errors += 1
            row["destination"] = json.dumps(destinations, ensure_ascii=False)
            writer.writerow({k: ("'" + v if v.startswith(("=", "+", "-", "@")) else v) for k, v in row.items()})
            handle.flush()
            if progress:
                progress(index, len(images), source.name)
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
