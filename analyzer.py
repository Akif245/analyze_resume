import argparse
import io
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


CURRENT_DATE = datetime(2026, 4, 9)

MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

SKILL_CATALOG = {
    "Programming Languages": [
        "python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "rust",
        "php", "ruby", "kotlin", "swift", "scala", "r", "sql", "matlab", "dart",
        "bash", "powershell",
    ],
    "Frameworks/Libraries": [
        "react", "next.js", "nextjs", "angular", "vue", "django", "flask", "fastapi",
        "spring", "spring boot", "node.js", "nodejs", "express", "laravel", "bootstrap",
        "tailwind", "pandas", "numpy", "scikit-learn", "tensorflow", "keras", "pytorch",
        "opencv", "selenium", "pytest",
    ],
    "Tools/Technologies": [
        "git", "github", "gitlab", "docker", "kubernetes", "aws", "azure", "gcp",
        "linux", "rest api", "graphql", "postman", "jira", "figma", "tableau",
        "power bi", "ci/cd", "jenkins", "terraform", "excel", "firebase", "supabase",
        "html", "css", "machine learning", "deep learning", "nlp", "computer vision",
    ],
    "Databases": [
        "mysql", "postgresql", "postgres", "mongodb", "sqlite", "oracle", "redis",
        "mariadb", "dynamodb", "firebase firestore", "sql server",
    ],
    "Soft Skills": [
        "communication", "leadership", "teamwork", "problem solving", "critical thinking",
        "adaptability", "time management", "collaboration", "ownership", "mentoring",
        "stakeholder management", "presentation", "analytical thinking",
    ],
}

ROLE_HINTS = [
    "software engineer", "developer", "frontend developer", "backend developer",
    "full stack developer", "data analyst", "data scientist", "machine learning engineer",
    "intern", "research assistant", "project engineer", "consultant", "qa engineer",
    "devops engineer", "product manager", "business analyst",
]

SECTION_ALIASES = {
    "experience": ["experience", "work experience", "professional experience", "employment", "internship"],
    "projects": ["projects", "academic projects", "personal projects", "project experience"],
    "education": ["education", "academic background", "academics", "qualification"],
    "skills": ["skills", "technical skills", "core competencies", "technologies"],
}


@dataclass
class DateRange:
    start: Optional[datetime]
    end: Optional[datetime]
    raw: str


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(raw_bytes: bytes) -> str:
    if PdfReader is None:
        raise ValueError("PDF support requires the optional dependency 'pypdf'. Install it with: pip install pypdf")

    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return clean_text("\n".join(pages))


def extract_text_from_docx(raw_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as archive:
        document_xml = archive.read("word/document.xml")

    root = ET.fromstring(document_xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        runs = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return clean_text("\n".join(paragraphs))


def extract_text_from_bytes(raw_bytes: bytes, filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in {".txt", ".md", ".text"}:
        return clean_text(raw_bytes.decode("utf-8", errors="ignore"))
    if suffix == ".json":
        return clean_text(raw_bytes.decode("utf-8", errors="ignore"))
    if suffix == ".docx":
        return extract_text_from_docx(raw_bytes)
    if suffix == ".pdf":
        return extract_text_from_pdf(raw_bytes)

    return clean_text(raw_bytes.decode("utf-8", errors="ignore"))


def read_text(path: Optional[str], direct_text: Optional[str]) -> str:
    if direct_text:
        return clean_text(direct_text)
    if path:
        file_path = Path(path)
        raw_bytes = file_path.read_bytes()
        return extract_text_from_bytes(raw_bytes, file_path.name)
    return ""


def split_lines(text: str) -> List[str]:
    return [line.strip(" -\t") for line in text.splitlines() if line.strip()]


def extract_basic_info(text: str) -> Dict[str, Optional[str]]:
    lines = split_lines(text)
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    phone_match = re.search(r"(\+?\d[\d\s().-]{7,}\d)", text)
    linkedin_match = re.search(r"(https?://)?(www\.)?linkedin\.com/[^\s|,]+", text, re.I)
    github_match = re.search(r"(https?://)?(www\.)?(github\.com|gitlab\.com|behance\.net|dribbble\.com|portfolio)[^\s|,]*", text, re.I)

    location = None
    for line in lines[:10]:
        if len(line.split()) > 5:
            continue
        if any(skill_word in line.lower() for skill_word in ("python", "react", "sql", "java", "docker", "git", "html", "css")):
            continue
        if re.search(r"\b[A-Z][a-z]+,\s*[A-Z][a-zA-Z. ]+\b", line):
            location = line
            break
        if re.search(r"\b(?:India|USA|United States|UK|Canada|Germany|Australia|Remote)\b", line, re.I):
            location = line
            break

    full_name = None
    for line in lines[:6]:
        if any(token in line.lower() for token in ("@", "linkedin", "github", "resume", "cv", "phone", "mobile")):
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(re.match(r"^[A-Za-z][A-Za-z'.-]*$", word) for word in words):
            full_name = line
            break

    return {
        "full_name": full_name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(1).strip() if phone_match else None,
        "linkedin": linkedin_match.group(0) if linkedin_match else None,
        "github_portfolio": github_match.group(0) if github_match else None,
        "location": location,
    }


def find_section_bounds(lines: List[str]) -> Dict[str, Tuple[int, int]]:
    lower_lines = [line.lower() for line in lines]
    section_positions = {}

    for section, aliases in SECTION_ALIASES.items():
        for idx, line in enumerate(lower_lines):
            if any(line == alias or line.startswith(alias + ":") for alias in aliases):
                section_positions[section] = idx
                break

    ordered = sorted(section_positions.items(), key=lambda item: item[1])
    bounds: Dict[str, Tuple[int, int]] = {}
    for pos, (section, start_idx) in enumerate(ordered):
        end_idx = len(lines)
        if pos + 1 < len(ordered):
            end_idx = ordered[pos + 1][1]
        bounds[section] = (start_idx + 1, end_idx)
    return bounds


def slice_section(lines: List[str], bounds: Dict[str, Tuple[int, int]], key: str) -> List[str]:
    if key not in bounds:
        return []
    start, end = bounds[key]
    return lines[start:end]


def normalize_skill_name(skill: str) -> str:
    mapping = {
        "nextjs": "Next.js",
        "nodejs": "Node.js",
        "postgres": "PostgreSQL",
        "firebase firestore": "Firebase Firestore",
        "ci/cd": "CI/CD",
        "nlp": "NLP",
        "sql": "SQL",
        "aws": "AWS",
        "gcp": "GCP",
        "git": "Git",
        "github": "GitHub",
    }
    if skill in mapping:
        return mapping[skill]
    return " ".join(part.upper() if len(part) <= 3 else part.capitalize() for part in skill.split())


def collect_skills(text: str) -> Dict[str, List[str]]:
    lowered = text.lower()
    result: Dict[str, List[str]] = {}
    for category, skills in SKILL_CATALOG.items():
        found = []
        for skill in skills:
            pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
            if re.search(pattern, lowered):
                found.append(normalize_skill_name(skill))
        result[category] = sorted(set(found))
    return result


def parse_month_year(text: str) -> Optional[datetime]:
    text = text.strip().lower()
    if text in {"present", "current", "now", "ongoing"}:
        return CURRENT_DATE

    month = None
    year = None
    month_match = re.search(r"\b(" + "|".join(MONTH_MAP.keys()) + r")\b", text)
    if month_match:
        month = MONTH_MAP[month_match.group(1)]

    year_match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", text)
    if year_match:
        year = int(year_match.group(1))

    if year is None:
        return None
    return datetime(year, month or 1, 1)


def extract_date_range(line: str) -> Optional[DateRange]:
    normalized = line.replace("–", "-").replace("—", "-").replace(" to ", " - ")
    match = re.search(
        r"((?:[A-Za-z]{3,9}\s+)?(?:19\d{2}|20\d{2}|21\d{2}))\s*-\s*((?:[A-Za-z]{3,9}\s+)?(?:19\d{2}|20\d{2}|21\d{2})|Present|Current|Now|Ongoing)",
        normalized,
        re.I,
    )
    if not match:
        return None
    start = parse_month_year(match.group(1))
    end = parse_month_year(match.group(2))
    return DateRange(start=start, end=end, raw=match.group(0))


def month_diff(start: datetime, end: datetime) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


def split_role_company(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not text:
        return None, None
    parts = [part.strip() for part in re.split(r"\s+\|\s+|\s+at\s+|,\s+", text, maxsplit=1) if part.strip()]
    if len(parts) >= 2:
        return parts[0], parts[1]
    line = text.lower()
    for hint in ROLE_HINTS:
        if hint in line:
            return text, None
    return None, text


def infer_experience_from_general_lines(lines: List[str]) -> List[Dict[str, object]]:
    inferred = []
    for line in lines:
        if any(role in line.lower() for role in ROLE_HINTS):
            inferred.append({
                "role": line,
                "company": None,
                "duration": None,
                "key_contributions": [],
            })
    return inferred


def format_total_experience(total_months: int) -> str:
    years = total_months // 12
    months = total_months % 12
    if total_months == 0:
        return "0 years 0 months"
    return f"{years} years {months} months"


def parse_experience(lines: List[str]) -> Dict[str, object]:
    experiences = []
    current = None

    for line in lines:
        date_range = extract_date_range(line)
        if date_range:
            if current:
                experiences.append(current)
            title_part = line.replace(date_range.raw, "").strip(" |,-")
            role, company = split_role_company(title_part)
            current = {
                "role": role,
                "company": company,
                "duration": date_range.raw,
                "key_contributions": [],
                "_start": date_range.start,
                "_end": date_range.end,
            }
            continue

        if current:
            current["key_contributions"].append(line.lstrip("- ").strip())

    if current:
        experiences.append(current)

    if not experiences:
        experiences = infer_experience_from_general_lines(lines)

    total_months = 0
    dated_items = []
    for exp in experiences:
        start = exp.pop("_start", None)
        end = exp.pop("_end", None)
        if start and end:
            total_months += month_diff(start, end)
            dated_items.append((start, end))

    dated_items.sort(key=lambda item: item[0])
    gaps = []
    for idx in range(1, len(dated_items)):
        prev_end = dated_items[idx - 1][1]
        current_start = dated_items[idx][0]
        gap = month_diff(prev_end, current_start)
        if gap >= 6:
            gaps.append(f"{gap} month gap between roles")

    return {
        "items": experiences,
        "total_experience": format_total_experience(total_months),
        "career_gaps": gaps,
    }


def is_project_header(line: str) -> bool:
    stripped = line.strip()
    if ":" in stripped or "|" in stripped:
        return True
    if len(stripped) > 90:
        return False
    words = stripped.split()
    return 1 <= len(words) <= 8 and stripped == stripped.title()


def clean_project_name(line: str) -> str:
    return re.split(r"[:|]", line, maxsplit=1)[0].strip(" -")


def extract_project_inline_description(line: str) -> str:
    parts = re.split(r"[:|]", line, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""


def infer_projects_from_text(lines: List[str]) -> List[Dict[str, object]]:
    inferred = []
    blob = " ".join(lines)
    if "project" in blob.lower():
        sentences = re.split(r"(?<=[.!?])\s+", blob)
        for sentence in sentences[:3]:
            if "project" in sentence.lower():
                inferred.append({
                    "project_name": sentence[:50].strip(),
                    "tech_stack": [],
                    "problem_solved": sentence.strip(),
                    "complexity_level": "Beginner",
                    "real_world_impact": "Low",
                })
    return inferred


def estimate_complexity(project: Dict[str, object]) -> str:
    text = f"{project['project_name']} {project['problem_solved']}".lower()
    tech_count = len(project["tech_stack"])
    advanced_markers = ["scalable", "real-time", "machine learning", "deep learning", "microservices", "deployment", "optimization", "nlp"]
    intermediate_markers = ["api", "dashboard", "authentication", "database", "automation", "analytics"]

    if tech_count >= 5 or any(marker in text for marker in advanced_markers):
        return "Advanced"
    if tech_count >= 3 or any(marker in text for marker in intermediate_markers):
        return "Intermediate"
    return "Beginner"


def estimate_impact(project: Dict[str, object]) -> str:
    text = project["problem_solved"].lower()
    high_markers = ["users", "clients", "revenue", "production", "deployed", "%", "reduced", "improved", "real-time"]
    medium_markers = ["automated", "analyzed", "dashboard", "prediction", "classification", "recommendation"]

    if any(marker in text for marker in high_markers):
        return "High"
    if any(marker in text for marker in medium_markers):
        return "Medium"
    return "Low"


def project_rank(project: Dict[str, object]) -> int:
    complexity_score = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}[project["complexity_level"]]
    impact_score = {"Low": 1, "Medium": 2, "High": 3}[project["real_world_impact"]]
    return complexity_score + impact_score + len(project["tech_stack"]) // 2


def parse_projects(lines: List[str], skills: Dict[str, List[str]]) -> Dict[str, object]:
    projects = []
    current = None

    for line in lines:
        if is_project_header(line):
            if current:
                projects.append(current)
            current = {
                "project_name": clean_project_name(line),
                "tech_stack": [],
                "problem_solved": extract_project_inline_description(line),
                "complexity_level": "Beginner",
                "real_world_impact": "Low",
            }
            continue

        if current:
            current["problem_solved"] = (current["problem_solved"] + " " + line).strip()

    if current:
        projects.append(current)

    if not projects:
        projects = infer_projects_from_text(lines)

    all_skill_terms = {
        skill.lower(): skill
        for category in skills.values()
        for skill in category
    }

    for project in projects:
        text_blob = f"{project['project_name']} {project['problem_solved']}".lower()
        tech_stack = []
        for term_lower, term_display in all_skill_terms.items():
            if term_lower in text_blob:
                tech_stack.append(term_display)
        project["tech_stack"] = sorted(set(tech_stack))
        project["complexity_level"] = estimate_complexity(project)
        project["real_world_impact"] = estimate_impact(project)
        if not project["problem_solved"]:
            project["problem_solved"] = "Problem statement not clearly described in resume."

    best_project = None
    weak_projects = []
    if projects:
        ranked = sorted(projects, key=project_rank, reverse=True)
        best_project = ranked[0]["project_name"]
        weak_projects = [
            project["project_name"]
            for project in projects
            if project_rank(project) <= 2 or "crud" in project["project_name"].lower()
        ]

    return {
        "items": projects,
        "best_project": best_project,
        "weak_or_repetitive_projects": weak_projects,
    }


def parse_education(lines: List[str]) -> Dict[str, object]:
    items = []
    joined = "\n".join(lines)
    entries = re.split(r"\n(?=[A-Z])", joined)

    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        degree = None
        institution = None
        year = None

        degree_match = re.search(r"(Bachelor|Master|B\.Tech|M\.Tech|BSc|MSc|MBA|PhD|Diploma|BE|ME)[^,\n]*", entry, re.I)
        year_match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", entry)

        if degree_match:
            degree = degree_match.group(0).strip()

        parts = [part.strip() for part in re.split(r"[,|]", entry) if part.strip()]
        if parts:
            institution = parts[1] if degree and len(parts) > 1 else parts[0]

        if year_match:
            year = year_match.group(1)

        items.append({
            "degree": degree,
            "institution": institution,
            "year": year,
        })

    return {"items": items}


def extract_keywords(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z.+#/-]{1,}", text.lower())
    stop_words = {
        "the", "and", "with", "for", "that", "have", "from", "this", "your", "you",
        "are", "was", "were", "will", "using", "used", "into", "over", "under", "than",
        "work", "team", "project", "experience", "skills", "education",
    }
    counts = Counter(token for token in tokens if token not in stop_words and len(token) > 2)
    return [token for token, _ in counts.most_common(40)]


def calculate_ats_score(
    resume_text: str,
    basic_info: Dict[str, Optional[str]],
    skills: Dict[str, List[str]],
    experience: Dict[str, object],
    projects: Dict[str, object],
) -> Dict[str, object]:
    score = 0
    reasons = []

    formatting_score = 15 if "\n" in resume_text and len(split_lines(resume_text)) >= 15 else 6
    score += formatting_score
    reasons.append(f"Formatting: {formatting_score}/15 based on structural readability.")

    extracted_skill_count = sum(len(items) for items in skills.values())
    skill_score = min(25, extracted_skill_count * 2)
    score += skill_score
    reasons.append(f"Skills relevance: {skill_score}/25 from detected technical and soft skills.")

    project_count = len(projects["items"])
    project_score = min(25, project_count * 6)
    if projects["best_project"]:
        project_score += 4
    project_score = min(25, project_score)
    score += project_score
    reasons.append(f"Project quality: {project_score}/25 based on project depth and clarity.")

    experience_count = len(experience["items"])
    experience_score = min(20, experience_count * 6)
    if experience["total_experience"] != "0 years 0 months":
        experience_score += 2
    experience_score = min(20, experience_score)
    score += experience_score
    reasons.append(f"Experience: {experience_score}/20 from role history and tenure signals.")

    keyword_score = 15 if extracted_skill_count >= 8 else 8 if extracted_skill_count >= 4 else 4
    score += keyword_score
    reasons.append(f"Keyword usage: {keyword_score}/15 based on ATS-searchable terms.")

    if not basic_info["email"] or not basic_info["phone"]:
        score -= 5
        reasons.append("Penalty: missing key contact fields reduces ATS trust.")

    score = max(0, min(100, score))
    return {"score": score, "reason": " ".join(reasons)}


def calculate_job_match(resume_text: str, job_description: str) -> Dict[str, object]:
    if not job_description.strip():
        return {
            "match_percentage": None,
            "missing_skills": [],
            "matching_skills": [],
            "suggestions": [],
        }

    resume_keywords = set(extract_keywords(resume_text))
    jd_keywords = set(extract_keywords(job_description))
    matching = sorted(resume_keywords & jd_keywords)
    missing = sorted(jd_keywords - resume_keywords)
    match_percentage = round(len(matching) / len(jd_keywords) * 100) if jd_keywords else 0

    suggestions = []
    if missing:
        suggestions.append("Add evidence for missing JD keywords only if you genuinely have that experience.")
        suggestions.append("Mirror the JD wording in skills, project bullets, and experience lines where accurate.")
    if match_percentage < 60:
        suggestions.append("Tailor the resume summary and top projects more directly to the target role.")

    return {
        "match_percentage": match_percentage,
        "missing_skills": missing[:15],
        "matching_skills": matching[:15],
        "suggestions": suggestions,
    }


def generate_strengths(
    basic_info: Dict[str, Optional[str]],
    skills: Dict[str, List[str]],
    experience: Dict[str, object],
    projects: Dict[str, object],
) -> List[str]:
    strengths = []
    if sum(len(items) for items in skills.values()) >= 8:
        strengths.append("Good breadth of identifiable ATS-readable skills.")
    if projects["best_project"]:
        strengths.append(f"Strongest project signal appears to be '{projects['best_project']}'.")
    if experience["items"]:
        strengths.append("Resume shows practical experience rather than skills-only claims.")
    if basic_info["linkedin"] or basic_info["github_portfolio"]:
        strengths.append("Resume includes professional profile links for recruiter validation.")
    if any(project["real_world_impact"] in {"Medium", "High"} for project in projects["items"]):
        strengths.append("At least one project suggests real-world or measurable impact.")
    if not strengths:
        strengths.append("Resume provides enough baseline content to begin evaluation.")
    return strengths[:5]


def generate_weaknesses(
    resume_text: str,
    basic_info: Dict[str, Optional[str]],
    skills: Dict[str, List[str]],
    experience: Dict[str, object],
    projects: Dict[str, object],
) -> List[str]:
    weaknesses = []
    if not basic_info["phone"] or not basic_info["email"]:
        weaknesses.append("Missing core contact details makes recruiter follow-up harder.")
    if len(resume_text.split()) < 250:
        weaknesses.append("Resume is short, so there is not enough depth to fully prove capability.")
    if not projects["items"]:
        weaknesses.append("No clear project section is a major weakness, especially for early-career candidates.")
    if projects["weak_or_repetitive_projects"]:
        weaknesses.append("Some projects look generic, repetitive, or weakly differentiated.")
    if not experience["items"]:
        weaknesses.append("No clear experience timeline reduces trust in career progression.")
    if sum(len(items) for items in skills.values()) < 5:
        weaknesses.append("Skill coverage is too thin for strong ATS performance.")
    if not any(exp["key_contributions"] for exp in experience["items"]):
        weaknesses.append("Experience bullets are vague or missing, which weakens impact.")
    return weaknesses[:5]


def generate_suggestions(
    basic_info: Dict[str, Optional[str]],
    skills: Dict[str, List[str]],
    experience: Dict[str, object],
    projects: Dict[str, object],
    job_match: Dict[str, object],
) -> List[str]:
    suggestions = []
    if not basic_info["linkedin"]:
        suggestions.append("Add a LinkedIn URL to improve credibility and recruiter verification.")
    if not basic_info["github_portfolio"]:
        suggestions.append("Add a GitHub or portfolio link so projects can be validated quickly.")
    if not experience["items"] or not any(exp["key_contributions"] for exp in experience["items"]):
        suggestions.append("Rewrite experience entries with action verbs, tools used, and measurable outcomes.")
    if projects["items"]:
        suggestions.append("For each project, state the problem, tech stack, scale, and one measurable result.")
    else:
        suggestions.append("Add 2 to 3 serious projects; without them the resume is weak for technical hiring.")
    if job_match.get("missing_skills"):
        suggestions.append("Close JD gaps by highlighting matching coursework, tools, or projects you already have.")
    if sum(len(items) for items in skills.values()) < 8:
        suggestions.append("Consolidate technical skills into a dedicated section with consistent naming.")
    return suggestions[:6]


def detect_red_flags(
    resume_text: str,
    basic_info: Dict[str, Optional[str]],
    experience: Dict[str, object],
    projects: Dict[str, object],
) -> List[str]:
    red_flags = []
    if not basic_info["email"] or not basic_info["phone"]:
        red_flags.append("Missing contact info")
    if not projects["items"]:
        red_flags.append("No projects")
    if len(resume_text.split()) < 150:
        red_flags.append("Too short resume")
    if experience["items"] and not any(exp["key_contributions"] for exp in experience["items"]):
        red_flags.append("Vague descriptions")
    buzzwords = ["hardworking", "passionate", "dynamic", "synergy", "results-driven", "go-getter"]
    buzzword_hits = [word for word in buzzwords if word in resume_text.lower()]
    if len(buzzword_hits) >= 3:
        red_flags.append("Overloaded buzzwords")
    return red_flags


def infer_roles(resume_text: str, projects: Dict[str, object], experience: Dict[str, object]) -> List[str]:
    text = resume_text.lower()
    roles = []
    if any(term in text for term in ["react", "html", "css", "javascript", "frontend"]):
        roles.append("Frontend Developer")
    if any(term in text for term in ["python", "java", "api", "backend", "database"]):
        roles.append("Backend Developer")
    if any(term in text for term in ["react", "node", "full stack", "fullstack"]):
        roles.append("Full Stack Developer")
    if any(term in text for term in ["machine learning", "tensorflow", "pytorch", "nlp"]):
        roles.append("Machine Learning Engineer")
    if any(term in text for term in ["sql", "tableau", "power bi", "analytics"]):
        roles.append("Data Analyst")
    if not roles and (projects["items"] or experience["items"]):
        roles.append("Software Engineer")
    return sorted(set(roles))[:5]


def final_verdict(
    experience: Dict[str, object],
    projects: Dict[str, object],
    ats_score: Dict[str, object],
    resume_text: str,
) -> Dict[str, object]:
    score = ats_score["score"]
    if score >= 75:
        hireability = "High"
    elif score >= 50:
        hireability = "Medium"
    else:
        hireability = "Low"

    confidence = "High" if len(resume_text.split()) >= 350 else "Medium" if len(resume_text.split()) >= 180 else "Low"
    return {
        "hireability_level": hireability,
        "suitable_roles": infer_roles(resume_text, projects, experience),
        "confidence_level": confidence,
    }


def analyze_resume(resume_text: str, job_description: str = "") -> Dict[str, object]:
    cleaned_resume = clean_text(resume_text)
    if not cleaned_resume:
        return {"error": "Resume text is empty. Unable to analyze."}

    lines = split_lines(cleaned_resume)
    bounds = find_section_bounds(lines)

    basic_info = extract_basic_info(cleaned_resume)
    skills = collect_skills(cleaned_resume)
    experience = parse_experience(slice_section(lines, bounds, "experience"))
    projects = parse_projects(slice_section(lines, bounds, "projects"), skills)
    education = parse_education(slice_section(lines, bounds, "education"))
    ats_score = calculate_ats_score(cleaned_resume, basic_info, skills, experience, projects)
    job_match = calculate_job_match(cleaned_resume, job_description)
    strengths = generate_strengths(basic_info, skills, experience, projects)
    weaknesses = generate_weaknesses(cleaned_resume, basic_info, skills, experience, projects)
    suggestions = generate_suggestions(basic_info, skills, experience, projects, job_match)
    red_flags = detect_red_flags(cleaned_resume, basic_info, experience, projects)
    verdict = final_verdict(experience, projects, ats_score, cleaned_resume)

    if len(cleaned_resume.split()) < 120:
        suggestions.insert(0, "Resume has limited detail, so analysis confidence is reduced. Add fuller bullets and context.")

    return {
        "basic_info": basic_info,
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "education": education,
        "ats_score": ats_score,
        "job_match": job_match,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "red_flags": red_flags,
        "final_verdict": verdict,
    }


def analyze_resume_file_bytes(raw_bytes: bytes, filename: str, job_description: str = "") -> Dict[str, object]:
    resume_text = extract_text_from_bytes(raw_bytes, filename)
    return analyze_resume(resume_text, job_description)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a resume and return structured JSON.")
    parser.add_argument("--resume-file", help="Path to resume text file.")
    parser.add_argument("--resume-text", help="Resume text content.")
    parser.add_argument("--jd-file", help="Path to job description file.")
    parser.add_argument("--jd-text", help="Job description text content.")
    parser.add_argument("--output", help="Optional output JSON file path.")
    args = parser.parse_args()

    resume_text = read_text(args.resume_file, args.resume_text)
    jd_text = read_text(args.jd_file, args.jd_text)
    result = analyze_resume(resume_text, jd_text)

    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
