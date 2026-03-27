from flask import Blueprint, request, jsonify, render_template, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import csv
import requests as req
import re
from io import BytesIO

# ==============================
# GEMINI AI SETUP
# ==============================
GEMINI_AVAILABLE = False
gemini_model = None

try:
    import google.generativeai as genai
    GEMINI_API_KEY = "AIzaSyDT8NZNw9aI9vzrIJxkSEOu_MyA7Z1EWTw"
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.5-flash")
    GEMINI_AVAILABLE = True
    print("✅ Gemini AI ready!")
except ImportError:
    print("⚠️  Run: pip install google-generativeai==0.8.3")
except Exception as e:
    print(f"⚠️  Gemini setup error: {e}")

routes = Blueprint("routes", __name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            education TEXT,
            income INTEGER,
            category TEXT,
            state TEXT,
            course TEXT,
            documents TEXT,
            saved_scholarships TEXT
        )
    """)
    conn.commit()
    conn.close()
    try:
        conn2 = get_db()
        conn2.execute("ALTER TABLE users ADD COLUMN documents TEXT")
        conn2.commit()
        conn2.close()
    except:
        pass
    try:
        conn3 = get_db()
        conn3.execute("ALTER TABLE users ADD COLUMN saved_scholarships TEXT")
        conn3.commit()
        conn3.close()
    except:
        pass

init_db()

# ==============================
# PAGE ROUTES
# ==============================
@routes.route("/")
def home():
    return render_template("landing.html")

@routes.route("/login")
def login_page():
    return render_template("index.html")

@routes.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@routes.route("/profile")
def profile():
    return render_template("profile.html")

@routes.route("/documents")
def documents_page():
    return render_template("documents.html")

@routes.route("/saved")
def saved_page():
    return render_template("saved.html")

@routes.route("/admin")
def admin_login_page():
    return render_template("admin_login.html")

@routes.route("/admin_dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html")

@routes.route("/map")
def map_page():
    return render_template("map.html")

# ==============================
# SIGNUP
# ==============================
@routes.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("index.html")
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = generate_password_hash(data.get("password"))
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, password))
        conn.commit()
        conn.close()
        return jsonify({"message": "Account created successfully!"})
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 400

# ==============================
# LOGIN
# ==============================
@routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("index.html")
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cur.fetchone()
    conn.close()
    if user and check_password_hash(user["password"], password):
        return jsonify({
            "message": "Login success",
            "name": user["name"],
            "email": user["email"]
        })
    return jsonify({"error": "Invalid email or password"}), 401

# ==============================
# SAVE PROFILE
# ==============================
@routes.route("/save_profile", methods=["POST"])
def save_profile():
    data = request.get_json()
    email = data.get("email", "")
    education = data.get("education", "")
    income = data.get("income", 0)
    category = data.get("category", "")
    state = data.get("state", "")
    course = data.get("course", "")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            UPDATE users SET education=?, income=?, category=?, state=?, course=?
            WHERE email=?
        """, (education, income, category, state, course, email))
        conn.commit()
        conn.close()
        return jsonify({"message": "Profile saved successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# GET PROFILE
# ==============================
@routes.route("/get_profile", methods=["GET", "POST"])
def get_profile():
    try:
        if request.method == "POST":
            data = request.get_json()
            email = data.get("email", "") if data else ""
        else:
           email = request.args.get("email", "")
           state = request.args.get("state", "")
        if not email:
            return jsonify({"error": "No email provided"}), 400
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()
        if user:
            return jsonify({
                "name": user["name"] or "",
                "email": user["email"] or "",
                "education": user["education"] or "",
                "income": str(user["income"]) if user["income"] else "",
                "category": user["category"] or "",
                "state": user["state"] or "",
                "course": user["course"] or ""
            })
        return jsonify({"error": "User not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# DOCUMENT UPLOAD
# ==============================
@routes.route("/upload_document", methods=["POST"])
def upload_document():
    try:
        email = request.form.get("email")
        doc_type = request.form.get("doc_type")
        file = request.files.get("file")
        if not file or not allowed_file(file.filename):
            return jsonify({"error": "Invalid file. Use PDF, JPG or PNG"}), 400
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        ext = file.filename.rsplit(".", 1)[1].lower()
        safe_name = secure_filename(f"{email}_{doc_type}.{ext}")
        file.save(os.path.join(UPLOAD_FOLDER, safe_name))
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT documents FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        existing = user["documents"] if user and user["documents"] else ""
        docs_list = [d for d in existing.split(",") if d] if existing else []
        if doc_type not in docs_list:
            docs_list.append(doc_type)
        new_docs = ",".join(docs_list)
        cur.execute("UPDATE users SET documents=? WHERE email=?", (new_docs, email))
        conn.commit()
        conn.close()
        return jsonify({"message": f"{doc_type} uploaded successfully!", "docs": new_docs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# GET DOCUMENTS
# ==============================
@routes.route("/get_documents", methods=["POST"])
def get_documents():
    try:
        data = request.get_json()
        email = data.get("email")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT documents FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()
        existing = user["documents"] if user and user["documents"] else ""
        docs_list = [d for d in existing.split(",") if d] if existing else []
        all_docs = [
            "Aadhaar Card", "Income Certificate", "Caste Certificate",
            "Marksheet", "Bank Passbook", "Domicile Certificate"
        ]
        result = []
        for doc in all_docs:
            result.append({"name": doc, "uploaded": doc in docs_list})
        percent = int((len(docs_list) / len(all_docs)) * 100)
        return jsonify({"documents": result, "percent": percent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# SAVE SCHOLARSHIP
# ==============================
@routes.route("/save_scholarship", methods=["POST"])
def save_scholarship():
    try:
        data = request.get_json()
        email = data.get("email")
        scholarship_name = data.get("name")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT saved_scholarships FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        existing = user["saved_scholarships"] if user and user["saved_scholarships"] else ""
        saved_list = [s for s in existing.split("||") if s] if existing else []
        if scholarship_name in saved_list:
            return jsonify({"message": "Already saved!", "status": "exists"})
        saved_list.append(scholarship_name)
        new_saved = "||".join(saved_list)
        cur.execute("UPDATE users SET saved_scholarships=? WHERE email=?", (new_saved, email))
        conn.commit()
        conn.close()
        return jsonify({"message": "Scholarship saved!", "status": "saved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# UNSAVE SCHOLARSHIP
# ==============================
@routes.route("/unsave_scholarship", methods=["POST"])
def unsave_scholarship():
    try:
        data = request.get_json()
        email = data.get("email")
        scholarship_name = data.get("name")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT saved_scholarships FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        existing = user["saved_scholarships"] if user and user["saved_scholarships"] else ""
        saved_list = [s for s in existing.split("||") if s] if existing else []
        if scholarship_name in saved_list:
            saved_list.remove(scholarship_name)
        new_saved = "||".join(saved_list)
        cur.execute("UPDATE users SET saved_scholarships=? WHERE email=?", (new_saved, email))
        conn.commit()
        conn.close()
        return jsonify({"message": "Removed from saved!", "status": "removed"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# GET SAVED
# ==============================
@routes.route("/get_saved", methods=["POST"])
def get_saved():
    try:
        data = request.get_json()
        email = data.get("email")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT saved_scholarships FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()
        existing = user["saved_scholarships"] if user and user["saved_scholarships"] else ""
        saved_list = [s for s in existing.split("||") if s] if existing else []
        all_scholarships = get_all_scholarships_combined()
        saved_details = []
        for s in all_scholarships:
            if s["name"] in saved_list:
                saved_details.append({
                    "name": s["name"],
                    "provider": s["provider"],
                    "amount": s.get("amount", "As per scheme"),
                    "deadline": s["deadline"],
                    "link": s["link"],
                    "type": s.get("type", "National")
                })
        return jsonify({"saved": saved_details, "count": len(saved_details)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# AI MATCHING ENGINE
# ==============================
def calculate_match(scholarship, education, income, category, state, course):
    score = 0
    total = 5
    edu_map = {
        "10th": ["10th", "school"],
        "12th": ["10th", "12th", "school"],
        "diploma": ["10th", "12th", "diploma", "school"],
        "undergraduate": ["10th", "12th", "diploma", "undergraduate", "ug", "ug/pg"],
        "postgraduate": ["10th", "12th", "diploma", "undergraduate", "postgraduate", "pg", "ug/pg"]
    }
    s_edu = str(scholarship.get("education", "")).lower()
    u_edu = (education or "").lower()
    if s_edu == "" or s_edu == "all" or u_edu in edu_map.get(s_edu, [s_edu]):
        score += 1
    s_income = scholarship.get("max_income", 999999)
    try:
        u_income = int(income or 999999)
        s_income = int(s_income) if str(s_income).replace('.','').isdigit() else 999999
    except:
        u_income = 999999
    if u_income <= s_income:
        score += 1
    s_category = str(scholarship.get("category", "all")).lower()
    u_category = (category or "general").lower()
    if s_category == "all" or s_category == u_category or u_category in s_category:
        score += 1
    s_state = str(scholarship.get("state", "all")).lower()
    u_state = (state or "").lower()
    if s_state == "all" or s_state == u_state:
        score += 1
    s_course = str(scholarship.get("course", "all")).lower()
    u_course = (course or "").lower()
    if s_course == "all" or s_course in u_course or u_course in s_course:
        score += 1
    return int((score / total) * 100)

# ==============================
# LOAD CSV SCHOLARSHIPS
# ==============================
def load_csv_scholarships():
    csv_scholarships = []
    csv_path = os.path.join(os.path.dirname(__file__), "scholarships_full.csv")
    if not os.path.exists(csv_path):
        return []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            seen = set()
            for row in reader:
                name = row.get("scholarship_name", "").strip()
                state = row.get("state", "All").strip()
                district = row.get("district", "All").strip()
                key = f"{name}_{state}_{district}"
                if key in seen:
                    continue
                seen.add(key)
                try:
                    income_val = int(row.get("income_limit", 999999))
                except:
                    income_val = 999999
                edu = row.get("education_level", "all").strip().lower()
                state_lower = state.lower()
                if state_lower == "all":
                    scholarship_type = "National"
                elif state_lower == "odisha":
                    scholarship_type = "Odisha State"
                else:
                    scholarship_type = f"{state} State"
                csv_scholarships.append({
                    "name": name,
                    "provider": row.get("provider", "Government").strip(),
                    "amount": "As per scheme",
                    "deadline": row.get("deadline", "31 Mar 2026").strip(),
                    "link": row.get("link", "https://scholarships.gov.in").strip(),
                    "type": scholarship_type,
                    "education": edu,
                    "max_income": income_val,
                    "category": row.get("category", "all").strip().lower(),
                    "state": state_lower,
                    "course": "all",
                    "district": district
                })
    except Exception as e:
        print(f"CSV Error: {e}")
    return csv_scholarships

# ==============================
# HARDCODED SCHOLARSHIPS
# ==============================
HARDCODED_SCHOLARSHIPS = [
    {"name": "AICTE Pragati Scholarship", "provider": "AICTE", "amount": "50,000 per year", "deadline": "31 Dec 2026", "link": "https://www.aicte-india.org/", "type": "National", "education": "undergraduate", "max_income": 800000, "category": "all", "state": "all", "course": "engineering"},
    {"name": "AICTE Saksham Scholarship", "provider": "AICTE", "amount": "50,000 per year", "deadline": "31 Dec 2026", "link": "https://www.aicte-india.org/", "type": "National", "education": "undergraduate", "max_income": 800000, "category": "all", "state": "all", "course": "engineering"},
    {"name": "PM Scholarship Scheme", "provider": "Government of India", "amount": "25,000 per year", "deadline": "15 Oct 2026", "link": "https://ksb.gov.in/", "type": "National", "education": "undergraduate", "max_income": 600000, "category": "all", "state": "all", "course": "all"},
    {"name": "National Scholarship Portal (NSP)", "provider": "Government of India", "amount": "Varies by scheme", "deadline": "30 Nov 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "undergraduate", "max_income": 800000, "category": "all", "state": "all", "course": "all"},
    {"name": "INSPIRE Scholarship", "provider": "Dept of Science & Technology", "amount": "80,000 per year", "deadline": "15 Sep 2026", "link": "https://online-inspire.gov.in/", "type": "National", "education": "undergraduate", "max_income": 999999, "category": "all", "state": "all", "course": "science"},
    {"name": "Begum Hazrat Mahal Scholarship", "provider": "Maulana Azad Foundation", "amount": "12,000 per year", "deadline": "30 Sep 2026", "link": "https://maef.nic.in/", "type": "National", "education": "12th", "max_income": 200000, "category": "minority", "state": "all", "course": "all"},
    {"name": "Sitaram Jindal Scholarship", "provider": "Sitaram Jindal Foundation", "amount": "2,000 per month", "deadline": "31 Aug 2026", "link": "https://sitaramjindalfoundation.org/", "type": "National", "education": "undergraduate", "max_income": 300000, "category": "all", "state": "all", "course": "all"},
    {"name": "Vidyasaarathi Scholarship", "provider": "NSDL e-Governance", "amount": "20,000 per year", "deadline": "31 Oct 2026", "link": "https://www.vidyasaarathi.co.in/", "type": "National", "education": "undergraduate", "max_income": 600000, "category": "all", "state": "all", "course": "all"},
    {"name": "Post Matric Scholarship (SC)", "provider": "Ministry of Social Justice", "amount": "15,000 per year", "deadline": "30 Nov 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "12th", "max_income": 250000, "category": "sc", "state": "all", "course": "all"},
    {"name": "Post Matric Scholarship (ST)", "provider": "Ministry of Tribal Affairs", "amount": "15,000 per year", "deadline": "30 Nov 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "12th", "max_income": 250000, "category": "st", "state": "all", "course": "all"},
    {"name": "Post Matric Scholarship (OBC)", "provider": "Ministry of Social Justice", "amount": "12,000 per year", "deadline": "30 Nov 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "12th", "max_income": 100000, "category": "obc", "state": "all", "course": "all"},
    {"name": "Central Sector Scheme Scholarship", "provider": "Ministry of Education", "amount": "12,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "undergraduate", "max_income": 800000, "category": "all", "state": "all", "course": "all"},
    {"name": "Minority Pre-Matric Scholarship", "provider": "Ministry of Minority Affairs", "amount": "10,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "10th", "max_income": 100000, "category": "minority", "state": "all", "course": "all"},
    {"name": "Minority Post-Matric Scholarship", "provider": "Ministry of Minority Affairs", "amount": "15,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "12th", "max_income": 200000, "category": "minority", "state": "all", "course": "all"},
    {"name": "Merit cum Means Scholarship (Minority)", "provider": "Ministry of Minority Affairs", "amount": "30,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "undergraduate", "max_income": 250000, "category": "minority", "state": "all", "course": "all"},
    {"name": "Ishan Uday Scholarship", "provider": "UGC", "amount": "7,800 per month", "deadline": "30 Sep 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "undergraduate", "max_income": 600000, "category": "all", "state": "all", "course": "all"},
    {"name": "KVPY Fellowship", "provider": "Dept of Science & Technology", "amount": "80,000 per year", "deadline": "30 Sep 2026", "link": "https://kvpy.iisc.ac.in/main/index.htm", "type": "National", "education": "12th", "max_income": 999999, "category": "all", "state": "all", "course": "science"},
    {"name": "NMMS Scholarship", "provider": "Ministry of Education", "amount": "12,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "National", "education": "10th", "max_income": 150000, "category": "all", "state": "all", "course": "all"},
    {"name": "Odisha Post-Matric Scholarship (SC)", "provider": "Odisha SC & ST Dept", "amount": "18,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "Odisha State", "education": "12th", "max_income": 250000, "category": "sc", "state": "odisha", "course": "all"},
    {"name": "Odisha Post-Matric Scholarship (ST)", "provider": "Odisha ST & SC Dev Dept", "amount": "18,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "Odisha State", "education": "12th", "max_income": 250000, "category": "st", "state": "odisha", "course": "all"},
    {"name": "Odisha Merit Scholarship", "provider": "Odisha Higher Education Dept", "amount": "10,000 per year", "deadline": "30 Nov 2026", "link": "https://dheodisha.gov.in/", "type": "Odisha State", "education": "undergraduate", "max_income": 600000, "category": "all", "state": "odisha", "course": "all"},
    {"name": "Biju Swasthya Kalyan Yojana", "provider": "Odisha Govt - Health Dept", "amount": "25,000 per year", "deadline": "31 Dec 2026", "link": "https://www.odisha.gov.in/", "type": "Odisha State", "education": "undergraduate", "max_income": 500000, "category": "all", "state": "odisha", "course": "medical"},
    {"name": "Odisha Medhabruti Scholarship", "provider": "Odisha Higher Education Dept", "amount": "15,000 per year", "deadline": "30 Sep 2026", "link": "https://dheodisha.gov.in/", "type": "Odisha State", "education": "undergraduate", "max_income": 600000, "category": "all", "state": "odisha", "course": "science"},
    {"name": "Gopabandhu Scholarship (Odisha)", "provider": "Odisha Govt", "amount": "12,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "Odisha State", "education": "undergraduate", "max_income": 300000, "category": "all", "state": "odisha", "course": "all"},
    {"name": "Odisha Police Welfare Scholarship", "provider": "Odisha Police Dept", "amount": "10,000 per year", "deadline": "30 Nov 2026", "link": "https://www.odishapolice.gov.in/", "type": "Odisha State", "education": "undergraduate", "max_income": 400000, "category": "all", "state": "odisha", "course": "all"},
    {"name": "Prerana Scholarship (Odisha Girls)", "provider": "Odisha Women & Child Dept", "amount": "10,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in/", "type": "Odisha State", "education": "12th", "max_income": 300000, "category": "all", "state": "odisha", "course": "all"},
    # Maharashtra
    {"name": "MahaDBT Scholarship", "provider": "Maharashtra Govt", "amount": "Varies", "deadline": "31 Dec 2026", "link": "https://mahadbt.maharashtra.gov.in", "type": "Maharashtra State", "education": "undergraduate", "max_income": 800000, "category": "all", "state": "maharashtra", "course": "all"},
    {"name": "Maharashtra EBC Scholarship", "provider": "Maharashtra Govt", "amount": "15,000 per year", "deadline": "31 Dec 2026", "link": "https://mahadbt.maharashtra.gov.in", "type": "Maharashtra State", "education": "undergraduate", "max_income": 100000, "category": "ebc", "state": "maharashtra", "course": "all"},
    {"name": "Maharashtra OBC Scholarship", "provider": "Maharashtra Govt", "amount": "12,000 per year", "deadline": "31 Dec 2026", "link": "https://mahadbt.maharashtra.gov.in", "type": "Maharashtra State", "education": "undergraduate", "max_income": 100000, "category": "obc", "state": "maharashtra", "course": "all"},
    # Karnataka
    {"name": "Karnataka Sanchi Scholarship", "provider": "Karnataka Govt", "amount": "10,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "Karnataka State", "education": "undergraduate", "max_income": 600000, "category": "all", "state": "karnataka", "course": "all"},
    {"name": "Karnataka SC/ST Scholarship", "provider": "Karnataka SC/ST Dept", "amount": "15,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "Karnataka State", "education": "undergraduate", "max_income": 250000, "category": "sc", "state": "karnataka", "course": "all"},
    # Tamil Nadu
    {"name": "Tamil Nadu Chief Minister Scholarship", "provider": "Tamil Nadu Govt", "amount": "12,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "Tamil Nadu State", "education": "undergraduate", "max_income": 200000, "category": "all", "state": "tamil nadu", "course": "all"},
    {"name": "Tamil Nadu BC/MBC Scholarship", "provider": "Tamil Nadu Govt", "amount": "10,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "Tamil Nadu State", "education": "undergraduate", "max_income": 100000, "category": "obc", "state": "tamil nadu", "course": "all"},
    # Uttar Pradesh
    {"name": "UP Post Matric Scholarship", "provider": "Uttar Pradesh Govt", "amount": "15,000 per year", "deadline": "30 Nov 2026", "link": "https://scholarship.up.gov.in", "type": "Uttar Pradesh State", "education": "12th", "max_income": 200000, "category": "all", "state": "uttar pradesh", "course": "all"},
    {"name": "Samajwadi Scholarship UP", "provider": "Uttar Pradesh Govt", "amount": "20,000 per year", "deadline": "30 Nov 2026", "link": "https://scholarship.up.gov.in", "type": "Uttar Pradesh State", "education": "undergraduate", "max_income": 300000, "category": "all", "state": "uttar pradesh", "course": "all"},
    # West Bengal
    {"name": "Aikyashree Scholarship WB", "provider": "West Bengal Govt", "amount": "10,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "West Bengal State", "education": "undergraduate", "max_income": 200000, "category": "minority", "state": "west bengal", "course": "all"},
    {"name": "Kanyashree Prakalpa WB", "provider": "West Bengal Govt", "amount": "25,000 per year", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "West Bengal State", "education": "12th", "max_income": 120000, "category": "all", "state": "west bengal", "course": "all"},
    # Telangana
    {"name": "TS ePass Scholarship", "provider": "Telangana Govt", "amount": "Varies", "deadline": "31 Oct 2026", "link": "https://telanganaepass.cgg.gov.in", "type": "Telangana State", "education": "undergraduate", "max_income": 200000, "category": "sc", "state": "telangana", "course": "all"},
    # Andhra Pradesh
    {"name": "AP Jagananna Vidya Deevena", "provider": "Andhra Pradesh Govt", "amount": "Full fee reimbursement", "deadline": "31 Oct 2026", "link": "https://scholarships.gov.in", "type": "Andhra Pradesh State", "education": "undergraduate", "max_income": 250000, "category": "all", "state": "andhra pradesh", "course": "all"},
    # Jharkhand
    {"name": "Jharkhand E-Kalyan Scholarship", "provider": "Jharkhand Govt", "amount": "19,000 per year", "deadline": "30 Nov 2026", "link": "https://ekalyan.cgg.gov.in", "type": "Jharkhand State", "education": "undergraduate", "max_income": 250000, "category": "sc", "state": "jharkhand", "course": "all"},
]

def get_all_scholarships_combined():
    csv_data = load_csv_scholarships()
    combined = HARDCODED_SCHOLARSHIPS.copy()
    existing_names = {s["name"] for s in combined}
    for s in csv_data:
        if s["name"] not in existing_names:
            combined.append(s)
            existing_names.add(s["name"])
    return combined

# ==============================
# GET SCHOLARSHIPS
# ==============================
@routes.route("/get_scholarships", methods=["GET", "POST"])
def get_scholarships():
    education = income = category = state = course = None
    filter_type = "all"
    try:
        if request.method == "POST":
            data = request.get_json()
            email = data.get("email") if data else None
            filter_type = data.get("filter", "all") if data else "all"
            if email:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE email=?", (email,))
                user = cur.fetchone()
                conn.close()
                if user:
                    education = user["education"]
                    income = user["income"]
                    category = user["category"]
                    state = user["state"]
                    course = user["course"]
    except:
        pass

    all_scholarships = get_all_scholarships_combined()
    result = []
    for s in all_scholarships:
        s_type = s.get("type", "National")
        s_state = s.get("state", "all").lower()
        if filter_type == "national":
            if s_type != "National":
                continue
        elif filter_type == "state":
            if s_type != "Odisha State" and s_state != "odisha":
                continue
        elif filter_type == "other":
            if s_type == "National":
                continue
            if s_type == "Odisha State" or s_state == "odisha":
                continue
        match = calculate_match(s, education, income, category, state, course)
        if match >= 40:
            result.append({
                "name": s["name"],
                "provider": s["provider"],
                "amount": s.get("amount", "As per scheme"),
                "deadline": s["deadline"],
                "match": str(match) + "%",
                "link": s["link"],
                "type": s_type,
                "district": s.get("district", "")
            })
    result.sort(key=lambda x: int(x["match"].replace("%", "")), reverse=True)
    return jsonify(result[:50])

@routes.route("/get_total_count", methods=["GET"])
def get_total_count():
    all_s = get_all_scholarships_combined()
    return jsonify({"total": len(all_s)})

# ==============================
# GET STATE SCHOLARSHIPS (for Map)
# ==============================
@routes.route("/get_state_scholarships", methods=["POST"])
def get_state_scholarships():
    try:
        data = request.get_json()
        state_name = data.get("state", "").strip().lower()

        all_scholarships = get_all_scholarships_combined()
        result = []

        for s in all_scholarships:
            s_state = s.get("state", "all").lower()
            s_type  = s.get("type",  "").lower()
            s_name  = s.get("name",  "").lower()

            # Match if: scholarship is for this state, OR national (all states), OR type contains state name
            is_national   = s_state == "all" or s.get("type") == "National"
            is_this_state = s_state == state_name or state_name in s_type or state_name in s_name

            if is_national or is_this_state:
                result.append({
                    "name":     s["name"],
                    "provider": s.get("provider", "Government"),
                    "amount":   s.get("amount", "As per scheme"),
                    "deadline": s.get("deadline", "N/A"),
                    "type":     s.get("type", "National"),
                    "match":    "80%" if is_this_state else "60%",
                    "link":     s.get("link", "https://scholarships.gov.in")
                })

        # State-specific ones first, then national
        result.sort(key=lambda x: (0 if x["match"] == "80%" else 1, x["name"]))

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# ADMIN
# ==============================
ADMIN_EMAIL = "admin@scholarai.com"
ADMIN_PASSWORD = "admin123"

@routes.route("/admin_login", methods=["POST"])
def admin_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return jsonify({"message": "Admin login success"})
    return jsonify({"error": "Invalid admin credentials"}), 401

@routes.route("/admin/get_users", methods=["GET"])
def get_all_users():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, education, income, category, state, course, documents FROM users")
    users = cur.fetchall()
    conn.close()
    result = []
    for u in users:
        docs = u["documents"] or ""
        doc_count = len([d for d in docs.split(",") if d]) if docs else 0
        result.append({
            "id": u["id"],
            "name": u["name"] or "N/A",
            "email": u["email"] or "N/A",
            "education": u["education"] or "Not set",
            "income": str(u["income"]) if u["income"] else "Not set",
            "category": u["category"] or "Not set",
            "state": u["state"] or "Not set",
            "course": u["course"] or "Not set",
            "documents": f"{doc_count}/6 uploaded"
        })
    return jsonify(result)

@routes.route("/admin/get_stats", methods=["GET"])
def get_stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as total FROM users")
    total = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) as complete FROM users WHERE education IS NOT NULL AND education != ''")
    complete = cur.fetchone()["complete"]
    conn.close()
    all_scholarships = get_all_scholarships_combined()
    return jsonify({
        "total_users": total,
        "profiles_complete": complete,
        "total_scholarships": len(all_scholarships)
    })

@routes.route("/admin/delete_user", methods=["POST"])
def delete_user():
    data = request.get_json()
    user_id = data.get("id")
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "User deleted successfully"})

# ==============================
# KEYWORD FALLBACK
# ==============================
def generate_reply(msg, lang="en"):
    msg_lower = msg.lower()
    if "aicte" in msg_lower or "pragati" in msg_lower:
        replies = {"en": "AICTE Pragati gives Rs.50,000/year for female engineering students. Deadline: 31 Dec 2026. Apply: https://www.aicte-india.org/", "hi": "AICTE प्रगति Rs.50,000/वर्ष। आवेदन: https://www.aicte-india.org/", "od": "AICTE Rs.50,000/ବର୍ଷ। ଆବେଦନ: https://www.aicte-india.org/"}
    elif "inspire" in msg_lower:
        replies = {"en": "INSPIRE gives Rs.80,000/year for science students. Apply: https://online-inspire.gov.in/", "hi": "INSPIRE Rs.80,000/वर्ष। आवेदन: https://online-inspire.gov.in/", "od": "INSPIRE Rs.80,000/ବର୍ଷ। ଆବେଦନ: https://online-inspire.gov.in/"}
    elif "odisha" in msg_lower:
        replies = {"en": "Odisha has 280+ scholarships! Top ones: Medhabruti, Gopabandhu, Prerana, SC/ST. Apply: https://scholarship.odisha.gov.in", "hi": "ओडिशा में 280+ छात्रवृत्तियां! आवेदन: https://scholarship.odisha.gov.in", "od": "ଓଡ଼ିଶାରେ 280+ ଛାତ୍ରବୃତ୍ତି! ଆବେଦନ: https://scholarship.odisha.gov.in"}
    elif "maharashtra" in msg_lower:
        replies = {"en": "Maharashtra scholarships. Apply: https://mahadbt.maharashtra.gov.in", "hi": "महाराष्ट्र। आवेदन: https://mahadbt.maharashtra.gov.in", "od": "ମହାରାଷ୍ଟ୍ର। ଆବେଦନ: https://mahadbt.maharashtra.gov.in"}
    elif "document" in msg_lower or "upload" in msg_lower:
        replies = {"en": "Required documents: Aadhaar Card, Income Certificate, Caste Certificate, Marksheet, Bank Passbook, Domicile Certificate.", "hi": "आवश्यक: आधार, आय प्रमाण, जाति प्रमाण, मार्कशीट, बैंक पासबुक।", "od": "ଆବଶ୍ୟକ: ଆଧାର, ଆୟ ପ୍ରମାଣ, ଜାତି ପ୍ରମାଣ, ମାର୍କଶିଟ।"}
    elif "deadline" in msg_lower or "last date" in msg_lower:
        replies = {"en": "Key deadlines: AICTE Dec 2026, PM Oct 2026, INSPIRE Sep 2026, NSP Nov 2026.", "hi": "तिथियां: AICTE दिसंबर, PM अक्टूबर, INSPIRE सितंबर 2026।", "od": "ଶେଷ ତାରିଖ: AICTE ଡିସେମ୍ବର, PM ଅକ୍ଟୋବର 2026।"}
    else:
        replies = {"en": "Ask me: 'Odisha scholarships', 'AICTE Pragati', 'SC/ST scholarships'. Apply: https://scholarships.gov.in/", "hi": "पूछें: 'ओडिशा छात्रवृत्ति', 'AICTE प्रगति'। आवेदन: https://scholarships.gov.in/", "od": "ପଚାରନ୍ତୁ: 'Odisha ଛାତ୍ରବୃତ୍ତି'। ଆବେଦନ: https://scholarships.gov.in/"}
    return replies.get(lang, replies["en"])

# ==============================
# CHATBOT
# ==============================
@routes.route("/chat", methods=["GET", "POST"])
def chat():
    if request.method == "GET":
        return jsonify({"message": "Chatbot is running!"})
    data = request.get_json()
    message = data.get("message", "").strip()
    lang = data.get("lang", "en")
    email = data.get("email", "")
    if not message:
        return jsonify({"reply": "Please type a message!", "source": "error"})
    user_profile = ""
    if email:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT name, education, income, category, state, course FROM users WHERE email=?", (email,))
            user = cur.fetchone()
            conn.close()
            if user:
                user_profile = (f"Student profile: Name={user['name']}, Education={user['education'] or 'not set'}, Category={user['category'] or 'not set'}, State={user['state'] or 'not set'}, Income=Rs.{user['income'] or 'not set'}, Course={user['course'] or 'not set'}")
        except:
            pass
    lang_instruction = {"hi": "Reply in Hindi language only.", "od": "Reply in Odia language only."}.get(lang, "Reply in English.")
    system_prompt = f"""You are ScholarAI, an expert Indian scholarship assistant. ALWAYS answer every question helpfully.
Key scholarships: AICTE Pragati/Saksham (Rs.50,000) aicte-india.org, PM Scholarship (Rs.25,000) ksb.gov.in, INSPIRE (Rs.80,000) online-inspire.gov.in, NSP scholarships.gov.in, Odisha Medhabruti (Rs.15,000) dheodisha.gov.in, MahaDBT mahadbt.maharashtra.gov.in, Reliance Foundation (Rs.2,00,000), Post Matric SC/ST/OBC scholarships.gov.in
Instructions: 1. Give direct helpful answer 2. List 3-5 scholarships with amounts and links 3. Personalize based on student profile 4. Be warm and encouraging 5. Keep to 5-8 lines 6. {lang_instruction}
{user_profile}"""
    if GEMINI_AVAILABLE:
        try:
            response = gemini_model.generate_content(f"{system_prompt}\n\nStudent question: {message}")
            return jsonify({"reply": response.text, "source": "gemini"})
        except Exception as e:
            print(f"Gemini error: {e}")
    reply = generate_reply(message, lang)
    return jsonify({"reply": reply, "source": "keyword"})

# ==============================
# PDF DOWNLOAD
# ==============================
@routes.route("/download_scholarships_pdf", methods=["GET", "POST"])
def download_scholarships_pdf():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        email = request.args.get("email", "")
        state_filter = request.args.get("state", "").strip().lower()

        user_name = "Student"
        if email:
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("SELECT name, state FROM users WHERE email=?", (email,))
                user = cur.fetchone()
                conn.close()
                if user:
                    user_name = user["name"] or "Student"
                    if not state_filter:
                        state_filter = (user["state"] or "").lower()
            except:
                pass

        # Get scholarships filtered by state
        all_scholarships = get_all_scholarships_combined()
        national = []
        state_specific = []

        for s in all_scholarships:
            s_state = s.get("state", "all").lower()
            s_type = s.get("type", "National")
            if s_state == "all" or s_type == "National":
                national.append(s)
            elif state_filter and (s_state == state_filter or state_filter in s_type.lower()):
                state_specific.append(s)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title = f"ScholarAI — Scholarship Report"
        if state_filter:
            title += f" ({state_filter.title()})"
        elements.append(Paragraph(f"<b>🎓 {title}</b>", styles["Title"]))
        elements.append(Spacer(1, 5))
        elements.append(Paragraph(f"<i>Prepared for: {user_name} | India's Smartest Scholarship Finder</i>", styles["Normal"]))
        elements.append(Spacer(1, 15))

        # National Scholarships Table
        elements.append(Paragraph("<b>📋 Top National Scholarships</b>", styles["Heading2"]))
        elements.append(Spacer(1, 8))
        nat_data = [["#", "Scholarship Name", "Amount", "Category", "Deadline"]]
        for i, s in enumerate(national[:15], 1):
            nat_data.append([
                str(i),
                s["name"][:35],
                s.get("amount", "As per scheme")[:20],
                s.get("category", "All").title()[:20],
                s.get("deadline", "N/A")
            ])
        t1 = Table(nat_data, colWidths=[25, 165, 80, 120, 85])
        t1.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#667eea")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f0f4ff")]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        elements.append(t1)
        elements.append(Spacer(1, 15))

        # State-specific Scholarships Table
        if state_specific:
            state_title = state_filter.title()
            elements.append(Paragraph(f"<b>🏛️ {state_title} State Scholarships</b>", styles["Heading2"]))
            elements.append(Spacer(1, 8))
            state_data = [["#", "Scholarship Name", "Amount", "Category", "Deadline"]]
            for i, s in enumerate(state_specific[:15], 1):
                state_data.append([
                    str(i),
                    s["name"][:35],
                    s.get("amount", "As per scheme")[:20],
                    s.get("category", "All").title()[:20],
                    s.get("deadline", "N/A")
                ])
            t2 = Table(state_data, colWidths=[25, 165, 80, 120, 85])
            t2.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#764ba2")),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 8),
                ("ALIGN", (0,0), (-1,-1), "CENTER"),
                ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f5f0ff")]),
                ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING", (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ]))
            elements.append(t2)
            elements.append(Spacer(1, 15))

        # Links
        elements.append(Paragraph("<b>🔗 Key Application Links</b>", styles["Heading2"]))
        elements.append(Spacer(1, 5))
        for name, link in [
            ("National Scholarship Portal", "scholarships.gov.in"),
            ("AICTE Scholarships", "aicte-india.org"),
            ("Odisha Scholarships", "dheodisha.gov.in"),
            ("Maharashtra MahaDBT", "mahadbt.maharashtra.gov.in"),
            ("INSPIRE Science", "online-inspire.gov.in"),
        ]:
            elements.append(Paragraph(f"• <b>{name}:</b> https://www.{link}", styles["Normal"]))
            elements.append(Spacer(1, 3))

        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<i>Generated by ScholarAI — India's Smartest Scholarship Finder</i>", styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        fname = f"ScholarAI_{state_filter.title() if state_filter else 'All'}_Scholarships.pdf"
        return send_file(buffer, as_attachment=True, download_name=fname, mimetype="application/pdf")

    except ImportError:
        return jsonify({"error": "Please run: pip install reportlab==4.0.4"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# STATE MAP DATA
# ==============================
@routes.route("/get_map_data", methods=["GET"])
def get_map_data():
    map_data = [
        {"state": "Odisha", "count": 45, "top": "Medhabruti, Gopabandhu, Prerana", "link": "https://scholarship.odisha.gov.in", "lat": 20.9517, "lng": 85.0985},
        {"state": "Maharashtra", "count": 38, "top": "MahaDBT, EBC, OBC Scholarship", "link": "https://mahadbt.maharashtra.gov.in", "lat": 19.7515, "lng": 75.7139},
        {"state": "Karnataka", "count": 32, "top": "Sanchi Scholarship, SC/ST Scheme", "link": "https://scholarships.gov.in", "lat": 15.3173, "lng": 75.7139},
        {"state": "Tamil Nadu", "count": 30, "top": "Chief Minister Scholarship, BC/MBC", "link": "https://scholarships.gov.in", "lat": 11.1271, "lng": 78.6569},
        {"state": "Uttar Pradesh", "count": 42, "top": "UP Scholarship, Samajwadi Scholarship", "link": "https://scholarship.up.gov.in", "lat": 26.8467, "lng": 80.9462},
        {"state": "West Bengal", "count": 28, "top": "Aikyashree, Kanyashree, SC/ST", "link": "https://scholarships.gov.in", "lat": 22.9868, "lng": 87.8550},
        {"state": "Rajasthan", "count": 25, "top": "Devnarayan Scholarship, SC/ST", "link": "https://scholarships.gov.in", "lat": 27.0238, "lng": 74.2179},
        {"state": "Madhya Pradesh", "count": 27, "top": "Vikramaditya Scholarship, OBC", "link": "https://scholarships.gov.in", "lat": 22.9734, "lng": 78.6569},
        {"state": "Bihar", "count": 24, "top": "Bihar Post Matric, BC/EBC", "link": "https://scholarships.gov.in", "lat": 25.0961, "lng": 85.3131},
        {"state": "Gujarat", "count": 22, "top": "Gujarat Scholarship, SC/ST/OBC", "link": "https://scholarships.gov.in", "lat": 22.2587, "lng": 71.1924},
        {"state": "Andhra Pradesh", "count": 26, "top": "AP Scholarship, Jagananna", "link": "https://scholarships.gov.in", "lat": 15.9129, "lng": 79.7400},
        {"state": "Telangana", "count": 24, "top": "TS ePass, SC/ST Scholarship", "link": "https://telanganaepass.cgg.gov.in", "lat": 18.1124, "lng": 79.0193},
        {"state": "Kerala", "count": 20, "top": "Kerala Scholarship, DCSE", "link": "https://scholarships.gov.in", "lat": 10.8505, "lng": 76.2711},
        {"state": "Punjab", "count": 18, "top": "Punjab Post Matric, SC/ST", "link": "https://scholarships.gov.in", "lat": 31.1471, "lng": 75.3412},
        {"state": "Haryana", "count": 19, "top": "Haryana Scholarship, BC/EWS", "link": "https://scholarships.gov.in", "lat": 29.0588, "lng": 76.0856},
        {"state": "Jharkhand", "count": 21, "top": "Jharkhand E-Kalyan, SC/ST/OBC", "link": "https://ekalyan.cgg.gov.in", "lat": 23.6102, "lng": 85.2799},
        {"state": "Assam", "count": 16, "top": "Assam Scholarship, Ishan Uday", "link": "https://scholarships.gov.in", "lat": 26.2006, "lng": 92.9376},
        {"state": "Chhattisgarh", "count": 17, "top": "CG Scholarship, SC/ST", "link": "https://scholarships.gov.in", "lat": 21.2787, "lng": 81.8661},
        {"state": "Himachal Pradesh", "count": 14, "top": "HP Merit, Dr Ambedkar Scheme", "link": "https://scholarships.gov.in", "lat": 31.1048, "lng": 77.1734},
        {"state": "Uttarakhand", "count": 13, "top": "UK Scholarship, SC/ST/OBC", "link": "https://scholarships.gov.in", "lat": 30.0668, "lng": 79.0193},
    ]
    return jsonify(map_data)

# ==============================
# EMAIL NOTIFICATIONS
# ==============================
from flask_mail import Message

def send_email(to_email, subject, body_html):
    try:
        from flask import current_app
        mail = current_app.extensions.get("mail")
        if not mail:
            print("❌ Mail extension not found!")
            return False
        msg = Message(subject=subject, recipients=[to_email], html=body_html)
        mail.send(msg)
        print(f"✅ Email sent to: {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

@routes.route("/send_welcome_email", methods=["POST"])
def send_welcome_email():
    try:
        data = request.get_json()
        email = data.get("email")
        name = data.get("name")
        html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:30px;border-radius:12px;text-align:center;">
                <h1 style="color:white;margin:0;">🎓 Welcome to ScholarAI!</h1>
            </div>
            <div style="background:white;padding:30px;border-radius:12px;margin-top:20px;border:1px solid #eee;">
                <h2>Hello {name}! 👋</h2>
                <p>Welcome to ScholarAI — India's smartest scholarship finder!</p>
                <ul><li>🎯 AI-matched scholarships</li><li>💬 AI chatbot guidance</li><li>📋 Document management</li><li>⏰ Deadline reminders</li></ul>
                <div style="text-align:center;margin-top:25px;">
                    <a href="http://127.0.0.1:5000/dashboard" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:14px 30px;border-radius:8px;text-decoration:none;font-weight:bold;">Go to Dashboard →</a>
                </div>
            </div>
        </div>"""
        success = send_email(to_email=email, subject="🎓 Welcome to ScholarAI!", body_html=html)
        if success:
            return jsonify({"message": "Welcome email sent!"})
        return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@routes.route("/send_deadline_reminder", methods=["POST"])
def send_deadline_reminder():
    try:
        data = request.get_json()
        email = data.get("email")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM users WHERE email=?", (email,))
        user = cur.fetchone()
        conn.close()
        if not user:
            return jsonify({"error": "User not found"}), 404
        name = user["name"]
        html = f"""<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
            <div style="background:linear-gradient(135deg,#f093fb,#f5576c);padding:30px;border-radius:12px;text-align:center;">
                <h1 style="color:white;margin:0;">⏰ Scholarship Deadline Alert!</h1>
            </div>
            <div style="background:white;padding:30px;border-radius:12px;margin-top:20px;border:1px solid #eee;">
                <h2>Hello {name}!</h2>
                <p>These scholarships have upcoming deadlines — apply now!</p>
                <table style="width:100%;border-collapse:collapse;">
                    <tr style="background:#f8f9ff;"><th style="padding:10px;color:#667eea;">Scholarship</th><th style="padding:10px;color:#667eea;">Amount</th><th style="padding:10px;color:#667eea;">Deadline</th></tr>
                    <tr><td style="padding:10px;">AICTE Pragati</td><td style="padding:10px;color:#667eea;">Rs.50,000/yr</td><td style="padding:10px;">31 Dec 2026</td></tr>
                    <tr><td style="padding:10px;">NSP Portal</td><td style="padding:10px;color:#667eea;">Varies</td><td style="padding:10px;">30 Nov 2026</td></tr>
                    <tr><td style="padding:10px;">PM Scholarship</td><td style="padding:10px;color:#667eea;">Rs.25,000/yr</td><td style="padding:10px;">15 Oct 2026</td></tr>
                </table>
                <div style="text-align:center;margin-top:25px;">
                    <a href="http://127.0.0.1:5000/dashboard" style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:14px 30px;border-radius:8px;text-decoration:none;font-weight:bold;">View All Scholarships →</a>
                </div>
            </div>
        </div>"""
        success = send_email(to_email=email, subject="⏰ Scholarship Deadlines Coming Up!", body_html=html)
        if success:
            return jsonify({"message": f"Reminder sent to {email}!"})
        return jsonify({"error": "Failed to send email"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==============================
# TEST ROUTE
# ==============================
@routes.route("/test")
def test():
    all_s = get_all_scholarships_combined()
    status = "✅ Gemini AI ready" if GEMINI_AVAILABLE else "❌ Gemini not working"
    return f"Server OK! Scholarships: {len(all_s)} | {status}"