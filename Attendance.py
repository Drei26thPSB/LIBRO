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
from PIL import Image, ImageTk

# ---------------- GLOBALS ----------------
# Store logs under project-local `csv_files` so code is portable across platforms (Windows/Linux/RPi)
CSV_ROOT = os.path.join(os.path.dirname(__file__), 'csv_files')
# Ensure directory exists
try:
    os.makedirs(CSV_ROOT, exist_ok=True)
except Exception as e:
    print(f"Error creating CSV directory: {e}")


def cleanup_old_csv_files(retention_days=30):
    """Delete CSV files older than retention_days using file modification time."""
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
                    print(f"Failed to evaluate/delete old CSV '{full}': {e}")
        if deleted:
            print(f"Deleted {deleted} CSV file(s) older than {retention_days} days.")
    except Exception as e:
        print(f"CSV cleanup failed: {e}")

librarian_ids = ["S1898"]
students = {
    "S0000": {"name": "Alfred Andrei Serquina", "grade": "12", "section": "MAPAGPALAYA"},
    "S2103": {"name": "Jaime Enrico Dilao", "grade": "12", "section": "MAPAGPALAYA"},
    "S24-0100": {"name": "Nataniela Vera Garcia", "grade": "12", "section": "MAPAGPALAYA"},
    "S14-0235": {"name": "Tish Darryne Yu", "grade": "12", "section": "MAPAGPALAYA"},
    "S22-0106": {"name": "Criselda Mendoza", "grade": "12", "section": "MAPAGPALAYA"},
    "S1910": {"name": "Rholand Anthony Puig", "grade": "12", "section": "MAPAGPALAYA"},
    "S24-0152": {"name": "Renee Magahiz", "grade": "12", "section": "MAPAGPALAYA"},
    "S18-0253": {"name": "Daniel Coralde", "grade": "12", "section": "MAPITAGAN"},
    "S1896": {"name": "Sebastian Andrei Abanilla", "grade": "12", "section": "MAPAGPALAYA"},
    "S24-0150": {"name": "Joshmar Sy", "grade": "12", "section": "MAPAGPALAYA"},
    "S19-0212": {"name": "Dwayne Bodota", "grade": "12", "section": "MAPAGNILAY"},
    "S24-0151": {"name": "Jelliuah Sureta", "grade": "12", "section": "MAPAGPALAYA"},
    "S1875": {"name": "Reign Yra Fernandez", "grade": "12", "section": "MAPAGPALAYA"},
    "S16-0199": {"name": "Kolin Dwayne Lacson", "grade": "12", "section": "MAPAGNILAY"},
    "S22-0165": {"name": "Isabelle Maristela", "grade": "12", "section": "MAPAGPALAYA"},
}

CSV_HEADERS = ["Student ID", "Name", "Section", "Purpose", "Time In", "Time Out", "Status"]

current_student = None
current_student_id = None
last_scan_time = {}
purpose_options = ["Study", "Borrow Book", "Research", "Use Ipad/PC", "Others"]
SCAN_TIMEOUT = 3  # anti-double-scan cooldown in seconds

# ---------------- UI STYLE ----------------
APP_BG = "#f2f4f7"
CARD_BG = "#ffffff"
BORDER = "#e5e7eb"
TEXT_MAIN = "#111827"
TEXT_MUTED = "#6b7280"
PRIMARY = "#0a84ff"
PRIMARY_ACTIVE = "#0866c5"
WARN = "#9a3412"
DANGER = "#b42318"
FONT = "Segoe UI"


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
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for row in rows:
                writer.writerow(normalize_row(row))
    except PermissionError:
        print(f"Permission denied: Cannot write to {path}")
    except Exception as e:
        print(f"Error writing attendance rows: {e}")


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

# ---------------- BEEP (cross-platform) ----------------
import shutil

def play_beep():
    """Cross-platform beep: use winsound on Windows, `beep` command on Linux if present, otherwise fallback to ASCII bell."""
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

# ---------------- CUSTOM DIALOGS ----------------
def show_info_dialog(title, message):
    messagebox.showinfo(title, message)

def show_error_dialog(title, message):
    messagebox.showerror(title, message)

def show_warning_dialog(title, message):
    messagebox.showwarning(title, message)

def show_yesno_dialog(title, message):
    return messagebox.askyesno(title, message)


def show_server_banner(ip, duration=8000):
    """Show a transient, non-modal banner at the top of the app with an 'Open' button to open the web UI."""
    try:
        import webbrowser
        # Avoid creating banner before root exists
        if not root:
            return
        banner = tk.Frame(root, bg='#0d6efd', bd=1, relief=tk.RIDGE)
        banner.place(relx=0.5, rely=0.01, anchor='n')
        label = tk.Label(banner, text=f"Web UI: http://{ip}:5000", fg='white', bg='#0d6efd', font=("Arial", 12))
        label.pack(side='left', padx=(10,5), pady=5)
        def open_browser():
            try:
                webbrowser.open(f'http://{ip}:5000')
            except Exception:
                pass
        btn = tk.Button(banner, text='Open', command=open_browser)
        btn.pack(side='left', padx=(0,10), pady=5)
        def remove_banner():
            try:
                banner.destroy()
            except Exception:
                pass
        # Auto-hide after duration milliseconds
        root.after(duration, remove_banner)
    except Exception:
        pass

# ---------------- UI UTIL ----------------
def clear():
    for widget in root.winfo_children():
        if widget != bg_label:
            widget.destroy()
    # Ensure background is at the back
    if bg_label:
        bg_label.lower()


def build_card(title, subtitle=None):
    clear()
    card = tk.Frame(root, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
    card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.74, relheight=0.82)

    tk.Label(card, text=title, font=(FONT, 36, "bold"), bg=CARD_BG, fg=TEXT_MAIN).pack(pady=(30, 10))
    if subtitle:
        tk.Label(card, text=subtitle, font=(FONT, 16), bg=CARD_BG, fg=TEXT_MUTED, wraplength=900, justify=tk.CENTER).pack(pady=(0, 22))
    return card


# ---------------- STARTUP ----------------
def initial_prompt():
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    if show_yesno_dialog("Start Attendance", f"Start attendance for {date}?"):
        librarian_verify_start()
    else:
        root.destroy()

# ---------------- LIBRARIAN VERIFY ----------------
def librarian_verify_start():
    card = build_card("Librarian Verification", "Scan Librarian ID to start attendance.")

    entry = tk.Entry(card, font=(FONT, 28), width=24, bd=0, highlightthickness=1, highlightbackground=BORDER)
    entry.pack(pady=30, ipady=10)
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
    card = build_card("Scan your ID", "Student scan auto-detects Time In or Time Out.")
    entry = tk.Entry(card, font=(FONT, 28), width=24, bd=0, highlightthickness=1, highlightbackground=BORDER)
    entry.pack(pady=30, ipady=10)
    entry.focus_set()

    def process_scan(event=None):
        sid = entry.get().strip()
        entry.delete(0, tk.END)
        if sid in librarian_ids:
            play_beep()
            admin_menu()
            return
        if sid in students:
            now = time.time()
            if sid in last_scan_time and now - last_scan_time[sid] < SCAN_TIMEOUT:
                play_double_beep()
                show_warning_dialog("Duplicate", "Please wait a moment before scanning again.")
                return
            last_scan_time[sid] = now
            global current_student, current_student_id
            current_student_id = sid
            current_student = students[sid]
            if has_open_session(sid):
                confirm_time_out()
            else:
                select_purpose()
        else:
            play_double_beep()
            show_error_dialog("Not Found", "ID not recognized.")

    entry.bind("<Return>", process_scan)

# ---------------- PURPOSE SELECT ----------------
def select_purpose():
    card = build_card(f"Hi, {current_student['name']}", "Select one or more purposes for this Time In.")
    checkbox_vars = []

    for p in purpose_options:
        var = tk.BooleanVar(value=False)
        checkbox_vars.append((p, var))
        tk.Checkbutton(
            card,
            text=p,
            variable=var,
            onvalue=True,
            offvalue=False,
            font=(FONT, 20),
            bg=CARD_BG,
            fg=TEXT_MAIN,
            anchor="w",
            padx=15,
            pady=8,
            selectcolor="#f9fafb",
            activebackground=CARD_BG,
        ).pack(fill="x", padx=120, pady=4)

    def submit_purposes():
        selected = [label for label, var in checkbox_vars if var.get()]
        if not selected:
            play_double_beep()
            show_warning_dialog("Purpose Required", "Select at least one purpose.")
            return
        confirm_student(", ".join(selected))

    tk.Button(
        card,
        text="Confirm Time In",
        width=20,
        font=(FONT, 20, "bold"),
        bg=PRIMARY,
        fg="white",
        activebackground=PRIMARY_ACTIVE,
        activeforeground="white",
        bd=0,
        padx=20,
        pady=10,
        command=submit_purposes,
    ).pack(pady=(24, 8))

    tk.Button(
        card,
        text="Back",
        width=20,
        font=(FONT, 16),
        bg="#f3f4f6",
        fg=TEXT_MAIN,
        bd=0,
        padx=18,
        pady=8,
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
        play_beep()
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
            play_beep()
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
    card = build_card("Admin Portal", "Attendance controls")
    tk.Button(card, text="View Today's Log", width=30, height=2, font=(FONT, 20), bg="#111827", fg="white", bd=0, command=view_log).pack(pady=10)
    tk.Button(card, text="Exit Admin", width=30, height=2, font=(FONT, 20), bg="#f3f4f6", fg=TEXT_MAIN, bd=0, command=standby_mode).pack(pady=10)
    tk.Button(card, text="Desktop Mode", width=30, height=2, font=(FONT, 20), bg="#f3f4f6", fg=TEXT_MAIN, bd=0, command=enter_desktop_mode).pack(pady=10)

def view_log():
    card = build_card(f"Today's Logs ({get_attendance_date()})")
    
    # Create frame for text and scrollbar
    frame = tk.Frame(card, bg=CARD_BG)
    frame.pack(pady=15, fill=tk.BOTH, expand=True, padx=30)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text = tk.Text(frame, width=90, height=12, font=(FONT, 13), yscrollcommand=scrollbar.set, bg="#f9fafb", fg=TEXT_MAIN, bd=0)
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)
    
    csv_filename = get_csv_filename()
    if os.path.exists(csv_filename):
        with open(csv_filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if lines:
                # Format header
                header = lines[0].strip()
                text.insert(tk.END, header + "\n")
                text.insert(tk.END, "-" * 80 + "\n")
                # Format data rows
                for line in lines[1:]:
                    text.insert(tk.END, line)
            else:
                text.insert(tk.END, "No logs yet.")
    else:
        text.insert(tk.END, "No logs yet.")
    
    text.config(state=tk.DISABLED)  # Make read-only
    tk.Button(card, text="Back", width=30, height=2, font=(FONT, 18), bg="#f3f4f6", fg=TEXT_MAIN, bd=0, command=admin_menu).pack(pady=15)
    
def enter_desktop_mode():
    root.attributes("-fullscreen", False)
    root.geometry("1000x600")  # optional window size

def enter_kiosk_mode():
    root.attributes("-fullscreen", True)

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
        # CREATE_NEW_PROCESS_GROUP to avoid sending signals to entire console group
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


# Ensure server subprocess is stopped on interpreter exit
atexit.register(stop_server)


# ---------------- MAIN ----------------
# Start server even in headless mode (so web UI is available)
cleanup_old_csv_files(retention_days=30)
try:
    start_server()
except Exception:
    print('Failed to start server subprocess')

if not TK_AVAILABLE:
    print("tkinter not available; running headless. Server should be accessible at http://<ip>:5000")
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
    print("No graphical display available or tkinter error:", e)
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
root.attributes("-fullscreen", True)  # Fullscreen auto
bg_label = None
bg_image_path = os.path.join(os.path.dirname(__file__), "Background.png")
if os.path.exists(bg_image_path):
    bg_image = Image.open(bg_image_path)
    bg_image = bg_image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.Resampling.LANCZOS)
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.image = bg_photo
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    bg_label.lower()
else:
    root.configure(bg=APP_BG)

# Start app
# If we successfully started the server subprocess, let the user know via the UI
try:
    # If server started by this process, or already running, show banner at launch
    if started_server or is_server_running('127.0.0.1', 5000):
        ip = get_local_ip()
        root.after(500, lambda: show_server_banner(ip))
except Exception:
    pass

root.after(100, initial_prompt)
root.mainloop()

# On normal exit, ensure server subprocess is stopped
stop_server()

