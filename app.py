import os
import pymysql
import PyPDF2
from flask import Flask, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

# ---------- MYSQL CONNECTION ----------
db = pymysql.connect(
    host=os.environ.get("DB_HOST"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    database=os.environ.get("DB_NAME"),
    port=25173
)

# ---------- HOME ----------
@app.route('/')
def home():
    return '''
    <h2>Login</h2>
    <form method="post" action="/login">
        Username: <input name="username"><br><br>
        Password: <input type="password" name="password"><br><br>
        <button>Login</button>
    </form>
    <br>
    <a href="/register">Register</a>
    '''

# ---------- REGISTER ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            return "Username already exists!"

        cur.execute("INSERT INTO users (username,password,role) VALUES (%s,%s,%s)",
                    (username,password,'student'))
        db.commit()
        cur.close()

        return redirect('/')

    return '''
    <h2>Register</h2>
    <form method="post">
        Username: <input name="username"><br><br>
        Password: <input type="password" name="password"><br><br>
        <button>Register</button>
    </form>
    '''

# ---------- LOGIN ----------
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    cur.close()

    if user and check_password_hash(user[2], password):
        session['username'] = user[1]
        session['role'] = user[3]

        if user[3] == 'admin':
            return redirect('/admin')
        else:
            return redirect('/student')

    return "Invalid Login"

# ---------- ADMIN ----------
@app.route('/admin')
def admin():
    if session.get('role') == 'admin':
        return '''
        <h2>Admin Dashboard</h2>
        <a href="/upload_pdf">Upload Question PDF</a><br><br>
        <a href="/results">View Results</a><br><br>
        <a href="/logout">Logout</a>
        '''
    return redirect('/')

# ---------- PDF UPLOAD ----------
@app.route('/upload_pdf', methods=['GET','POST'])
def upload_pdf():

    if session.get('role') != 'admin':
        return redirect('/')

    if request.method == 'POST':

        file = request.files['pdf_file']
        pdf_reader = PyPDF2.PdfReader(file)

        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        lines = text.split("\n")

        question=""
        options=[]
        answer_key={}
        reading_answers=False

        cur = db.cursor()

        for line in lines:
            line=line.strip()

            if "Answer Key" in line:
                reading_answers=True
                continue

            if reading_answers:
                if "." in line:
                    parts=line.split(".")
                    answer_key[parts[0].strip()] = parts[1].strip()
                continue

            if line and line[0].isdigit() and "." in line:

                if question and len(options)==4:
                    q_no = question.split(".")[0]
                    correct = answer_key.get(q_no,"")

                    cur.execute("""
                        INSERT INTO questions
                        (question,option_a,option_b,option_c,option_d,correct_answer)
                        VALUES (%s,%s,%s,%s,%s,%s)
                    """,(question,options[0],options[1],options[2],options[3],correct))

                question=line
                options=[]

            elif line.startswith(("A)", "B)", "C)", "D)")):
                options.append(line[3:].strip())

        # 🔥 INSERT LAST QUESTION
        if question and len(options)==4:
            q_no = question.split(".")[0]
            correct = answer_key.get(q_no,"")

            cur.execute("""
                INSERT INTO questions
                (question,option_a,option_b,option_c,option_d,correct_answer)
                VALUES (%s,%s,%s,%s,%s,%s)
            """,(question,options[0],options[1],options[2],options[3],correct))

        db.commit()
        cur.close()

        return "PDF Uploaded & Questions Inserted!"

    return '''
    <h2>Upload PDF</h2>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="pdf_file">
        <button>Upload</button>
    </form>
    '''

# ---------- RESULTS (ADMIN ONLY) ----------
@app.route('/results')
def results():

    if session.get('role') != 'admin':
        return redirect('/')

    cur=db.cursor()
    cur.execute("SELECT * FROM results")
    data=cur.fetchall()
    cur.close()

    html="<h2>Results</h2>"
    for r in data:
        html+=f"<p>{r[1]} - Score: {r[2]}</p>"

    html+="<br><a href='/admin'>Back</a>"
    return html

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)












