import os
import pandas as pd

# ==============================
# LOAD SCHOLARSHIP CSV
# ==============================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(CURRENT_DIR, "scholarships_full.csv")

df = pd.read_csv(CSV_PATH)

# ==============================
# REQUIRED DOCUMENTS
# ==============================

REQUIRED_DOCUMENTS = [
    "Aadhaar",
    "Income Certificate",
    "Caste Certificate",
    "Marksheet"
]

# ==============================
# DOCUMENT MATCH FUNCTION
# ==============================

def calculate_document_match(uploaded_docs):

    uploaded_docs = [d.strip() for d in uploaded_docs]

    matched = set(uploaded_docs) & set(REQUIRED_DOCUMENTS)
    missing = set(REQUIRED_DOCUMENTS) - set(uploaded_docs)

    percentage = int((len(matched) / len(REQUIRED_DOCUMENTS)) * 100)

    return percentage, list(missing)

# ==============================
# MAIN MATCH FUNCTION
# ==============================

def match_scholarships(user):

    results = []

    uploaded_docs = user.get("documents", [])
    doc_percent, missing_docs = calculate_document_match(uploaded_docs)

    for _, row in df.iterrows():

        score = 0

        # ------------------------------
        # Gender match (flexible)
        # ------------------------------
        if "female" in str(row.get("gender", "")).lower():
            score += 10

        # ------------------------------
        # Category match
        # ------------------------------
        if user.get("category", "").lower() in \
           str(row.get("category", "")).lower():
            score += 20

        # ------------------------------
        # State match
        # ------------------------------
        if "all" in str(row.get("state", "")).lower() or \
           user.get("state", "").lower() in \
           str(row.get("state", "")).lower():
            score += 15

        # ------------------------------
        # Income match
        # ------------------------------
        try:
            if int(user.get("income", 0)) <= int(row.get("income_limit", 99999999)):
                score += 25
        except:
            pass

        # ------------------------------
        # Education match
        # ------------------------------
        if user.get("education", "").lower() in \
           str(row.get("education_level", "")).lower():
            score += 20

        # ------------------------------
        # ADD RESULT
        # ------------------------------
        results.append({
            "scholarship_name": row["scholarship_name"],
            "provider": row["provider"],
            "deadline": row["deadline"],
            "application_link": row["link"],

            # ✅ IMPORTANT (frontend uses this)
            "eligibility_match_percent": score,

            "document_match_percent": doc_percent,
            "missing_documents": missing_docs
        })

    # ------------------------------
    # SORT BY BEST MATCH
    # ------------------------------
    results.sort(
        key=lambda x: x["eligibility_match_percent"],
        reverse=True
    )

    return results