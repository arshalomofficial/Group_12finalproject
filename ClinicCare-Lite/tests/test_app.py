"""
test_app.py  -  ClinicCare-Lite
Run from the ClinicCare-Lite folder:
    python -m unittest tests.test_app -v
"""

import io
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as clinic_app
from utils import validators


class ValidatorTests(unittest.TestCase):

    def test_clinician_id_valid(self):
        ok, _ = validators.validate_user_id("12350000", "clinician")
        self.assertTrue(ok)

    def test_clinician_id_wrong_suffix(self):
        ok, _ = validators.validate_user_id("12341234", "clinician")
        self.assertFalse(ok)

    def test_patient_id_valid_year(self):
        ok, _ = validators.validate_user_id("12342024", "patient")
        self.assertTrue(ok)

    def test_patient_id_invalid_year(self):
        ok, _ = validators.validate_user_id("12342099", "patient")
        self.assertFalse(ok)

    def test_id_wrong_length(self):
        ok, _ = validators.validate_user_id("123", "patient")
        self.assertFalse(ok)

    def test_password_too_short(self):
        ok, _ = validators.validate_password("Ab1!")
        self.assertFalse(ok)

    def test_password_missing_special_char(self):
        ok, _ = validators.validate_password("Abcdefg1")
        self.assertFalse(ok)

    def test_password_valid(self):
        ok, _ = validators.validate_password("Abcdefg1!")
        self.assertTrue(ok)

    def test_file_extension_rejected(self):
        ok, _ = validators.validate_file("scan.exe", 1000)
        self.assertFalse(ok)

    def test_file_extension_accepted(self):
        ok, _ = validators.validate_file("results.csv", 1000)
        self.assertTrue(ok)

    def test_file_too_large(self):
        ok, _ = validators.validate_file("results.csv", 10 * 1024 * 1024)
        self.assertFalse(ok)

    def test_csv_completeness_good(self):
        content = b"date,value\n2026-01-01,120\n2026-01-02,118\n"
        ok, issues = validators.check_csv_completeness(content)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_csv_completeness_missing_field(self):
        content = b"date,value\n2026-01-01,\n"
        ok, issues = validators.check_csv_completeness(content)
        self.assertFalse(ok)
        self.assertTrue(len(issues) > 0)


class ClinicCareIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        clinic_app.DATA_DIR = self.temp_dir
        clinic_app.SUBMISSIONS_DIR = os.path.join(self.temp_dir, "submissions")
        clinic_app.USERS_FILE = os.path.join(self.temp_dir, "users.json")
        clinic_app.TASKS_FILE = os.path.join(self.temp_dir, "health_tasks.json")
        clinic_app.SUBMISSIONS_FILE = os.path.join(self.temp_dir, "task_submissions.json")
        clinic_app.MESSAGES_FILE = os.path.join(self.temp_dir, "messages.json")
        clinic_app.ANNOUNCEMENTS_FILE = os.path.join(self.temp_dir, "announcements.json")
        os.makedirs(clinic_app.SUBMISSIONS_DIR, exist_ok=True)
        clinic_app.app.config["TESTING"] = True
        clinic_app.app.secret_key = "test-secret-key"
        self.client = clinic_app.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def register(self, user_id, name, email, password, role):
        return self.client.post("/register", data={
            "user_id": user_id, "name": name, "email": email,
            "password": password, "role": role,
        }, follow_redirects=True)

    def login(self, user_id, password):
        return self.client.post("/login", data={
            "user_id": user_id, "password": password,
        }, follow_redirects=True)

    def test_registration_rejects_weak_password(self):
        response = self.register("12342024", "Test Patient", "p@test.com", "weak", "patient")
        self.assertIn(b"Password must", response.data)

    def test_registration_rejects_bad_patient_id(self):
        response = self.register("12341234", "Test Patient", "p@test.com", "Abcdefg1!", "patient")
        self.assertIn(b"registration year", response.data)

    def test_full_workflow_clinician_and_patient(self):
        self.register("12350000", "Dr. Adjei", "doc@clinic.com", "Clinician1!", "clinician")
        self.register("12342024", "Ama Owusu", "ama@example.com", "Patient123!", "patient")

        self.login("12350000", "Clinician1!")
        self.client.post("/clinician/tasks/new", data={
            "title": "Home BP log", "description": "Log your readings",
            "due_date": "2099-01-01",
        }, follow_redirects=True)
        self.client.get("/logout")

        self.login("12342024", "Patient123!")
        dashboard = self.client.get("/patient")
        self.assertIn(b"Home BP log", dashboard.data)

        csv_content = b"date,systolic,diastolic\n2026-01-01,120,80\n"
        response = self.client.post("/patient/tasks/1/submit", data={
            "file": (io.BytesIO(csv_content), "readings.csv"),
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertIn(b"Submission received", response.data)
        self.client.get("/logout")

        self.login("12350000", "Clinician1!")
        submissions = clinic_app.load_json(clinic_app.SUBMISSIONS_FILE)
        submission_id = list(submissions.keys())[0]
        response = self.client.post(f"/clinician/submissions/{submission_id}/review", data={
            "outcome": "Reviewed - Normal", "notes": "Looks fine.",
        }, follow_redirects=True)
        self.assertIn(b"Review recorded", response.data)
        self.client.get("/logout")

        self.login("12342024", "Patient123!")
        dashboard = self.client.get("/patient")
        self.assertIn(b"Reviewed - Normal", dashboard.data)
        self.assertIn(b"Looks fine", dashboard.data)

    def test_patient_cannot_access_another_patients_file(self):
        self.register("12342024", "Patient A", "a@example.com", "Patient123!", "patient")
        self.register("12342025", "Patient B", "b@example.com", "Patient123!", "patient")
        self.login("12342024", "Patient123!")
        os.makedirs(os.path.join(clinic_app.SUBMISSIONS_DIR, "12342025"), exist_ok=True)
        with open(os.path.join(clinic_app.SUBMISSIONS_DIR, "12342025", "secret.txt"), "w") as f:
            f.write("private data")
        response = self.client.get("/files/12342025/secret.txt")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_cannot_reach_dashboard(self):
        response = self.client.get("/dashboard", follow_redirects=True)
        self.assertIn(b"Log In", response.data)

    def test_patient_cannot_reach_clinician_route(self):
        self.register("12342024", "Ama Owusu", "ama@example.com", "Patient123!", "patient")
        self.login("12342024", "Patient123!")
        response = self.client.get("/clinician")
        self.assertEqual(response.status_code, 403)

    def test_invalid_file_type_rejected(self):
        self.register("12350000", "Dr. Adjei", "doc@clinic.com", "Clinician1!", "clinician")
        self.register("12342024", "Ama Owusu", "ama@example.com", "Patient123!", "patient")
        self.login("12350000", "Clinician1!")
        self.client.post("/clinician/tasks/new", data={
            "title": "Task", "description": "desc", "due_date": "2099-01-01",
        }, follow_redirects=True)
        self.client.get("/logout")
        self.login("12342024", "Patient123!")
        response = self.client.post("/patient/tasks/1/submit", data={
            "file": (io.BytesIO(b"binary junk"), "malware.exe"),
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertIn(b"Only .txt, .csv, and .pdf", response.data)


if __name__ == "__main__":
    unittest.main()
