# Version 1.1

## 1. Group photographs

A photograph containing QR codes for several known students is copied to every matching student's folder. Repeated codes for the same student produce one copy in that student's folder. Both centre and candidate must match for NEA/NEA1 codes. Existing candidate-only cards remain supported.

If an image has known codes and an unknown or detected-but-unreadable code, known students still receive it and a copy also goes to Manual_Check_Required. Check that extra identity manually. Software cannot recognise a QR that is too damaged to detect at all; include full, readable cards for every student concerned.

The results distinguish photos newly sorted from new student-folder copies. One photo sent to three students counts as one sorted photo and three copies. A photo can count as both sorted and requiring review. Error counts can overlap those counts when some destinations succeed and another fails. Reports list every successful destination, the archive path and any errors.

## 2. Original images

The output includes All_Original_Images alongside the group folders, Manual_Check_Required and Reports. This keeps unedited, byte-verified copies of processed input photographs, including photos needing review. Files on the SD card remain untouched. Identical filenames from different cameras are preserved using numbered suffixes. Repeat imports recognise unchanged copies and do not add another copy to the same location.

JPEG, PNG, BMP, TIFF, WebP, HEIC/HEIF and common camera RAW filename extensions are collected. Formats the installed decoder cannot read are archived and sent to review. Non-image sidecars, documents and videos are not included. The archive is a flat folder, not a reproduction of the SD card directories.

Keep sufficient space for the archive plus student copies. If you cancel, only processed photos have been archived; the summary reports how many. A batch that fails its initial roster check copies nothing. Inspect errors before treating an archive as complete. This folder is not a separate backup drive.

## 3. Excel changes and the first valid QR

Every time you start a sort, the app rereads the selected roster from disk. Save and close your Excel edits first. If you moved or renamed the workbook, use Load Excel / CSV to select it again.

Columns are located by headings, not fixed letters such as B, D or F. You can insert an unrelated column, move the Name column or rearrange the roster fields without reprinting cards. Header detection scans the first 100 rows of each worksheet. The import panel lists the identified columns and any skipped records/sheets.

The app scans photos in filename/path order until it finds at least one readable QR whose centre/candidate matches the current roster. It skips unreadable or unknown early photos for this check, then includes them in the normal sorting/review pass. Decoding done during the check is reused. If no photo matches, the app stops before copying anything and explains what to check.

We check on every import because it is quick and catches stale class lists before filing starts. A QR confirms the identity mapping; it does not contain Excel column positions or reliably identify an arbitrary renamed column. We therefore use known headings instead of guessing which column contains a pupil name.

If headings have changed beyond the accepted names, use these headings:

| Field | Suitable heading |
|---|---|
| Student name | Name or StudentName |
| Candidate | Candidate number or CandidateNumber |
| Class | Group Code or GroupCode |
| Centre | CentreNumber (or set the default centre in the app) |

Adding columns does not invalidate cards. Changing the actual candidate or centre number does: correct the data or print new cards. The current roster determines the name and group used for destination folders. Renaming a student or moving them to a group does not move previously sorted files automatically.

## Try it before a full class batch

1. Load a fictional roster and generate two cards.
2. Use a batch whose first photo has no QR, a second has an unknown QR and a later photo shows both valid student cards.
3. Insert an unrelated column into the Excel roster, move its Name column, save and close it.
4. Run the sort to a fresh separate output folder. The app reloads the edited workbook automatically.
5. Check that the group photo appears in both student folders, every processed original is archived, and the early unmatched pictures appear in review.
6. Repeat the import: the same files should be reported as already copied.
7. Try a roster with no matching candidate numbers: the batch should stop before copying anything.

Direct OneDrive delivery remains a future development. Existing local or synced folder use is unchanged.

## Version 1.1.1: PDFs and subfolders

The source folder you select is searched recursively: include all of its ordinary subfolders, at any depth. You only need to select the top folder. Overlapping source selections are de-duplicated. Symbolic links to folders are not followed. Keep the output separate from the source; the output folder is not rescanned.

PDFs are now included alongside photographs. Every page is rendered locally for QR recognition, including scanned pages and documents whose first page has no code. The whole, unchanged PDF is copied to every recognised student's folder. It is not split into student-specific pages. This means a PDF containing several students' work is copied in full to each matching student's folder; use separate PDFs if that is not wanted.

The originals archive retains its existing name, All_Original_Images, and now also contains the original PDFs. Reports list the PDF file and all destinations. Repeat imports and same-name collision protection apply to PDFs too.

A PDF with an unknown code or an unreadable page is additionally copied for manual review. Damaged or password-protected PDFs are kept for review when the batch has another valid roster match. If no file anywhere in the batch matches the roster, the existing preflight rule stops the batch before any copying.

The review tab shows the first PDF page. Use Open selected file to inspect every page in your usual PDF viewer before manually assigning the whole document. Cancellation takes effect after the current file has finished; a long PDF can take longer than a photo.

When updating a source installation on Mac, run `.venv/bin/python -m pip install -r requirements.txt` in the new project folder so the PDF reader is installed. The Windows download includes it.
