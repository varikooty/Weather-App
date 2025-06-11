from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
import csv
import io
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("WEATHER_API_KEY")


app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "weather.db")}'
db = SQLAlchemy(app)

with app.app_context():
    db.create_all()



class WeatherEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    temperature = db.Column(db.String(50))
    description = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def as_dict(self):
        return {
            "id": self.id,
            "location": self.location,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "temperature": self.temperature,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
        }

@app.route("/", methods=["GET", "POST"])
def index():
    weather_data = None
    if request.method == "POST":
        location = request.form.get("city")
        if location:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={API_KEY}&units=metric"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                weather_data = {
                    "city": location,
                    "temperature": data["main"]["temp"],
                    "description": data["weather"][0]["description"],
                    "icon": data["weather"][0]["icon"]
                }

                today = datetime.today().date()
                entry = WeatherEntry(
                    location=location,
                    start_date=today,
                    end_date=today,
                    temperature=str(data["main"]["temp"]),
                    description=data["weather"][0]["description"]
                )
                db.session.add(entry)
                db.session.commit()
            else:
                weather_data = {"error": "City not found"}
    return render_template("index.html", weather=weather_data)


@app.route("/create", methods=["POST"])
def create():
    location = request.form.get("location")
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    if not location or not start_date or not end_date:
        return "Missing data", 400

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        if end_dt < start_dt:
            return "Invalid date range", 400
    except ValueError:
        return "Invalid date format", 400

    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={API_KEY}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return "Invalid location", 400

    data = response.json()
    temp = data["main"]["temp"]
    desc = data["weather"][0]["description"]

    entry = WeatherEntry(location=location, start_date=start_dt, end_date=end_dt, temperature=str(temp), description=desc)
    db.session.add(entry)
    db.session.commit()

    return redirect(url_for("read"))

@app.route("/read")
def read():
    entries = WeatherEntry.query.order_by(WeatherEntry.timestamp.desc()).all()
    return render_template("read.html", entries=entries)

@app.route('/update/<int:id>', methods=['GET', 'POST'])   
def update(id):
    task = Todo.query.get_or_404(id) 
    if request.method == 'POST':
        task.content = request.form['content']
        try:
            db.session.commit()
            return redirect('/')
        except:
            return 'There was an issue updating your task'
    else:
        return render_template('update.html', task=task)


@app.route("/delete/<int:id>")
def delete(id):
    entry = WeatherEntry.query.get_or_404(id)
    db.session.delete(entry)
    db.session.commit()
    return redirect(url_for("read"))

@app.route("/export/csv")
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    entries = WeatherEntry.query.all()
    writer.writerow(["ID", "Location", "Start Date", "End Date", "Temperature", "Description", "Timestamp"])
    for e in entries:
        writer.writerow([e.id, e.location, e.start_date, e.end_date, e.temperature, e.description, e.timestamp])

    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype="text/csv", as_attachment=True, download_name="weather_data.csv")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
