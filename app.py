from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

from modules.drive_detector import find_camera_sources
from modules.excel_loader import load_students
from modules.photo_sorter import assign_review_photo, sort_photos
from modules.qr_generator import generate_qr_cards
from modules.settings_manager import load_settings, save_settings


class NEAToolbox:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("NEA Toolbox")
        self.root.geometry("1040x760")
        self.root.minsize(940, 680)

        self.settings = load_settings()
        self.students = []
        self.sources: list[str] = []
        self.output_folder = tk.StringVar(value=self.settings.get("last_output_folder", ""))
        self.centre_number = tk.StringVar(value=self.settings.get("centre_number", "23162"))
        self.group_filter = tk.StringVar(value="All groups")
        self.demo_subset = tk.BooleanVar(value=False)
        self.cancel_requested = False
        self.preview_photo = None

        self._configure_style()
        self._build_ui()

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"))
        style.configure("Heading.TLabel", font=("Segoe UI", 13, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10))
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), padding=8)

    def _build_ui(self):
        shell = ttk.Frame(self.root, padding=14)
        shell.pack(fill="both", expand=True)
        ttk.Label(shell, text="NEA Toolbox", style="Title.TLabel").pack(anchor="w")
        ttk.Label(shell, text="Local QR photo sorting for Food NEA evidence • Centre 23162", style="Status.TLabel").pack(anchor="w", pady=(0, 12))

        self.tabs = ttk.Notebook(shell)
        self.tabs.pack(fill="both", expand=True)
        self.tag_tab = ttk.Frame(self.tabs, padding=16)
        self.sort_tab = ttk.Frame(self.tabs, padding=16)
        self.review_tab = ttk.Frame(self.tabs, padding=16)
        self.tabs.add(self.tag_tab, text="1. Create printable QR tags")
        self.tabs.add(self.sort_tab, text="2. Sort student photos")
        self.tabs.add(self.review_tab, text="3. Review exceptions")

        self._build_tag_tab()
        self._build_sort_tab()
        self._build_review_tab()

    def _build_tag_tab(self):
        top = ttk.Frame(self.tag_tab)
        top.pack(fill="x")
        ttk.Label(top, text="Load the class roster", style="Heading.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(top, text="Centre number").grid(row=1, column=0, sticky="w", pady=(12, 4))
        ttk.Entry(top, textvariable=self.centre_number, width=12).grid(row=2, column=0, sticky="w", padx=(0, 12))
        ttk.Button(top, text="Load Excel / CSV", command=self.load_roster, style="Primary.TButton").grid(row=2, column=1, sticky="w")
        self.roster_label = ttk.Label(top, text="No roster loaded")
        self.roster_label.grid(row=2, column=2, sticky="w", padx=14)

        ttk.Separator(self.tag_tab).pack(fill="x", pady=18)
        options = ttk.Frame(self.tag_tab)
        options.pack(fill="x")
        ttk.Label(options, text="Choose which tags to print", style="Heading.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(options, text="Group").grid(row=1, column=0, sticky="w", pady=(12, 4))
        self.group_combo = ttk.Combobox(options, textvariable=self.group_filter, values=["All groups"], state="readonly", width=28)
        self.group_combo.grid(row=2, column=0, sticky="w", padx=(0, 18))
        ttk.Checkbutton(options, text="Demonstration subset: first 3 students from each group", variable=self.demo_subset).grid(row=2, column=1, sticky="w")

        ttk.Button(self.tag_tab, text="Create printable QR tags", command=self.create_tags, style="Primary.TButton").pack(anchor="w", pady=22)
        self.tag_status = tk.Text(self.tag_tab, height=12, wrap="word", state="disabled")
        self.tag_status.pack(fill="both", expand=True)

    def _build_sort_tab(self):
        ttk.Label(self.sort_tab, text="Choose photo sources", style="Heading.TLabel").pack(anchor="w")
        source_buttons = ttk.Frame(self.sort_tab)
        source_buttons.pack(fill="x", pady=(8, 6))
        ttk.Button(source_buttons, text="Add source folder", command=self.add_source).pack(side="left")
        ttk.Button(source_buttons, text="Find camera / SD cards", command=self.find_cameras).pack(side="left", padx=8)
        ttk.Button(source_buttons, text="Clear sources", command=self.clear_sources).pack(side="left")
        self.source_list = tk.Listbox(self.sort_tab, height=7)
        self.source_list.pack(fill="x")

        ttk.Label(self.sort_tab, text="Choose local output folder", style="Heading.TLabel").pack(anchor="w", pady=(18, 6))
        output_row = ttk.Frame(self.sort_tab)
        output_row.pack(fill="x")
        ttk.Entry(output_row, textvariable=self.output_folder).pack(side="left", fill="x", expand=True)
        ttk.Button(output_row, text="Choose output folder", command=self.choose_output).pack(side="left", padx=(8, 0))

        action = ttk.Frame(self.sort_tab)
        action.pack(fill="x", pady=18)
        ttk.Button(action, text="Run automated photo sort", command=self.start_sort, style="Primary.TButton").pack(side="left")
        self.cancel_button = ttk.Button(action, text="Cancel", command=self.request_cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.progress = ttk.Progressbar(self.sort_tab, maximum=100)
        self.progress.pack(fill="x")
        self.sort_status = ttk.Label(self.sort_tab, text="Ready")
        self.sort_status.pack(anchor="w", pady=(8, 4))
        self.sort_results = tk.Text(self.sort_tab, height=10, wrap="word", state="disabled")
        self.sort_results.pack(fill="both", expand=True)

    def _build_review_tab(self):
        ttk.Label(self.review_tab, text="Manual review", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self.review_tab, text="Choose the correct student only when you can identify the photo confidently.").pack(anchor="w", pady=(3, 10))
        row = ttk.Frame(self.review_tab)
        row.pack(fill="x")
        ttk.Button(row, text="Refresh exception list", command=self.refresh_review).pack(side="left")
        ttk.Button(row, text="Open exception folder", command=self.open_review_folder).pack(side="left", padx=8)

        body = ttk.Panedwindow(self.review_tab, orient="horizontal")
        body.pack(fill="both", expand=True, pady=12)
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=2)
        self.review_list = tk.Listbox(left)
        self.review_list.pack(fill="both", expand=True)
        self.review_list.bind("<<ListboxSelect>>", self.show_review_preview)
        self.preview_label = ttk.Label(right, anchor="center")
        self.preview_label.pack(fill="both", expand=True)

        assign = ttk.Frame(self.review_tab)
        assign.pack(fill="x")
        ttk.Label(assign, text="Student").pack(side="left")
        self.review_student = tk.StringVar()
        self.student_combo = ttk.Combobox(assign, textvariable=self.review_student, state="readonly", width=48)
        self.student_combo.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Button(assign, text="Assign photo to selected student", command=self.assign_photo, style="Primary.TButton").pack(side="left")

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def load_roster(self):
        path = filedialog.askopenfilename(filetypes=[("Excel / CSV", "*.xlsx *.xlsm *.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            result = load_students(path, self.centre_number.get().strip() or "23162")
        except Exception as exc:
            messagebox.showerror("Could not load roster", str(exc))
            return
        self.students = result.students
        self.settings["last_roster"] = path
        self.settings["centre_number"] = self.centre_number.get().strip() or "23162"
        save_settings(self.settings)
        groups = ["All groups"] + result.groups
        self.group_combo["values"] = groups
        self.group_filter.set("All groups")
        self.roster_label.configure(text=f"{len(self.students)} students • {len(result.groups)} groups")
        student_labels = [f"{s.group_code} • {s.student_name} • {s.candidate_number}" for s in self.students]
        self.student_combo["values"] = student_labels
        if student_labels:
            self.student_combo.current(0)
        warning_text = "\n".join(f"• {w}" for w in result.warnings) if result.warnings else "No import warnings."
        self._set_text(self.tag_status, f"Loaded: {Path(path).name}\nStudents: {len(self.students)}\nSheets used: {', '.join(result.sheets_used)}\n\n{warning_text}")

    def _selected_students_for_tags(self):
        selected = self.students
        if self.group_filter.get() != "All groups":
            selected = [s for s in selected if s.group_code == self.group_filter.get()]
        if self.demo_subset.get():
            grouped = {}
            for student in selected:
                grouped.setdefault(student.group_code, []).append(student)
            selected = [student for group in sorted(grouped) for student in grouped[group][:3]]
        return selected

    def create_tags(self):
        if not self.students:
            messagebox.showerror("Roster required", "Load the Excel / CSV roster first.")
            return
        folder = filedialog.askdirectory(title="Choose where to save printable tags")
        if not folder:
            return
        try:
            selected = self._selected_students_for_tags()
            result = generate_qr_cards(selected, folder, demo=self.demo_subset.get())
            self._set_text(self.tag_status, f"Created {len(selected)} tag(s).\n\nPDF: {result['pdf']}\nIndividual cards: {result['images']}")
            messagebox.showinfo("Tags created", f"Created {len(selected)} tag(s).\n\n{result['pdf']}")
        except Exception as exc:
            messagebox.showerror("Could not create tags", str(exc))

    def add_source(self):
        folder = filedialog.askdirectory(title="Choose a camera / photo folder")
        if folder and folder not in self.sources:
            self.sources.append(folder)
            self.source_list.insert("end", folder)

    def find_cameras(self):
        found = find_camera_sources()
        for folder in found:
            if folder not in self.sources:
                self.sources.append(folder)
                self.source_list.insert("end", folder)
        messagebox.showinfo("Camera search", f"Found {len(found)} camera / SD-card DCIM folder(s).")

    def clear_sources(self):
        self.sources.clear()
        self.source_list.delete(0, "end")

    def choose_output(self):
        folder = filedialog.askdirectory(title="Choose a local output folder")
        if folder:
            self.output_folder.set(folder)
            self.settings["last_output_folder"] = folder
            save_settings(self.settings)
            self.refresh_review()

    def request_cancel(self):
        self.cancel_requested = True
        self.sort_status.configure(text="Cancelling after the current photo…")

    def start_sort(self):
        if not self.students:
            messagebox.showerror("Roster required", "Load the Excel / CSV roster in tab 1 first.")
            return
        if not self.sources:
            messagebox.showerror("Photo source required", "Add at least one source folder or find an SD card.")
            return
        if not self.output_folder.get().strip():
            messagebox.showerror("Output required", "Choose a local output folder.")
            return
        out = Path(self.output_folder.get()).resolve()
        for source in self.sources:
            src = Path(source).resolve()
            if out == src or src in out.parents:
                messagebox.showerror("Unsafe folder choice", "The output folder cannot be the source folder or be inside a source folder.")
                return
        self.cancel_requested = False
        self.cancel_button.configure(state="normal")
        self.progress["value"] = 0
        self.sort_status.configure(text="Starting…")
        threading.Thread(target=self._sort_worker, daemon=True).start()

    def _sort_worker(self):
        def progress(done, total, name):
            pct = (done / total * 100) if total else 0
            self.root.after(0, lambda: self._update_progress(pct, done, total, name))
        try:
            summary = sort_photos(self.sources, self.output_folder.get(), self.students, progress=progress, should_cancel=lambda: self.cancel_requested)
            self.root.after(0, lambda: self._sort_finished(summary))
        except Exception as exc:
            self.root.after(0, lambda: self._sort_failed(exc))

    def _update_progress(self, pct, done, total, name):
        self.progress["value"] = pct
        self.sort_status.configure(text=f"{done}/{total}: {name}")

    def _sort_finished(self, summary):
        self.cancel_button.configure(state="disabled")
        status = "Cancelled" if summary.cancelled else "Complete"
        text = (
            f"{status}\n\n"
            f"Sorted: {summary.sorted}\n"
            f"Manual review: {summary.review}\n"
            f"Already copied: {summary.already_copied}\n"
            f"Errors: {summary.errors}\n\n"
            f"Report: {summary.report_csv}"
        )
        self._set_text(self.sort_results, text)
        self.sort_status.configure(text=status)
        self.refresh_review()
        messagebox.showinfo("Photo sort", text)

    def _sort_failed(self, exc):
        self.cancel_button.configure(state="disabled")
        self.sort_status.configure(text="Failed")
        messagebox.showerror("Photo sort failed", str(exc))

    def _review_files(self):
        folder = Path(self.output_folder.get()) / "Manual_Check_Required"
        if not folder.exists():
            return []
        return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})

    def refresh_review(self):
        self.review_list.delete(0, "end")
        for path in self._review_files():
            self.review_list.insert("end", path.name)

    def show_review_preview(self, _event=None):
        selection = self.review_list.curselection()
        if not selection:
            return
        files = self._review_files()
        if selection[0] >= len(files):
            return
        try:
            image = Image.open(files[selection[0]])
            image.thumbnail((600, 430), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_photo)
        except Exception:
            self.preview_label.configure(text="Preview unavailable", image="")

    def open_review_folder(self):
        folder = Path(self.output_folder.get()) / "Manual_Check_Required"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif os.uname().sysname == "Darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception:
            messagebox.showinfo("Exception folder", str(folder))

    def assign_photo(self):
        selection = self.review_list.curselection()
        student_index = self.student_combo.current()
        if not selection or student_index < 0 or student_index >= len(self.students):
            messagebox.showerror("Selection required", "Choose an exception photo and the correct student.")
            return
        files = self._review_files()
        if selection[0] >= len(files):
            return
        student = self.students[student_index]
        if not messagebox.askyesno("Confirm assignment", f"Assign this photo to {student.student_name} ({student.candidate_number})?\n\nA review copy will be retained."):
            return
        destination = assign_review_photo(files[selection[0]], self.output_folder.get(), student)
        messagebox.showinfo("Assigned", f"Copied to:\n{destination}")


def main():
    root = tk.Tk()
    NEAToolbox(root)
    root.mainloop()


if __name__ == "__main__":
    main()
