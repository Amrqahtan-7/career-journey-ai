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

# ─── Master Intent Map ────────────────────────────────────────────────────────
# Every keyword → rich O*NET-friendly expansion
# Covers: exact job names, natural phrases, "I like/want/love" variants
INTENT_MAP = [

    # ── Protective / Emergency ──
    (["fireman", "fire man", "fire fighter", "firefighter", "put out fire", "rescue fire", "fire station", "fire truck", "i want to be a fireman", "i want to be a firefighter"],
     "firefighter fire suppression emergency rescue fire station"),

    (["police", "policeman", "police officer", "cop", "law enforcement", "detective", "investigat", "i want to be a police", "i want to be a cop"],
     "police officer detective law enforcement investigation patrol"),

    (["soldier", "army", "military", "navy", "air force", "marines", "combat", "armed forces", "i want to be a soldier"],
     "military officer soldier armed forces defense combat"),

    (["security guard", "security officer", "bodyguard", "i want to be a security"],
     "security guard protective services surveillance bodyguard"),

    (["paramedic", "ambulance", "emt", "emergency medical technician", "i want to be a paramedic"],
     "paramedic emergency medical technician ambulance first responder"),

    # ── Healthcare ──
    (["doctor", "physician", "medical doctor", "be a doctor", "want to be doctor", "i want to be a doctor", "i like medicine", "i love medicine"],
     "physician medical doctor diagnosis treatment clinical"),

    (["nurse", "nursing", "care for patients", "patient care", "i want to be a nurse", "i like nursing"],
     "nurse nursing patient care healthcare registered nurse"),

    (["dentist", "teeth", "dental", "oral health", "i want to be a dentist"],
     "dentist dental oral health teeth examination"),

    (["pharmacist", "pharmacy", "medicine dispensing", "i want to be a pharmacist"],
     "pharmacist pharmacy medication dispensing drug"),

    (["surgeon", "surgery", "operate on patients", "i want to be a surgeon"],
     "surgeon surgery surgical operations theater"),

    (["therapist", "mental health", "counseling", "psychology", "psychologist", "i like psychology", "i love psychology"],
     "psychologist therapist mental health counseling behavioral"),

    (["veterinarian", "vet", "animal doctor", "treat animals", "i want to be a vet", "i love animals", "i like animals"],
     "veterinarian animal care veterinary medicine pet"),

    (["physiotherapist", "physical therapist", "physiotherapy", "physical therapy"],
     "physical therapist physiotherapy rehabilitation movement"),

    (["optometrist", "eye doctor", "vision", "eye care"],
     "optometrist eye care vision health"),

    (["radiologist", "radiology", "xray", "x-ray", "mri", "scan"],
     "radiologist radiology imaging diagnostic"),

    # ── Writing & Media ──
    (["writing", "write", "writer", "author", "novelist", "storytelling", "creative writing", "i like writing", "i love writing", "i enjoy writing"],
     "writer author technical writing content creation journalism editorial"),

    (["journalist", "journalism", "news", "reporter", "media", "broadcast", "i want to be a journalist", "i like news"],
     "journalist reporter news media broadcasting journalism"),

    (["reading", "books", "literature", "library", "librarian", "i like reading", "i love reading", "i love books"],
     "librarian literature research information services books"),

    (["editing", "editor", "proofreading", "i want to be an editor"],
     "editor editorial proofreading publishing content"),

    (["blogging", "blog", "content creation", "content creator", "i like blogging"],
     "content creator writer blogger digital media online"),

    (["social media", "influencer", "instagram", "youtube", "tiktok", "i like social media"],
     "social media manager content creator digital marketing influencer"),

    (["photography", "photographer", "photos", "camera", "i like photography", "i love photography"],
     "photographer photography visual media camera portrait"),

    (["filmmaking", "film", "movie", "cinema", "director", "video production", "i like films", "i love movies"],
     "film director video production cinematography director"),

    (["podcast", "podcasting", "radio", "broadcasting"],
     "radio broadcaster announcer media audio production"),

    # ── Art & Design ──
    (["drawing", "draw", "sketch", "illustration", "illustrator", "i like drawing", "i love drawing", "i enjoy drawing"],
     "graphic designer illustrator visual arts animation drawing"),

    (["painting", "paint", "painter", "artist", "fine art", "i like painting", "i love painting"],
     "artist fine arts painter visual arts creative"),

    (["graphic design", "graphic designer", "design", "designer", "visual design", "i like design", "i love design"],
     "graphic designer visual arts design creative layout"),

    (["fashion", "clothes", "clothing", "style", "fashion design", "i like fashion", "i love fashion"],
     "fashion designer clothing apparel textile style"),

    (["interior design", "interior decorator", "room design", "home design", "i like interior design"],
     "interior designer space planning architecture decor"),

    (["animation", "animator", "cartoon", "3d modeling", "i like animation", "i love animation"],
     "animator animation 3D modeling visual effects digital"),

    (["music", "musician", "singing", "singer", "song", "guitar", "piano", "i like music", "i love music", "i love singing"],
     "musician music performance composer audio singer"),

    (["acting", "actor", "theatre", "theater", "drama", "performing arts", "i like acting", "i love acting"],
     "actor performer theatre arts entertainment drama"),

    (["dance", "dancer", "dancing", "choreograph", "i like dancing", "i love dancing"],
     "dancer choreographer performing arts movement"),

    (["sculpture", "sculpting", "3d art", "pottery", "ceramics"],
     "sculptor artist fine arts ceramics visual"),

    # ── Education ──
    (["teaching", "teacher", "educate", "education", "school", "classroom", "i like teaching", "i want to be a teacher", "i love teaching"],
     "teacher education instruction curriculum classroom"),

    (["professor", "university", "college lecturer", "academic", "i want to be a professor"],
     "professor university lecturer academic research"),

    (["tutor", "tutoring", "private teaching", "i want to be a tutor"],
     "tutor educational support instruction learning"),

    (["school counselor", "student counselor", "guidance counselor"],
     "school counselor guidance educational support students"),

    (["principal", "school principal", "headmaster"],
     "principal school administrator education management"),

    # ── Engineering ──
    (["electrical engineer", "electrical engineering", "electrician", "wiring", "electrical work", "circuits", "electronics", "i like electronics"],
     "electrician electrical engineer wiring installation circuits power"),

    (["mechanical engineer", "mechanical engineering", "machines", "motors", "manufacturing", "i like machines"],
     "mechanical engineer machinery manufacturing motors design"),

    (["civil engineer", "civil engineering", "construction", "building", "structures", "bridges", "i like construction"],
     "civil engineer construction structural building infrastructure"),

    (["chemical engineer", "chemical engineering", "chemicals", "chemical plant"],
     "chemical engineer chemical process plant industrial"),

    (["aerospace engineer", "aerospace engineering", "aviation", "aircraft", "airplane", "rocket", "i like planes"],
     "aerospace engineer aviation aircraft flight rocket"),

    (["robotics", "robots", "robot", "automation", "i like robots", "i love robots"],
     "robotics engineer automation mechanical systems"),

    (["biomedical engineer", "biomedical", "medical devices", "medical engineering"],
     "biomedical engineer medical devices healthcare technology"),

    (["petroleum engineer", "oil", "gas", "oil and gas", "petroleum"],
     "petroleum engineer oil gas energy extraction"),

    (["nuclear engineer", "nuclear energy", "nuclear power"],
     "nuclear engineer energy reactor power plant"),

    (["industrial engineer", "industrial engineering", "process improvement"],
     "industrial engineer process improvement operations efficiency"),

    (["engineer", "engineering"],
     "engineer engineering technical design systems"),

    # ── Science & Research ──
    (["scientist", "science", "research", "researcher", "lab", "laboratory", "i like science", "i love science"],
     "scientist research laboratory analysis experimentation"),

    (["biology", "biologist", "living things", "organisms", "life science", "i like biology"],
     "biologist biology life sciences research organisms"),

    (["chemistry", "chemist", "lab work", "i like chemistry"],
     "chemist chemistry laboratory research compounds"),

    (["physics", "physicist", "i like physics"],
     "physicist physics research quantum mechanics"),

    (["environment", "environmental", "ecology", "climate", "climate change", "i like environment", "i love nature"],
     "environmental scientist ecology conservation climate nature"),

    (["space", "astronomy", "astronomer", "stars", "planets", "nasa", "universe", "i like space", "i love space"],
     "astronomer space scientist astrophysics research planets"),

    (["geology", "geologist", "earth", "rocks", "minerals", "i like geology"],
     "geologist geology earth sciences minerals rocks"),

    (["marine biology", "marine", "ocean", "sea", "underwater"],
     "marine biologist oceanographer aquatic science"),

    (["genetics", "genetic", "dna", "genomics"],
     "geneticist genetics research dna molecular biology"),

    (["neuroscience", "neuroscientist", "brain", "neurology"],
     "neuroscientist brain research neurology cognitive science"),

    # ── Business & Finance ──
    (["business", "entrepreneur", "startup", "own business", "company", "i like business", "i want to start a business"],
     "business manager entrepreneur management operations strategy"),

    (["finance", "financial", "investment", "stocks", "trading", "stock market", "i like finance", "i love finance"],
     "financial analyst investment banking finance portfolio"),

    (["accounting", "accountant", "bookkeeping", "taxes", "i like accounting", "i want to be an accountant"],
     "accountant accounting financial reporting tax audit"),

    (["marketing", "advertise", "advertising", "branding", "campaigns", "i like marketing"],
     "marketing manager advertising brand management campaigns"),

    (["sales", "selling", "salesperson", "sell products", "i like sales"],
     "sales representative business development selling"),

    (["management", "manager", "team leader", "leadership", "i like management"],
     "manager management operations leadership team"),

    (["consulting", "consultant", "business advice", "i want to be a consultant"],
     "consultant business strategy management consulting advisory"),

    (["real estate", "property", "houses", "homes", "land", "i like real estate"],
     "real estate agent property management broker housing"),

    (["banking", "bank", "banker", "i want to be a banker"],
     "banker financial services bank management loans"),

    (["insurance", "actuary", "risk", "risk management"],
     "actuary insurance risk analysis underwriting"),

    (["human resources", "hr", "recruitment", "hiring", "i like hr"],
     "human resources specialist recruitment staffing talent"),

    (["economics", "economist", "economic policy", "i like economics"],
     "economist economic analysis policy research"),

    (["project management", "project manager", "pmp", "managing projects"],
     "project manager operations planning coordination"),

    # ── Legal ──
    (["lawyer", "law", "legal", "attorney", "court", "justice", "i want to be a lawyer", "i like law"],
     "lawyer attorney legal services law court"),

    (["judge", "judiciary", "i want to be a judge"],
     "judge court judicial legal"),

    (["paralegal", "legal assistant", "law office"],
     "paralegal legal assistant law office support"),

    (["criminology", "criminologist", "crime", "criminal justice"],
     "criminologist criminal justice crime analysis law enforcement"),

    # ── Technology ──
    (["it support", "tech support", "help desk", "computer repair", "i like fixing computers"],
     "IT support technician computer hardware help desk troubleshooting"),

    (["network", "networking", "wifi", "internet infrastructure", "i like networking"],
     "network administrator systems IT infrastructure"),

    (["cybersecurity", "hacking", "ethical hacker", "cyber", "information security", "i like hacking"],
     "cybersecurity analyst information security ethical hacking"),

    (["game", "gaming", "game development", "game design", "video game", "i like gaming", "i love games"],
     "game designer developer video game entertainment interactive"),

    (["ui", "ux", "user interface", "user experience", "product design"],
     "UX designer user experience interface design product"),

    # ── Trades & Skilled Work ──
    (["plumber", "plumbing", "pipes", "pipe fitting", "water systems", "i want to be a plumber"],
     "plumber plumbing pipefitting water systems pipe installation"),

    (["carpenter", "woodwork", "furniture", "carpentry", "i want to be a carpenter", "i like woodwork"],
     "carpenter woodworking furniture construction joinery"),

    (["welder", "welding", "metalwork", "metal fabrication", "i want to be a welder"],
     "welder welding metal fabrication joining"),

    (["mechanic", "car repair", "auto", "vehicle", "fix cars", "automobile", "i like cars", "i love cars"],
     "mechanic automotive repair vehicle maintenance garage"),

    (["chef", "cook", "cooking", "kitchen", "culinary", "food", "i like cooking", "i love cooking", "i enjoy cooking"],
     "chef cook culinary arts food preparation kitchen"),

    (["baker", "baking", "pastry", "bread", "i like baking", "i love baking"],
     "baker pastry chef baking food production bread"),

    (["hairstylist", "hair", "barber", "salon", "beautician", "makeup", "cosmetologist", "i like hair", "i like beauty"],
     "hairstylist cosmetologist barber beauty services hair"),

    (["tailor", "sewing", "clothing repair", "alterations"],
     "tailor sewing clothing alterations textile"),

    (["hvac", "heating", "cooling", "air conditioning", "ventilation"],
     "HVAC technician heating cooling ventilation air conditioning"),

    (["mason", "masonry", "bricklayer", "brickwork"],
     "mason bricklayer masonry construction"),

    (["painter", "house painting", "painting walls", "decorator"],
     "painter decorator coating surface finishing"),

    # ── Agriculture & Nature ──
    (["farming", "farm", "farmer", "crops", "agriculture", "i like farming", "i love farming"],
     "farmer agricultural worker crop production soil"),

    (["wildlife", "wild animals", "zoo", "zoology", "zoologist", "i love wildlife"],
     "wildlife biologist zoologist animal conservation"),

    (["forest", "forestry", "trees", "park ranger", "national park"],
     "forester conservation park ranger natural resources trees"),

    (["horticulture", "horticulturist", "plants", "gardening", "garden", "i like gardening"],
     "horticulturist gardener plant science landscape"),

    (["fishery", "fishing", "aquaculture", "marine resources"],
     "fishery worker aquaculture marine resources"),

    # ── Sports & Fitness ──
    (["sports", "athlete", "sport", "football", "basketball", "soccer", "i like sports", "i love sports", "i am good at sports"],
     "athletic trainer sports coach physical education athlete"),

    (["fitness", "gym", "personal trainer", "workout", "exercise", "i like fitness", "i love fitness"],
     "fitness trainer personal trainer physical education exercise"),

    (["coach", "coaching", "sports coach", "i want to be a coach"],
     "coach athletic trainer sports management"),

    (["physiotherapy", "sports medicine", "rehabilitation"],
     "sports medicine therapist rehabilitation physical"),

    # ── Architecture ──
    (["architect", "architecture", "building design", "i want to be an architect", "i like architecture"],
     "architect architecture building design construction planning"),

    (["urban planning", "city planning", "urban design", "urban development"],
     "urban planner city planning land use development"),

    (["landscape", "landscape architect", "landscape design"],
     "landscape architect outdoor design environment planning"),

    # ── Transportation ──
    (["pilot", "flying", "fly planes", "aviator", "i want to be a pilot", "i like flying", "i love flying"],
     "pilot aviation aircraft commercial flight"),

    (["truck driver", "truck driving", "lorry driver", "i want to be a truck driver"],
     "truck driver transportation vehicle operator"),

    (["flight attendant", "cabin crew", "airline steward", "i want to be a flight attendant"],
     "flight attendant cabin crew airline passenger services"),

    (["logistics", "supply chain", "warehouse", "delivery", "shipping", "i like logistics"],
     "logistics manager supply chain warehouse distribution"),

    (["train driver", "railway", "locomotive"],
     "locomotive engineer train operator railway transportation"),

    # ── Social & Community ──
    (["social work", "social worker", "help community", "helping people", "helping others", "i love helping people", "i like helping others"],
     "social worker community services counseling support"),

    (["nonprofit", "charity", "volunteer", "humanitarian", "ngo"],
     "nonprofit coordinator community outreach social services"),

    (["counselor", "life coach", "mental support", "guidance"],
     "counselor mental health social services support guidance"),

    (["event", "event planning", "events", "organizing events", "event management"],
     "event planner coordinator meetings hospitality management"),

    # ── Hospitality & Tourism ──
    (["hotel", "hospitality", "resort", "lodging", "i like hospitality"],
     "hotel manager hospitality lodging services guest"),

    (["travel", "tourism", "tour guide", "travel agent", "i like travel", "i love traveling"],
     "travel agent tourism guide hospitality destination"),

    # ── Environment & Sustainability ──
    (["renewable energy", "solar", "wind energy", "green energy", "sustainability"],
     "renewable energy engineer solar sustainability green"),

    (["conservation", "conservationist", "wildlife conservation", "protect environment"],
     "conservation scientist wildlife environmental protection"),

    # ── Psychology & Social Science ──
    (["sociology", "sociologist", "society", "social science"],
     "sociologist social science research community"),

    (["anthropology", "anthropologist", "culture", "cultural studies"],
     "anthropologist cultural studies research society"),

    (["political science", "politics", "politician", "government", "i like politics"],
     "political scientist government policy analyst"),

    (["economics", "economist"],
     "economist economic research policy analysis"),
]

# ─── Filler phrases to strip before matching ─────────────────────────────────
FILLERS = [
    "i want to be a", "i want to be an", "i want to become a", "i want to become an",
    "i would like to be a", "i would like to be an", "i'd like to be a",
    "i love", "i like", "i enjoy", "i am passionate about", "i'm passionate about",
    "i am interested in", "i'm interested in", "i am good at", "i'm good at",
    "my passion is", "my interest is", "my hobby is",
    "i want to work in", "i want to work as", "i want a job in",
    "i dream of being", "i dream of becoming",
    "help me find", "find me a career in", "suggest careers for",
    "i prefer", "i really like", "i really love",
    "i have always wanted to be", "i've always wanted to be",
    "a career in", "career in", "job in", "jobs in",
    "what career", "what job", "i want to",
]

def enhance_query(user_text: str) -> str:
    text = user_text.lower().strip()

    # Step 1: Check FULL text (before stripping) — catches "i want to be a fireman" etc.
    for keywords, expansion in INTENT_MAP:
        for kw in keywords:
            if kw in text:
                return expansion

    # Step 2: Strip fillers and check again
    for filler in FILLERS:
        text = text.replace(filler, " ")
    text = " ".join(text.split()).strip()

    # Step 3: Check cleaned text
    for keywords, expansion in INTENT_MAP:
        for kw in keywords:
            if kw in text:
                return expansion

    # Step 4: Return cleaned text if no match (at least fillers removed)
    return text if text else user_text.lower()


ONET_SALARY_ESTIMATES_USD = {
    "surgeon": 250000, "physician": 200000, "doctor": 190000,
    "psychiatrist": 220000, "anesthesiolog": 250000, "radiolog": 210000,
    "dentist": 160000, "orthodont": 180000, "pharmacist": 125000,
    "nurse": 80000, "registered nurse": 80000, "midwife": 75000,
    "therapist": 70000, "physical therapist": 90000, "occupational therapist": 85000,
    "speech": 80000, "optometrist": 120000, "veterinarian": 100000,
    "paramedic": 50000, "medical": 65000, "health": 60000,
    "aerospace engineer": 120000, "chemical engineer": 110000,
    "civil engineer": 90000, "electrical engineer": 100000,
    "mechanical engineer": 95000, "industrial engineer": 90000,
    "environmental engineer": 88000, "petroleum engineer": 130000,
    "nuclear engineer": 115000, "biomedical engineer": 95000,
    "engineer": 90000,
    "physicist": 120000, "astronomer": 110000, "chemist": 80000,
    "biologist": 70000, "microbiologist": 75000, "biochemist": 95000,
    "geologist": 85000, "environmental scientist": 73000,
    "epidemiologist": 78000, "psychologist": 82000, "sociologist": 68000,
    "economist": 105000, "statistician": 95000, "mathematician": 98000,
    "scientist": 80000, "researcher": 75000,
    "farmer": 45000, "farming": 38000, "agriculture": 40000,
    "agricultural": 42000, "forester": 62000, "conservation": 60000,
    "wildlife": 58000, "fishery": 48000, "plant": 50000,
    "horticulturist": 52000, "soil": 58000, "animal": 45000,
    "veterinary": 55000,
    "ceo": 200000, "chief executive": 200000, "executive": 150000,
    "financial manager": 130000, "investment banker": 150000,
    "financial analyst": 85000, "accountant": 70000, "auditor": 72000,
    "actuary": 110000, "budget analyst": 78000, "credit analyst": 68000,
    "loan officer": 65000, "insurance": 60000, "real estate": 65000,
    "manager": 85000, "management": 80000, "administrator": 70000,
    "business": 72000, "consultant": 90000, "analyst": 75000,
    "judge": 130000, "lawyer": 120000, "attorney": 120000,
    "paralegal": 55000, "legal": 65000, "compliance": 75000,
    "professor": 85000, "teacher": 58000, "instructor": 60000,
    "principal": 98000, "counselor": 57000, "librarian": 60000,
    "educator": 58000, "tutor": 45000,
    "architect": 85000, "urban planner": 76000,
    "graphic designer": 55000, "ux designer": 85000, "ui designer": 80000,
    "industrial designer": 68000, "interior designer": 60000,
    "fashion designer": 58000, "animator": 65000, "art director": 98000,
    "photographer": 48000, "film": 65000, "director": 80000,
    "writer": 67000, "editor": 60000, "journalist": 55000,
    "public relations": 62000, "marketing": 65000, "advertising": 68000,
    "social media": 55000, "content": 52000,
    "electrician": 60000, "plumber": 58000, "carpenter": 52000,
    "welder": 48000, "mechanic": 50000, "technician": 55000,
    "construction": 55000, "surveyor": 65000, "drafter": 58000,
    "hvac": 52000, "mason": 48000, "painter": 45000,
    "police": 65000, "detective": 85000, "firefighter": 52000,
    "security": 42000, "corrections": 47000,
    "pilot": 130000, "air traffic": 120000, "captain": 90000,
    "truck driver": 48000, "driver": 42000, "logistics": 60000,
    "supply chain": 75000, "warehouse": 38000,
    "social worker": 52000, "social": 50000, "community": 48000,
    "nonprofit": 50000,
    "chef": 55000, "cook": 35000, "baker": 33000,
    "hotel manager": 65000, "hospitality": 50000,
    "event planner": 52000, "travel": 48000, "tourism": 50000,
    "coach": 50000, "trainer": 48000, "athlete": 45000,
    "supervisor": 62000, "coordinator": 52000, "specialist": 60000,
    "operator": 48000, "assistant": 42000, "clerk": 38000,
}

def estimate_onet_salary(title: str) -> int:
    title_lower    = title.lower()
    best_match_len = 0
    best_salary    = 55000
    for keyword, salary in ONET_SALARY_ESTIMATES_USD.items():
        if keyword in title_lower and len(keyword) > best_match_len:
            best_match_len = len(keyword)
            best_salary    = salary
    return best_salary

def fmt_amount(n, symbol):
    if symbol == "PKR":
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M {symbol}"
        elif n >= 1_000:   return f"{n/1_000:.0f}K {symbol}"
        return f"{n:,.0f} {symbol}"
    elif symbol in ("AED", "SAR"):
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M {symbol}"
        elif n >= 1_000:   return f"{n/1_000:.0f}K {symbol}"
        return f"{n:,.0f} {symbol}"
    elif symbol == "INR":
        if n >= 100_000: return f"{n/100_000:.1f}L {symbol}"
        elif n >= 1_000: return f"{n/1_000:.0f}K {symbol}"
        return f"{n:,.0f} {symbol}"
    else:
        prefix = {"USD": "$", "GBP": "£", "EUR": "€"}.get(symbol, f"{symbol} ")
        if n >= 1_000_000: return f"{prefix}{n/1_000_000:.1f}M"
        elif n >= 1_000:   return f"{prefix}{n/1_000:.0f}K"
        return f"{prefix}{n:,.0f}"

def convert_salary(usd_salary, region):
    symbol, rate = CURRENCY_SYMBOLS.get(region, ("USD", 1.0))
    local   = usd_salary * rate
    display = fmt_amount(local, symbol) + "/yr"
    low     = fmt_amount(local * 0.85, symbol)
    high    = fmt_amount(local * 1.15, symbol)
    return display, f"{low} – {high}/yr"

ROADMAPS = {
    "Full-Stack Development": ["Learn HTML, CSS, and JavaScript fundamentals","Master a frontend framework (React or Vue)","Learn backend development (Node.js or Python)","Study databases (SQL and NoSQL)","Build 3-5 full stack projects","Learn Git, deployment, and DevOps basics"],
    "Data Science & ML": ["Learn Python and statistics fundamentals","Master pandas, numpy, and matplotlib","Study machine learning algorithms","Work on real datasets from Kaggle","Build a data portfolio with 3+ projects","Get certified (Google Data Analytics / IBM)"],
    "Backend Development": ["Master a backend language (Python, Java, or Node.js)","Learn REST API design and development","Study databases (SQL and NoSQL)","Learn authentication and security basics","Master Docker and deployment","Study system design and scalability"],
    "Frontend Development": ["Master HTML, CSS, and JavaScript","Learn React or Vue framework","Study UI/UX design principles","Learn state management","Build responsive and accessible websites","Learn testing and performance optimization"],
    "Cybersecurity": ["Learn networking fundamentals (TCP/IP, DNS)","Study Linux and command line tools","Learn ethical hacking basics","Get certified (CompTIA Security+ or CEH)","Practice on HackTheBox or TryHackMe","Specialize in a security domain"],
    "DevOps & Cloud": ["Master Linux and shell scripting","Learn Git and CI/CD pipelines","Study Docker and Kubernetes","Learn a cloud platform (AWS, Azure, or GCP)","Master infrastructure as code (Terraform)","Get cloud certified (AWS Solutions Architect)"],
    "Mobile Development": ["Choose iOS (Swift) or Android (Kotlin)","Or learn cross-platform (Flutter or React Native)","Build UI components and understand mobile UX","Learn API integration and local storage","Publish an app to App Store or Google Play","Learn performance optimization"],
    "default": ["Research the key skills needed in your field","Take online courses or get a relevant degree","Build a portfolio with real projects","Network with professionals in the field","Apply for internships or entry-level positions","Keep learning and stay updated"],
}

DEMAND_MAP = {
    "Full-Stack Development": "High", "Data Science & ML": "Very High",
    "Backend Development": "High", "Frontend Development": "High",
    "Cybersecurity": "Very High", "DevOps & Cloud": "Very High",
    "Mobile Development": "Medium-High", "QA & Testing": "Medium-High",
    "Database & Data Engineering": "High", "Game Development": "Medium",
    "Blockchain & Web3": "Medium-High", "default": "High",
}

def build_onet_roadmap(title, skills, edu):
    title_lower = title.lower()
    roadmap = []
    if edu and str(edu).lower() not in ["nan", "none", ""]:
        roadmap.append(f"Get the required education: {edu}")
    else:
        roadmap.append("Complete a relevant degree or certification in your field")
    if skills:
        roadmap.append(f"Develop core skills: {', '.join(skills[:4])}")
    if any(w in title_lower for w in ["doctor", "physician", "surgeon", "nurse"]):
        roadmap += ["Complete medical school or nursing program","Finish clinical internship and residency","Get licensed in your country/state","Join a hospital or clinic as a junior professional"]
    elif any(w in title_lower for w in ["teacher", "instructor", "educator"]):
        roadmap += ["Get a teaching degree or education certification","Complete student teaching practicum","Get certified by your education board","Apply for teaching positions"]
    elif any(w in title_lower for w in ["engineer", "engineering"]):
        roadmap += ["Complete an engineering degree","Do internships during your studies","Get a professional engineering license","Build practical project experience"]
    elif any(w in title_lower for w in ["lawyer", "attorney", "legal"]):
        roadmap += ["Complete a law degree (LLB or JD)","Pass the bar exam","Work as a junior associate at a law firm","Build specialization in a legal area"]
    elif any(w in title_lower for w in ["firefighter", "fire"]):
        roadmap += ["Complete a fire science or emergency services degree","Pass physical fitness and written exams","Complete firefighter academy training","Get EMT certification","Apply to local fire departments"]
    elif any(w in title_lower for w in ["police", "detective", "officer"]):
        roadmap += ["Meet basic requirements (age, fitness, background)","Complete police academy training","Pass written and physical exams","Serve as a patrol officer and build experience"]
    elif any(w in title_lower for w in ["writer", "author", "journalist"]):
        roadmap += ["Study English, journalism, or communications","Build a writing portfolio with regular practice","Publish on blogs, Medium, or local papers","Network with editors and publishers","Apply for writing or editorial positions"]
    elif any(w in title_lower for w in ["chef", "cook", "culinary"]):
        roadmap += ["Enroll in a culinary arts program","Work as a kitchen assistant to gain experience","Master a specialty cuisine or technique","Work your way up from commis to head chef"]
    elif any(w in title_lower for w in ["plumber", "plumbing"]):
        roadmap += ["Complete a plumbing apprenticeship program","Learn pipefitting and water systems","Get licensed as a journeyman plumber","Build experience across residential and commercial projects"]
    else:
        roadmap += ["Gain entry-level experience through internships","Build a strong professional network","Get certified in key areas","Apply for junior positions and grow"]
    return roadmap[:7]

def is_tech_query(user_text):
    tech_keywords = [
        "code", "coding", "programming", "software", "developer", "web",
        "data", "machine learning", "ai", "artificial intelligence", "python",
        "javascript", "react", "backend", "frontend", "fullstack", "cloud",
        "aws", "docker", "kubernetes", "cybersecurity", "hacking", "mobile",
        "android", "ios", "flutter", "devops", "database", "sql", "blockchain",
    ]
    return any(kw in user_text.lower() for kw in tech_keywords)

def get_skills_gap(user_skills, required_skills):
    if not user_skills or not required_skills:
        return [], required_skills[:5] if required_skills else []
    user_lower = [s.lower().strip() for s in user_skills]
    have, missing = [], []
    for skill in required_skills:
        skill_lower = skill.lower().strip()
        matched = any(skill_lower in u or u in skill_lower for u in user_lower)
        if matched: have.append(skill)
        else:       missing.append(skill)
    return have, missing

def get_vision_alignment(career_title, tech_field, region):
    if region not in VISION_SECTORS:
        return None
    vision = VISION_SECTORS[region]
    title_lower = career_title.lower()
    field_lower = tech_field.lower() if tech_field else ""
    for sector in vision["sectors"]:
        for kw in sector["keywords"]:
            if kw in title_lower or kw in field_lower:
                return {"vision_label": vision["label"], "flag": vision["flag"],
                        "sector": sector["name"], "demand": sector["demand"], "growth": sector["growth"]}
    return None

def get_tech_recommendations(user_text, experience, education, region="USA", user_skills=None):
    proba = nlp_model.predict_proba([user_text.lower()])[0]
    classes = nlp_model.classes_
    max_proba = float(proba.max())
    dynamic_threshold = max_proba * 0.40
    top_fields = [(classes[i], float(proba[i])) for i in proba.argsort()[::-1]
                  if proba[i] >= dynamic_threshold and proba[i] > 0.05][:5]
    recommendations = []
    for field, confidence in top_fields:
        field_data = df_salary[df_salary["primary_tech_field"] == field]
        if len(field_data) < 5: continue
        top_job    = field_data["job_title"].value_counts().index[0]
        avg_salary = field_data["annual_salary_usd"].mean()
        all_skills = ";".join(field_data["skills"].tolist())
        skills_list = [s.strip() for s in all_skills.replace(",", ";").split(";") if s.strip()]
        top_skills = [s for s, _ in Counter(skills_list).most_common(6)]
        all_certs  = ";".join(field_data["certifications"].tolist())
        certs_list = [c.strip() for c in all_certs.replace(",", ";").split(";")
                      if c.strip() and c.strip().lower() not in ["nan", ""]]
        top_certs = list(dict.fromkeys([c for c, _ in Counter(certs_list).most_common(3)]))
        try:
            def encode_field(col, val):
                le = encoders.get(f"salary_{col}")
                if le and val in le.classes_: return int(le.transform([val])[0])
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
        exp_level = "Junior" if experience < 2 else "Mid-level" if experience < 5 else "Senior"
        have_skills, missing_skills = get_skills_gap(user_skills or [], top_skills)
        vision_align = get_vision_alignment(top_job, field, region)
        popular_careers[top_job] += 1
        recommendations.append({
            "career_title": top_job, "tech_field": field,
            "estimated_salary": round(final_salary_usd, 2),
            "salary_display": salary_display, "salary_range": salary_range,
            "currency": CURRENCY_SYMBOLS.get(region, ("USD", 1.0))[0], "region": region,
            "future_demand": DEMAND_MAP.get(field, DEMAND_MAP["default"]),
            "required_skills": top_skills, "skills_you_have": have_skills,
            "skills_to_learn": missing_skills, "certifications": top_certs,
            "roadmap": ROADMAPS.get(field, ROADMAPS["default"]),
            "experience_level": exp_level, "data_points": len(field_data),
            "confidence": round(confidence * 100, 1), "source": "tech_dataset",
            "description": f"A career in {field} focusing on {', '.join(top_skills[:3])}.",
            "vision_alignment": vision_align,
        })
    return recommendations

def get_onet_recommendations(user_text, experience, region="USA", user_skills=None):
    # Enhance query with intent map BEFORE vectorizing
    enhanced_text = enhance_query(user_text)

    query_vec    = onet_vectorizer.transform([enhanced_text])
    similarities = cosine_similarity(query_vec, onet_matrix)[0]
    max_sim      = float(similarities.max())

    if max_sim < 0.03:
        return []

    dynamic_threshold = max_sim * 0.45
    top_indices = [i for i in similarities.argsort()[::-1]
                   if similarities[i] >= dynamic_threshold][:10]

    recommendations = []
    exp_level = "Junior" if experience < 2 else "Mid-level" if experience < 5 else "Senior"

    for idx in top_indices:
        row        = df_occ.iloc[idx]
        similarity = float(similarities[idx])
        if similarity < 0.03: continue
        occ_code   = row.get("O*NET-SOC Code", "")
        title      = row["Title"]
        desc       = row["Description"]
        onet_skills = skills_map.get(occ_code, [])
        edu_req    = edu_map.get(occ_code, "Relevant degree or certification")
        roadmap    = build_onet_roadmap(title, onet_skills, edu_req)
        est_usd    = estimate_onet_salary(title)
        sal_display, sal_range = convert_salary(est_usd, region)
        have_skills, missing_skills = get_skills_gap(user_skills or [], onet_skills)
        vision_align = get_vision_alignment(title, "", region)
        popular_careers[title] += 1
        recommendations.append({
            "career_title": title, "tech_field": "General Career",
            "estimated_salary": est_usd, "salary_display": sal_display,
            "salary_range": sal_range,
            "currency": CURRENCY_SYMBOLS.get(region, ("USD", 1.0))[0], "region": region,
            "future_demand": "High", "required_skills": onet_skills[:6],
            "skills_you_have": have_skills, "skills_to_learn": missing_skills,
            "certifications": [], "education_required": str(edu_req) if edu_req else "Relevant degree",
            "roadmap": roadmap, "experience_level": exp_level,
            "data_points": len(df_occ), "confidence": round(similarity * 100, 1),
            "description": desc[:250] + "..." if len(desc) > 250 else desc,
            "source": "onet", "vision_alignment": vision_align,
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
        search_log.append({"timestamp": datetime.now().isoformat(), "query": user_text[:50], "region": region, "results": len(recommendations)})
        return jsonify({"success": True, "recommendations": recommendations, "total": len(recommendations)})
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
        "total_searches": len(search_log),
        "popular_careers": popular_careers.most_common(10),
        "popular_regions": popular_regions.most_common(10),
        "recent_searches": search_log[-20:][::-1],
        "region_salary_summary": {
            region: {field: data["avg_usd"] for field, data in fields.items()}
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
        return jsonify({"career": row["Title"], "skills_you_have": have, "skills_to_learn": missing,
                        "match_percent": round(len(have) / max(len(required), 1) * 100, 1)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)