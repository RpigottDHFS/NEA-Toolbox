import tkinter as tk

from tkinter import filedialog
from tkinter import messagebox

from modules.excel_loader import load_students
from modules.qr_generator import generate_qr_cards
from modules.drive_detector import find_camera_sources
from modules.photo_sorter import sort_photos
from modules.settings_manager import (
    load_settings,
    save_settings
)


class NEAToolbox:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "NEA Toolbox"
        )

        self.root.geometry(
            "900x650"
        )

        self.students = {}

        self.settings = load_settings()

        self.build_ui()

        self.refresh_dashboard()

    def build_ui(self):

        title = tk.Label(
            self.root,
            text="NEA Toolbox",
            font=("Arial", 24, "bold")
        )

        title.pack(
            pady=15
        )

        self.info_label = tk.Label(
            self.root,
            justify="left",
            font=("Arial", 12)
        )

        self.info_label.pack(
            pady=20
        )

        tk.Button(
            self.root,
            text="Load Student Excel",
            width=25,
            command=self.load_excel
        ).pack(
            pady=5
        )

        tk.Button(
            self.root,
            text="Generate QR Cards",
            width=25,
            command=self.generate_cards
        ).pack(
            pady=5
        )

        tk.Button(
            self.root,
            text="Set Teams Folder",
            width=25,
            command=self.select_teams_folder
        ).pack(
            pady=5
        )

        tk.Button(
            self.root,
            text="IMPORT & SORT EVERYTHING",
            width=35,
            height=3,
            bg="green",
            fg="white",
            font=("Arial", 14, "bold"),
            command=self.run_sort
        ).pack(
            pady=25
        )

    def refresh_dashboard(self):

        drives = find_camera_sources()

        self.info_label.config(
            text=
            f"""
Students Loaded: {len(self.students)}

Connected Camera Sources: {len(drives)}

Destination Folder:
{self.settings.get("teams_folder","")}
"""
        )

    def load_excel(self):

        filename = filedialog.askopenfilename(
            filetypes=[
                ("Excel Files",
                 "*.xlsx")
            ]
        )

        if filename:

            self.students = load_students(
                filename
            )

            self.refresh_dashboard()

            messagebox.showinfo(
                "Complete",
                f"{len(self.students)} students loaded"
            )

    def generate_cards(self):

        if not self.students:

            messagebox.showerror(
                "Error",
                "Load students first"
            )

            return

        generate_qr_cards(
            self.students,
            "generated_cards"
        )

        messagebox.showinfo(
            "Complete",
            "QR cards generated"
        )

    def select_teams_folder(self):

        folder = filedialog.askdirectory()

        if folder:

            self.settings[
                "teams_folder"
            ] = folder

            save_settings(
                self.settings
            )

            self.refresh_dashboard()

    def run_sort(self):

        drives = find_camera_sources()

        if not drives:

            messagebox.showerror(
                "Error",
                "No SD cards detected"
            )

            return

        if not self.students:

            messagebox.showerror(
                "Error",
                "Load class spreadsheet first"
            )

            return

        sorted_count, failed_count = sort_photos(
            drives,
            self.settings["teams_folder"],
            self.students
        )

        messagebox.showinfo(
            "Import Complete",
            f"""
Sorted:
{sorted_count}

Manual Review:
{failed_count}
"""
        )


root = tk.Tk()

app = NEAToolbox(root)

root.mainloop()
