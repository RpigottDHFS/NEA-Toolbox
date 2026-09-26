# NEA Toolbox

NEA Toolbox is a Windows desktop application for creating pupil QR identification cards and sorting Food NEA practical photographs into local folders.

**Default centre number:** 23162

## Production-local workflow

The production workflow deliberately keeps pupil information local. The application can load the school's Excel dashboard or a simple CSV at runtime, but the real dashboard, real pupil data and private sample photographs must **never** be committed to this repository.

Current workflow:

1. Load Excel/CSV locally.
2. Create printable cards showing centre number, candidate name, candidate number and QR code.
3. Add one or more camera/SD-card folders.
4. Choose a local output folder.
5. Sort photographs into Group / Student name - Candidate number.
6. Send unreadable or ambiguous photographs to Manual_Check_Required.
7. Review an exception and manually assign it only when the student is known.
8. Keep CSV audit reports in the local output folder.

The QR payload contains only NEA|centre|candidate_number. The visible card carries the student's name for human checking.

## Privacy

.gitignore blocks the common pupil-data and private-sample formats/folders used during development. This is a safety net, not permission to put school data in GitHub.

Do not commit:
- the real Excel dashboard or exports containing real pupils;
- private sample packs or practical photographs;
- generated real-pupil QR cards;
- sorted pupil folders or reports containing pupil names.

Only fictional examples belong in data/.

## Run from source on Windows

Python 3.12 is recommended. Double-click Start_NEA_Toolbox.bat. On first run it creates a local virtual environment and installs the required packages.

For school deployment, prefer the packaged Windows build from GitHub Actions after IT review.

## Windows build

The Build Windows app GitHub Action builds on a Windows runner with Python 3.12 and PyInstaller. A successful run produces an artifact named NEA-Toolbox-Windows. Extract the whole artifact and keep _internal next to NEA-Toolbox.exe.

## Simple CSV format

Required headings are CentreNumber, CandidateNumber, StudentName and GroupCode. A fictional example is included in data/students.csv.

Excel workbooks may contain additional sheets. The importer scans for sheets containing candidate-number and student-name headings and skips irrelevant sheets.

## Important operating notes

- Work locally first; direct per-pupil OneDrive upload is a later phase.
- Never erase SD cards until the copied evidence has been checked and backed up or synced according to school policy.
- Do not guess when a QR code fails. Leave the image in Manual_Check_Required.
- Test the packaged build on the actual school Windows PC before wider deployment.
