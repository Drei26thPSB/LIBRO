from flask import Flask, redirect, render_template, request, flash, Response, url_for, send_file
import os
import csv
import time
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)
app.secret_key = 'change-me-to-a-secure-key'

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_ROOT = 'csv_files'
CSV_ROOT_ABS = os.path.join(ROOT_DIR, CSV_ROOT)

logs_dir = os.path.join(ROOT_DIR, 'logs')
os.makedirs(logs_dir, exist_ok=True)
file_handler = RotatingFileHandler(os.path.join(logs_dir, 'server.log'), maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Starting server')

AUTH_USER = os.getenv('LIBRO_USER')
AUTH_PASS = os.getenv('LIBRO_PASS')
if AUTH_USER and AUTH_PASS:
    def _check_auth(username, password):
        return username == AUTH_USER and password == AUTH_PASS

    @app.before_request
    def require_basic_auth():
        if request.endpoint == 'static':
            return None
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return Response('Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})


def ensure_csv_root_and_move_existing():
    os.makedirs(CSV_ROOT_ABS, exist_ok=True)
    moved = []
    for name in os.listdir(ROOT_DIR):
        fullpath = os.path.join(ROOT_DIR, name)
        if name.lower().endswith('.csv') and os.path.isfile(fullpath):
            dest = os.path.join(CSV_ROOT_ABS, name)
            if not os.path.exists(dest):
                try:
                    os.rename(fullpath, dest)
                    moved.append(name)
                except Exception:
                    app.logger.exception('Failed to move %s', name)
    if moved:
        app.logger.info('Moved CSV files on startup: %s', moved)


def cleanup_old_csv_files(retention_days=30):
    cutoff = time.time() - (retention_days * 24 * 60 * 60)
    deleted = 0
    for dirpath, _, filenames in os.walk(CSV_ROOT_ABS):
        for name in filenames:
            if not name.lower().endswith('.csv'):
                continue
            full = os.path.join(dirpath, name)
            try:
                if os.path.getmtime(full) <= cutoff:
                    os.remove(full)
                    deleted += 1
            except Exception:
                app.logger.exception('Failed deleting old CSV: %s', full)
    if deleted:
        app.logger.info('Deleted %d CSV file(s) older than %d days', deleted, retention_days)


ensure_csv_root_and_move_existing()
cleanup_old_csv_files(retention_days=30)


def safe_join(root, *paths):
    root = os.path.abspath(root)
    final = os.path.abspath(os.path.join(root, *paths))
    if os.path.commonpath([root, final]) != root:
        raise ValueError('Attempted path traversal')
    return final


def csv_safe_join(rel_path=''):
    return safe_join(CSV_ROOT_ABS, rel_path or '')


def list_folders():
    out = ['']
    for dirpath, _, _ in os.walk(CSV_ROOT_ABS):
        rel = os.path.relpath(dirpath, CSV_ROOT_ABS)
        if rel != '.':
            out.append(rel.replace('\\', '/'))
    return sorted(set(out))


def list_all_csv_files():
    files = []
    for dirpath, _, filenames in os.walk(CSV_ROOT_ABS):
        rel_dir = os.path.relpath(dirpath, CSV_ROOT_ABS)
        rel_dir = '' if rel_dir == '.' else rel_dir.replace('\\', '/')
        for name in sorted(filenames):
            if not name.lower().endswith('.csv'):
                continue
            rel = f"{rel_dir}/{name}".strip('/') if rel_dir else name
            full = os.path.join(dirpath, name)
            files.append({
                'name': name,
                'rel': rel,
                'folder': rel_dir if rel_dir else '',
                'size': os.path.getsize(full),
            })
    return sorted(files, key=lambda x: x['rel'].lower())


@app.errorhandler(Exception)
def handle_exception(e):
    app.logger.exception('Unhandled exception: %s', e)
    return render_template('error.html'), 500


@app.route('/')
@app.route('/files')
def manage_files():
    path = (request.args.get('path') or '').strip('/')
    try:
        abs_path = csv_safe_join(path) if path else csv_safe_join()
    except ValueError:
        flash('Invalid path', 'danger')
        return redirect(url_for('manage_files'))

    if not os.path.isdir(abs_path):
        flash('Folder not found', 'danger')
        return redirect(url_for('manage_files'))

    entries = []
    for name in sorted(os.listdir(abs_path), key=lambda n: (not os.path.isdir(os.path.join(abs_path, n)), n.lower())):
        full = os.path.join(abs_path, name)
        rel = os.path.join(path, name) if path else name
        is_dir = os.path.isdir(full)
        is_csv = os.path.isfile(full) and name.lower().endswith('.csv')
        if not (is_dir or is_csv):
            continue
        entries.append({
            'name': name,
            'rel': rel.replace('\\', '/'),
            'is_dir': is_dir,
            'size': os.path.getsize(full) if is_csv else None,
        })

    folders = list_folders()
    all_csv_files = list_all_csv_files()
    return render_template(
        'servers.html',
        entries=entries,
        folders=folders,
        path=path,
        csv_root=CSV_ROOT,
        all_csv_files=all_csv_files,
    )


@app.route('/mkdir', methods=['POST'])
def mkdir():
    parent = (request.form.get('parent') or '').strip('/')
    name = secure_filename(request.form.get('name') or '')
    if not name:
        flash('Folder name required', 'danger')
        return redirect(url_for('manage_files', path=parent))
    try:
        target = csv_safe_join(parent)
        os.makedirs(os.path.join(target, name), exist_ok=True)
        flash('Folder created', 'success')
    except Exception:
        app.logger.exception('mkdir failed')
        flash('Failed to create folder', 'danger')
    return redirect(url_for('manage_files', path=parent))


@app.route('/create_csv', methods=['POST'])
def create_csv():
    parent = (request.form.get('parent') or '').strip('/')
    raw_name = (request.form.get('name') or '').strip()
    headers_input = (request.form.get('headers') or '').strip()

    name = secure_filename(raw_name)
    if not name:
        flash('CSV filename required', 'danger')
        return redirect(url_for('manage_files', path=parent))
    if not name.lower().endswith('.csv'):
        name = f'{name}.csv'

    try:
        dest_dir = csv_safe_join(parent)
        os.makedirs(dest_dir, exist_ok=True)
        full = os.path.join(dest_dir, name)
        if os.path.exists(full):
            flash('CSV already exists', 'danger')
            return redirect(url_for('manage_files', path=parent))

        with open(full, 'w', newline='', encoding='utf-8') as fh:
            if headers_input:
                writer = csv.writer(fh)
                headers = [h.strip() for h in headers_input.split(',') if h.strip()]
                if headers:
                    writer.writerow(headers)
        flash('CSV created', 'success')
    except Exception:
        app.logger.exception('create_csv failed')
        flash('Failed to create CSV', 'danger')
    return redirect(url_for('manage_files', path=parent))


@app.route('/edit/<path:filename>')
def edit_csv(filename):
    try:
        full = csv_safe_join(filename)
    except ValueError:
        flash('Invalid filename', 'danger')
        return redirect(url_for('manage_files'))

    if not os.path.isfile(full) or not full.lower().endswith('.csv'):
        flash('CSV not found', 'danger')
        return redirect(url_for('manage_files'))

    try:
        with open(full, 'r', encoding='utf-8') as fh:
            content = fh.read()
    except Exception:
        app.logger.exception('Failed reading CSV for edit')
        flash('Failed to open CSV', 'danger')
        return redirect(url_for('manage_files'))

    return render_template('edit_csv.html', filename=filename, content=content)


@app.route('/view/<path:filename>')
def view_csv(filename):
    try:
        full = csv_safe_join(filename)
    except ValueError:
        flash('Invalid filename', 'danger')
        return redirect(url_for('manage_files'))

    if not os.path.isfile(full) or not full.lower().endswith('.csv'):
        flash('CSV not found', 'danger')
        return redirect(url_for('manage_files'))

    try:
        with open(full, newline='', encoding='utf-8') as fh:
            rows = list(csv.reader(fh))
        headers = rows[0] if rows else []
        data = rows[1:] if len(rows) > 1 else []
        return render_template('view_csv.html', filename=filename, headers=headers, rows=data)
    except Exception:
        app.logger.exception('view_csv failed')
        flash('Failed to view CSV', 'danger')
        return redirect(url_for('manage_files'))


@app.route('/download/<path:filename>')
def download_csv(filename):
    try:
        full = csv_safe_join(filename)
    except ValueError:
        flash('Invalid filename', 'danger')
        return redirect(url_for('manage_files'))

    if not os.path.isfile(full) or not full.lower().endswith('.csv'):
        flash('CSV not found', 'danger')
        return redirect(url_for('manage_files'))
    return send_file(full, as_attachment=True)


@app.route('/save/<path:filename>', methods=['POST'])
def save_csv(filename):
    content = request.form.get('content', '')
    try:
        full = csv_safe_join(filename)
    except ValueError:
        flash('Invalid filename', 'danger')
        return redirect(url_for('manage_files'))

    if not full.lower().endswith('.csv'):
        flash('Only CSV files can be saved', 'danger')
        return redirect(url_for('manage_files'))

    try:
        with open(full, 'w', encoding='utf-8', newline='') as fh:
            fh.write(content.replace('\r\n', '\n'))
        flash('CSV saved', 'success')
    except Exception:
        app.logger.exception('save_csv failed')
        flash('Failed to save CSV', 'danger')

    return redirect(url_for('edit_csv', filename=filename))


@app.route('/move', methods=['POST'])
def move():
    path = request.form.get('path') or ''
    dest_folder = (request.form.get('dest_folder') or '').strip('/')
    try:
        src = csv_safe_join(path)
        dest_dir = csv_safe_join(dest_folder)
        if not os.path.isfile(src) or not src.lower().endswith('.csv'):
            flash('Only CSV files can be moved', 'danger')
            return redirect(url_for('manage_files'))
        os.makedirs(dest_dir, exist_ok=True)
        shutil.move(src, os.path.join(dest_dir, os.path.basename(src)))
        flash('CSV moved', 'success')
    except Exception:
        app.logger.exception('Move failed')
        flash('Move failed', 'danger')
    return redirect(url_for('manage_files', path=dest_folder))


@app.route('/clear/<path:filename>', methods=['POST'])
def clear_csv(filename):
    try:
        full = csv_safe_join(filename)
    except ValueError:
        flash('Invalid filename', 'danger')
        return redirect(url_for('manage_files'))

    if not os.path.isfile(full) or not full.lower().endswith('.csv'):
        flash('CSV not found', 'danger')
        return redirect(url_for('manage_files'))

    try:
        header_row = ''
        with open(full, 'r', encoding='utf-8', newline='') as fh:
            first_line = fh.readline()
            if first_line:
                header_row = first_line.rstrip('\r\n')

        with open(full, 'w', encoding='utf-8', newline='') as fh:
            if header_row:
                fh.write(header_row + '\n')
        flash('CSV cleared (header kept)', 'success')
    except Exception:
        app.logger.exception('clear_csv failed')
        flash('Failed to clear CSV', 'danger')

    return redirect(url_for('edit_csv', filename=filename))


@app.route('/delete', methods=['POST'])
def delete_item():
    path = (request.form.get('path') or '').strip('/')
    back_path = (request.form.get('back_path') or '').strip('/')
    try:
        target = csv_safe_join(path)
    except ValueError:
        flash('Invalid path', 'danger')
        return redirect(url_for('manage_files', path=back_path))

    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
            flash('Folder deleted', 'success')
        elif os.path.isfile(target) and target.lower().endswith('.csv'):
            os.remove(target)
            flash('CSV deleted', 'success')
        else:
            flash('Item not found', 'danger')
    except Exception:
        app.logger.exception('delete failed')
        flash('Delete failed', 'danger')

    return redirect(url_for('manage_files', path=back_path))


if __name__ == '__main__':
    ensure_csv_root_and_move_existing()
    port = int(os.getenv('PORT', os.getenv('LIBRO_PORT', '5000')))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port)
