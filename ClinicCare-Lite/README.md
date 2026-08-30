ClinicCare-Lite
CS 112 Final Project — Summer 2026

Flask web app for clinic patient administration. Two roles: clinician and patient.

Install
pip3 install flask bcrypt werkzeug

Run
cd ClinicCare-Lite
python3 app.py
Then open http://127.0.0.1:5000

Register accounts
Go to /register and create an account. A clinician ID has to end in 0000 (e.g. 12350000), and a patient ID has to end in a year from 2022-2028 (e.g. 12342024). Passwords need an uppercase letter, a lowercase letter, a digit, and a special character, e.g. Patient123!

Tests
python3 -m unittest tests.test_app -v