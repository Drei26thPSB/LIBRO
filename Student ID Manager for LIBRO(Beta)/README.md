# Student ID Manager for LIBRO (Beta)

Windows desktop app (C# WinForms) for yearly student ID maintenance.

## What it does

- Add, update, remove, search, and sort student records.
- Saves records to `students.csv` in LIBRO root.
- Syncs the `students = { ... }` block in `Attendance.py`.
- Optional: `Commit + Push (Git)` for your deployment flow.

## Requirement

Install .NET SDK 8.0 (or newer):

https://dotnet.microsoft.com/download

## Run

From LIBRO root:

```powershell
dotnet run --project "Student ID Manager for LIBRO(Beta)\StudentIDManager.csproj"
```

## Build EXE

```powershell
dotnet publish "Student ID Manager for LIBRO(Beta)\StudentIDManager.csproj" -c Release -r win-x64 --self-contained false
```

Published output:

`Student ID Manager for LIBRO(Beta)\bin\Release\net8.0-windows\win-x64\publish\`
