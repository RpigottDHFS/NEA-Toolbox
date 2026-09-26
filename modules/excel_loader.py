from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

import pandas as pd

from .models import Student
from .utils import clean_text

CENTRE_ALIASES = {"centrenumber", "centre", "centreno", "center", "centernumber"}
CANDIDATE_ALIASES = {"candidatenumber", "candidate", "candidateno", "candidateid", "candno"}
NAME_ALIASES = {"studentname", "name", "candidate name", "pupilname", "student"}
GROUP_ALIASES = {"groupcode", "teachinggroup", "group", "class", "classcode", "teaching group"}


def _norm_header(value) -> str:
    text = clean_text(value).lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def _find_columns(columns):
    normalized = {_norm_header(c): c for c in columns if clean_text(c)}

    def pick(aliases):
        for alias in aliases:
            key = _norm_header(alias)
            if key in normalized:
                return normalized[key]
        return None

    return pick(CENTRE_ALIASES), pick(CANDIDATE_ALIASES), pick(NAME_ALIASES), pick(GROUP_ALIASES)


@dataclass
class LoadResult:
    students: list[Student] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sheets_used: list[str] = field(default_factory=list)

    @property
    def by_candidate(self) -> dict[str, Student]:
        return {s.candidate_number: s for s in self.students}

    @property
    def groups(self) -> list[str]:
        return sorted({s.group_code for s in self.students if s.group_code})


def _records_from_frame(df: pd.DataFrame, default_centre: str, sheet_name: str, result: LoadResult):
    centre_col, candidate_col, name_col, group_col = _find_columns(df.columns)
    if not candidate_col or not name_col:
        return False

    used = False
    missing_candidate = 0
    seen = {s.candidate_number for s in result.students}
    for _, row in df.iterrows():
        name = clean_text(row.get(name_col, ""))
        candidate = clean_text(row.get(candidate_col, ""))
        group = clean_text(row.get(group_col, "")) if group_col else ""
        centre = clean_text(row.get(centre_col, "")) if centre_col else default_centre
        centre = centre or default_centre

        if not name and not candidate:
            continue
        used = True
        if not candidate:
            missing_candidate += 1
            continue
        if not name:
            result.warnings.append(f"{sheet_name}: candidate {candidate} has no student name and was skipped.")
            continue
        if candidate in seen:
            result.warnings.append(f"{sheet_name}: duplicate candidate number {candidate} was skipped.")
            continue
        seen.add(candidate)
        result.students.append(Student(centre, candidate, name, group))

    if missing_candidate:
        result.warnings.append(f"{sheet_name}: {missing_candidate} row(s) with a student name but no candidate number were skipped.")
    if used:
        result.sheets_used.append(sheet_name)
    return used


def _read_excel_sheet_with_header_scan(filepath: str | Path, sheet_name: str, default_centre: str, result: LoadResult) -> bool:
    raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None, dtype=object)
    for header_row in range(min(25, len(raw))):
        headers = list(raw.iloc[header_row])
        _, candidate_col, name_col, _ = _find_columns(headers)
        if candidate_col and name_col:
            frame = raw.iloc[header_row + 1 :].copy()
            frame.columns = headers
            frame = frame.dropna(how="all")
            return _records_from_frame(frame, default_centre, sheet_name, result)
    return False


def load_students(filepath: str | Path, default_centre: str = "23162") -> LoadResult:
    filepath = Path(filepath)
    result = LoadResult()

    if filepath.suffix.lower() == ".csv":
        df = pd.read_csv(filepath, dtype=object)
        if not _records_from_frame(df, default_centre, filepath.name, result):
            raise ValueError("CSV needs CandidateNumber and StudentName columns (GroupCode is recommended).")
    elif filepath.suffix.lower() in {".xlsx", ".xlsm"}:
        book = pd.ExcelFile(filepath)
        for sheet_name in book.sheet_names:
            try:
                _read_excel_sheet_with_header_scan(filepath, sheet_name, default_centre, result)
            except Exception as exc:
                result.warnings.append(f"{sheet_name}: could not read this sheet ({exc}).")
    else:
        raise ValueError("Please choose an .xlsx, .xlsm or .csv file.")

    if not result.students:
        raise ValueError("No valid student rows were found. Expected candidate number and student name headings.")
    return result
