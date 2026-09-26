# Privacy and school-data handling

NEA Toolbox is designed so that the GitHub repository contains code and fictional examples only.

Real pupil data remains on the authorised local/school storage chosen by the user at runtime. The application does not upload pupil data to GitHub and does not sign into Microsoft accounts.

Before every pull request or release, check the changed-file list for:
- `.xlsx`, `.xls`, `.xlsm`, or CSV files containing real pupil data;
- pupil names or candidate numbers in source/test fixtures;
- classroom or practical photographs;
- generated QR cards made from real pupils;
- sorted-output folders or local reports.

If any are present, remove them from the branch before merging.
