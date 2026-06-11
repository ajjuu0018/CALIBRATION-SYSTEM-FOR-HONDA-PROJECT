from flask import Flask, render_template, request, redirect, session
from config import Config
from models.db import init_db, get_db
from flask import render_template
from models.db import get_db
from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import A4
app = Flask(__name__)
app.config.from_object(Config)

init_db(app)

app.secret_key = "supersecretkey"


# ---------------- HOME ----------------
@app.route('/')
def home():
    return redirect('/login')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )

        user = cursor.fetchone()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]

            # ROLE BASED REDIRECTION
            if user[3] == 'head':
                return redirect('/head-dashboard')
            elif user[3] == 'calibration':
                return redirect('/calibration-dashboard')
            else:
                return redirect('/user-dashboard')

        return "Invalid Credentials"

    return render_template('auth/login.html')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- DASHBOARDS ----------------

@app.route('/user-dashboard')
def user_dashboard():
    if 'user_id' in session and session['role'] == 'user':
        return f"USER DASHBOARD - Welcome {session['username']}"
    return redirect('/login')


@app.route('/calibration-dashboard')
def calibration_dashboard():
    if 'user_id' in session and session['role'] == 'calibration':
        return f"CALIBRATION DASHBOARD - Welcome {session['username']}"
    return redirect('/login')

@app.route('/gauge-list')
def gauge_list():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master")
    data = cursor.fetchall()

    return render_template('gauge/gauge_list.html', gauges=data)
@app.route('/add-gauge', methods=['GET', 'POST'])
def add_gauge():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        master_key = request.form['master_key']
        gauge_name = request.form['gauge_name']
        gauge_type = request.form['gauge_type']
        color = request.form['color']
        department = request.form['department']

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO gauge_master 
            (master_key, gauge_name, gauge_type, color, department)
            VALUES (%s, %s, %s, %s, %s)
        """, (master_key, gauge_name, gauge_type, color, department))

        conn.commit()

        return redirect('/gauge-list')

    return render_template('gauge/add_gauge.html')

@app.route('/active-inventory')
def active_inventory():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master WHERE inventory_status='ACTIVE'")
    data = cursor.fetchall()

    return render_template('inventory/active.html', data=data)
 
@app.route('/inactive-inventory')
def inactive_inventory():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master WHERE inventory_status='INACTIVE'")
    data = cursor.fetchall()

    return render_template('inventory/inactive.html', data=data)

@app.route('/toggle-status/<int:id>')
def toggle_status(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT inventory_status FROM gauge_master WHERE id=%s", (id,))
    current = cursor.fetchone()[0]

    new_status = 'INACTIVE' if current == 'ACTIVE' else 'ACTIVE'

    cursor.execute("""
        UPDATE gauge_master 
        SET inventory_status=%s 
        WHERE id=%s
    """, (new_status, id))

    conn.commit()

    return redirect('/active-inventory')

@app.route('/issue-gauge/<int:id>', methods=['GET', 'POST'])
def issue_gauge(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        to_dept = request.form['to_department']

        # Get gauge info
        cursor.execute("SELECT master_key FROM gauge_master WHERE id=%s", (id,))
        gauge = cursor.fetchone()
        master_key = gauge[0]

        # Insert transaction
        cursor.execute("""
            INSERT INTO gauge_transactions 
            (gauge_id, master_key, action, from_department, to_department, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, master_key, "ISSUE", "CALIBRATION", to_dept, "ISSUED"))

        # Update inventory status
        cursor.execute("""
            UPDATE gauge_master 
            SET inventory_status='ISSUED'
            WHERE id=%s
        """, (id,))

        conn.commit()
        return redirect('/active-inventory')

    return render_template('workflow/issue.html', gauge_id=id)

@app.route('/return-gauge/<int:id>', methods=['GET', 'POST'])
def return_gauge(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        from_dept = request.form['from_department']

        cursor.execute("SELECT master_key FROM gauge_master WHERE id=%s", (id,))
        gauge = cursor.fetchone()
        master_key = gauge[0]

        cursor.execute("""
            INSERT INTO gauge_transactions 
            (gauge_id, master_key, action, from_department, to_department, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (id, master_key, "RETURN", from_dept, "CALIBRATION", "RETURNED"))

        cursor.execute("""
            UPDATE gauge_master 
            SET inventory_status='ACTIVE'
            WHERE id=%s
        """, (id,))

        conn.commit()
        return redirect('/active-inventory')

    return render_template('workflow/return.html', gauge_id=id)

@app.route('/inspect-gauge/<int:id>', methods=['GET', 'POST'])
def inspect_gauge(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        condition = request.form['condition']
        remarks = request.form['remarks']

        cursor.execute("SELECT master_key FROM gauge_master WHERE id=%s", (id,))
        gauge = cursor.fetchone()
        master_key = gauge[0]

        action_taken = ""

        if condition == "OK":
            action_taken = "SEND_TO_CALIBRATION"

        elif condition == "REPAIR":
            action_taken = "SEND_TO_REPAIR"

        else:
            action_taken = "MARK_NON_REPAIRABLE"

        cursor.execute("""
            INSERT INTO gauge_inspection 
            (gauge_id, master_key, condition_status, remarks, action_taken)
            VALUES (%s, %s, %s, %s, %s)
        """, (id, master_key, condition, remarks, action_taken))

        conn.commit()
        return redirect('/active-inventory')

    return render_template('workflow/inspect.html', gauge_id=id)

@app.route('/calibrate-gauge/<int:id>', methods=['POST'])
def calibrate_gauge(id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    result = request.form['result']
    next_due = request.form['next_due_date']

    cursor.execute("SELECT master_key FROM gauge_master WHERE id=%s", (id,))
    gauge = cursor.fetchone()
    master_key = gauge[0]

    cursor.execute("""
        INSERT INTO calibration_records
        (gauge_id, master_key, calibration_result, calibrated_by, next_due_date)
        VALUES (%s, %s, %s, %s, %s)
    """, (id, master_key, result, session['username'], next_due))

    # Update inventory status
    cursor.execute("""
        UPDATE gauge_master
        SET inventory_status='ACTIVE'
        WHERE id=%s
    """, (id,))

    conn.commit()
    return redirect('/active-inventory')

@app.route('/raise-approval/<int:id>/<request_type>')
def raise_approval(id, request_type):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT master_key FROM gauge_master WHERE id=%s", (id,))
    gauge = cursor.fetchone()
    master_key = gauge[0]

    cursor.execute("""
        INSERT INTO approvals 
        (gauge_id, master_key, request_type, request_by, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (id, master_key, request_type, session['username'], 'PENDING'))

    conn.commit()
    return redirect('/active-inventory')

@app.route('/head-dashboard')
def head_dashboard():
    if 'user_id' in session and session['role'] == 'head':
        return f"HEAD DASHBOARD - Welcome {session['username']}"
    return redirect('/login')

@app.route('/head-approvals')
def head_approvals():
    if 'user_id' not in session or session['role'] != 'head':
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM approvals WHERE status='PENDING'")
    data = cursor.fetchall()

    return render_template('workflow/approvals.html', data=data)

@app.route('/process-approval/<int:id>/<action>')
def process_approval(id, action):
    if 'user_id' not in session or session['role'] != 'head':
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    if action == "APPROVE":
        status = "APPROVED"
    else:
        status = "REJECTED"

    cursor.execute("""
        UPDATE approvals
        SET status=%s, action_taken=%s
        WHERE id=%s
    """, (status, action, id))

    conn.commit()
    return redirect('/head-approvals')

@app.route('/mis-dashboard')
def mis_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM gauge_master")
    total_gauges = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gauge_master WHERE inventory_status='ACTIVE'")
    active = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gauge_master WHERE inventory_status='INACTIVE'")
    inactive = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM approvals WHERE status='PENDING'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM gauge_transactions")
    transactions = cursor.fetchone()[0]

    return render_template(
        "reports/mis_dashboard.html",
        total=total_gauges,
        active=active,
        inactive=inactive,
        pending=pending,
        transactions=transactions
    )
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT department, COUNT(*) FROM gauge_master GROUP BY department")
    dept_data = cursor.fetchall()

    cursor.execute("SELECT color, COUNT(*) FROM gauge_master GROUP BY color")
    color_data = cursor.fetchall()

    print("DEPT DATA:", dept_data)

    return render_template(
        "reports/analytics.html",
        dept=dept_data,
        color=color_data
    )
from flask import send_file
import os

@app.route('/download-mis-report')
def download_mis_report():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master")
    gauges = cursor.fetchall()

    file_path = "MIS_REPORT.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=A4)

    data = [["ID", "Master Key", "Name", "Type", "Color", "Dept", "Status"]]

    for g in gauges:
        data.append([g[0], g[1], g[2], g[3], g[4], g[5], g[6]])

    table = Table(data)

    doc.build([table])

    return send_file(file_path, as_attachment=True)
if __name__ == "__main__":
    app.run(debug=True)