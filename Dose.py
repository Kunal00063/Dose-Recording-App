from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import date

#Scheduler section:
from flask_mail import Mail, Message
from apscheduler.schedulers.background import BackgroundScheduler
import csv
from io import StringIO
from datetime import datetime

from datetime import datetime, date
import calendar

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///SAT136.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db =SQLAlchemy(app)

# ---------------------
# Email Configuration
# ---------------------
app.config['MAIL_SERVER'] = '10.2.150.13'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_TLS'] = False    # Most local relays do NOT use TLS
app.config['MAIL_USE_SSL'] = False

app.config['MAIL_USERNAME'] = None
app.config['MAIL_PASSWORD'] = None

app.config['MAIL_DEFAULT_SENDER'] = 'dosereport@mcrs3.tmc.org'

mail = Mail(app)


class Sat136(db.Model):
    sno = db.Column(db.Integer, primary_key = True)
    Date = db.Column(db.String(200), default=lambda: date.today().strftime("%d %b %Y"))
    Name = db.Column(db.String(200), nullable = False)
    Purpose = db.Column(db.String(500), nullable = False)
    Dosimeter = db.Column(db.String(10), nullable = False)
    Time_In = db.Column(db.String(10), nullable = False)
    Time_Out = db.Column(db.String(10), nullable = False)
    Dose = db.Column(db.Integer, nullable = False)

    def __repr__(self) -> str:
        return f'{self.sno} - {self.Name}'


# ---------------------------------------------------
# Function: Send Monthly Dose Report (CSV + TABLE)
# ---------------------------------------------------

def send_monthly_report():
    with app.app_context():

        today = datetime.today()
        year = today.year
        month = today.month - 1 #Kunal

        if month == 0:
            month = 12
            year -= 1

        last_month_str = datetime(year, month, 1).strftime("%b %Y")

        # Fetch last month’s records
        records = Sat136.query.filter(
            Sat136.Date.like(f"%{last_month_str}%")
        ).all()

        if not records:
            print("No records for last month.")
            return

        # -------------------------
        # Build HTML Table
        # -------------------------
        table_html = """
        <h3>Dose Records for {}</h3>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">
            <tr>
                <th>Date</th>
                <th>Name</th>
                <th>Purpose</th>
                <th>Dosimeter</th>
                <th>Time In</th>
                <th>Time Out</th>
                <th>Dose(µSv)</th>
            </tr>
        """.format(last_month_str)

        for r in records:
            table_html += f"""
            <tr>
                <td>{r.Date}</td>
                <td>{r.Name}</td>
                <td>{r.Purpose}</td>
                <td>{r.Dosimeter}</td>
                <td>{r.Time_In}</td>
                <td>{r.Time_Out}</td>
                <td>{r.Dose}</td>
            </tr>
            """

        table_html += "</table>"

        # -------------------------
        # Compose Email
        # -------------------------
          # ==== 3. Create CSV ====
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["Date", "Name", "Purpose", "Dosimeter", "Time_In", "Time_Out", "Dose"])

        for r in records:
            writer.writerow([r.Date, r.Name, r.Purpose, r.Dosimeter,
                             r.Time_In, r.Time_Out, r.Dose])


        msg = Message(
            subject=f"Monthly Dose Report – {last_month_str}",
            recipients=["pt_mumbai_team@iba-group.com"]
        )

        msg.html = f"""
        <p>Hello Team,</p>

        <p>Please find below the dose records for <b>{last_month_str}</b>.</p>

        {table_html}

        <p>Thank you,<br>Dose Monitoring System</p>
        """
         # Attach CSV
        msg.attach(
            filename=f"DoseRecords_{last_month_str}.csv",
            content_type="text/csv",
            data=csv_buffer.getvalue()
        )

        mail.send(msg)
        print("Monthly HTML email sent successfully!")



@app.route("/", methods=['GET', 'POST'])
def hello_world():
    if request.method == 'POST' and 'Dosimeter' in request.form:
        Name = request.form.get('Name')
        Purpose = request.form.get('Purpose')
        Dosimeter = request.form.get('Dosimeter')
        Time_In = request.form.get('Time_In')
        Time_Out = request.form.get('Time_Out')
        Dose = request.form.get('Dose')

        eg_data = Sat136(
            Name=Name, Purpose=Purpose, Dosimeter=Dosimeter,
            Time_In=Time_In, Time_Out=Time_Out, Dose=Dose
        )
        db.session.add(eg_data)
        db.session.commit()

    allSat136 = Sat136.query.order_by(Sat136.sno.desc()).all()
    return render_template('index.html', allSat136=allSat136)


@app.route("/stats")
def stats():
    records = Sat136.query.all()

    # Total dose per person
    dose_by_person = {}
    active_dates = set()

    for r in records:
        # Normalize name → Title Case
        name = r.Name.strip().title()

        # Dose per person
        dose_by_person[name] = dose_by_person.get(name, 0) + int(r.Dose)

        # Convert "07 Dec 2025" → date object
        dt = datetime.strptime(r.Date, "%d %b %Y").date()
        active_dates.add(dt)

    # Prepare chart data
    labels = list(dose_by_person.keys())
    values = list(dose_by_person.values())

    # -------------------------------------------
    # CALENDAR LOGIC FOR CURRENT MONTH
    # -------------------------------------------
    today = date.today()
    current_year = today.year
    current_month = today.month
    current_month_name = today.strftime("%B")

    # Days in month
    _, num_days = calendar.monthrange(current_year, current_month)
    current_month_days = list(range(1, num_days + 1))

    # Active days for current month
    active_days = [
        d.day for d in active_dates
        if d.month == current_month and d.year == current_year
    ]

    # Offset (0 = Monday)
    first_day_weekday = calendar.monthrange(current_year, current_month)[0]
    month_start_offset = (first_day_weekday + 1) % 7

    return render_template(
        "stats.html",
        labels=labels,
        values=values,
        current_month_name=current_month_name,
        current_year=current_year,
        current_month_days=current_month_days,
        active_days=active_days,
        month_start_offset=month_start_offset
    )



@app.route("/delete_latest", methods=['POST'])
def delete_latest():
    latest_record = Sat136.query.order_by(Sat136.sno.desc()).first()
    if latest_record:
        db.session.delete(latest_record)
        db.session.commit()
    return redirect("/")


# Initialize database
def init_db():
    with app.app_context():
        db.create_all()

# -----------------------------------------
# APScheduler: Run on the 1st of every month
# -----------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(
    send_monthly_report,
    trigger='cron',
    day= 1,
    hour= 9,      # You can change this
    minute= 00
    )
scheduler.start()

if __name__ == '__main__':
    init_db()  # This will create tables when you run the app
    app.run(host='localhost', port=8000, debug=True)