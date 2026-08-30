CS 112 Final Project — Summer 2026
Integrated Data Science and Software Engineering

Group: Final Project 12
Team members: Manyok Gai Chop Deng, Gilford Irvin Adamnor Mensah-Akutteh, Benedict Anorgeyine Atanga, Atiah Roland Shalom

This project has three parts. DataScience looks at a synthetic national electricity grid network. GridCare-Lite is a Tkinter desktop app for managing outages and maintenance. ClinicCare-Lite is a Flask web app for clinic patient administration.

Folder Structure

project/
- README.md
- requirements.txt
- ClinicCare-Lite/
  - __pycache__/
  - data/
  - static/
  - submissions/
  - templates/
  - tests/
  - utils/
  - .env.example
  - app.py
  - README.md
- docs/
  - architecture_and_design.docx
  - clinician_user_guide.docx
  - defect_log.docx
  - final_project_report.docx
  - installation_guide.docx
  - patient_user_guide.docx
  - team_contribution_report.docx
  - technical_report.docx
  - test_plan_and_report.docx
- grid_care_analysis/
  - outputs/
  - generate_grid_data.py
  - grid_analysis.py
  - lines.csv
  - substations.csv
  - utilities.csv
- GridCare-Lite/
  - __pycache__/
  - database.py
  - gridcare_app.py
  - gridcare.db
  - README.md
- Videos
  - gridcare_demo
  - clinicare-demo

How to run each part:

DataScience
cd DataScience
pip3 install -r requirements.txt
python3 generate_grid_data.py
python3 grid_analysis.py

GridCare-Lite
cd GridCare-Lite
pip3 install -r requirements.txt
python3 gridcare_app.py

ClinicCare-Lite
cd ClinicCare-Lite
pip3 install -r requirements.txt
python3 app.py
Then open http://127.0.0.1:5000 in a browser.

Demo accounts for GridCare-Lite:
admin1 / Admin@123 — Administrator
engineer1 / Engineer@123 — Engineer
tech1 / Tech@123 — Technician
cs1 / Service@123 — Customer Service

For ClinicCare-Lite you can register your own account at /register, or use a clinician ID ending in 0000 (e.g. 12350000, password Clinician1!) or a patient ID ending in a year from 2022-2028 (e.g. 12342024, password Patient123!).

To run the ClinicCare-Lite tests:
cd ClinicCare-Lite
python3 -m unittest tests.test_app -v

One note on the dataset — the grid data (coordinates, capacities, connections) is synthetic and made up for this project. It isn't real Ghana or West Africa grid data.


GITHUB
https://github.com/arshalomofficial/Group_12finalproject.git
