import re
import csv
import io

ID_PATTERN     = re.compile(r"^\d{8}$")
ALLOWED_EXT    = (".txt", ".csv", ".pdf")
MAX_FILE_BYTES = 5 * 1024 * 1024


def validate_user_id(user_id, role):
    if not ID_PATTERN.match(user_id):
        return False, "ID must be exactly 8 digits."
    suffix = user_id[-4:]
    if role == "clinician":
        if suffix != "0000":
            return False, "Clinician IDs must end in 0000."
    elif role == "patient":
        yr = int(suffix)
        if not (2022 <= yr <= 2028):
            return False, "Patient IDs must end in a registration year between 2022 and 2028."
    else:
        return False, "Unknown role."
    return True, ""


def validate_password(pw):
    if len(pw) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", pw):
        return False, "Password must include at least one uppercase letter."
    if not re.search(r"[a-z]", pw):
        return False, "Password must include at least one lowercase letter."
    if not re.search(r"\d", pw):
        return False, "Password must include at least one digit."
    if not re.search(r"[!@#$%^&*]", pw):
        return False, "Password must include at least one special character (!@#$%^&*)."
    return True, ""


def validate_file(filename, size_bytes):
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in ALLOWED_EXT:
        return False, "Only .txt, .csv, and .pdf files are accepted."
    if size_bytes > MAX_FILE_BYTES:
        return False, "File is too large (5 MB limit)."
    return True, ""


def check_csv_completeness(file_bytes):
    try:
        text   = file_bytes.decode("utf-8", errors="replace")
        reader = list(csv.reader(io.StringIO(text)))
    except Exception:
        return False, ["Could not read the file as CSV."]

    if not reader:
        return False, ["The file is empty."]

    header = reader[0]
    issues = []
    if not header or all(c.strip() == "" for c in header):
        issues.append("The header row looks empty.")

    for i, row in enumerate(reader[1:], start=2):
        if len(row) != len(header):
            issues.append(f"Row {i} has {len(row)} fields but the header has {len(header)}.")
        elif any(c.strip() == "" for c in row):
            issues.append(f"Row {i} has one or more empty fields.")

    return len(issues) == 0, issues


def check_txt_not_empty(file_bytes):
    text = file_bytes.decode("utf-8", errors="replace").strip()
    if not text:
        return False, ["The text file is empty."]
    return True, []
