try:
    import tkinter as tk
    from tkinter import messagebox
    TK_AVAILABLE = True
except Exception:
    tk = None
    messagebox = None
    TK_AVAILABLE = False
import datetime
import csv
import time
import os
import sys
import subprocess
import socket
import atexit
import re
import shutil
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image, ImageTk, ImageDraw

# ---------------- GLOBALS ----------------
CSV_ROOT = os.path.join(os.path.dirname(__file__), 'csv_files')
STUDENT_ROSTER_ROOT = os.path.join(os.path.dirname(__file__), 'studentid_data')
BACKUP_ROOT = os.path.join(os.path.dirname(__file__), "backups", "daily")
LOG_ROOT = os.path.join(os.path.dirname(__file__), "logs")
STUDENT_ID_PATTERN = re.compile(os.getenv("LIBRO_STUDENT_ID_REGEX", r"^[A-Za-z0-9-]{4,20}$"))
try:
    os.makedirs(CSV_ROOT, exist_ok=True)
    os.makedirs(STUDENT_ROSTER_ROOT, exist_ok=True)
    os.makedirs(BACKUP_ROOT, exist_ok=True)
    os.makedirs(LOG_ROOT, exist_ok=True)
except Exception as e:
    print(f"Error creating CSV directory: {e}")

logger = logging.getLogger("attendance")
logger.setLevel(logging.INFO)
if not logger.handlers:
    attendance_log = RotatingFileHandler(
        os.path.join(LOG_ROOT, "attendance.log"),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    attendance_log.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(attendance_log)


def cleanup_old_csv_files(retention_days=30):
    cutoff = time.time() - (retention_days * 24 * 60 * 60)
    deleted = 0
    try:
        for dirpath, _, filenames in os.walk(CSV_ROOT):
            for name in filenames:
                if not name.lower().endswith(".csv"):
                    continue
                full = os.path.join(dirpath, name)
                try:
                    if os.path.getmtime(full) <= cutoff:
                        os.remove(full)
                        deleted += 1
                except Exception as e:
                    logger.exception("Failed to evaluate/delete old CSV '%s': %s", full, e)
        if deleted:
            logger.info("Deleted %d CSV file(s) older than %d days.", deleted, retention_days)
    except Exception as e:
        logger.exception("CSV cleanup failed: %s", e)


def daily_backup_csv_files():
    day = get_attendance_date()
    target_dir = os.path.join(BACKUP_ROOT, day)
    if os.path.isdir(target_dir):
        return
    copied = 0
    try:
        os.makedirs(target_dir, exist_ok=True)
        for dirpath, _, filenames in os.walk(CSV_ROOT):
            rel_dir = os.path.relpath(dirpath, CSV_ROOT)
            rel_dir = "" if rel_dir == "." else rel_dir
            for name in filenames:
                if not name.lower().endswith(".csv"):
                    continue
                src = os.path.join(dirpath, name)
                dst_dir = os.path.join(target_dir, rel_dir)
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dst_dir, name))
                copied += 1
        logger.info("Daily backup created: %s (%d file(s))", target_dir, copied)
    except Exception:
        logger.exception("Daily backup failed for %s", day)


def is_valid_student_id(student_id):
    return bool(STUDENT_ID_PATTERN.fullmatch(student_id or ""))

librarian_ids = ["S1898"]
students = {}
students_signature = None


def normalize_spaces(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def normalize_student_id(text):
    return normalize_spaces(text).upper()


def normalize_name(text):
    return normalize_spaces(text).casefold()


def get_student_field(row, candidate_keys):
    normalized_row = {k.strip().casefold(): (v or "").strip() for k, v in row.items() if k}
    for key in candidate_keys:
        val = normalized_row.get(key.casefold(), "")
        if val:
            return val
    return ""


def parse_grade_section_from_filename(csv_path):
    base = os.path.splitext(os.path.basename(csv_path))[0]
    if "_" in base:
        grade, section = base.split("_", 1)
        return normalize_spaces(grade), normalize_spaces(section)
    return "", normalize_spaces(base)


def compute_students_signature():
    parts = []
    try:
        for dirpath, _, filenames in os.walk(STUDENT_ROSTER_ROOT):
            for name in filenames:
                if not name.lower().endswith(".csv"):
                    continue
                full = os.path.join(dirpath, name)
                try:
                    stat = os.stat(full)
                    rel = os.path.relpath(full, STUDENT_ROSTER_ROOT).replace("\\", "/")
                    parts.append((rel, int(stat.st_mtime), stat.st_size))
                except Exception:
                    continue
    except Exception:
        return None
    return tuple(sorted(parts))


def load_students_from_rosters():
    loaded = {}
    for dirpath, _, filenames in os.walk(STUDENT_ROSTER_ROOT):
        for name in filenames:
            if not name.lower().endswith(".csv"):
                continue
            full = os.path.join(dirpath, name)
            filename_grade, filename_section = parse_grade_section_from_filename(full)
            try:
                with open(full, "r", newline="", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames:
                        continue
                    for row in reader:
                        sid = normalize_student_id(
                            get_student_field(
                                row,
                                ["Student ID", "Student Id", "StudentID", "ID", "Student Number", "Student ID Number"],
                            )
                        )
                        name_val = normalize_spaces(get_student_field(row, ["Name", "Student Name", "Full Name"]))
                        if not sid or not name_val:
                            continue
                        grade = normalize_spaces(get_student_field(row, ["Grade", "Grade Level", "GradeLevel"])) or filename_grade
                        section = normalize_spaces(get_student_field(row, ["Section"])) or filename_section
                        class_number = normalize_spaces(get_student_field(row, ["Class Number", "Class", "Class No", "No"]))
                        loaded[sid] = {
                            "name": name_val,
                            "grade": grade,
                            "section": section,
                            "class_number": class_number,
                            "source": os.path.relpath(full, STUDENT_ROSTER_ROOT).replace("\\", "/"),
                        }
            except Exception as e:
                print(f"Failed loading roster '{full}': {e}")
    return loaded


def ensure_students_loaded(force=False):
    global students, students_signature
    new_signature = compute_students_signature()
    if not force and new_signature == students_signature:
        return
    students = load_students_from_rosters()
    students_signature = new_signature
    if students:
        logger.info("Loaded %d student record(s) from %s.", len(students), STUDENT_ROSTER_ROOT)
    else:
        logger.warning("No valid student roster records found in %s.", STUDENT_ROSTER_ROOT)


def parse_scan_input(raw_text):
    raw = normalize_spaces(raw_text)
    if not raw:
        return "", ""
    for sep in ("|", ",", ";", "\t"):
        if sep in raw:
            left, right = [part.strip() for part in raw.split(sep, 1)]
            return normalize_student_id(left), normalize_name(right)
    return normalize_student_id(raw), ""


def find_student_from_scan(raw_text):
    ensure_students_loaded()
    scan_id, scan_name = parse_scan_input(raw_text)
    if not scan_id:
        return None, None, "empty"
    if not is_valid_student_id(scan_id):
        return None, scan_id, "invalid_id_format"
    student = students.get(scan_id)
    if not student:
        return None, scan_id, "id_not_found"
    if scan_name and normalize_name(student["name"]) != scan_name:
        return None, scan_id, "name_mismatch"
    return student, scan_id, ""

CSV_HEADERS = ["Student ID", "Name", "Section", "Purpose", "Time In", "Time Out", "Status"]

current_student = None
current_student_id = None
last_scan_time = {}
purpose_options = ["Study", "Borrow Book", "Research", "Use Ipad/PC", "Others"]
SCAN_TIMEOUT = 7

# ---------------- UI STYLE ----------------
APP_BG = "#f2f4f7"
CARD_BG = "#f2f2f2"
BORDER = "#dddddd"
TEXT_MAIN = "#d81f3f"
TEXT_MUTED = "#d81f3f"
PRIMARY = "#d81f3f"
PRIMARY_ACTIVE = "#ba1430"
WARN = "#9a3412"
DANGER = "#b42318"
FONT = "Segoe UI"
INPUT_BG = "#cdcdcf"
BOOT_DIRECT_START = os.getenv("LIBRO_BOOT_DIRECT_START", "1") == "1"

bg_label = None
bg_render_image = None
psb_logo_label = None
top_title_label = None
top_title_bg = APP_BG
UI_SCALE = 1.0
SMALL_DISPLAY = False
KIOSK_MODE = True


def update_ui_scale():
    global UI_SCALE, SMALL_DISPLAY
    sw, sh = get_viewport_size()
    SMALL_DISPLAY = sw <= 900 or sh <= 520
    raw = min(sw / 1280.0, sh / 720.0)
    UI_SCALE = max(0.58, min(1.0, raw))


def ui_px(value, minimum=8):
    return max(minimum, int(round(value * UI_SCALE)))


def get_viewport_size():
    if KIOSK_MODE:
        return root.winfo_screenwidth(), root.winfo_screenheight()
    root.update_idletasks()
    ww = root.winfo_width()
    wh = root.winfo_height()
    if ww <= 1 or wh <= 1:
        return root.winfo_screenwidth(), root.winfo_screenheight()
    return ww, wh


def format_clock_text():
    return datetime.datetime.now().strftime("%I:%M:%S %p").lstrip("0")


def bind_live_clock(clock_label):
    def _tick():
        if not clock_label.winfo_exists():
            return
        clock_label.config(text=format_clock_text())
        clock_label.after(1000, _tick)

    _tick()


def make_rounded_card_image(width, height, radius=42):
    if bg_render_image is not None:
        base = bg_render_image.copy().convert("RGBA")
    else:
        base = Image.new("RGBA", (width, height), (242, 242, 242, 255))
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rounded_rectangle((0, 0, width - 1, height - 1), radius=radius, fill=(242, 242, 242, 245))
    return Image.alpha_composite(base, overlay)


def make_scan_entry(parent, width_chars=24):
    entry_shell = tk.Frame(parent, bg=INPUT_BG, bd=0, highlightthickness=0)
    entry_shell.pack(pady=ui_px(18, 6), ipady=ui_px(8, 3), ipadx=ui_px(38, 8))
    entry = tk.Entry(
        entry_shell,
        font=(FONT, ui_px(28, 12), "bold"),
        width=width_chars,
        bd=0,
        bg=INPUT_BG,
        fg=TEXT_MAIN,
        justify=tk.CENTER,
        insertbackground=TEXT_MAIN,
        highlightthickness=0,
    )
    entry.pack(ipady=4)
    return entry


def place_psb_logo():
    global psb_logo_label
    if psb_logo_label and psb_logo_label.winfo_exists():
        psb_logo_label.place(relx=0.5, rely=0.985, anchor="s")
        psb_logo_label.lift()
        return
    logo_path = os.path.join(os.path.dirname(__file__), "PSB_Logo.png")
    if not os.path.exists(logo_path):
        return
    try:
        logo = Image.open(logo_path).convert("RGBA")
        logo_size = ui_px(116, 64)
        logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
        logo_bg = APP_BG
        if bg_render_image is not None:
            try:
                px = bg_render_image.getpixel((root.winfo_screenwidth() // 2, int(root.winfo_screenheight() * 0.965)))
                logo_bg = f"#{px[0]:02x}{px[1]:02x}{px[2]:02x}"
            except Exception:
                logo_bg = APP_BG
        logo_photo = ImageTk.PhotoImage(logo)
        psb_logo_label = tk.Label(
            root,
            image=logo_photo,
            bd=0,
            highlightthickness=0,
            relief="flat",
            bg=logo_bg,
            padx=0,
            pady=0,
        )
        psb_logo_label.image = logo_photo
        psb_logo_label.place(relx=0.5, rely=0.985, anchor="s")
        psb_logo_label.lift()
    except Exception:
        psb_logo_label = None


def get_attendance_date():
    return datetime.datetime.now().strftime("%Y-%m-%d")


def get_csv_filename():
    return os.path.join(CSV_ROOT, f"{get_attendance_date()}.csv")


def normalize_row(row):
    time_in = row.get("Time In", "").strip() or row.get("Time", "").strip()
    time_out = row.get("Time Out", "").strip()
    status = row.get("Status", "").strip() or ("OUT" if time_out else "IN")
    return {
        "Student ID": row.get("Student ID", "").strip(),
        "Name": row.get("Name", "").strip(),
        "Section": row.get("Section", "").strip(),
        "Purpose": row.get("Purpose", "").strip(),
        "Time In": time_in,
        "Time Out": time_out,
        "Status": status,
    }


def read_attendance_rows():
    path = get_csv_filename()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return []
            return [normalize_row(row) for row in reader]
    except Exception as e:
        print(f"Error reading attendance rows: {e}")
        return []


def write_attendance_rows(rows):
    path = get_csv_filename()
    try:
        daily_backup_csv_files()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for row in rows:
                writer.writerow(normalize_row(row))
    except PermissionError:
        logger.exception("Permission denied: Cannot write to %s", path)
    except Exception as e:
        logger.exception("Error writing attendance rows: %s", e)


def get_open_session_index(rows, student_id):
    for i in range(len(rows) - 1, -1, -1):
        row = rows[i]
        if row["Student ID"] == student_id and row["Time In"] and not row["Time Out"]:
            return i
    return None


def has_open_session(student_id):
    rows = read_attendance_rows()
    return get_open_session_index(rows, student_id) is not None


def record_time_in(student_id, student, purpose):
    rows = read_attendance_rows()
    time_in = datetime.datetime.now().strftime("%H:%M:%S")
    rows.append(
        {
            "Student ID": student_id,
            "Name": student["name"],
            "Section": student["section"],
            "Purpose": purpose,
            "Time In": time_in,
            "Time Out": "",
            "Status": "IN",
        }
    )
    write_attendance_rows(rows)
    return time_in


def record_time_out(student_id):
    rows = read_attendance_rows()
    idx = get_open_session_index(rows, student_id)
    if idx is None:
        return None
    time_out = datetime.datetime.now().strftime("%H:%M:%S")
    rows[idx]["Time Out"] = time_out
    rows[idx]["Status"] = "OUT"
    write_attendance_rows(rows)
    return time_out

# ---------------- BEEP ----------------

CHIME_PATH = os.path.join(os.path.dirname(__file__), "Chime.mp3")
CHIME_ALIAS = "libro_chime"

def play_beep():
    try:
        if os.name == 'nt':
            try:
                import winsound
                winsound.Beep(1000, 120)
            except Exception:
                print('\a', end='', flush=True)
        else:
            if shutil.which('beep'):
                os.system("beep -f 1000 -l 120")
            else:
                print('\a', end='', flush=True)
    except Exception:
        pass

def play_double_beep():
    try:
        if os.name == 'nt':
            try:
                import winsound
                winsound.Beep(1000, 150)
                time.sleep(0.08)
                winsound.Beep(1000, 150)
            except Exception:
                print('\a\a', end='', flush=True)
        else:
            if shutil.which('beep'):
                os.system("beep -f 1000 -l 150 -n -f 1000 -l 150")
            else:
                print('\a\a', end='', flush=True)
    except Exception:
        pass


def play_chime():
    try:
        if os.name == "nt" and os.path.exists(CHIME_PATH):
            import ctypes

            winmm = ctypes.windll.winmm
            winmm.mciSendStringW(f"close {CHIME_ALIAS}", None, 0, None)
            open_cmd = f'open "{CHIME_PATH}" type mpegvideo alias {CHIME_ALIAS}'
            if winmm.mciSendStringW(open_cmd, None, 0, None) == 0:
                winmm.mciSendStringW(f"play {CHIME_ALIAS} from 0", None, 0, None)
                return
    except Exception:
        pass
    play_beep()

# ---------------- CUSTOM DIALOGS ----------------
def show_info_dialog(title, message):
    root.lift()
    root.focus_force()
    messagebox.showinfo(title, message, parent=root)

def show_error_dialog(title, message):
    root.lift()
    root.focus_force()
    messagebox.showerror(title, message, parent=root)

def show_warning_dialog(title, message):
    root.lift()
    root.focus_force()
    messagebox.showwarning(title, message, parent=root)

def show_yesno_dialog(title, message):
    root.lift()
    root.focus_force()
    return messagebox.askyesno(title, message, parent=root)


def show_server_banner(ip, duration=8000):
    try:
        import webbrowser
        if not root:
            return
        banner = tk.Frame(root, bg='#f3f3f3', bd=1, relief=tk.RIDGE)
        banner.place(relx=0.5, rely=0.01, anchor='n')
        label = tk.Label(banner, text=f"Web UI: http://{ip}:5000", fg=TEXT_MAIN, bg='#f3f3f3', font=(FONT, ui_px(12, 8), "bold"))
        label.pack(side='left', padx=(10,5), pady=5)
        def open_browser():
            try:
                webbrowser.open(f'http://{ip}:5000')
            except Exception:
                pass
        btn = tk.Button(banner, text='Open', command=open_browser, bg=PRIMARY, fg='white', bd=0)
        btn.pack(side='left', padx=(0,10), pady=5)
        def remove_banner():
            try:
                banner.destroy()
            except Exception:
                pass
        root.after(duration, remove_banner)
    except Exception:
        pass

# ---------------- UI ----------------
def clear():
    for widget in root.winfo_children():
        if widget not in (bg_label, psb_logo_label):
            widget.destroy()
    if bg_label:
        bg_label.lower()
    if psb_logo_label:
        psb_logo_label.lift()


def build_card(title, subtitle=None, show_clock=False, card_relwidth=0.72, card_relheight=0.52):
    global top_title_label
    clear()
    screen_w, screen_h = get_viewport_size()
    if SMALL_DISPLAY:
        card_relwidth = max(card_relwidth, 0.86)
        card_relheight = max(card_relheight, 0.70)

    top_title_label = tk.Label(
        root,
        text="Library Attendance System",
        font=(FONT, ui_px(50, 14)),
        bg=top_title_bg,
        fg=TEXT_MAIN,
    )
    top_title_label.place(relx=0.5, rely=0.08 if not SMALL_DISPLAY else 0.055, anchor="center")

    card_w = int(screen_w * card_relwidth)
    card_h = int(screen_h * card_relheight)
    card_x = (screen_w - card_w) // 2
    card_y = int(screen_h * (0.20 if not SMALL_DISPLAY else 0.11))

    if bg_render_image is not None:
        bg_crop = bg_render_image.crop((card_x, card_y, card_x + card_w, card_y + card_h))
    else:
        bg_crop = None
    card_radius = ui_px(46, 16)
    card_image = make_rounded_card_image(card_w, card_h, radius=card_radius) if bg_crop is None else Image.alpha_composite(
        bg_crop.convert("RGBA"),
        Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0)),
    )
    if bg_crop is not None:
        draw = ImageDraw.Draw(card_image)
        draw.rounded_rectangle((0, 0, card_w - 1, card_h - 1), radius=card_radius, fill=(242, 242, 242, 245))
    card_photo = ImageTk.PhotoImage(card_image)
    card_shell = tk.Canvas(root, bd=0, highlightthickness=0, bg=APP_BG)
    card_shell.bg_photo = card_photo
    card_shell.create_image(0, 0, image=card_photo, anchor="nw")
    card_shell.place(x=card_x, y=card_y, width=card_w, height=card_h)

    pad = ui_px(22, 10)
    card = tk.Frame(card_shell, bg=CARD_BG)
    card_shell.create_window(pad, pad, anchor="nw", window=card, width=card_w - (pad * 2), height=card_h - (pad * 2))

    tk.Label(card, text=title, font=(FONT, ui_px(38, 12)), bg=CARD_BG, fg=TEXT_MAIN).pack(pady=(ui_px(18, 4), ui_px(8, 2)))
    if subtitle:
        tk.Label(
            card,
            text=subtitle,
            font=(FONT, ui_px(16, 7)),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            wraplength=min(900, int(card_w * 0.88)),
            justify=tk.CENTER,
        ).pack(pady=(0, ui_px(10, 2)))
    if show_clock:
        clock_label = tk.Label(card, text=format_clock_text(), font=(FONT, ui_px(56, 14), "bold"), bg=CARD_BG, fg=TEXT_MAIN)
        clock_label.pack(side=tk.BOTTOM, pady=(0, ui_px(12, 2)))
        bind_live_clock(clock_label)
    place_psb_logo()
    return card


# ---------------- STARTUP ----------------
def initial_prompt():
    if BOOT_DIRECT_START:
        librarian_verify_start()
        return
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    if show_yesno_dialog("Start Attendance", f"Start attendance for {date}?"):
        librarian_verify_start()
    else:
        root.destroy()

# ---------------- LIBRARIAN VERIFY ----------------
def librarian_verify_start():
    card = build_card("Scan Librarian ID to start\nattendance", show_clock=True, card_relwidth=0.78, card_relheight=0.62)

    entry = make_scan_entry(card, width_chars=12 if SMALL_DISPLAY else 20)
    entry.focus_set()

    def check(event=None):
        sid = entry.get().strip()
        entry.delete(0, tk.END)
        if sid in librarian_ids:
            play_beep()
            show_info_dialog("Access Granted", "Attendance Initialized!")
            standby_mode()
        else:
            play_double_beep()
            show_error_dialog("Denied", "Invalid Librarian ID!")

    entry.bind("<Return>", check)
    
# ---------------- STANDBY ----------------
def standby_mode():
    card = build_card("Scan Student/Staff ID", show_clock=True, card_relwidth=0.78, card_relheight=0.62)
    entry = make_scan_entry(card, width_chars=12 if SMALL_DISPLAY else 20)
    entry.focus_set()

    def process_scan(event=None):
        sid = entry.get().strip()
        entry.delete(0, tk.END)
        if sid in librarian_ids:
            play_beep()
            admin_menu()
            return
        student, resolved_sid, reason = find_student_from_scan(sid)
        if student and resolved_sid:
            now = time.time()
            if resolved_sid in last_scan_time and now - last_scan_time[resolved_sid] < SCAN_TIMEOUT:
                play_double_beep()
                show_warning_dialog("Duplicate", "Please wait a moment before scanning again.")
                return
            last_scan_time[resolved_sid] = now
            global current_student, current_student_id
            current_student_id = resolved_sid
            current_student = student
            if has_open_session(resolved_sid):
                confirm_time_out()
            else:
                select_purpose()
        else:
            play_double_beep()
            if reason == "invalid_id_format":
                show_error_dialog("Not Found", "Invalid ID format.")
            elif reason == "name_mismatch":
                show_error_dialog("Not Found", "ID was found, but the scanned name does not match the roster.")
            elif reason == "id_not_found":
                show_error_dialog("Not Found", "ID not recognized in any roster CSV.")
            else:
                show_error_dialog("Not Found", "Invalid scan input.")

    entry.bind("<Return>", process_scan)

# ---------------- PURPOSE SELECT ----------------
def select_purpose():
    card = build_card(
        f"Hi, {current_student['name']}",
        "Select one or more purposes for this Time In.",
        card_relheight=0.84 if SMALL_DISPLAY else 0.70,
    )
    checkbox_vars = []
    list_frame = tk.Frame(card, bg=CARD_BG)
    list_frame.pack(fill="both", expand=True)

    for p in purpose_options:
        var = tk.BooleanVar(value=False)
        checkbox_vars.append((p, var))
        tk.Checkbutton(
            list_frame,
            text=p,
            variable=var,
            onvalue=True,
            offvalue=False,
            font=(FONT, ui_px(18, 9)),
            bg=CARD_BG,
            fg=TEXT_MAIN,
            anchor="w",
            padx=15,
            pady=8,
            selectcolor="#f9fafb",
            activebackground=CARD_BG,
        ).pack(fill="x", padx=ui_px(90, 12), pady=ui_px(3, 1))

    def submit_purposes():
        selected = [label for label, var in checkbox_vars if var.get()]
        if not selected:
            play_double_beep()
            show_warning_dialog("Purpose Required", "Select at least one purpose.")
            return
        confirm_student(", ".join(selected))

    actions = tk.Frame(card, bg=CARD_BG)
    actions.pack(side="bottom", fill="x", pady=(ui_px(8, 2), ui_px(4, 1)))

    tk.Button(
        actions,
        text="Confirm Time In",
        width=16 if SMALL_DISPLAY else 20,
        font=(FONT, ui_px(18, 10), "bold"),
        bg=PRIMARY,
        fg="white",
        activebackground=PRIMARY_ACTIVE,
        activeforeground="white",
        bd=0,
        padx=ui_px(20, 8),
        pady=ui_px(10, 4),
        command=submit_purposes,
    ).pack(pady=(ui_px(4, 1), ui_px(4, 1)))

    tk.Button(
        actions,
        text="Back",
        width=16 if SMALL_DISPLAY else 20,
        font=(FONT, ui_px(15, 9)),
        bg="#f3f4f6",
        fg=TEXT_MAIN,
        bd=0,
        padx=ui_px(18, 8),
        pady=ui_px(8, 4),
        command=standby_mode,
    ).pack()

# ---------------- CONFIRM ----------------
def confirm_student(purpose):
    msg = (f"Name: {current_student['name']}\n"
           f"Grade: {current_student['grade']}\n"
           f"Section: {current_student['section']}\n"
           f"Purpose: {purpose}\n\n"
           f"Proceed with Time In?")
    if show_yesno_dialog("Confirm", msg):
        play_chime()
        time_in = record_time_in(current_student_id, current_student, purpose)
        show_info_dialog("Success", f"Time In recorded at {time_in}.")
        standby_mode()
    else:
        play_double_beep()
        show_warning_dialog("Cancelled", "Time In was cancelled.")


def confirm_time_out():
    msg = (f"Name: {current_student['name']}\n"
           f"Grade: {current_student['grade']}\n"
           f"Section: {current_student['section']}\n\n"
           f"Proceed with Time Out?")
    if show_yesno_dialog("Confirm Time Out", msg):
        time_out = record_time_out(current_student_id)
        if time_out:
            play_chime()
            show_info_dialog("Success", f"Time Out recorded at {time_out}.")
        else:
            play_double_beep()
            show_error_dialog("Error", "No active Time In found for this student.")
        standby_mode()
    else:
        play_double_beep()
        show_warning_dialog("Cancelled", "Time Out was cancelled.")

# ---------------- ADMIN MENU ----------------
def admin_menu():
    card = build_card("Admin Portal", "Attendance controls", card_relheight=0.70)
    tk.Button(card, text="View Today's Log", width=30, height=2, font=(FONT, ui_px(20, 11)), bg="#111827", fg="white", bd=0, command=view_log).pack(pady=ui_px(10, 4))
    tk.Button(card, text="Exit Admin", width=30, height=2, font=(FONT, ui_px(20, 11)), bg="#f3f4f6", fg=TEXT_MAIN, bd=0, command=standby_mode).pack(pady=ui_px(10, 4))
    tk.Button(card, text="Desktop Mode", width=30, height=2, font=(FONT, ui_px(20, 11)), bg="#f3f4f6", fg=TEXT_MAIN, bd=0, command=enter_desktop_mode).pack(pady=ui_px(10, 4))

def view_log():
    card = build_card(f"Today's Logs ({get_attendance_date()})", card_relheight=0.72)
    
    frame = tk.Frame(card, bg=CARD_BG)
    frame.pack(pady=15, fill=tk.BOTH, expand=True, padx=30)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text = tk.Text(
        frame,
        width=90,
        height=12,
        font=(FONT, ui_px(13, 9)),
        yscrollcommand=scrollbar.set,
        bg="#f9fafb",
        fg=TEXT_MAIN,
        bd=0,
    )
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)
    
    csv_filename = get_csv_filename()
    if os.path.exists(csv_filename):
        with open(csv_filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                header = lines[0].strip()
                text.insert(tk.END, header + "\n")
                text.insert(tk.END, "-" * 80 + "\n")
                for line in lines[1:]:
                    text.insert(tk.END, line)
            else:
                text.insert(tk.END, "No logs yet.")
    else:
        text.insert(tk.END, "No logs yet.")
    
    text.config(state=tk.DISABLED)
    tk.Button(card, text="Back", width=30, height=2, font=(FONT, ui_px(18, 10)), bg="#f3f4f6", fg=TEXT_MAIN, bd=0, command=admin_menu).pack(pady=ui_px(15, 6))
    
def enter_desktop_mode():
    global KIOSK_MODE
    KIOSK_MODE = False
    try:
        root.overrideredirect(False)
    except Exception:
        pass
    try:
        root.attributes("-fullscreen", False)
    except Exception:
        pass
    try:
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        ww = min(1000, max(700, sw - 80))
        wh = min(620, max(420, sh - 80))
        x = max(0, (sw - ww) // 2)
        y = max(0, (sh - wh) // 2)
        root.geometry(f"{ww}x{wh}+{x}+{y}")
        root.resizable(False, False)
    except Exception:
        pass
    update_ui_scale()
    admin_menu()

def enter_kiosk_mode():
    global KIOSK_MODE
    KIOSK_MODE = True
    force_kiosk_mode()
    update_ui_scale()
    admin_menu()


def force_kiosk_mode():
    global KIOSK_MODE
    KIOSK_MODE = True
    try:
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.overrideredirect(False)
        root.attributes("-fullscreen", True)
        root.geometry(f"{sw}x{sh}+0+0")
        root.resizable(False, False)
        root.lift()
        root.focus_force()
    except Exception as e:
        logger.exception("force_kiosk_mode failed: %s", e)

# ---------------- SERVER MANAGEMENT ----------------
server_proc = None
started_server = False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'


def is_server_running(host='127.0.0.1', port=5000, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def start_server():
    global server_proc, started_server
    if is_server_running('127.0.0.1', 5000):
        print('Server already running on 127.0.0.1:5000')
        return False
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, 'server_from_attendance.log')
    logfile = open(log_path, 'a')
    args = [sys.executable, os.path.join(os.path.dirname(__file__), 'Server.py')]
    kwargs = {'stdout': logfile, 'stderr': subprocess.STDOUT, 'cwd': os.path.dirname(__file__)}
    if os.name == 'posix' and hasattr(os, 'setsid'):
        kwargs['preexec_fn'] = os.setsid
    elif os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
    server_proc = subprocess.Popen(args, **kwargs)
    started_server = True
    print(f'Started server subprocess pid={server_proc.pid}')
    return True


def stop_server():
    global server_proc, started_server
    if started_server and server_proc:
        try:
            if server_proc.poll() is None:
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=5)
                except Exception:
                    server_proc.kill()
        except Exception as e:
            print('Error stopping server:', e)
        finally:
            server_proc = None
            started_server = False


atexit.register(stop_server)


# ---------------- MAIN ----------------
cleanup_old_csv_files(retention_days=30)
ensure_students_loaded(force=True)
daily_backup_csv_files()
try:
    start_server()
except Exception:
    logger.exception("Failed to start server subprocess")

if not TK_AVAILABLE:
    logger.warning("tkinter not available; running headless")
    try:
        if server_proc:
            server_proc.wait()
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        stop_server()
    sys.exit(0)

try:
    root = tk.Tk()
except Exception as e:
    logger.exception("No graphical display available or tkinter error: %s", e)
    try:
        if server_proc:
            server_proc.wait()
        else:
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        stop_server()
    sys.exit(0)

root.title("Library Attendance System")
force_kiosk_mode()
root.after(250, force_kiosk_mode)
root.after(750, force_kiosk_mode)
update_ui_scale()
bg_image_path = os.path.join(os.path.dirname(__file__), "Background.png")
if os.path.exists(bg_image_path):
    bg_image = Image.open(bg_image_path).convert("RGB")
    bg_image = bg_image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.Resampling.LANCZOS)
    bg_render_image = bg_image
    try:
        px = bg_render_image.getpixel((root.winfo_screenwidth() // 2, int(root.winfo_screenheight() * 0.08)))
        top_title_bg = f"#{px[0]:02x}{px[1]:02x}{px[2]:02x}"
    except Exception:
        top_title_bg = APP_BG
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.image = bg_photo
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    bg_label.lower()
else:
    root.configure(bg=APP_BG)
    top_title_bg = APP_BG

place_psb_logo()

try:
    if started_server or is_server_running('127.0.0.1', 5000):
        ip = get_local_ip()
        root.after(500, lambda: show_server_banner(ip))
except Exception:
    pass

root.after(100, initial_prompt)
root.mainloop()

stop_server()

