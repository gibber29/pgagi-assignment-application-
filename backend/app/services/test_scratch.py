import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "app"))

from services.resume_service import split_sections, extract_terms_by_vocab, SKILL_KEYWORDS, parse_resume

text = """
John Doe
Software Engineer

SKILLS
Programming Languages       C, C++, Python, Java
Frameworks & Web            HTML, CSS, JavaScript, React.js, Node.js, Tailwind
AI & DataScience            ML, OpenCv, LangChain, Numpy, Pandas, Scikit-Learn, LLMs, RAG, NLP
Tools                       Git, GitHub, Render, AWS, Postman, Hugging Face

EXPERIENCE
Company ABC
"""

print("Testing split_sections...")
sections = split_sections(text)
for k, v in sections.items():
    print(f"[{k}] -> {repr(v)}")

print("\nTesting extract_terms_from_sections...")
from services.resume_service import extract_terms_from_sections
skills = extract_terms_from_sections(sections, ["skills", "technical skills", "tools", "technologies", "frameworks"])
print(f"Extracted skills: {skills}")

print("\nTesting extract_terms_by_vocab regex...")
print("C++ in 'C++':", extract_terms_by_vocab("C++", ["C++"]))
print("C in 'Machine':", extract_terms_by_vocab("Machine", ["C"]))
print("C in 'C, C++':", extract_terms_by_vocab("C, C++", ["C"]))
print("React.js in 'React.js':", extract_terms_by_vocab("React.js", ["React.js"]))

