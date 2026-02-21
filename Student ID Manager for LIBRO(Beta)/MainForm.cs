using System.Data;
using System.Diagnostics;
using System.Drawing.Drawing2D;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace StudentIdManagerForLibro;

public class MainForm : Form
{
    private static readonly Color CBg = ColorTranslator.FromHtml("#f6f7fb");
    private static readonly Color CSurface = ColorTranslator.FromHtml("#ffffff");
    private static readonly Color CSurfaceSoft = ColorTranslator.FromHtml("#f8f9fd");
    private static readonly Color CLine = ColorTranslator.FromHtml("#dce2f0");
    private static readonly Color CText = ColorTranslator.FromHtml("#1b1f2a");
    private static readonly Color CMuted = ColorTranslator.FromHtml("#56607a");
    private static readonly Color CPrimary = ColorTranslator.FromHtml("#8a1538");
    private static readonly Color CPrimaryHover = ColorTranslator.FromHtml("#73112f");
    private static readonly Color CAccent = ColorTranslator.FromHtml("#a3204b");

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
    private readonly TreeView _folderTree = new();
    private string _selectedGrade = "";
    private string _selectedSection = "";

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
        Width = 1240;
        Height = 800;
        MinimumSize = new Size(1080, 700);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = CBg;
        Font = new Font("Segoe UI", 10);
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
        var header = GradientHeaderPanel();
        header.Dock = DockStyle.Top;
        header.Height = 102;
        Controls.Add(header);

        var title = new Label
        {
            Text = "Student ID Manager for LIBRO (Beta)",
            Font = new Font("Segoe UI", 17, FontStyle.Bold),
            ForeColor = Color.White,
            AutoSize = true,
            Location = new Point(16, 14),
            BackColor = Color.Transparent
        };
        header.Controls.Add(title);

        var subtitle = new Label
        {
            Text = "Reads from Attendance.py and organizes students by Grade and Section folders",
            Font = new Font("Segoe UI", 10),
            ForeColor = ColorTranslator.FromHtml("#f6d9e4"),
            AutoSize = true,
            Location = new Point(18, 50),
            BackColor = Color.Transparent
        };
        header.Controls.Add(subtitle);

        var body = new Panel { Dock = DockStyle.Fill, Padding = new Padding(12), BackColor = CBg };
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

        var split = new SplitContainer
        {
            Dock = DockStyle.Fill,
            Orientation = Orientation.Vertical,
            SplitterDistance = 260,
            BorderStyle = BorderStyle.None,
            BackColor = CSurface
        };
        left.Controls.Add(split);

        var folderPanel = new Panel { Dock = DockStyle.Fill, BackColor = CSurface };
        split.Panel1.Controls.Add(folderPanel);
        var foldersTitle = new Label
        {
            Text = "Folders (Grade / Section)",
            AutoSize = true,
            Font = new Font("Segoe UI", 10, FontStyle.Bold),
            BackColor = CSurface,
            ForeColor = CText,
            Left = 0,
            Top = 0
        };
        folderPanel.Controls.Add(foldersTitle);

        _folderTree.Left = 0;
        _folderTree.Top = 26;
        _folderTree.Width = split.Panel1.Width - 8;
        _folderTree.Height = split.Panel1.Height - 30;
        _folderTree.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
        _folderTree.BorderStyle = BorderStyle.FixedSingle;
        _folderTree.BackColor = CSurfaceSoft;
        _folderTree.ForeColor = CText;
        _folderTree.AfterSelect += (_, _) => OnFolderSelected();
        folderPanel.Controls.Add(_folderTree);

        var listPanel = new Panel { Dock = DockStyle.Fill, BackColor = CSurface };
        split.Panel2.Controls.Add(listPanel);

        var searchLabel = new Label { Text = "Search", AutoSize = true, Font = new Font("Segoe UI", 10, FontStyle.Bold), BackColor = CSurface, ForeColor = CText };
        listPanel.Controls.Add(searchLabel);

        _txtSearch.Top = 26;
        _txtSearch.Left = 0;
        _txtSearch.Width = 420;
        StyleTextBox(_txtSearch);
        _txtSearch.TextChanged += (_, _) => ApplyFilter();
        listPanel.Controls.Add(_txtSearch);

        _lblCount.AutoSize = true;
        _lblCount.Font = new Font("Segoe UI", 9);
        _lblCount.ForeColor = CMuted;
        _lblCount.BackColor = CSurface;
        _lblCount.Left = 440;
        _lblCount.Top = 30;
        listPanel.Controls.Add(_lblCount);

        _grid.Top = 62;
        _grid.Left = 0;
        _grid.Width = listPanel.Width - 8;
        _grid.Height = listPanel.Height - 68;
        _grid.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right;
        _grid.AutoGenerateColumns = true;
        _grid.DataSource = _view;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.MultiSelect = false;
        _grid.ReadOnly = true;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.BackgroundColor = CSurface;
        _grid.BorderStyle = BorderStyle.None;
        _grid.RowHeadersVisible = false;
        _grid.GridColor = CLine;
        _grid.ColumnHeadersDefaultCellStyle.BackColor = CSurfaceSoft;
        _grid.ColumnHeadersDefaultCellStyle.ForeColor = CText;
        _grid.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI", 9, FontStyle.Bold);
        _grid.EnableHeadersVisualStyles = false;
        _grid.DefaultCellStyle.BackColor = CSurface;
        _grid.DefaultCellStyle.ForeColor = CText;
        _grid.DefaultCellStyle.SelectionBackColor = ColorTranslator.FromHtml("#f3d5e1");
        _grid.DefaultCellStyle.SelectionForeColor = CText;
        _grid.AlternatingRowsDefaultCellStyle.BackColor = ColorTranslator.FromHtml("#fbfcff");
        _grid.CellClick += (_, _) => FillFromSelected();
        listPanel.Controls.Add(_grid);

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
            Text = "Workflow: organize by folders -> Save + Sync -> Commit + Push.",
            AutoSize = false,
            Width = 320,
            Height = 44,
            Left = 12,
            Top = y,
            BackColor = CSurface,
            ForeColor = CMuted,
            Font = new Font("Segoe UI", 9)
        };
        right.Controls.Add(note);
    }

    private Panel CardPanel() => new()
    {
        BackColor = CSurface,
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
        BackColor = CSurface,
        ForeColor = CText
    };

    private Control FieldBox(TextBox box, int top)
    {
        box.Left = 12;
        box.Top = top;
        box.Width = 320;
        StyleTextBox(box);
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
            BackColor = primary ? CPrimary : CSurfaceSoft,
            ForeColor = primary ? Color.White : CText
        };
        b.FlatAppearance.BorderColor = CLine;
        b.FlatAppearance.MouseOverBackColor = primary ? CPrimaryHover : ColorTranslator.FromHtml("#eef2fb");
        b.FlatAppearance.MouseDownBackColor = primary ? CPrimaryHover : ColorTranslator.FromHtml("#e8edf8");
        b.Click += onClick;
        return b;
    }

    private void StyleTextBox(TextBox box)
    {
        box.BorderStyle = BorderStyle.FixedSingle;
        box.BackColor = CSurfaceSoft;
        box.ForeColor = CText;
        box.Font = new Font("Segoe UI", 10);
    }

    private Panel GradientHeaderPanel()
    {
        var panel = new Panel { BackColor = CPrimary };
        panel.Paint += (_, e) =>
        {
            using var brush = new LinearGradientBrush(panel.ClientRectangle, CPrimary, CAccent, LinearGradientMode.ForwardDiagonal);
            e.Graphics.FillRectangle(brush, panel.ClientRectangle);
            using var pen = new Pen(ColorTranslator.FromHtml("#651028"));
            e.Graphics.DrawLine(pen, 0, panel.Height - 1, panel.Width, panel.Height - 1);
        };
        return panel;
    }

    private void LoadRecords()
    {
        _table.Rows.Clear();
        List<StudentRecord> records = [];
        if (File.Exists(_csvPath))
        {
            records = ReadCsv(_csvPath).ToList();
        }
        if (records.Count == 0 && File.Exists(_attendancePath))
        {
            records = ReadFromAttendancePy(_attendancePath).ToList();
        }
        foreach (var rec in records)
        {
            _table.Rows.Add(rec.StudentId, rec.Name, rec.Grade, rec.Section);
        }
        SortById(silent: true);
        RebuildFolders();
        ApplyFilter();
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

    private static IEnumerable<StudentRecord> ReadFromAttendancePy(string path)
    {
        string text = File.ReadAllText(path, Encoding.UTF8);
        int start = text.IndexOf("students = {", StringComparison.Ordinal);
        int end = text.IndexOf("\n\nCSV_HEADERS", start, StringComparison.Ordinal);
        if (start < 0 || end < 0) yield break;
        string block = text[start..end];

        var linePattern = new Regex(
            "\"(?<sid>[^\"]+)\"\\s*:\\s*\\{\"name\"\\s*:\\s*\"(?<name>[^\"]*)\"\\s*,\\s*\"grade\"\\s*:\\s*\"(?<grade>[^\"]*)\"\\s*,\\s*\"section\"\\s*:\\s*\"(?<section>[^\"]*)\"\\s*\\}",
            RegexOptions.Compiled);

        foreach (Match m in linePattern.Matches(block))
        {
            yield return new StudentRecord(
                m.Groups["sid"].Value,
                m.Groups["name"].Value,
                m.Groups["grade"].Value,
                m.Groups["section"].Value
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

    private void RebuildFolders()
    {
        _folderTree.BeginUpdate();
        _folderTree.Nodes.Clear();

        var allNode = new TreeNode("All Students")
        {
            Tag = new FolderFilter("", "")
        };
        _folderTree.Nodes.Add(allNode);

        var rows = _table.AsEnumerable().ToList();
        var gradeGroups = rows
            .GroupBy(r => (r["Grade"]?.ToString() ?? "").Trim())
            .OrderBy(g => g.Key, StringComparer.OrdinalIgnoreCase);

        foreach (var gradeGroup in gradeGroups)
        {
            string grade = string.IsNullOrWhiteSpace(gradeGroup.Key) ? "No Grade" : gradeGroup.Key;
            var gradeNode = new TreeNode($"Grade {grade} ({gradeGroup.Count()})")
            {
                Tag = new FolderFilter(gradeGroup.Key, "")
            };

            var sectionGroups = gradeGroup
                .GroupBy(r => (r["Section"]?.ToString() ?? "").Trim())
                .OrderBy(g => g.Key, StringComparer.OrdinalIgnoreCase);

            foreach (var sectionGroup in sectionGroups)
            {
                string section = string.IsNullOrWhiteSpace(sectionGroup.Key) ? "No Section" : sectionGroup.Key;
                var sectionNode = new TreeNode($"{section} ({sectionGroup.Count()})")
                {
                    Tag = new FolderFilter(gradeGroup.Key, sectionGroup.Key)
                };
                gradeNode.Nodes.Add(sectionNode);
            }

            _folderTree.Nodes.Add(gradeNode);
        }

        allNode.Expand();
        _folderTree.SelectedNode = allNode;
        _folderTree.EndUpdate();
    }

    private void OnFolderSelected()
    {
        if (_folderTree.SelectedNode?.Tag is FolderFilter filter)
        {
            _selectedGrade = filter.Grade;
            _selectedSection = filter.Section;
        }
        else
        {
            _selectedGrade = "";
            _selectedSection = "";
        }
        ApplyFilter();
    }

    private void ApplyFilter()
    {
        var clauses = new List<string>();

        if (!string.IsNullOrWhiteSpace(_selectedGrade))
        {
            string grade = _selectedGrade.Replace("'", "''");
            clauses.Add($"[Grade] = '{grade}'");
        }
        if (!string.IsNullOrWhiteSpace(_selectedSection))
        {
            string section = _selectedSection.Replace("'", "''");
            clauses.Add($"[Section] = '{section}'");
        }

        string q = _txtSearch.Text.Trim().Replace("'", "''");
        if (!string.IsNullOrWhiteSpace(q))
        {
            clauses.Add($"([Student ID] LIKE '%{q}%' OR [Name] LIKE '%{q}%' OR [Section] LIKE '%{q}%')");
        }

        _view.RowFilter = string.Join(" AND ", clauses);
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
        SortById(silent: true);
        RebuildFolders();
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
        SortById(silent: true);
        RebuildFolders();
        ApplyFilter();
        ClearForm();
    }

    private void SortById(bool silent = false)
    {
        var sortedRows = _table.AsEnumerable()
            .OrderBy(r => (r["Student ID"]?.ToString() ?? "").ToLowerInvariant())
            .ToList();
        _table.Rows.Clear();
        foreach (var row in sortedRows)
        {
            _table.Rows.Add(
                row["Student ID"]?.ToString() ?? "",
                row["Name"]?.ToString() ?? "",
                row["Grade"]?.ToString() ?? "",
                row["Section"]?.ToString() ?? ""
            );
        }
        if (!silent)
        {
            RebuildFolders();
            ApplyFilter();
        }
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
    private sealed record FolderFilter(string Grade, string Section);
}
