📚 LIBRO – Library Attendance System
📖 Introduction

LIBRO is a server-based Library Attendance System developed to streamline and modernize student attendance monitoring inside the school library.
This system was designed to replace manual logbooks with a faster, more organized, and digitally recorded process.
LIBRO focuses on simplicity, efficiency, and controlled access to attendance records.

⚙️ How the System Works
1️⃣ Student Check-In (Kiosk System)

Students scan their Student ID barcode using the kiosk interface.
Once scanned, the system automatically records:
* Student ID
* Time In & Time Out
* Purpose of Visit

The data is saved into a daily CSV file inside the csv_files folder.
Each day generates a new attendance file.

2️⃣ Web-Based CSV Manager

The system includes a Flask-based web server that:

Reads all files inside the csv_files folder

Dynamically displays the available attendance logs

Allows authorized personnel to view and download records

The project is deployed using GitHub for version control and Render for cloud hosting, allowing centralized access to attendance records through a secure web interface.

🎯 Purpose of the Project

LIBRO was created to:
Eliminate manual attendance logging
Improve accuracy of student records
Provide organized digital documentation
Allow librarians and administrators easy access to reports
The system is file-based and lightweight, making it easy to maintain and deploy.

⚠️ IMPORTANT NOTICE

THIS IS A PHILIPPINE SCHOOL BAHRAIN CAPSTONE PROJECT FROM STUDENTS OF 12-MAPAGPALAYA.

THIS PROJECT IS NOT FOR PUBLIC USE BUT ONLY WITHIN THE USE OF THE SCHOOL LIBRARIAN AND THE PHILIPPINE SCHOOL ADMINISTRATORS.

Unauthorized use, distribution, modification, replication, or public deployment of this system is strictly prohibited.

📌 Closing Statement

LIBRO represents the application of practical programming, system deployment, and real-world problem solving in an academic environment.

This project demonstrates how simple technologies can be used to create efficient and scalable solutions for institutional needs.
