using System.Data;
using System.Diagnostics;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace StudentIdManagerForLibro;

public class MainForm : Form
{
    private const string CsvFileName = "students.csv";
    private const string AttendanceFileName = "Attendance.py";

    private readonly string _rootDir;
    private readonly string _csvPath;
    private readonly string _attendancePath;

    private readonly DataGridView _grid = new();
    private readonly TextBox _txtSearch = new();
    private readonly TextBox _txtId = new();
    private readonly TextBox _txtName = new();
    private readonly TextBox _txtGrade = new();
    private readonly TextBox _txtSection = new();
    private readonly Label _lblCount = new();

    private readonly DataTable _table = new("students");
    private readonly DataView _view;

    public MainForm()
    {
        _rootDir = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", ".."));
        _csvPath = Path.Combine(_rootDir, CsvFileName);
        _attendancePath = Path.Combine(_rootDir, AttendanceFileName);
        _view = new DataView(_table);

        SetupWindow();
        SetupData();
        BuildLayout();
        LoadRecords();
    }

    private void SetupWindow()
    {
        Text = "Student ID Manager for LIBRO (Beta)";
        Width = 1200;
        Height = 780;
        MinimumSize = new Size(1000, 680);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = ColorTranslator.FromHtml("#f5f6fb");
    }

    private void SetupData()
    {
        _table.Columns.Add("Student ID", typeof(string));
        _table.Columns.Add("Name", typeof(string));
        _table.Columns.Add("Grade", typeof(string));
        _table.Columns.Add("Section", typeof(string));
    }

    private void BuildLayout()
    {
        var header = CardPanel();
        header.Dock = DockStyle.Top;
        header.Height = 90;
        Controls.Add(header);

        var title = new Label
        {
            Text = "Student ID Manager for LIBRO (Beta)",
            Font = new Font("Segoe UI", 17, FontStyle.Bold),
            ForeColor = ColorTranslator.FromHtml("#111827"),
            AutoSize = true,
            Location = new Point(16, 14),
            BackColor = Color.White
        };
        header.Controls.Add(title);

        var subtitle = new Label
        {
            Text = "Desktop app to add, remove, and organize students then sync Attendance.py",
            Font = new Font("Segoe UI", 10),
            ForeColor = ColorTranslator.FromHtml("#6b7280"),
            AutoSize = true,
            Location = new Point(18, 50),
            BackColor = Color.White
        };
        header.Controls.Add(subtitle);

        var body = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12, 12, 12, 12), BackColor = BackColor };
        Controls.Add(body);

        var left = CardPanel();
        left.Dock = DockStyle.Fill;
        left.Padding = new Padding(12);
        body.Controls.Add(left);

        var right = CardPanel();
        right.Dock = DockStyle.Right;
        right.Width = 360;
        right.Padding = new Padding(12);
        body.Controls.Add(right);

        var searchLabel = new Label { Text = "Search", AutoSize = true, Font = new Font("Segoe UI", 10, FontStyle.Bold), BackColor = Color.White };
        left.Controls.Add(searchLabel);
        _txtSearch.Top = 26;
        _txtSearch.Left = 0;
        _txtSearch.Width = 420;
        _txtSearch.TextChanged += (_, _) => ApplyFilter();
        left.Controls.Add(_txtSearch);

        _lblCount.AutoSize = true;
        _lblCount.Font = new Font("Segoe UI", 9);
        _lblCount.ForeColor = ColorTranslator.FromHtml("#6b7280");
        _lblCount.BackColor = Color.White;
        _lblCount.Left = 440;
        _lblCount.Top = 30;
        left.Controls.Add(_lblCount);

        _grid.Top = 62;
        _grid.Left = 0;
        _grid.Width = left.Width - 24;
        _grid.Height = left.Height - 74;
        _grid.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
        _grid.AutoGenerateColumns = true;
        _grid.DataSource = _view;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.MultiSelect = false;
        _grid.ReadOnly = true;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.BackgroundColor = Color.White;
        _grid.BorderStyle = BorderStyle.FixedSingle;
        _grid.RowHeadersVisible = false;
        _grid.CellClick += (_, _) => FillFromSelected();
        left.Controls.Add(_grid);

        int y = 10;
        right.Controls.Add(FieldLabel("Student ID", y)); y += 22;
        right.Controls.Add(FieldBox(_txtId, y)); y += 42;
        right.Controls.Add(FieldLabel("Name", y)); y += 22;
        right.Controls.Add(FieldBox(_txtName, y)); y += 42;
        right.Controls.Add(FieldLabel("Grade", y)); y += 22;
        right.Controls.Add(FieldBox(_txtGrade, y)); y += 42;
        right.Controls.Add(FieldLabel("Section", y)); y += 22;
        right.Controls.Add(FieldBox(_txtSection, y)); y += 50;

        right.Controls.Add(ButtonAt("Add / Update", y, OnAddOrUpdate, true)); y += 38;
        right.Controls.Add(ButtonAt("Remove Selected", y, OnRemoveSelected)); y += 38;
        right.Controls.Add(ButtonAt("Clear Form", y, (_, _) => ClearForm())); y += 38;
        right.Controls.Add(ButtonAt("Sort by ID", y, (_, _) => SortById())); y += 48;
        right.Controls.Add(ButtonAt("Save students.csv", y, (_, _) => SaveCsv())); y += 38;
        right.Controls.Add(ButtonAt("Sync Attendance.py", y, (_, _) => SyncAttendance())); y += 38;
        right.Controls.Add(ButtonAt("Save + Sync", y, (_, _) => { SaveCsv(); SyncAttendance(); }, true)); y += 38;
        right.Controls.Add(ButtonAt("Commit + Push (Git)", y, (_, _) => CommitPush())); y += 44;

        var note = new Label
        {
            Text = "Workflow: update records -> Save + Sync -> Commit + Push.",
            AutoSize = false,
            Width = 320,
            Height = 44,
            Left = 12,
            Top = y,
            BackColor = Color.White,
            ForeColor = ColorTranslator.FromHtml("#6b7280"),
            Font = new Font("Segoe UI", 9)
        };
        right.Controls.Add(note);
    }

    private Panel CardPanel() => new()
    {
        BackColor = Color.White,
        Padding = new Padding(10),
        Margin = new Padding(0)
    };

    private Label FieldLabel(string text, int top) => new()
    {
        Text = text,
        Left = 12,
        Top = top,
        Width = 120,
        AutoSize = false,
        Font = new Font("Segoe UI", 10, FontStyle.Bold),
        BackColor = Color.White
    };

    private Control FieldBox(TextBox box, int top)
    {
        box.Left = 12;
        box.Top = top;
        box.Width = 320;
        return box;
    }

    private Button ButtonAt(string text, int top, EventHandler onClick, bool primary = false)
    {
        var b = new Button
        {
            Text = text,
            Left = 12,
            Top = top,
            Width = 320,
            Height = 32,
            FlatStyle = FlatStyle.Flat,
            Font = new Font("Segoe UI", 9, FontStyle.Bold),
            BackColor = primary ? ColorTranslator.FromHtml("#8a1538") : ColorTranslator.FromHtml("#eef1f7"),
            ForeColor = primary ? Color.White : ColorTranslator.FromHtml("#111827")
        };
        b.FlatAppearance.BorderColor = ColorTranslator.FromHtml("#dce2ee");
        b.Click += onClick;
        return b;
    }

    private void LoadRecords()
    {
        _table.Rows.Clear();
        if (File.Exists(_csvPath))
        {
            foreach (var rec in ReadCsv(_csvPath))
                _table.Rows.Add(rec.StudentId, rec.Name, rec.Grade, rec.Section);
        }
        UpdateCount();
    }

    private static IEnumerable<StudentRecord> ReadCsv(string path)
    {
        using var sr = new StreamReader(path, Encoding.UTF8);
        string? line = sr.ReadLine();
        while ((line = sr.ReadLine()) is not null)
        {
            var cells = SplitCsv(line);
            if (cells.Count < 2) continue;
            yield return new StudentRecord(
                cells.ElementAtOrDefault(0) ?? "",
                cells.ElementAtOrDefault(1) ?? "",
                cells.ElementAtOrDefault(2) ?? "",
                cells.ElementAtOrDefault(3) ?? ""
            );
        }
    }

    private static List<string> SplitCsv(string line)
    {
        var outList = new List<string>();
        var sb = new StringBuilder();
        bool inQuotes = false;
        for (int i = 0; i < line.Length; i++)
        {
            char c = line[i];
            if (c == '"' && (i == 0 || line[i - 1] != '\\'))
            {
                inQuotes = !inQuotes;
            }
            else if (c == ',' && !inQuotes)
            {
                outList.Add(sb.ToString().Trim().Trim('"'));
                sb.Clear();
            }
            else
            {
                sb.Append(c);
            }
        }
        outList.Add(sb.ToString().Trim().Trim('"'));
        return outList;
    }

    private void ApplyFilter()
    {
        string q = _txtSearch.Text.Trim().Replace("'", "''");
        _view.RowFilter = string.IsNullOrWhiteSpace(q)
            ? ""
            : $"[Student ID] LIKE '%{q}%' OR [Name] LIKE '%{q}%' OR [Section] LIKE '%{q}%'";
        UpdateCount();
    }

    private void UpdateCount() => _lblCount.Text = $"{_view.Count} records";

    private void FillFromSelected()
    {
        if (_grid.CurrentRow?.DataBoundItem is not DataRowView row) return;
        _txtId.Text = row["Student ID"].ToString();
        _txtName.Text = row["Name"].ToString();
        _txtGrade.Text = row["Grade"].ToString();
        _txtSection.Text = row["Section"].ToString();
    }

    private void ClearForm()
    {
        _txtId.Text = "";
        _txtName.Text = "";
        _txtGrade.Text = "";
        _txtSection.Text = "";
    }

    private void OnAddOrUpdate(object? sender, EventArgs e)
    {
        var sid = _txtId.Text.Trim();
        var name = _txtName.Text.Trim();
        var grade = _txtGrade.Text.Trim();
        var section = _txtSection.Text.Trim();
        if (string.IsNullOrWhiteSpace(sid) || string.IsNullOrWhiteSpace(name))
        {
            MessageBox.Show("Student ID and Name are required.", "Missing data", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var existing = _table.AsEnumerable()
            .FirstOrDefault(r => string.Equals((r["Student ID"]?.ToString() ?? ""), sid, StringComparison.OrdinalIgnoreCase));
        if (existing is null)
        {
            _table.Rows.Add(sid, name, grade, section);
        }
        else
        {
            existing["Student ID"] = sid;
            existing["Name"] = name;
            existing["Grade"] = grade;
            existing["Section"] = section;
        }
        SortById();
        ApplyFilter();
    }

    private void OnRemoveSelected(object? sender, EventArgs e)
    {
        if (_grid.CurrentRow?.DataBoundItem is not DataRowView row)
        {
            MessageBox.Show("Select a row first.", "No selection", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }
        var sid = row["Student ID"]?.ToString() ?? "";
        if (MessageBox.Show($"Remove student ID {sid}?", "Confirm", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            return;
        row.Delete();
        ApplyFilter();
        ClearForm();
    }

    private void SortById()
    {
        var sorted = _table.AsEnumerable()
            .OrderBy(r => (r["Student ID"]?.ToString() ?? "").ToLowerInvariant())
            .CopyToDataTable();
        _table.Clear();
        foreach (DataRow r in sorted.Rows) _table.ImportRow(r);
        ApplyFilter();
    }

    private void SaveCsv()
    {
        try
        {
            using var sw = new StreamWriter(_csvPath, false, new UTF8Encoding(false));
            sw.WriteLine("Student ID,Name,Grade,Section");
            foreach (DataRow r in _table.Rows)
            {
                var sid = CsvEscape(r["Student ID"]?.ToString() ?? "");
                var name = CsvEscape(r["Name"]?.ToString() ?? "");
                var grade = CsvEscape(r["Grade"]?.ToString() ?? "");
                var section = CsvEscape(r["Section"]?.ToString() ?? "");
                sw.WriteLine($"{sid},{name},{grade},{section}");
            }
            MessageBox.Show("Saved students.csv", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"Failed saving CSV:\n{ex.Message}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private static string CsvEscape(string value)
    {
        if (value.Contains(',') || value.Contains('"') || value.Contains('\n'))
            return "\"" + value.Replace("\"", "\"\"") + "\"";
        return value;
    }

    private void SyncAttendance()
    {
        if (!File.Exists(_attendancePath))
        {
            MessageBox.Show("Attendance.py not found.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        string text = File.ReadAllText(_attendancePath, Encoding.UTF8);
        var pattern = @"students\s*=\s*\{[\s\S]*?\}\r?\n\r?\nCSV_HEADERS";

        var sb = new StringBuilder();
        sb.AppendLine("students = {");
        foreach (DataRow r in _table.Rows)
        {
            string sid = PyString(r["Student ID"]?.ToString() ?? "");
            string name = PyString(r["Name"]?.ToString() ?? "");
            string grade = PyString(r["Grade"]?.ToString() ?? "");
            string section = PyString(r["Section"]?.ToString() ?? "");
            sb.AppendLine($"    {sid}: {{\"name\": {name}, \"grade\": {grade}, \"section\": {section}}},");
        }
        sb.AppendLine("}");
        sb.AppendLine();
        sb.Append("CSV_HEADERS");

        if (!Regex.IsMatch(text, pattern))
        {
            MessageBox.Show("Could not find students block in Attendance.py.", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        text = Regex.Replace(text, pattern, sb.ToString());
        File.WriteAllText(_attendancePath, text, new UTF8Encoding(false));
        MessageBox.Show("Attendance.py students block synced.", "Success", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private static string PyString(string value)
    {
        return "\"" + value.Replace("\\", "\\\\").Replace("\"", "\\\"") + "\"";
    }

    private void CommitPush()
    {
        SaveCsv();
        SyncAttendance();
        if (MessageBox.Show("Commit and push students update now?", "Git", MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
            return;

        var cmds = new[]
        {
            "git add students.csv Attendance.py",
            "git commit -m \"Update student IDs via desktop manager\"",
            "git pull --rebase origin main",
            "git push origin main"
        };

        var logs = new StringBuilder();
        foreach (var cmd in cmds)
        {
            var (code, output) = RunGit(cmd);
            logs.AppendLine($"> {cmd}");
            logs.AppendLine(output);
            logs.AppendLine();
            if (code != 0)
            {
                MessageBox.Show(logs.ToString(), "Git failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
        }
        MessageBox.Show("Commit and push successful.", "Git", MessageBoxButtons.OK, MessageBoxIcon.Information);
    }

    private (int exitCode, string output) RunGit(string args)
    {
        var psi = new ProcessStartInfo("powershell", $"-NoProfile -Command {args}")
        {
            WorkingDirectory = _rootDir,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        using var p = Process.Start(psi)!;
        string output = p.StandardOutput.ReadToEnd() + p.StandardError.ReadToEnd();
        p.WaitForExit();
        return (p.ExitCode, output);
    }

    private sealed record StudentRecord(string StudentId, string Name, string Grade, string Section);
}
