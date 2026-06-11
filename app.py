from flask import Flask, render_template, request, redirect, session, send_file
from config import Config
from models.db import get_db
import pandas as pd
import os

from reportlab.platypus import SimpleDocTemplate, Table
from reportlab.lib.pagesizes import A4


app = Flask(__name__)
app.config.from_object(Config)
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

        cursor.close()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]

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


@app.route('/head-dashboard')
def head_dashboard():
    if 'user_id' in session and session['role'] == 'head':
        return f"HEAD DASHBOARD - Welcome {session['username']}"
    return redirect('/login')


# ---------------- GAUGE LIST ----------------
@app.route('/gauge-list')
def gauge_list():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('gauge/gauge_list.html', gauges=data)


# ---------------- ADD GAUGE ----------------
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
            (master_key, gauge_name, gauge_type, color, department, inventory_status)
            VALUES (%s, %s, %s, %s, %s, 'ACTIVE')
        """, (master_key, gauge_name, gauge_type, color, department))

        conn.commit()
        cursor.close()
        conn.close()

        return redirect('/gauge-list')

    return render_template('gauge/add_gauge.html')


# ---------------- ACTIVE / INACTIVE ----------------
@app.route('/active-inventory')
def active_inventory():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master WHERE inventory_status='ACTIVE'")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('inventory/active.html', data=data)


@app.route('/inactive-inventory')
def inactive_inventory():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master WHERE inventory_status='INACTIVE'")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('inventory/inactive.html', data=data)


# ---------------- TOGGLE STATUS ----------------
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
    cursor.close()
    conn.close()

    return redirect('/active-inventory')


# ---------------- EXCEL EXPORT ----------------
@app.route('/download-excel-report')
def download_excel_report():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM gauge_master")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    columns = ["ID", "Master Key", "Name", "Type", "Color", "Department", "Status"]

    df = pd.DataFrame(data, columns=columns)

    file_path = os.path.join(os.getcwd(), "MIS_REPORT.xlsx")
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)