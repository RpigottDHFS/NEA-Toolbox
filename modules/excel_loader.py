import pandas as pd


def load_students(filepath):

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)
    else:
        df = pd.read_excel(filepath)

    students = {}

    for _, row in df.iterrows():

        candidate = str(row["CandidateNumber"]).strip()

        students[candidate] = {
            "name": row["StudentName"],
            "group": row.get(
                "TeachingGroup",
                ""
            )
        }

    return students
