import sqlite3
import random
from faker import Faker
from datetime import date

db_name="db/hr.db"
num_employees=25

fake=Faker()

conn=sqlite3.connect(db_name)
cursor=conn.cursor()

# Create tables
# -----------------------------
cursor.executescript("""
CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    role TEXT NOT NULL,
    joining_date DATE NOT NULL,
    employment_type TEXT NOT NULL
);

CREATE TABLE leave_types (
    leave_type TEXT PRIMARY KEY,
    description TEXT,
    annual_quota INTEGER NOT NULL
);

CREATE TABLE leave_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    leave_type TEXT NOT NULL,
    total_allowed INTEGER NOT NULL,
    used INTEGER NOT NULL,
    remaining INTEGER NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    FOREIGN KEY (leave_type) REFERENCES leave_types(leave_type)
);

CREATE TABLE leave_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT NOT NULL,
    leave_type TEXT NOT NULL,
    days INTEGER NOT NULL,
    status TEXT NOT NULL,
    applied_on DATE NOT NULL
);
""")
leave_types = [
    ("medical", "Medical leave for illness or treatment", 12),
    ("casual", "Casual leave for personal reasons", 8),
    ("earned", "Earned leave accumulated monthly", 15),
    ("parental", "Leave for maternity/paternity", 180),
]


cursor.executemany("""
INSERT INTO leave_types (leave_type, description, annual_quota)
VALUES (?, ?, ?)
""", leave_types)

departments = ["Engineering", "HR", "Finance", "Marketing", "Operations"]
roles = ["Software Engineer", "Analyst", "Manager", "Executive", "HR Partner"]

employees = []

for i in range(1, num_employees + 1):
    emp_id = f"EMP{i:03d}"
    employees.append((
        emp_id,
        fake.name(),
        random.choice(departments),
        random.choice(roles),
        fake.date_between(start_date="-3y", end_date="today"),
        "Full-time"
    ))

cursor.executemany("""
INSERT INTO employees (
    employee_id, name, department, role, joining_date, employment_type
) VALUES (?, ?, ?, ?, ?, ?)
""", employees)

for emp in employees:
    emp_id = emp[0]

    for leave_type, _, quota in leave_types:
        used = random.randint(0, quota // 2)
        remaining = quota - used

        cursor.execute("""
        INSERT INTO leave_balances (
            employee_id, leave_type, total_allowed, used, remaining
        ) VALUES (?, ?, ?, ?, ?)
        """, (emp_id, leave_type, quota, used, remaining))

conn.commit()
conn.close()

print("✅ HR database created and seeded successfully!")