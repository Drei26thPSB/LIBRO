import os
import shutil

CSV_ROOT = 'csv_files'

os.makedirs(CSV_ROOT, exist_ok=True)
moved = []
for f in os.listdir('.'):
    if f.lower().endswith('.csv') and os.path.isfile(f) and f != 'servers.csv':
        dest = os.path.join(CSV_ROOT, f)
        if not os.path.exists(dest):
            shutil.move(f, dest)
            moved.append(f)

print('Moved files:', moved)