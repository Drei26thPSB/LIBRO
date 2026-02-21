import csv
import json
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk


APP_TITLE = "Student ID Manager for LIBRO (Beta)"
BG = "#f4f6fb"
CARD = "#ffffff"
TEXT = "#111827"
MUTED = "#6b7280"
PRIMARY = "#8a1538"
PRIMARY_HOVER = "#73112f"
LINE = "#dde3ee"


ROOT_DIR = Path(__file__).resolve().parent.parent
ATTENDANCE_PATH = ROOT_DIR / "Attendance.py"
STUDENTS_CSV_PATH = ROOT_DIR / "students.csv"


def run_cmd(command, cwd):
    proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, shell=False)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


class StudentManagerApp:
    def __init__(self, root):
        self.root = root
        self.records = []
        self.filtered_records = []

        self.root.title(APP_TITLE)
        self.root.geometry("1180x760")
        self.root.configure(bg=BG)
        self.root.minsize(980, 640)

        self._build_styles()
        self._build_ui()
        self.load_records_initial()

    def _build_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Root.TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="flat")
        style.configure("Title.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 18, "bold"))
        style.configure("Sub.TLabel", background=CARD, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Field.TLabel", background=CARD, foreground=TEXT, font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground="white", foreground=TEXT, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(10, 6))
        style.configure("Primary.TButton", foreground="white", background=PRIMARY, bordercolor=PRIMARY)
        style.map("Primary.TButton", background=[("active", PRIMARY_HOVER)])
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), fieldbackground="white", bordercolor=LINE)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#eef1f8", foreground=TEXT)

    def _build_ui(self):
        container = ttk.Frame(self.root, style="Root.TFrame")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        header = ttk.Frame(container, style="Card.TFrame", padding=16)
        header.pack(fill="x")
        ttk.Label(header, text="Student ID Manager for LIBRO (Beta)", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Manage yearly student IDs without editing code manually. Save to students.csv, then sync Attendance.py.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(container, style="Root.TFrame")
        content.pack(fill="both", expand=True, pady=(12, 0))

        left = ttk.Frame(content, style="Card.TFrame", padding=14)
        left.pack(side="left", fill="both", expand=True)

        right = ttk.Frame(content, style="Card.TFrame", padding=14)
        right.pack(side="left", fill="y", padx=(12, 0))

        search_row = ttk.Frame(left, style="Card.TFrame")
        search_row.pack(fill="x", pady=(0, 10))

        ttk.Label(search_row, text="Search", style="Field.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(search_row, textvariable=self.search_var, width=40)
        search.pack(side="left", padx=8)
        search.bind("<KeyRelease>", lambda _e: self.refresh_tree())

        self.count_label = ttk.Label(search_row, text="0 records", style="Sub.TLabel")
        self.count_label.pack(side="right")

        columns = ("student_id", "name", "grade", "section")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        self.tree.heading("student_id", text="Student ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("grade", text="Grade")
        self.tree.heading("section", text="Section")
        self.tree.column("student_id", width=150, anchor="w")
        self.tree.column("name", width=360, anchor="w")
        self.tree.column("grade", width=90, anchor="center")
        self.tree.column("section", width=180, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        form_title = ttk.Label(right, text="Student Details", style="Title.TLabel")
        form_title.pack(anchor="w", pady=(0, 8))

        self.id_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.grade_var = tk.StringVar()
        self.section_var = tk.StringVar()

        self._field(right, "Student ID", self.id_var)
        self._field(right, "Name", self.name_var)
        self._field(right, "Grade", self.grade_var)
        self._field(right, "Section", self.section_var)

        btn_row_1 = ttk.Frame(right, style="Card.TFrame")
        btn_row_1.pack(fill="x", pady=(14, 8))
        ttk.Button(btn_row_1, text="Add / Update", command=self.add_or_update, style="Primary.TButton").pack(side="left")
        ttk.Button(btn_row_1, text="Clear Form", command=self.clear_form).pack(side="left", padx=8)

        btn_row_2 = ttk.Frame(right, style="Card.TFrame")
        btn_row_2.pack(fill="x", pady=(0, 8))
        ttk.Button(btn_row_2, text="Remove Selected", command=self.remove_selected).pack(side="left")
        ttk.Button(btn_row_2, text="Sort by ID", command=self.sort_records).pack(side="left", padx=8)

        ttk.Separator(right).pack(fill="x", pady=10)

        ttk.Label(right, text="Data Actions", style="Field.TLabel").pack(anchor="w", pady=(2, 8))
        ttk.Button(right, text="Save students.csv", command=self.save_csv).pack(fill="x", pady=3)
        ttk.Button(right, text="Sync to Attendance.py", command=self.sync_attendance).pack(fill="x", pady=3)
        ttk.Button(right, text="Save + Sync", command=self.save_and_sync, style="Primary.TButton").pack(fill="x", pady=3)
        ttk.Button(right, text="Commit + Push (Git)", command=self.commit_and_push).pack(fill="x", pady=3)

        note = (
            "Workflow: Update students -> Save + Sync -> Commit + Push.\n"
            "This keeps Attendance.py student IDs updated for deployment."
        )
        ttk.Label(right, text=note, style="Sub.TLabel", wraplength=280, justify="left").pack(anchor="w", pady=(10, 0))

    def _field(self, parent, label, var):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, style="Field.TLabel").pack(anchor="w")
        ttk.Entry(row, textvariable=var, width=34).pack(fill="x", pady=(3, 0))

    def load_records_initial(self):
        if STUDENTS_CSV_PATH.exists():
            self.records = self.load_from_csv(STUDENTS_CSV_PATH)
        else:
            self.records = self.load_from_attendance_py(ATTENDANCE_PATH)
            if self.records:
                self.save_csv(silent=True)
        self.sort_records(silent=True)
        self.refresh_tree()

    def load_from_csv(self, path):
        out = []
        try:
            with path.open("r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sid = (row.get("Student ID") or "").strip()
                    name = (row.get("Name") or "").strip()
                    grade = (row.get("Grade") or "").strip()
                    section = (row.get("Section") or "").strip()
                    if sid and name:
                        out.append({"student_id": sid, "name": name, "grade": grade, "section": section})
        except Exception as e:
            messagebox.showerror("Error", f"Failed loading students.csv:\n{e}")
        return out

    def load_from_attendance_py(self, path):
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        start = text.find("students = {")
        end = text.find("\n\nCSV_HEADERS", start)
        if start < 0 or end < 0:
            return []
        block = text[start + len("students = "):end].strip()
        try:
            data = eval(block, {"__builtins__": {}})
        except Exception:
            return []
        out = []
        if isinstance(data, dict):
            for sid, info in data.items():
                out.append(
                    {
                        "student_id": str(sid),
                        "name": str(info.get("name", "")),
                        "grade": str(info.get("grade", "")),
                        "section": str(info.get("section", "")),
                    }
                )
        return out

    def refresh_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        q = self.search_var.get().strip().lower()
        self.filtered_records = [
            r for r in self.records if q in r["student_id"].lower() or q in r["name"].lower() or q in r["section"].lower()
        ]
        for rec in self.filtered_records:
            self.tree.insert("", "end", values=(rec["student_id"], rec["name"], rec["grade"], rec["section"]))
        self.count_label.configure(text=f"{len(self.filtered_records)} records")

    def on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0], "values")
        if len(vals) != 4:
            return
        self.id_var.set(vals[0])
        self.name_var.set(vals[1])
        self.grade_var.set(vals[2])
        self.section_var.set(vals[3])

    def clear_form(self):
        self.id_var.set("")
        self.name_var.set("")
        self.grade_var.set("")
        self.section_var.set("")

    def add_or_update(self):
        sid = self.id_var.get().strip()
        name = self.name_var.get().strip()
        grade = self.grade_var.get().strip()
        section = self.section_var.get().strip()
        if not sid or not name:
            messagebox.showwarning("Missing data", "Student ID and Name are required.")
            return
        rec = {"student_id": sid, "name": name, "grade": grade, "section": section}
        updated = False
        for i, row in enumerate(self.records):
            if row["student_id"].lower() == sid.lower():
                self.records[i] = rec
                updated = True
                break
        if not updated:
            self.records.append(rec)
        self.sort_records(silent=True)
        self.refresh_tree()
        messagebox.showinfo("Saved", "Student record updated." if updated else "Student added.")

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select record", "Select a student row first.")
            return
        vals = self.tree.item(selected[0], "values")
        sid = vals[0]
        if not messagebox.askyesno("Confirm", f"Remove student ID {sid}?"):
            return
        self.records = [r for r in self.records if r["student_id"] != sid]
        self.refresh_tree()
        self.clear_form()

    def sort_records(self, silent=False):
        self.records.sort(key=lambda r: r["student_id"].lower())
        if not silent:
            self.refresh_tree()

    def save_csv(self, silent=False):
        try:
            with STUDENTS_CSV_PATH.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Student ID", "Name", "Grade", "Section"])
                for r in self.records:
                    writer.writerow([r["student_id"], r["name"], r["grade"], r["section"]])
            if not silent:
                messagebox.showinfo("Success", f"Saved {len(self.records)} records to students.csv")
        except Exception as e:
            messagebox.showerror("Error", f"Failed saving students.csv:\n{e}")

    def sync_attendance(self):
        if not ATTENDANCE_PATH.exists():
            messagebox.showerror("Error", "Attendance.py not found.")
            return
        new_block_lines = ["students = {"]
        for r in self.records:
            sid = json.dumps(r["student_id"], ensure_ascii=False)
            name = json.dumps(r["name"], ensure_ascii=False)
            grade = json.dumps(r["grade"], ensure_ascii=False)
            section = json.dumps(r["section"], ensure_ascii=False)
            new_block_lines.append(
                f"    {sid}: {{\"name\": {name}, \"grade\": {grade}, \"section\": {section}}},"
            )
        new_block_lines.append("}")
        new_block = "\n".join(new_block_lines)

        try:
            text = ATTENDANCE_PATH.read_text(encoding="utf-8")
            start = text.find("students = {")
            end = text.find("\n\nCSV_HEADERS", start)
            if start < 0 or end < 0:
                messagebox.showerror("Error", "Could not locate students block in Attendance.py.")
                return
            updated = text[:start] + new_block + text[end:]
            ATTENDANCE_PATH.write_text(updated, encoding="utf-8")
            messagebox.showinfo("Synced", "Attendance.py students block updated successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sync Attendance.py:\n{e}")

    def save_and_sync(self):
        self.save_csv(silent=True)
        self.sync_attendance()

    def commit_and_push(self):
        self.save_csv(silent=True)
        self.sync_attendance()
        if not messagebox.askyesno("Confirm Git", "Commit and push students update to GitHub now?"):
            return

        msg = "Update student IDs via StudentIDManager"
        cmds = [
            ["git", "add", "students.csv", "Attendance.py"],
            ["git", "commit", "-m", msg],
            ["git", "pull", "--rebase", "origin", "main"],
            ["git", "push", "origin", "main"],
        ]
        log_output = []
        for cmd in cmds:
            code, output = run_cmd(cmd, str(ROOT_DIR))
            log_output.append(f"$ {' '.join(cmd)}\n{output.strip()}\n")
            if code != 0:
                messagebox.showerror("Git failed", "\n".join(log_output))
                return
        messagebox.showinfo("Git success", "Committed and pushed successfully.")


def main():
    root = tk.Tk()
    StudentManagerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
