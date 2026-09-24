import pandas as pd


def load_students(excel_file):
    df = pd.read_excel(excel_file)

    students = {}

    for _, row in df.iterrows():
        students[str(row["CandidateNumber"])] = row["StudentName"]

    return students
