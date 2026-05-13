import fitz  # PyMuPDF
import re
from typing import Dict, List

SKILL_KEYWORDS = [
    "Python",
    "JavaScript",
    "TypeScript",
    "FastAPI",
    "Django",
    "Flask",
    "React",
    "Node.js",
    "SQL",
    "PostgreSQL",
    "MongoDB",
    "TensorFlow",
    "PyTorch",
    "Scikit-learn",
    "Pandas",
    "NumPy",
    "Spark",
    "Keras",
    "AWS",
    "Docker",
    "Kubernetes",
    "Redis",
    "GraphQL",
    "REST",
    "gRPC",
    "CI/CD",
    "Git",
    "GitHub",
    "Linux",
    "NLP",
    "C",
    "C++",
    "Java",
    "HTML",
    "CSS",
    "Tailwind",
    "ML",
    "OpenCV",
    "LangChain",
    "LLMs",
    "RAG",
    "Render",
    "Postman",
    "Hugging Face",
]

DOMAIN_KEYWORDS = [
    "Machine Learning",
    "Data Science",
    "NLP",
    "Backend Development",
    "AI",
    "Computer Vision",
    "Analytics",
]

SECTION_HEADERS = [
    "skills",
    "technical skills",
    "frameworks",
    "technologies",
    "tools",
    "experience",
    "projects",
    "summary",
    "profile",
    "education",
    "certifications",
    "domains",
]


def parse_resume(content: bytes) -> Dict:
    """
    Parse a resume PDF and extract structured skills, domains, frameworks, and project technologies.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        normalized = normalize_text(text)
        sections = split_sections(text)

        skills = extract_terms_from_sections(sections, ["skills", "technical skills", "tools", "technologies", "frameworks"])
        frameworks = extract_terms_from_sections(sections, ["frameworks", "technologies", "tools"])
        technologies = extract_terms_by_vocab(normalized, SKILL_KEYWORDS)
        domains = extract_terms_by_vocab(normalized, DOMAIN_KEYWORDS)
        project_technologies = extract_project_technologies(sections)

        # Merge section-specific skills with global technologies for a more robust result
        unified_skills = sorted(set(skills + technologies))[:30]

        return {
            "skills": unified_skills,
            "frameworks": sorted(set(frameworks))[:20],
            "technologies": sorted(set(technologies))[:30],
            "domains": sorted(set(domains))[:10],
            "project_technologies": sorted(set(project_technologies))[:30],
            "summary_text": text[:1200].strip(),
        }
    except Exception as e:
        raise Exception(f"Failed to parse PDF: {str(e)}")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sections(text: str) -> Dict[str, str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    sections: Dict[str, List[str]] = {"summary": []}
    current = "summary"

    for line in lines:
        lower = line.lower().rstrip(":")
        heading = next((header for header in SECTION_HEADERS if lower.startswith(header)), None)
        if heading:
            current = heading
            sections.setdefault(current, [])
            content_after = lower[len(heading):].strip(" :-")
            if content_after:
                sections[current].append(line)
            continue
        sections.setdefault(current, []).append(line)

    return {section: "\n".join(lines) for section, lines in sections.items()}


def extract_terms_by_vocab(text: str, vocabulary: List[str]) -> List[str]:
    lower_text = text.lower()
    found = []
    for term in vocabulary:
        escaped_term = re.escape(term.lower())
        pattern = r'(?<![a-z0-9])' + escaped_term + r'(?![a-z0-9])'
        if re.search(pattern, lower_text):
            found.append(term)
    return found


def extract_terms_from_sections(sections: Dict[str, str], section_names: List[str]) -> List[str]:
    text = "\n".join(sections.get(name, "") for name in section_names)
    return extract_terms_by_vocab(text, SKILL_KEYWORDS)


def extract_project_technologies(sections: Dict[str, str]) -> List[str]:
    project_text = sections.get("projects", "") + "\n" + sections.get("experience", "")
    return extract_terms_by_vocab(project_text, SKILL_KEYWORDS + DOMAIN_KEYWORDS)