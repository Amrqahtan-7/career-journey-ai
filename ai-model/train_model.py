import pandas as pd
import joblib
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

print("Loading datasets...")

# ===== DATASET 1: Tech Salary =====
df_salary = pd.read_csv("tech_salary_dataset.csv")
df_salary_clean = df_salary[[
    "primary_tech_field", "experience_years_total", "education_level",
    "employment_type", "work_arrangement", "annual_salary_usd",
    "job_title", "skills", "certifications", "location", "currency"
]].copy()

df_salary_clean["skills"] = df_salary_clean["skills"].fillna("")
df_salary_clean["certifications"] = df_salary_clean["certifications"].fillna("")
df_salary_clean["job_title"] = df_salary_clean["job_title"].fillna("")
df_salary_clean["location"] = df_salary_clean["location"].fillna("")
df_salary_clean["currency"] = df_salary_clean["currency"].fillna("USD")
df_salary_clean = df_salary_clean.dropna(subset=["primary_tech_field", "annual_salary_usd"])

# ===== BUILD COUNTRY/REGION MAP =====
def detect_region(location, currency):
    loc = str(location).lower()
    cur = str(currency).upper()
    if any(x in loc for x in ["riyadh", "jeddah", "saudi", "ksa", "dammam"]) or cur == "SAR":
        return "KSA"
    if any(x in loc for x in ["dubai", "abu dhabi", "uae", "sharjah"]) or cur == "AED":
        return "UAE"
    if any(x in loc for x in ["karachi", "lahore", "islamabad", "pakistan"]) or cur == "PKR":
        return "Pakistan"
    if any(x in loc for x in ["london", "manchester", "uk", "birmingham"]) or cur == "GBP":
        return "UK"
    if any(x in loc for x in ["berlin", "munich", "germany", "frankfurt"]) or cur == "EUR":
        return "Europe"
    if any(x in loc for x in ["bangalore", "mumbai", "delhi", "india", "hyderabad", "chennai"]) or cur == "INR":
        return "India"
    if any(x in loc for x in ["tokyo", "osaka", "japan"]) or cur == "JPY":
        return "Japan"
    if any(x in loc for x in ["singapore", "sgd"]) or cur == "SGD":
        return "Singapore"
    if any(x in loc for x in ["sydney", "melbourne", "australia"]) or cur == "AUD":
        return "Australia"
    return "USA"

df_salary_clean["region"] = df_salary_clean.apply(
    lambda r: detect_region(r["location"], r["currency"]), axis=1
)

# Currency conversion to USD (approximate)
CURRENCY_TO_USD = {
    "USD": 1.0, "GBP": 1.27, "EUR": 1.08, "JPY": 0.0067,
    "INR": 0.012, "AUD": 0.65, "SGD": 0.74, "AED": 0.27,
    "SAR": 0.27, "PKR": 0.0036, "CAD": 0.74
}

def to_usd(salary, currency):
    rate = CURRENCY_TO_USD.get(str(currency).upper(), 1.0)
    return salary * rate

df_salary_clean["salary_usd_normalized"] = df_salary_clean.apply(
    lambda r: to_usd(r["annual_salary_usd"], r["currency"]), axis=1
)

# Save region salary data for app.py
region_salary_data = {}
for region in df_salary_clean["region"].unique():
    region_df = df_salary_clean[df_salary_clean["region"] == region]
    region_salary_data[region] = {
        field: {
            "avg_usd": float(grp["salary_usd_normalized"].mean()),
            "count": len(grp)
        }
        for field, grp in region_df.groupby("primary_tech_field")
        if len(grp) >= 3
    }

with open("region_salary_data.json", "w") as f:
    json.dump(region_salary_data, f, indent=2)
print(f"Region salary data saved: {list(region_salary_data.keys())}")

encoders = {}
for col in ["primary_tech_field", "education_level", "employment_type", "work_arrangement"]:
    le = LabelEncoder()
    df_salary_clean[col] = le.fit_transform(df_salary_clean[col].astype(str))
    encoders[f"salary_{col}"] = le

X_salary = df_salary_clean[[
    "primary_tech_field", "experience_years_total",
    "education_level", "employment_type", "work_arrangement"
]]
y_salary = df_salary_clean["annual_salary_usd"]

X_tr, X_te, y_tr, y_te = train_test_split(X_salary, y_salary, test_size=0.2, random_state=42)
salary_model = RandomForestRegressor(n_estimators=100, random_state=42)
salary_model.fit(X_tr, y_tr)
print(f"Salary Model R2 Score: {r2_score(y_te, salary_model.predict(X_te)):.3f}")

# ===== NLP MODEL: COMBINED tech_salary + career_recommender =====
print("\nBuilding COMBINED NLP model...")
df_nlp = pd.read_csv("tech_salary_dataset.csv")
df_nlp["skills"] = df_nlp["skills"].fillna("")
df_nlp["job_title"] = df_nlp["job_title"].fillna("")
df_nlp["primary_tech_field"] = df_nlp["primary_tech_field"].fillna("")

texts = []
labels = []

# From tech_salary_dataset
for _, row in df_nlp.iterrows():
    field = str(row["primary_tech_field"]).strip()
    skills = str(row["skills"]).replace(";", " ").replace(",", " ").lower()
    title = str(row["job_title"]).lower()
    if not field:
        continue
    texts.append(f"i work as {title} and my skills include {skills}")
    labels.append(field)
    texts.append(f"i enjoy working with {skills} in {field.lower()}")
    labels.append(field)
    texts.append(f"{title} {skills}")
    labels.append(field)

# From career_recommender.csv
try:
    df_rec = pd.read_csv("career_recommender.csv")
    interest_col = "What are your interests?"
    skills_col = "What are your skills ? (Select multiple if necessary)"
    job_col = "If yes, then what is/was your first Job title in your current field of work? If not applicable, write NA."
    spec_col = "What is your UG specialization? Major Subject (Eg; Mathematics)"

    df_rec_working = df_rec[df_rec[job_col].notna() & (df_rec[job_col].str.upper() != "NA")].copy()

    for _, row in df_rec_working.iterrows():
        job = str(row[job_col]).strip()
        interests = str(row.get(interest_col, "")).strip()
        skills = str(row.get(skills_col, "")).replace(";", " ").replace(",", " ").lower()
        spec = str(row.get(spec_col, "")).strip()

        if not job or job.lower() in ["na", "nan", ""]:
            continue

        # Map job titles to tech fields or use as-is
        field = map_job_to_field(job) if 'map_job_to_field' in dir() else job

        texts.append(f"i am interested in {interests.lower()} and my skills are {skills}")
        labels.append(field)
        texts.append(f"i studied {spec.lower()} and want to work as {job.lower()}")
        labels.append(field)
        if interests:
            texts.append(interests.lower())
            labels.append(field)

    print(f"career_recommender added {len(df_rec_working)} working professionals")
except Exception as e:
    print(f"career_recommender skipped: {e}")

print(f"Combined NLP: {len(texts)} sentences, {len(set(labels))} fields")

nlp_model = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=15000, min_df=2, sublinear_tf=True)),
    ("clf", LogisticRegression(max_iter=1000, C=5.0, class_weight="balanced"))
])
nlp_model.fit(texts, labels)
print("Combined NLP model trained!")

# ===== LOAD O*NET SKILLS & EDUCATION =====
print("\nLoading O*NET skills and education data...")

df_occ = pd.read_excel("onet_occupations.xlsx")
df_occ["Description"] = df_occ["Description"].fillna("")
df_occ["Title"] = df_occ["Title"].fillna("")

df_skills_raw = pd.read_excel("onet_skills.xlsx")
df_edu_raw = pd.read_excel("onet_education.xlsx")

skills_map = {}
if "O*NET-SOC Code" in df_skills_raw.columns and "Element Name" in df_skills_raw.columns:
    if "Data Value" in df_skills_raw.columns:
        df_skills_imp = df_skills_raw[df_skills_raw["Data Value"] >= 3.0]
    else:
        df_skills_imp = df_skills_raw
    for code, group in df_skills_imp.groupby("O*NET-SOC Code"):
        top = group["Element Name"].value_counts().head(6).index.tolist()
        skills_map[code] = top

edu_map = {}
if "O*NET-SOC Code" in df_edu_raw.columns:
    edu_col = None
    for col in df_edu_raw.columns:
        if "education" in col.lower() or "category" in col.lower() or "level" in col.lower():
            edu_col = col
            break
    if edu_col:
        for code, group in df_edu_raw.groupby("O*NET-SOC Code"):
            edu_map[code] = group[edu_col].value_counts().index[0] if len(group) > 0 else "Bachelor's degree"

joblib.dump(skills_map, "onet_skills_map.pkl")
joblib.dump(edu_map, "onet_edu_map.pkl")

# ===== BUILD ONET SEARCH MODEL =====
print("\nBuilding O*NET career search model...")

def expand_description(title, description):
    title_lower = title.lower()
    extra = ""
    if any(w in title_lower for w in ["software", "developer", "programmer", "coder", "full stack"]):
        extra = "coding programming build apps websites software systems computer science technology"
    elif any(w in title_lower for w in ["data scientist", "data analyst", "machine learning", "ai researcher"]):
        extra = "data science machine learning artificial intelligence python statistics analysis models"
    elif any(w in title_lower for w in ["cybersecurity", "security analyst", "ethical hacker", "penetration"]):
        extra = "cybersecurity hacking protect networks systems firewall security breach defend digital"
    elif any(w in title_lower for w in ["cloud", "devops", "site reliability", "infrastructure"]):
        extra = "cloud aws azure docker kubernetes devops automation deployment infrastructure"
    elif any(w in title_lower for w in ["doctor", "physician", "surgeon", "nurse", "medical"]):
        extra = "doctor medicine saving lives healing patients treatment diagnosis hospital care health"
    elif any(w in title_lower for w in ["teacher", "instructor", "educator"]):
        extra = "teaching education students school learning knowledge help children grow inspire"
    elif any(w in title_lower for w in ["lawyer", "attorney", "legal"]):
        extra = "law justice rights court legal advocacy cases defending people"
    elif any(w in title_lower for w in ["engineer", "engineering"]):
        extra = "engineering design build systems technical problem solving construction"
    elif any(w in title_lower for w in ["artist", "designer", "creative"]):
        extra = "design art creativity visual aesthetics creative expression"
    elif any(w in title_lower for w in ["scientist", "researcher", "biologist"]):
        extra = "research science discovery laboratory experiments analysis knowledge"
    elif any(w in title_lower for w in ["accountant", "auditor", "financial"]):
        extra = "accounting finance numbers money budget audit financial reporting"
    elif any(w in title_lower for w in ["chef", "cook", "culinary"]):
        extra = "cooking food kitchen restaurant culinary creative recipes hospitality"
    elif any(w in title_lower for w in ["pilot", "aviation"]):
        extra = "flying aviation aircraft travel sky navigation flight"
    elif any(w in title_lower for w in ["musician", "composer", "music"]):
        extra = "music sound instruments performance creative entertainment"
    elif any(w in title_lower for w in ["athlete", "sport", "fitness"]):
        extra = "sports athletics competition physical fitness training performance"
    return f"{title} {description} {extra}".lower()

onet_texts = []
for _, row in df_occ.iterrows():
    text = expand_description(row["Title"], row["Description"])
    onet_texts.append(text)

onet_vectorizer = TfidfVectorizer(
    ngram_range=(1, 2), max_features=15000,
    sublinear_tf=True, stop_words="english"
)
onet_matrix = onet_vectorizer.fit_transform(onet_texts)
print(f"O*NET: {len(df_occ)} occupations indexed!")

# ===== VISION 2030/2035 DATA =====
VISION_SECTORS = {
    "KSA": {
        "label": "Saudi Vision 2030",
        "flag": "🇸🇦",
        "color": "#006C35",
        "sectors": [
            {"name": "Tourism & Hospitality", "keywords": ["hotel", "tourism", "travel", "hospitality", "guide"], "demand": "Very High", "growth": "+150% by 2030"},
            {"name": "Technology & Digital", "keywords": ["software", "data", "cloud", "cybersecurity", "ai"], "demand": "Very High", "growth": "+200% by 2030"},
            {"name": "Healthcare", "keywords": ["doctor", "nurse", "pharmacy", "medical", "health"], "demand": "Very High", "growth": "+80% by 2030"},
            {"name": "Entertainment & Sports", "keywords": ["entertainment", "sports", "gaming", "media", "film"], "demand": "High", "growth": "+120% by 2030"},
            {"name": "Renewable Energy", "keywords": ["energy", "solar", "environment", "sustainability", "green"], "demand": "High", "growth": "+90% by 2030"},
            {"name": "Financial Services", "keywords": ["finance", "banking", "fintech", "investment", "accounting"], "demand": "High", "growth": "+60% by 2030"},
        ]
    },
    "UAE": {
        "label": "UAE Vision 2030",
        "flag": "🇦🇪",
        "color": "#00732F",
        "sectors": [
            {"name": "FinTech & Banking", "keywords": ["finance", "fintech", "banking", "crypto", "blockchain"], "demand": "Very High", "growth": "+180% by 2030"},
            {"name": "AI & Smart Cities", "keywords": ["ai", "machine learning", "smart", "data", "cloud"], "demand": "Very High", "growth": "+250% by 2030"},
            {"name": "Logistics & Trade", "keywords": ["logistics", "supply chain", "trade", "transport", "shipping"], "demand": "High", "growth": "+70% by 2030"},
            {"name": "Healthcare Innovation", "keywords": ["medical", "health", "biotech", "pharmaceutical", "doctor"], "demand": "Very High", "growth": "+100% by 2030"},
            {"name": "Space & Aviation", "keywords": ["space", "aviation", "aerospace", "pilot", "engineer"], "demand": "High", "growth": "+85% by 2030"},
            {"name": "Creative Economy", "keywords": ["design", "media", "art", "film", "content", "creative"], "demand": "Medium-High", "growth": "+60% by 2030"},
        ]
    },
    "Pakistan": {
        "label": "Pakistan Vision 2035",
        "flag": "🇵🇰",
        "color": "#01411C",
        "sectors": [
            {"name": "IT & Freelancing", "keywords": ["software", "web", "mobile", "freelance", "development"], "demand": "Very High", "growth": "+300% by 2035"},
            {"name": "Agriculture Tech", "keywords": ["agriculture", "farming", "food", "rural", "crop"], "demand": "High", "growth": "+80% by 2035"},
            {"name": "Education Technology", "keywords": ["education", "teaching", "edtech", "e-learning", "training"], "demand": "High", "growth": "+120% by 2035"},
            {"name": "Healthcare", "keywords": ["medical", "health", "doctor", "nurse", "pharmacy"], "demand": "Very High", "growth": "+90% by 2035"},
            {"name": "Textile & Manufacturing", "keywords": ["textile", "manufacturing", "production", "industrial", "fashion"], "demand": "Medium-High", "growth": "+50% by 2035"},
            {"name": "Renewable Energy", "keywords": ["energy", "solar", "power", "electricity", "environment"], "demand": "High", "growth": "+100% by 2035"},
        ]
    }
}

with open("vision_sectors.json", "w") as f:
    json.dump(VISION_SECTORS, f, indent=2)
print("Vision sectors data saved!")

# Save admin stats data
admin_stats = {
    "total_occupations": len(df_occ),
    "tech_fields": len(df_nlp["primary_tech_field"].unique()),
    "salary_records": len(df_salary),
    "regions": list(region_salary_data.keys()),
}
with open("admin_stats.json", "w") as f:
    json.dump(admin_stats, f, indent=2)

# Save all models
joblib.dump(nlp_model, "nlp_model.pkl")
joblib.dump(onet_vectorizer, "onet_vectorizer.pkl")
joblib.dump(onet_matrix, "onet_matrix.pkl")
joblib.dump(df_occ, "onet_occupations.pkl")
joblib.dump(salary_model, "career_model.pkl")
joblib.dump(encoders, "career_data.pkl")

unique_values = {
    "primary_tech_field": encoders["salary_primary_tech_field"].classes_.tolist(),
    "education_level": encoders["salary_education_level"].classes_.tolist(),
    "employment_type": encoders["salary_employment_type"].classes_.tolist(),
    "work_arrangement": encoders["salary_work_arrangement"].classes_.tolist(),
}
with open("career_data.json", "w") as f:
    json.dump(unique_values, f, indent=2)

print("\n✅ All models saved successfully!")
print(f"  - Salary model: {len(df_salary)} records")
print(f"  - NLP model: {len(texts)} training sentences")
print(f"  - O*NET: {len(df_occ)} occupations")
print(f"  - Regions: {list(region_salary_data.keys())}")