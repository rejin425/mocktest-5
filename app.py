import os
import pymysql
import PyPDF2
from flask import Flask, request, redirect, session

app = Flask(__name__)
app.secret_key = "secret123"
# ---------- MYSQL CONNECTION ----------

db = pymysql.connect(
    host=os.environ.get("DB_HOST"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASSWORD"),
    database=os.environ.get("DB_NAME"),
    port=25173
)


cursor = db.cursor()
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
        password = request.form['password']

        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s",(username,))
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
    cur.execute("SELECT * FROM users WHERE username=%s AND password=%s",
                (username,password))
    user = cur.fetchone()
    cur.close()

    if user:
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
            text += page.extract_text() + "\n"

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

# ---------- STUDENT ----------
@app.route('/student')
def student():
    if session.get('role') == 'student':
        return '''
        <h2>Student Dashboard</h2>
        <a href="/start_test">Start Test</a><br><br>
        <a href="/logout">Logout</a>
        '''
    return redirect('/')

# ---------- START TEST ----------
@app.route('/start_test', methods=['GET','POST'])
def start_test():

    if session.get('role') != 'student':
        return redirect('/')

    cur = db.cursor()
    cur.execute("SELECT * FROM questions")
    questions = cur.fetchall()
    cur.close()

    if not questions:
        return "<h3>No Questions Found in Database!</h3>"

    if request.method == 'POST':
        score=0
        for q in questions:
            selected=request.form.get(str(q[0]))
            if selected == q[6]:
                score+=1

        cur=db.cursor()
        cur.execute("INSERT INTO results (username,score) VALUES (%s,%s)",
                    (session['username'],score))
        db.commit()
        cur.close()

        return f"<h2>Your Score: {score}</h2><a href='/student'>Back</a>"

    html="<h2>Mock Test</h2><form method='post'>"
    for q in questions:
        html+=f"<p>{q[1]}</p>"
        html+=f"<input type='radio' name='{q[0]}' value='A'> {q[2]}<br>"
        html+=f"<input type='radio' name='{q[0]}' value='B'> {q[3]}<br>"
        html+=f"<input type='radio' name='{q[0]}' value='C'> {q[4]}<br>"
        html+=f"<input type='radio' name='{q[0]}' value='D'> {q[5]}<br><hr>"

    html+="<button>Submit</button></form>"
    return html

# ---------- RESULTS ----------
@app.route('/results')
def results():
    cur=db.cursor()
    cur.execute("SELECT * FROM results")
    data=cur.fetchall()
    cur.close()

    html="<h2>Results</h2>"
    for r in data:
        html+=f"<p>{r[1]} - Score: {r[2]}</p>"

    html+="<br><a href='/admin'>Back</a>"
    return html

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')











