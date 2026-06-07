from app import create_app, db
from sqlalchemy import text
import sys

app = create_app()
with app.app_context():
    f = open('migration_check_output.txt', 'w')
    
    # Check alembic version
    try:
        result = db.session.execute(text('SELECT version_num FROM alembic_version')).fetchone()
        f.write(f"Alembic version: {result[0] if result else 'None'}\n")
    except Exception as e:
        f.write(f"No alembic_version table: {e}\n")
    
    # Check if manager_id exists in department table
    try:
        cols = db.session.execute(text('PRAGMA table_info(department)')).fetchall()
        f.write("Department columns:\n")
        for col in cols:
            f.write(f"  {col}\n")
    except Exception as e:
        f.write(f"Error checking department: {e}\n")
    
    f.close()