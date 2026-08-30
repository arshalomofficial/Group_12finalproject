GridCare-Lite
CS 112 Final Project — Summer 2026

Tkinter desktop app for outage and maintenance management. Four roles: admin, engineer, technician, customer_service.

Install
pip3 install bcrypt

Run
cd GridCare-Lite
python3 gridcare_app.py

Demo accounts:
admin1 / Admin@123 — Administrator
engineer1 / Engineer@123 — Engineer
tech1 / Tech@123 — Technician
cs1 / Service@123 — Customer Service

Typical workflow: engineer1 logs an outage, admin1 assigns a work order to tech1, tech1 marks it In Progress then Completed, admin1 resolves it with notes, and cs1 logs a complaint linked to the outage.