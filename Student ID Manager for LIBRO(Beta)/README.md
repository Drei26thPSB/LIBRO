# Student ID Manager for LIBRO (Beta)

Standalone desktop app for yearly student ID maintenance.

## What it does

- Add, update, remove, search, and sort student records.
- Saves records to `students.csv` in the LIBRO root.
- Syncs the `students = { ... }` block inside `Attendance.py`.
- Optional: `Commit + Push` for automatic Render redeploy workflow.

## Run

From LIBRO root:

```powershell
py "Student ID Manager for LIBRO(Beta)\StudentIDManager.py"
```

## Safe workflow

1. Update student records in the app.
2. Click `Save + Sync`.
3. Test locally.
4. Click `Commit + Push (Git)` when ready.

## Notes

- `Student ID` and `Name` are required.
- `Grade` and `Section` are optional but recommended.
- If `students.csv` does not exist yet, the app tries to import current students from `Attendance.py`.
