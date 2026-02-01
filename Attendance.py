import tkinter as tk
from PIL import Image, ImageTk
import datetime
import csv
import time
import os
import sys
import subprocess
import socket
import atexit

# ---------------- GLOBALS ----------------
# Store logs under project-local `csv_files` so code is portable across platforms (Windows/Linux/RPi)
CSV_ROOT = os.path.join(os.path.dirname(__file__), 'csv_files')
attendance_date = datetime.datetime.now().strftime("%Y-%m-%d")
csv_filename = os.path.join(CSV_ROOT, f"{attendance_date}.csv")
# Ensure directory exists
try:
    os.makedirs(CSV_ROOT, exist_ok=True)
except Exception as e:
    print(f"Error creating CSV directory: {e}")

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
    "S24-0151": {"name": "Jelliuah Sureta", "grade": "12", "section": "MAPAGNILAY"},
    "S1875": {"name": "Reign Yra Fernandez", "grade": "12", "section": "MAPAGNILAY"},
    "S16-0199": {"name": "Kolin Dwayne Lacson", "grade": "12", "section": "MAPAGNILAY"},
    "S22-0165": {"name": "Isabelle Maristela", "grade": "12", "section": "MAPAGNILAY"},
}

current_student = None
last_scan_time = {}
purpose_options = ["Study", "Borrow Book", "Research", "Use Ipad/PC", "Others"]
SCAN_TIMEOUT = 60 # seconds

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
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("700x300")
    dialog.attributes("-topmost", True)
    dialog.resizable(False, False)
    
    tk.Label(dialog, text=message, font=("Arial", 28), wraplength=650, justify=tk.CENTER, pady=20).pack()
    tk.Button(dialog, text="OK", width=20, height=2, font=("Arial", 24), command=dialog.destroy).pack(pady=20)
    root.wait_window(dialog)

def show_error_dialog(title, message):
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("700x300")
    dialog.attributes("-topmost", True)
    dialog.resizable(False, False)
    
    tk.Label(dialog, text=message, font=("Arial", 28), wraplength=650, justify=tk.CENTER, pady=20, fg="red").pack()
    tk.Button(dialog, text="OK", width=20, height=2, font=("Arial", 24), command=dialog.destroy).pack(pady=20)
    root.wait_window(dialog)

def show_warning_dialog(title, message):
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("700x300")
    dialog.attributes("-topmost", True)
    dialog.resizable(False, False)
    
    tk.Label(dialog, text=message, font=("Arial", 28), wraplength=650, justify=tk.CENTER, pady=20, fg="orange").pack()
    tk.Button(dialog, text="OK", width=20, height=2, font=("Arial", 24), command=dialog.destroy).pack(pady=20)
    root.wait_window(dialog)

def show_yesno_dialog(title, message):
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.geometry("700x350")
    dialog.attributes("-topmost", True)
    dialog.resizable(False, False)
    
    result = [None]
    
    tk.Label(dialog, text=message, font=("Arial", 26), wraplength=650, justify=tk.CENTER, pady=20).pack()
    
    button_frame = tk.Frame(dialog)
    button_frame.pack(pady=20)
    
    tk.Button(button_frame, text="YES", width=15, height=2, font=("Arial", 24), command=lambda: (result.__setitem__(0, True), dialog.destroy())).pack(side=tk.LEFT, padx=10)
    tk.Button(button_frame, text="NO", width=15, height=2, font=("Arial", 24), command=lambda: (result.__setitem__(0, False), dialog.destroy())).pack(side=tk.LEFT, padx=10)
    
    root.wait_window(dialog)
    return result[0]


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

# ---------------- LOG ----------------
def log_attendance(student, purpose):
    try:
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        file_exists = os.path.exists(csv_filename)
        with open(csv_filename, "a", newline="") as f:
            writer = csv.writer(f)
            # Add header if file is new
            if not file_exists:
                writer.writerow(["Name", "Section", "Purpose", "Time"])
            writer.writerow([student["name"], student["section"], purpose, time_str])
    except PermissionError:
        print(f"Permission denied: Cannot write to {csv_filename}")
    except Exception as e:
        print(f"Error logging attendance: {e}")

# ---------------- UI UTIL ----------------
def clear():
    for widget in root.winfo_children():
        if widget != bg_label:
            widget.destroy()
    # Ensure background is at the back
    if bg_label:
        bg_label.lower()


# ---------------- STARTUP ----------------
def initial_prompt():
    date = datetime.datetime.now().strftime("%d/%m/%Y")
    if show_yesno_dialog("Start Attendance", f"Start attendance for {date}?"):
        librarian_verify_start()
    else:
        root.destroy()

# ---------------- LIBRARIAN VERIFY ----------------
def librarian_verify_start():
    clear()
    tk.Label(root, text="Librarian Verification", font=("Arial", 48), bg="white", fg="black").pack(pady=30)
    tk.Label(root, text="Scan Librarian ID to Begin", font=("Arial", 40), bg="white", fg="black").pack(pady=20)

    entry = tk.Entry(root, font=("Arial", 32), width=20)
    entry.pack(pady=30)
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
    clear()
    tk.Label(root, text="Scan your ID", font=("Arial", 48), bg="white", fg="black").pack(pady=40)
    entry = tk.Entry(root, font=("Arial", 32), width=20)
    entry.pack(pady=30)
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
                show_warning_dialog("Duplicate", "You already scanned recently.")
                return
            last_scan_time[sid] = now
            global current_student
            current_student = students[sid]
            select_purpose()
        else:
            play_double_beep()
            show_error_dialog("Not Found", "ID not recognized.")

    entry.bind("<Return>", process_scan)

# ---------------- PURPOSE SELECT ----------------
def select_purpose():
    clear()
    tk.Label(root, text=f"Hi {current_student['name']}!\nSelect Purpose:", font=("Arial", 32), bg="white", fg="black").pack(pady=20)
    for p in purpose_options:
        tk.Button(root, text=p, width=40, height=2, font=("Arial", 24), command=lambda x=p: confirm_student(x)).pack(pady=12)

# ---------------- CONFIRM ----------------
def confirm_student(purpose):
    msg = (f"Name: {current_student['name']}\n"
           f"Grade: {current_student['grade']}\n"
           f"Section: {current_student['section']}\n"
           f"Purpose: {purpose}")
    if show_yesno_dialog("Confirm", msg):
        play_beep()
        log_attendance(current_student, purpose)
        show_info_dialog("Success", "Logged successfully!")
        standby_mode()
    else:
        play_double_beep()
        show_warning_dialog("Cancelled", "Please ask the librarian for assistance")

# ---------------- ADMIN MENU ----------------
def admin_menu():
    clear()
    tk.Label(root, text="Admin Portal", font=("Arial", 40), bg="white", fg="black").pack(pady=20)
    tk.Button(root, text="View Today's Log", width=40, height=2, font=("Arial", 24), command=view_log).pack(pady=15)
    tk.Button(root, text="Exit Admin", width=40, height=2, font=("Arial", 24), command=standby_mode).pack(pady=15)
    tk.Button(root, text="Desktop Mode", width=40, height=2, font=("Arial", 24), command=enter_desktop_mode).pack(pady=15)

def view_log():
    clear()
    tk.Label(root, text=f"Today's Logs ({attendance_date})", font=("Arial", 28), bg="white", fg="black").pack(pady=15)
    
    # Create frame for text and scrollbar
    frame = tk.Frame(root, bg="white")
    frame.pack(pady=15, fill=tk.BOTH, expand=True)
    
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    text = tk.Text(frame, width=90, height=12, font=("Arial", 14), yscrollcommand=scrollbar.set, bg="white", fg="black")
    text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=text.yview)
    
    if os.path.exists(csv_filename):
        with open(csv_filename, "r") as f:
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
    tk.Button(root, text="Back", width=40, height=2, font=("Arial", 24), command=admin_menu).pack(pady=15)
    
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
try:
    start_server()
except Exception:
    print('Failed to start server subprocess')

# If there's no graphical display (headless Pi), give a helpful error and exit instead of raising a Tk exception
try:
    root = tk.Tk()
except tk.TclError:
    print("No graphical display available. Attendance UI requires a desktop environment (X11).")
    # Keep server running if it was started by this process; just exit the UI
    sys.exit(0)

root.title("Library Attendance System")
root.attributes("-fullscreen", True)  # Fullscreen auto

# Load background image
bg_label = None
bg_image_path = os.path.join(os.path.dirname(__file__), "Background.png")
if os.path.exists(bg_image_path):
    bg_image = Image.open(bg_image_path)
    bg_image = bg_image.resize((root.winfo_screenwidth(), root.winfo_screenheight()), Image.Resampling.LANCZOS)
    bg_photo = ImageTk.PhotoImage(bg_image)
    bg_label = tk.Label(root, image=bg_photo)
    bg_label.image = bg_photo
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)
    bg_label.lower()  # Send to back
else:
    root.configure(bg="#333333")  # Dark background for better readability

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

