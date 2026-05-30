import os
import joblib
import json
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime

app = Flask(__name__)
CORS(app)

print("Loading models...")
salary_model    = joblib.load("career_model.pkl")
encoders        = joblib.load("career_data.pkl")
nlp_model       = joblib.load("nlp_model.pkl")
onet_vectorizer = joblib.load("onet_vectorizer.pkl")
onet_matrix     = joblib.load("onet_matrix.pkl")
df_occ          = joblib.load("onet_occupations.pkl")
skills_map      = joblib.load("onet_skills_map.pkl")
edu_map         = joblib.load("onet_edu_map.pkl")

df_salary = pd.read_csv("tech_salary_dataset.csv")
df_salary["skills"]             = df_salary["skills"].fillna("")
df_salary["certifications"]     = df_salary["certifications"].fillna("")
df_salary["job_title"]          = df_salary["job_title"].fillna("")
df_salary["primary_tech_field"] = df_salary["primary_tech_field"].fillna("")
df_salary["location"]           = df_salary["location"].fillna("")
df_salary["currency"]           = df_salary["currency"].fillna("USD")

with open("career_data.json") as f:
    unique_values = json.load(f)

try:
    with open("region_salary_data.json") as f:
        region_salary_data = json.load(f)
except Exception:
    region_salary_data = {}

try:
    with open("vision_sectors.json") as f:
        VISION_SECTORS = json.load(f)
except Exception:
    VISION_SECTORS = {}

try:
    with open("admin_stats.json") as f:
        admin_stats_base = json.load(f)
except Exception:
    admin_stats_base = {}

print("All models loaded!")

search_log       = []
popular_careers  = Counter()
popular_regions  = Counter()

CURRENCY_SYMBOLS = {
    "KSA":       ("SAR", 3.75),
    "UAE":       ("AED", 3.67),
    "Pakistan":  ("PKR", 278),
    "UK":        ("GBP", 0.79),
    "Europe":    ("EUR", 0.92),
    "India":     ("INR", 83),
    "Japan":     ("JPY", 149),
    "Singapore": ("SGD", 1.35),
    "Australia": ("AUD", 1.53),
    "USA":       ("USD", 1.0),
}

ONET_SALARY_ESTIMATES_USD = {
    # Healthcare
    "surgeon": 250000, "physician": 200000, "doctor": 190000,
    "psychiatrist": 220000, "anesthesiolog": 250000, "radiolog": 210000,
    "dentist": 160000, "orthodont": 180000, "pharmacist": 125000,
    "nurse": 80000, "registered nurse": 80000, "midwife": 75000,
    "therapist": 70000, "physical therapist": 90000, "occupational therapist": 85000,
    "speech": 80000, "optometrist": 120000, "veterinarian": 100000,
    "paramedic": 50000, "medical": 65000, "health": 60000,
    # Engineering
    "aerospace engineer": 120000, "chemical engineer": 110000,
    "civil engineer": 90000, "electrical engineer": 100000,
    "mechanical engineer": 95000, "industrial engineer": 90000,
    "environmental engineer": 88000, "petroleum engineer": 130000,
    "nuclear engineer": 115000, "biomedical engineer": 95000,
    "engineer": 90000,
    # Science & Research
    "physicist": 120000, "astronomer": 110000, "chemist": 80000,
    "biologist": 70000, "microbiologist": 75000, "biochemist": 95000,
    "geologist": 85000, "environmental scientist": 73000,
    "epidemiologist": 78000, "psychologist": 82000, "sociologist": 68000,
    "economist": 105000, "statistician": 95000, "mathematician": 98000,
    "scientist": 80000, "researcher": 75000,
    # Agriculture & Nature
    "farmer": 45000, "farming": 38000, "agriculture": 40000,
    "agricultural": 42000, "forester": 62000, "conservation": 60000,
    "wildlife": 58000, "fishery": 48000, "plant": 50000,
    "horticulturist": 52000, "soil": 58000, "animal": 45000,
    "veterinary": 55000,
    # Business & Finance
    "ceo": 200000, "chief executive": 200000, "executive": 150000,
    "financial manager": 130000, "investment banker": 150000,
    "financial analyst": 85000, "accountant": 70000, "auditor": 72000,
    "actuary": 110000, "budget analyst": 78000, "credit analyst": 68000,
    "loan officer": 65000, "insurance": 60000, "real estate": 65000,
    "manager": 85000, "management": 80000, "administrator": 70000,
    "business": 72000, "consultant": 90000, "analyst": 75000,
    # Legal
    "judge": 130000, "lawyer": 120000, "attorney": 120000,
    "paralegal": 55000, "legal": 65000, "compliance": 75000,
    # Education
    "professor": 85000, "teacher": 58000, "instructor": 60000,
    "principal": 98000, "counselor": 57000, "librarian": 60000,
    "educator": 58000, "tutor": 45000,
    # Arts & Media
    "architect": 85000, "urban planner": 76000,
    "graphic designer": 55000, "ux designer": 85000, "ui designer": 80000,
    "industrial designer": 68000, "interior designer": 60000,
    "fashion designer": 58000, "animator": 65000, "art director": 98000,
    "photographer": 48000, "film": 65000, "director": 80000,
    "writer": 67000, "editor": 60000, "journalist": 55000,
    "public relations": 62000, "marketing": 65000, "advertising": 68000,
    "social media": 55000, "content": 52000,
    # Trades & Construction
    "electrician": 60000, "plumber": 58000, "carpenter": 52000,
    "welder": 48000, "mechanic": 50000, "technician": 55000,
    "construction": 55000, "surveyor": 65000, "drafter": 58000,
    "hvac": 52000, "mason": 48000, "painter": 45000,
    # Protective Services
    "police": 65000, "detective": 85000, "firefighter": 52000,
    "security": 42000, "corrections": 47000,
    # Transportation & Logistics
    "pilot": 130000, "air traffic": 120000, "captain": 90000,
    "truck driver": 48000, "driver": 42000, "logistics": 60000,
    "supply chain": 75000, "warehouse": 38000,
    # Social Services
    "social worker": 52000, "social": 50000, "community": 48000,
    "nonprofit": 50000,
    # Hospitality & Food
    "chef": 55000, "cook": 35000, "baker": 33000,
    "hotel manager": 65000, "hospitality": 50000,
    "event planner": 52000, "travel": 48000, "tourism": 50000,
    # Fallback
    "supervisor": 62000, "coordinator": 52000, "specialist": 60000,
    "operator": 48000, "assistant": 42000, "clerk": 38000,
}

def estimate_onet_salary(title: str) -> int:
    title_lower   = title.lower()
    best_match_len = 0
    best_salary    = 55000
    for keyword, salary in ONET_SALARY_ESTIMATES_USD.items():
        if keyword in title_lower and len(keyword) > best_match_len:
            best_match_len = len(keyword)
            best_salary    = salary
    return best_salary

def fmt_amount(n, symbol):
    if symbol == "PKR":
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M {symbol}"
        elif n >= 1_000:
            return f"{n / 1_000:.0f}K {symbol}"
        return f"{n:,.0f} {symbol}"
    elif symbol in ("AED", "SAR"):
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M {symbol}"
        elif n >= 1_000:
            return f"{n / 1_000:.0f}K {symbol}"
        return f"{n:,.0f} {symbol}"
    elif symbol == "INR":
        if n >= 100_000:
            return f"{n / 100_000:.1f}L {symbol}"
        elif n >= 1_000:
            return f"{n / 1_000:.0f}K {symbol}"
        return f"{n:,.0f} {symbol}"
    else:
        prefix = {"USD": "$", "GBP": "£", "EUR": "€"}.get(symbol, f"{symbol} ")
        if n >= 1_000_000:
            return f"{prefix}{n / 1_000_000:.1f}M"
        elif n >= 1_000:
            return f"{prefix}{n / 1_000:.0f}K"
        return f"{prefix}{n:,.0f}"

def convert_salary(usd_salary, region):
    symbol, rate = CURRENCY_SYMBOLS.get(region, ("USD", 1.0))
    local        = usd_salary * rate
    display      = fmt_amount(local, symbol) + "/yr"
    low          = fmt_amount(local * 0.85, symbol)
    high         = fmt_amount(local * 1.15, symbol)
    return display, f"{low} – {high}/yr"

ROADMAPS = {
    "Full-Stack Development": [
        "Learn HTML, CSS, and JavaScript fundamentals",
        "Master a frontend framework (React or Vue)",
        "Learn backend development (Node.js or Python)",
        "Study databases (SQL and NoSQL)",
        "Build 3-5 full stack projects",
        "Learn Git, deployment, and DevOps basics",
    ],
    "Data Science & ML": [
        "Learn Python and statistics fundamentals",
        "Master pandas, numpy, and matplotlib",
        "Study machine learning algorithms",
        "Work on real datasets from Kaggle",
        "Build a data portfolio with 3+ projects",
        "Get certified (Google Data Analytics / IBM)",
    ],
    "Backend Development": [
        "Master a backend language (Python, Java, or Node.js)",
        "Learn REST API design and development",
        "Study databases (SQL and NoSQL)",
        "Learn authentication and security basics",
        "Master Docker and deployment",
        "Study system design and scalability",
    ],
    "Frontend Development": [
        "Master HTML, CSS, and JavaScript",
        "Learn React or Vue framework",
        "Study UI/UX design principles",
        "Learn state management",
        "Build responsive and accessible websites",
        "Learn testing and performance optimization",
    ],
    "Cybersecurity": [
        "Learn networking fundamentals (TCP/IP, DNS)",
        "Study Linux and command line tools",
        "Learn ethical hacking basics",
        "Get certified (CompTIA Security+ or CEH)",
        "Practice on HackTheBox or TryHackMe",
        "Specialize in a security domain",
    ],
    "DevOps & Cloud": [
        "Master Linux and shell scripting",
        "Learn Git and CI/CD pipelines",
        "Study Docker and Kubernetes",
        "Learn a cloud platform (AWS, Azure, or GCP)",
        "Master infrastructure as code (Terraform)",
        "Get cloud certified (AWS Solutions Architect)",
    ],
    "Mobile Development": [
        "Choose iOS (Swift) or Android (Kotlin)",
        "Or learn cross-platform (Flutter or React Native)",
        "Build UI components and understand mobile UX",
        "Learn API integration and local storage",
        "Publish an app to App Store or Google Play",
        "Learn performance optimization",
    ],
    "default": [
        "Research the key skills needed in your field",
        "Take online courses or get a relevant degree",
        "Build a portfolio with real projects",
        "Network with professionals in the field",
        "Apply for internships or entry-level positions",
        "Keep learning and stay updated",
    ],
}

DEMAND_MAP = {
    "Full-Stack Development":      "High",
    "Data Science & ML":           "Very High",
    "Backend Development":         "High",
    "Frontend Development":        "High",
    "Cybersecurity":               "Very High",
    "DevOps & Cloud":              "Very High",
    "Mobile Development":          "Medium-High",
    "QA & Testing":                "Medium-High",
    "Database & Data Engineering": "High",
    "Game Development":            "Medium",
    "Blockchain & Web3":           "Medium-High",
    "default":                     "High",
}

def build_onet_roadmap(title, skills, edu):
    title_lower = title.lower()
    roadmap     = []
    if edu and str(edu).lower() not in ["nan", "none", ""]:
        roadmap.append(f"Get the required education: {edu}")
    else:
        roadmap.append("Complete a relevant degree or certification in your field")
    if skills:
        roadmap.append(f"Develop core skills: {', '.join(skills[:4])}")
    if any(w in title_lower for w in ["doctor", "physician", "surgeon", "nurse"]):
        roadmap += [
            "Complete medical school or nursing program",
            "Finish clinical internship and residency",
            "Get licensed in your country/state",
            "Join a hospital or clinic as a junior professional",
        ]
    elif any(w in title_lower for w in ["teacher", "instructor", "educator"]):
        roadmap += [
            "Get a teaching degree or education certification",
            "Complete student teaching practicum",
            "Get certified by your education board",
            "Apply for teaching positions",
        ]
    elif any(w in title_lower for w in ["engineer", "engineering"]):
        roadmap += [
            "Complete an engineering degree",
            "Do internships during your studies",
            "Get a professional engineering license",
            "Build practical project experience",
        ]
    elif any(w in title_lower for w in ["lawyer", "attorney", "legal"]):
        roadmap += [
            "Complete a law degree (LLB or JD)",
            "Pass the bar exam",
            "Work as a junior associate at a law firm",
            "Build specialization in a legal area",
        ]
    else:
        roadmap += [
            "Gain entry-level experience through internships",
            "Build a strong professional network",
            "Get certified in key areas",
            "Apply for junior positions and grow",
        ]
    return roadmap[:7]

def is_tech_query(user_text):
    tech_keywords = [
        "code", "coding", "programming", "software", "developer", "web",
        "data", "machine learning", "ai", "artificial intelligence", "python",
        "javascript", "react", "backend", "frontend", "fullstack", "cloud",
        "aws", "docker", "kubernetes", "cybersecurity", "hacking", "mobile",
        "android", "ios", "flutter", "devops", "database", "sql", "blockchain",
    ]
    lower = user_text.lower()
    return any(kw in lower for kw in tech_keywords)

def get_skills_gap(user_skills, required_skills):
    if not user_skills or not required_skills:
        return [], required_skills[:5] if required_skills else []
    user_lower = [s.lower().strip() for s in user_skills]
    have, missing = [], []
    for skill in required_skills:
        skill_lower = skill.lower().strip()
        matched     = any(skill_lower in u or u in skill_lower for u in user_lower)
        if matched:
            have.append(skill)
        else:
            missing.append(skill)
    return have, missing

def get_vision_alignment(career_title, tech_field, region):
    if region not in VISION_SECTORS:
        return None
    vision      = VISION_SECTORS[region]
    title_lower = career_title.lower()
    field_lower = tech_field.lower() if tech_field else ""
    for sector in vision["sectors"]:
        for kw in sector["keywords"]:
            if kw in title_lower or kw in field_lower:
                return {
                    "vision_label": vision["label"],
                    "flag":         vision["flag"],
                    "sector":       sector["name"],
                    "demand":       sector["demand"],
                    "growth":       sector["growth"],
                }
    return None

def get_tech_recommendations(user_text, experience, education, region="USA", user_skills=None):
    proba     = nlp_model.predict_proba([user_text.lower()])[0]
    classes   = nlp_model.classes_
    max_proba = float(proba.max())
    dynamic_threshold = max_proba * 0.40

    top_fields = [
        (classes[i], float(proba[i]))
        for i in proba.argsort()[::-1]
        if proba[i] >= dynamic_threshold and proba[i] > 0.05
    ][:5]

    recommendations = []
    for field, confidence in top_fields:
        field_data = df_salary[df_salary["primary_tech_field"] == field]
        if len(field_data) < 5:
            continue

        top_job    = field_data["job_title"].value_counts().index[0]
        avg_salary = field_data["annual_salary_usd"].mean()

        all_skills  = ";".join(field_data["skills"].tolist())
        skills_list = [s.strip() for s in all_skills.replace(",", ";").split(";") if s.strip()]
        top_skills  = [s for s, _ in Counter(skills_list).most_common(6)]

        all_certs  = ";".join(field_data["certifications"].tolist())
        certs_list = [
            c.strip() for c in all_certs.replace(",", ";").split(";")
            if c.strip() and c.strip().lower() not in ["nan", ""]
        ]
        top_certs = list(dict.fromkeys([c for c, _ in Counter(certs_list).most_common(3)]))

        try:
            def encode_field(col, val):
                le = encoders.get(f"salary_{col}")
                if le and val in le.classes_:
                    return int(le.transform([val])[0])
                return 0

            input_df = pd.DataFrame([{
                "primary_tech_field":     encode_field("primary_tech_field", field),
                "experience_years_total": experience,
                "education_level":        encode_field("education_level", education),
                "employment_type":        encode_field("employment_type", "Full-time"),
                "work_arrangement":       encode_field("work_arrangement", "Remote"),
            }])
            ml_salary        = float(salary_model.predict(input_df)[0])
            final_salary_usd = (avg_salary + ml_salary) / 2
        except Exception:
            final_salary_usd = avg_salary

        salary_display, salary_range = convert_salary(final_salary_usd, region)
        exp_level                    = "Junior" if experience < 2 else "Mid-level" if experience < 5 else "Senior"
        have_skills, missing_skills  = get_skills_gap(user_skills or [], top_skills)
        vision_align                 = get_vision_alignment(top_job, field, region)
        popular_careers[top_job]    += 1

        recommendations.append({
            "career_title":     top_job,
            "tech_field":       field,
            "estimated_salary": round(final_salary_usd, 2),
            "salary_display":   salary_display,
            "salary_range":     salary_range,
            "currency":         CURRENCY_SYMBOLS.get(region, ("USD", 1.0))[0],
            "region":           region,
            "future_demand":    DEMAND_MAP.get(field, DEMAND_MAP["default"]),
            "required_skills":  top_skills,
            "skills_you_have":  have_skills,
            "skills_to_learn":  missing_skills,
            "certifications":   top_certs,
            "roadmap":          ROADMAPS.get(field, ROADMAPS["default"]),
            "experience_level": exp_level,
            "data_points":      len(field_data),
            "confidence":       round(confidence * 100, 1),
            "source":           "tech_dataset",
            "description":      f"A career in {field} focusing on {', '.join(top_skills[:3])}.",
            "vision_alignment": vision_align,
        })

    return recommendations

def get_onet_recommendations(user_text, experience, region="USA", user_skills=None):
    query_vec    = onet_vectorizer.transform([user_text.lower()])
    similarities = cosine_similarity(query_vec, onet_matrix)[0]
    max_sim      = float(similarities.max())
    if max_sim < 0.05:
        return []

    dynamic_threshold = max_sim * 0.60
    top_indices = [
        i for i in similarities.argsort()[::-1]
        if similarities[i] >= dynamic_threshold
    ][:10]

    recommendations = []
    exp_level       = "Junior" if experience < 2 else "Mid-level" if experience < 5 else "Senior"

    for idx in top_indices:
        row        = df_occ.iloc[idx]
        similarity = float(similarities[idx])
        if similarity < 0.05:
            continue

        occ_code    = row.get("O*NET-SOC Code", "")
        title       = row["Title"]
        desc        = row["Description"]
        onet_skills = skills_map.get(occ_code, [])
        edu_req     = edu_map.get(occ_code, "Relevant degree or certification")
        roadmap     = build_onet_roadmap(title, onet_skills, edu_req)

        est_usd                      = estimate_onet_salary(title)
        sal_display, sal_range       = convert_salary(est_usd, region)
        have_skills, missing_skills  = get_skills_gap(user_skills or [], onet_skills)
        vision_align                 = get_vision_alignment(title, "", region)
        popular_careers[title]      += 1

        recommendations.append({
            "career_title":       title,
            "tech_field":         "General Career",
            "estimated_salary":   est_usd,
            "salary_display":     sal_display,
            "salary_range":       sal_range,
            "currency":           CURRENCY_SYMBOLS.get(region, ("USD", 1.0))[0],
            "region":             region,
            "future_demand":      "High",
            "required_skills":    onet_skills[:6],
            "skills_you_have":    have_skills,
            "skills_to_learn":    missing_skills,
            "certifications":     [],
            "education_required": str(edu_req) if edu_req else "Relevant degree",
            "roadmap":            roadmap,
            "experience_level":   exp_level,
            "data_points":        len(df_occ),
            "confidence":         round(similarity * 100, 1),
            "description":        desc[:250] + "..." if len(desc) > 250 else desc,
            "source":             "onet",
            "vision_alignment":   vision_align,
        })

    return recommendations


# ─────────────────────────── Routes ───────────────────────────

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data        = request.json
        user_text   = data.get("interests", "")
        experience  = float(data.get("experience_years_total", 2))
        education   = data.get("education_level", "Bachelor")
        region      = data.get("region", "USA")
        user_skills = data.get("user_skills", [])

        if not user_text.strip():
            return jsonify({"success": False, "error": "No input provided"}), 400

        popular_regions[region] += 1

        if is_tech_query(user_text):
            recommendations = get_tech_recommendations(user_text, experience, education, region, user_skills)
            if not recommendations:
                recommendations = get_onet_recommendations(user_text, experience, region, user_skills)
        else:
            recommendations = get_onet_recommendations(user_text, experience, region, user_skills)

        if not recommendations:
            return jsonify({"success": False, "error": "Could not find matching careers"}), 404

        search_log.append({
            "timestamp": datetime.now().isoformat(),
            "query":     user_text[:50],
            "region":    region,
            "results":   len(recommendations),
        })

        return jsonify({
            "success":         True,
            "recommendations": recommendations,
            "total":           len(recommendations),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/options", methods=["GET"])
def options():
    return jsonify(unique_values)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"})


@app.route("/vision", methods=["GET"])
def vision():
    return jsonify(VISION_SECTORS)


@app.route("/admin/stats", methods=["GET"])
def admin_stats():
    return jsonify({
        **admin_stats_base,
        "total_searches":  len(search_log),
        "popular_careers": popular_careers.most_common(10),
        "popular_regions": popular_regions.most_common(10),
        "recent_searches": search_log[-20:][::-1],
        "region_salary_summary": {
            region: {
                field: data["avg_usd"]
                for field, data in fields.items()
            }
            for region, fields in list(region_salary_data.items())[:5]
        },
    })


@app.route("/skills-gap", methods=["POST"])
def skills_gap_endpoint():
    try:
        data        = request.json
        user_skills = data.get("user_skills", [])
        career      = data.get("career", "")

        query_vec    = onet_vectorizer.transform([career.lower()])
        similarities = cosine_similarity(query_vec, onet_matrix)[0]
        top_idx      = similarities.argsort()[-1]
        row          = df_occ.iloc[top_idx]
        occ_code     = row.get("O*NET-SOC Code", "")
        required     = skills_map.get(occ_code, [])

        have, missing = get_skills_gap(user_skills, required)

        return jsonify({
            "career":          row["Title"],
            "skills_you_have": have,
            "skills_to_learn": missing,
            "match_percent":   round(len(have) / max(len(required), 1) * 100, 1),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────── Entry Point ───────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)