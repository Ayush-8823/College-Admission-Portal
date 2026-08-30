from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, render_template, request, redirect, session, send_from_directory, send_file
from flask_mysqldb import MySQL
from openpyxl import Workbook
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)

app.secret_key = "college_secret_key"


# ==========================
# MYSQL CONFIGURATION
# ==========================

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "Ayush221105@"
app.config["MYSQL_DB"] = "college_portal"

mysql = MySQL(app)



# ==========================
# UPLOAD FOLDER
# ==========================

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)



# ==========================
# HOME PAGES
# ==========================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/courses")
def courses():
    return render_template("courses.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")



# ==========================
# ADMIN LOGIN
# ==========================

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM admin WHERE username=%s",
            (username,)
        )

        admin = cur.fetchone()

        cur.close()


        if admin and check_password_hash(admin[2], password):

            session["admin"] = username

            return redirect("/dashboard")

        else:

            return "Invalid Username or Password"


    return render_template("login.html")

# ==========================
# DASHBOARD
@app.route("/dashboard")
def dashboard():

    if "admin" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    # Total Students
    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]

    # Total Courses
    cur.execute("SELECT COUNT(DISTINCT course) FROM students")
    total_courses = cur.fetchone()[0]

    # Students List
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()

    cur.close()

        # Course Wise Student Count

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT course, COUNT(*) 
        FROM students
        GROUP BY course
    """)

    courses = cur.fetchall()
    print(courses)

    return render_template(
        "dashboard.html",
        students=students,
        total_students=total_students,
        total_courses=total_courses,
        courses=courses
    )




# ==========================
# SEARCH STUDENT
# ==========================

@app.route("/search", methods=["POST"])
def search():

    if "admin" not in session:
        return redirect("/login")


    search = request.form["search"]


    cur = mysql.connection.cursor()


    cur.execute("""
        SELECT * FROM students
        WHERE name LIKE %s
        OR mobile LIKE %s
    """,
    (
        "%"+search+"%",
        "%"+search+"%"
    ))


    students = cur.fetchall()

    cur.close()


    return render_template(
        "dashboard.html",
        students=students
    )


# ==========================
# VIEW STUDENT PROFILE
# ==========================

@app.route("/view/<int:id>")
def view_student(id):

    if "admin" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM students WHERE id=%s",
        (id,)
    )

    student = cur.fetchone()

    cur.close()

    return render_template(
        "view.html",
        student=student
    )

# ==========================
# EDIT STUDENT
# ==========================

@app.route("/edit/<int:id>")
def edit_student(id):

    if "admin" not in session:
        return redirect("/login")


    cur = mysql.connection.cursor()


    cur.execute(
        "SELECT * FROM students WHERE id=%s",
        (id,)
    )


    student = cur.fetchone()


    cur.close()


    return render_template(
        "edit.html",
        student=student
    )


@app.route("/update/<int:id>", methods=["POST"])
def update_student(id):

    if "admin" not in session:
        return redirect("/login")

    name = request.form["name"]
    father = request.form["father"]
    email = request.form["email"]
    mobile = request.form["mobile"]

    dob = request.form.get("dob")
    if dob == "":
        dob = None

    course = request.form["course"]
    address = request.form["address"]

    photo = request.files.get("photo")

    cur = mysql.connection.cursor()

    # Purani photo ka naam nikalna
    cur.execute("SELECT photo FROM students WHERE id=%s", (id,))
    result = cur.fetchone()

    if result:
        photo_name = result[0]
    else:
        photo_name = ""

    # Agar nayi photo upload hui hai
    if photo and photo.filename != "":
        photo_name = photo.filename
        photo.save(os.path.join("uploads", photo_name))

    # Database update
    cur.execute("""
        UPDATE students
        SET
            name=%s,
            father=%s,
            email=%s,
            mobile=%s,
            dob=%s,
            course=%s,
            address=%s,
            photo=%s
        WHERE id=%s
    """,
    (
        name,
        father,
        email,
        mobile,
        dob,
        course,
        address,
        photo_name,
        id
    ))

    mysql.connection.commit()
    cur.close()

    return redirect("/dashboard")


# ==========================
# SHOW UPLOADED PHOTO
# ==========================

@app.route("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        "uploads",
        filename
    )



# ==========================
# DELETE STUDENT
# ==========================

@app.route("/delete/<int:id>")
def delete_student(id):

    cur = mysql.connection.cursor()


    cur.execute(
        "DELETE FROM students WHERE id=%s",
        (id,)
    )


    mysql.connection.commit()

    cur.close()


    return redirect("/dashboard")

@app.route("/pdf/<int:id>")
def download_pdf(id):

    if "admin" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, name, father, email, mobile, dob, course, address
        FROM students
        WHERE id=%s
    """, (id,))

    student = cur.fetchone()

    cur.close()

    filename = f"Student_{id}.pdf"

    c = canvas.Canvas(filename)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(180, 800, "COLLEGE ADMISSION PORTAL")

    c.setFont("Helvetica", 12)

    y = 760

    labels = [
        ("Student ID", student[0]),
        ("Name", student[1]),
        ("Father Name", student[2]),
        ("Email", student[3]),
        ("Mobile", student[4]),
        ("DOB", str(student[5])),
        ("Course", student[6]),
        ("Address", student[7]),
    ]

    for label, value in labels:
        c.drawString(60, y, f"{label}: {value}")
        y -= 30

    c.save()

    return send_file(filename, as_attachment=True)


# ==========================
# LOGOUT
# ==========================

@app.route("/logout")
def logout():

    session.pop("admin",None)

    return redirect("/login")

@app.route("/export")
def export_excel():

    if "admin" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, name, father, email, mobile, dob, course, address
        FROM students
    """)
    students = cur.fetchall()
    cur.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Students"

    ws.append([
        "ID",
        "Name",
        "Father Name",
        "Email",
        "Mobile",
        "DOB",
        "Course",
        "Address"
    ])

    for student in students:
        ws.append(student)

    filename = "students.xlsx"
    wb.save(filename)

    return send_file(filename, as_attachment=True)

# ==========================
# ADMISSION FORM
# ==========================

@app.route("/admission", methods=["GET","POST"])
def admission():

    if request.method == "POST":


        name = request.form.get("name")
        father = request.form.get("father")
        email = request.form.get("email")
        mobile = request.form.get("mobile")


        dob = request.form.get("dob")

        if dob == "":
            dob = None


        course = request.form.get("course")
        address = request.form.get("address")



        photo = request.files.get("photo")


        photo_name = ""


        if photo and photo.filename != "":

            photo_name = photo.filename

            photo.save(
                os.path.join(
                    "uploads",
                    photo_name
                )
            )



        cur = mysql.connection.cursor()


        cur.execute("""
            INSERT INTO students
            (
            name,
            father,
            email,
            mobile,
            dob,
            course,
            address,
            photo
            )

            VALUES
            (%s,%s,%s,%s,%s,%s,%s,%s)

        """,
        (
            name,
            father,
            email,
            mobile,
            dob,
            course,
            address,
            photo_name
        ))


        mysql.connection.commit()

        send_confirmation_email(
    email,
    name,
    course
)

        cur.close()



        return render_template(
            "success.html",
            name=name
        )



    return render_template("admission.html")

def send_confirmation_email(receiver_email, student_name, course):

    sender_email = "officialayush8823@gmail.com"
    sender_password = "tfpd vlfq visf tdqe"

    subject = "Admission Submitted Successfully"

    body = f"""
Dear {student_name},

Your admission application has been submitted successfully.

Course : {course}

Thank you for applying.

Regards,
Sheat College Admission Portal
"""

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print("Email Sent Successfully")
    except Exception as e:
        print("Email Error:", e)



# ==========================
# RUN APP
# ==========================

if __name__ == "__main__":

    app.run(debug=True)