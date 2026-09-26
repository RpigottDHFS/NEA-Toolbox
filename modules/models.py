from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Student:
    centre_number: str
    candidate_number: str
    student_name: str
    group_code: str = ""

    @property
    def qr_payload(self) -> str:
        return f"NEA|{self.centre_number}|{self.candidate_number}"
