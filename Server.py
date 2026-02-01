from flask import Flask, send_file, redirect, url_for, render_template, request, flash
import os
import re
import csv
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.secret_key = 'change-me-to-a-secure-key'

# Configure logging to file
if not os.path.exists('logs'):
    os.makedirs('logs')
file_handler = RotatingFileHandler('logs/server.log', maxBytes=5*1024*1024, backupCount=3)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Starting server')

ROOT_DIR = os.getcwd()

from werkzeug.utils import secure_filename
import shutil

# Folder to keep CSV logs
CSV_ROOT = 'csv_files'


def ensure_csv_root_and_move_existing():
    """Create CSV_ROOT and move any top-level .csv files (except internal ones) into it."""
    os.makedirs(CSV_ROOT, exist_ok=True)
    moved = []
    for name in os.listdir('.'):
        if name.lower().endswith('.csv') and os.path.isfile(name) and name not in (CSV_ROOT, 'servers.csv'):
            dest = os.path.join(CSV_ROOT, name)
            if not os.path.exists(dest):
                try:
                    os.rename(name, dest)
                    app.logger.info('Moved %s to %s', name, dest)
                    moved.append(name)
                except Exception:
                    app.logger.exception('Failed to move %s', name)
    return moved

# Ensure CSV folder and relocate files on startup
moved_files = ensure_csv_root_and_move_existing()
if moved_files:
    app.logger.info('Moved CSV files on startup: %s', moved_files)


def safe_join(rel_path):
    """Return absolute, normalized path inside project root for a relative path; raise ValueError for unsafe paths."""
    if rel_path is None:
        rel_path = ''
    # prevent leading slashes or parent traversal
    rel_path = rel_path.strip()
    normalized = os.path.normpath(os.path.join(ROOT_DIR, rel_path))
    if not normalized.startswith(ROOT_DIR):
        raise ValueError('Unsafe path')
    return normalized


def csv_safe_join(rel_path):
    """Return absolute, normalized path inside CSV_ROOT for a relative path; raise ValueError for unsafe paths.

    Accepts paths like 'sub/folder' or 'csv_files/sub/folder' or just 'filename.csv'.
    """
    if rel_path is None:
        rel_path = ''
    rel_path = rel_path.strip()
    # If the caller passed a path starting with CSV_ROOT, strip it to get relative part
    if rel_path == CSV_ROOT:
        rel_inside = ''
    elif rel_path.startswith(CSV_ROOT + os.sep) or rel_path.startswith(CSV_ROOT + '/'):
        rel_inside = rel_path[len(CSV_ROOT)+1:]
    else:
        rel_inside = rel_path
    normalized = os.path.normpath(os.path.join(ROOT_DIR, CSV_ROOT, rel_inside))
    csv_root_abs = os.path.normpath(os.path.join(ROOT_DIR, CSV_ROOT))
    if not normalized.startswith(csv_root_abs):
        raise ValueError('Unsafe path')
    return normalized


def list_dir(rel_path=''):
    # Only allow browsing within CSV_ROOT and show only dated CSV logs (exclude servers.csv)
    rel_path = rel_path or ''
    try:
        base = safe_join(os.path.join(CSV_ROOT, rel_path))
    except ValueError:
        raise
    items = []
    date_csv_re = re.compile(r'^\d{4}[-_]?\d{2}[-_]?\d{2}\.csv$', re.IGNORECASE)
    for name in sorted(os.listdir(base)):
        full = os.path.join(base, name)
        is_dir = os.path.isdir(full)
        # If it's a file, only include CSVs that look like dated attendance logs, and exclude servers.csv
        if not is_dir:
            if not name.lower().endswith('.csv'):
                continue
            if name.lower() == 'servers.csv':
                continue
            if not date_csv_re.match(name):
                continue
        rel = os.path.normpath(os.path.join(os.path.relpath(os.path.join(CSV_ROOT, rel_path), CSV_ROOT), name)).replace('\\\\', '/')
        rel = rel.lstrip('./')
        full_rel = os.path.normpath(os.path.join(CSV_ROOT, rel)).replace('\\\\', '/')
        items.append({
            'name': name,
            'rel': rel,
            'full_rel': full_rel,
            'is_dir': is_dir,
            'size': os.path.getsize(full) if os.path.isfile(full) else None,
            'mtime': os.path.getmtime(full)
        })
    return items


def list_folders():
    # Only show folders under CSV_ROOT
    folders = ['']
    for root, dirs, files in os.walk(CSV_ROOT):
        rel = os.path.relpath(root, CSV_ROOT)
        if rel == '.':
            rel = ''
        folders.append(rel.replace('\\\\', '/'))
    folders = sorted(set(folders))
    return folders


def find_csvs_in_root():
    """Recursively find dated CSV files under CSV_ROOT and return their relative paths."""
    results = []
    date_csv_re = re.compile(r'^\d{4}[-_]?\d{2}[-_]?\d{2}\.csv$', re.IGNORECASE)
    for r, dirs, files in os.walk(CSV_ROOT):
        for f in files:
            if not f.lower().endswith('.csv'):
                continue
            if f.lower() == 'servers.csv':
                continue
            if not date_csv_re.match(f):
                continue
            rel = os.path.normpath(os.path.join(r, f)).replace('\\\\', '/')
            results.append(rel)
    results.sort()
    return results


@app.errorhandler(Exception)
def handle_exception(e):
    # Let Flask handle HTTP exceptions (404, 400, etc.)
    if isinstance(e, HTTPException):
        return e
    # Log unexpected exceptions with traceback
    app.logger.exception('Unhandled exception:')
    # Show friendly error page
    return render_template('error.html'), 500


@app.route('/')
def index():
    return redirect(url_for('manage_files'))


@app.route('/files')
def manage_files():
    path = request.args.get('path', '')
    # Normalize path: treat explicit CSV_ROOT as root, and strip a leading CSV_ROOT/ prefix
    if path == CSV_ROOT:
        path = ''
    elif path.startswith(CSV_ROOT + os.sep) or path.startswith(CSV_ROOT + '/'):
        path = path[len(CSV_ROOT)+1:]
    try:
        entries = list_dir(path)
    except ValueError:
        flash('Invalid path', 'error')
        return redirect(url_for('manage_files'))
    folders = list_folders()
    csv_list = find_csvs_in_root()
    return render_template('servers.html', path=path, entries=entries, folders=folders, csv_list=csv_list, CSV_ROOT=CSV_ROOT)


@app.route('/upload', methods=['POST'])
def upload():
    target = request.form.get('target', '').strip()
    f = request.files.get('file')
    if not f:
        flash('No file provided', 'error')
        return redirect(url_for('manage_files', path=target))
    filename = secure_filename(f.filename)
    if not filename.lower().endswith('.csv'):
        flash('Only CSV files are allowed', 'error')
        return redirect(url_for('manage_files', path=target))
    date_csv_re = re.compile(r'^\d{4}[-_]?\d{2}[-_]?\d{2}\.csv$', re.IGNORECASE)
    if not date_csv_re.match(filename):
        flash('Only date-named CSV files (e.g., 2026-01-28.csv) are allowed', 'error')
        return redirect(url_for('manage_files', path=target))
    try:
        dest_dir = csv_safe_join(target)
    except ValueError:
        flash('Invalid target folder', 'error')
        return redirect(url_for('manage_files'))
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, filename)
    f.save(dest_path)
    flash('File uploaded', 'success')
    # If target was CSV_ROOT (root), show root view; otherwise show the selected subfolder
    redirect_path = '' if (not target or target == CSV_ROOT) else target
    return redirect(url_for('manage_files', path=redirect_path))


@app.route('/mkdir', methods=['POST'])
def mkdir():
    name = request.form.get('name', '').strip()
    parent = request.form.get('parent', '').strip()
    if not name:
        flash('Folder name required', 'error')
        return redirect(url_for('manage_files', path=parent))
    if '/' in name or '\\' in name or '..' in name:
        flash('Invalid folder name', 'error')
        return redirect(url_for('manage_files', path=parent))
    try:
        # Create folder under CSV_ROOT
        path = csv_safe_join(os.path.join(parent, name))
    except ValueError:
        flash('Invalid path', 'error')
        return redirect(url_for('manage_files'))
    if os.path.exists(path):
        flash('Folder already exists', 'error')
    else:
        os.makedirs(path)
        flash('Folder created', 'success')
    redirect_parent = '' if not parent or parent == CSV_ROOT else parent
    return redirect(url_for('manage_files', path=redirect_parent))


@app.route('/rename', methods=['POST'])
def rename():
    path = request.form.get('path', '').strip()
    new_name = request.form.get('new_name', '').strip()
    if not path or not new_name:
        flash('Invalid rename request', 'error')
        return redirect(url_for('manage_files'))
    if '/' in new_name or '\\' in new_name or '..' in new_name:
        flash('Invalid new name', 'error')
        return redirect(url_for('manage_files'))
    try:
        src = csv_safe_join(path)
    except ValueError:
        flash('Invalid source', 'error')
        return redirect(url_for('manage_files'))
    dst = os.path.join(os.path.dirname(src), secure_filename(new_name))
    # Ensure dst still inside CSV_ROOT
    try:
        if not os.path.normpath(dst).startswith(os.path.normpath(os.path.join(ROOT_DIR, CSV_ROOT))):
            raise ValueError('Invalid destination')
    except ValueError:
        flash('Invalid destination', 'error')
        return redirect(url_for('manage_files'))
    if os.path.exists(dst):
        flash('Target already exists', 'error')
        return redirect(url_for('manage_files'))
    os.rename(src, dst)
    flash('Renamed', 'success')
    parent = os.path.relpath(os.path.dirname(src), os.path.join(ROOT_DIR, CSV_ROOT))
    parent = '' if parent == '.' else parent
    return redirect(url_for('manage_files', path=parent))


@app.route('/move', methods=['POST'])
def move():
    path = request.form.get('path', '').strip()
    dest_folder = request.form.get('dest_folder', '').strip()
    try:
        src = csv_safe_join(path)
        dst_dir = csv_safe_join(dest_folder)
    except ValueError:
        flash('Invalid path', 'error')
        return redirect(url_for('manage_files'))
    if not os.path.isdir(dst_dir):
        flash('Destination is not a folder', 'error')
        return redirect(url_for('manage_files'))
    dst = os.path.join(dst_dir, os.path.basename(src))
    if os.path.exists(dst):
        flash('Destination already exists', 'error')
        return redirect(url_for('manage_files'))
    os.rename(src, dst)
    flash('Moved', 'success')
    parent = os.path.relpath(dst_dir, os.path.join(ROOT_DIR, CSV_ROOT))
    parent = '' if parent == '.' else parent
    return redirect(url_for('manage_files', path=parent))


@app.route('/delete', methods=['POST'])
def delete():
    path = request.form.get('path', '').strip()
    try:
        target = csv_safe_join(path)
    except ValueError:
        flash('Invalid path', 'error')
        return redirect(url_for('manage_files'))
    if os.path.isdir(target):
        if os.listdir(target):
            flash('Folder not empty', 'error')
            parent = os.path.relpath(target, os.path.join(ROOT_DIR, CSV_ROOT))
            parent = '' if parent == '.' else parent
            return redirect(url_for('manage_files', path=parent))
        os.rmdir(target)
        flash('Folder deleted', 'success')
        parent = os.path.relpath(os.path.dirname(target), os.path.join(ROOT_DIR, CSV_ROOT))
        parent = '' if parent == '.' else parent
        return redirect(url_for('manage_files', path=parent))
    else:
        os.remove(target)
        flash('File deleted', 'success')
        parent = os.path.relpath(os.path.dirname(target), os.path.join(ROOT_DIR, CSV_ROOT))
        parent = '' if parent == '.' else parent
        return redirect(url_for('manage_files', path=parent))


@app.route('/csv/view/<path:filename>')
def view_csv(filename):
    try:
        abs_path = csv_safe_join(filename)
    except ValueError:
        return 'Invalid file', 400
    if not abs_path.lower().endswith('.csv') or not os.path.isfile(abs_path):
        return 'File not found', 404

    headers = []
    rows = []
    with open(abs_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                headers = row
            else:
                rows.append(row)

    return render_template('view_csv.html', filename=filename, headers=headers, rows=rows)


@app.route('/download/<path:filename>')
def download(filename):
    try:
        abs_path = csv_safe_join(filename)
    except ValueError:
        return 'Invalid file', 400
    if not abs_path.lower().endswith('.csv') or not os.path.isfile(abs_path):
        return 'File not found', 404
    return send_file(abs_path, as_attachment=True)


if __name__ == '__main__':
    # Run with debug=False so users see a friendly error page; check 'logs/server.log' for details
    app.run(host='0.0.0.0', port=5000, debug=False)
