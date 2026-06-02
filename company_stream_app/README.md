# Fab Stream Business Platform

Fab Stream is a Flask web application for company communication, employee management, reports, tasks, and internal updates.

## What The Web App Does

- Lets employees register, log in, and view their personal dashboard.
- Gives each user a profile page with account details, assigned tasks, direct messages, and reports.
- Lets admins and managers publish company announcements.
- Lets admins and managers manage departments and add employees.
- Lets admins and managers send direct messages and assign employee tasks.
- Lets admins and managers upload report documents to specific employees.
- Provides a department chat area for admin and manager users.

## Main Pages

- `/` - Home page.
- `/login` - User login page.
- `/register` - New account registration page.
- `/dashboard` - User dashboard.
- `/manager-dashboard` - Admin/manager announcements dashboard.
- `/departments` - Department and employee management.
- `/reports` - Report upload and report list.
- `/chat` - Department chat.
- `/employees/<id>` - Employee profile, tasks, messages, and reports.

## Admin Access

Admin features are available only to users whose role is:

- `admin`
- `manager`

Current admin-only features include departments, reports, department chat, employee creation, task assignment, and direct messages.

The current local database does not contain an admin user yet. It contains employee accounts only, so none of those accounts can open the admin-only pages until one is promoted.

To make an existing user an admin, update the user's role in the SQLite database:

```powershell
python -c "import sqlite3; con=sqlite3.connect('instance/company.db'); con.execute(\"update user set role='admin' where email='USER_EMAIL_HERE'\"); con.commit(); con.close()"
```

Run that command from inside the `company_stream_app` folder and replace `USER_EMAIL_HERE` with the email of the account you want to promote.

## How To Run

Install the dependencies:

```powershell
pip install -r requirements.txt
```

Start the web app:

```powershell
python run.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-Bcrypt
- Flask-WTF
- Flask-SocketIO
- SQLite
- Bootstrap
