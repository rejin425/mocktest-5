from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector
import os
import PyPDF2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback-secret")

# ---------------------------
# DATABASE CONNECTION FUNCTION
# ---------------------------
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME")
    )

# ---------------------------
# HOME
# ---------------------------
@app.route('/')
def home():
    return render_template("index.html")

# ---------------------------
# REGISTER
# ---------------------------
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']

    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",
                (username, hashed_password, 'student'))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/')

# ---------------------------
# LOGIN
# ---------------------------
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['role'] = user[3]

        if user[3] == 'admin':
            return redirect('/admin_dashboard')
        else:
            return redirect('/student_dashboard')

    return "Invalid Credentials"

# ---------------------------
# ADMIN DASHBOARD
# ---------------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/')
    return render_template("admin_dashboard.html")

# ---------------------------
# STUDENT DASHBOARD
# ---------------------------
@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect('/')
    return render_template("student_dashboard.html")

# ---------------------------
# UPLOAD PDF
# ---------------------------
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if session.get('role') != 'admin':
        return redirect('/')

    file = request.files['pdf']
    pdf_reader = PyPDF2.PdfReader(file)

    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    lines = text.split("\n")

    conn = get_db_connection()
    cur = conn.cursor()

    question = ""
    options = []
    answer_key = {}

    for line in lines:
        line = line.strip()

        if line.lower().startswith("answer"):
            continue

        if line and line[0].isdigit() and "." in line:
            if question and len(options) == 4:
                q_no = question.split(".")[0]
                correct = answer_key.get(q_no, "")

                cur.execute("""
                    INSERT INTO questions
                    (question,option_a,option_b,option_c,option_d,correct_answer)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (question, options[0], options[1], options[2], options[3], correct))

            question = line
            options = []

        elif line.startswith("A") or line.startswith("B") or line.startswith("C") or line.startswith("D"):
            options.append(line)

        elif ":" in line:
            parts = line.split(":")
            if len(parts) == 2:
                answer_key[parts[0].strip()] = parts[1].strip()

    # Insert last question
    if question and len(options) == 4:
        q_no = question.split(".")[0]
        correct = answer_key.get(q_no, "")

        cur.execute("""
            INSERT INTO questions
            (question,option_a,option_b,option_c,option_d,correct_answer)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (question, options[0], options[1], options[2], options[3], correct))

    conn.commit()
    cur.close()
    conn.close()

    return "PDF Uploaded Successfully"

# ---------------------------
# RESULTS (ADMIN ONLY)
# ---------------------------
@app.route('/results')
def results():
    if session.get('role') != 'admin':
        return redirect('/')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM results")
    data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("results.html", data=data)

# ---------------------------
# LOGOUT
# ---------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ---------------------------
# RENDER PORT BINDING
# ---------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
