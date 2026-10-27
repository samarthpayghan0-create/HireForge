"""Skill taxonomy, role profiles and learning hints used by the analyzer."""

import re

# canonical skill -> (category, [aliases])
SKILLS = {
    # Programming languages
    "Python": ("Programming languages", ["python", "python3"]),
    "Java": ("Programming languages", ["java"]),
    "JavaScript": ("Programming languages", ["javascript", "js", "ecmascript", "es6"]),
    "TypeScript": ("Programming languages", ["typescript"]),
    "C++": ("Programming languages", ["c++"]),
    "C#": ("Programming languages", ["c#"]),
    "C": ("Programming languages", ["c programming", "c language"]),
    "Go": ("Programming languages", ["golang"]),
    "Kotlin": ("Programming languages", ["kotlin"]),
    "PHP": ("Programming languages", ["php"]),
    "SQL": ("Programming languages", ["sql", "t-sql", "pl/sql"]),
    "R": ("Programming languages", ["r programming", "rstudio"]),
    # Web
    "HTML": ("Web development", ["html", "html5"]),
    "CSS": ("Web development", ["css", "css3"]),
    "React": ("Web development", ["react", "reactjs", "react.js"]),
    "Angular": ("Web development", ["angular", "angularjs"]),
    "Vue": ("Web development", ["vue", "vue.js", "vuejs"]),
    "Node.js": ("Web development", ["node.js", "nodejs", "node js", "express.js", "expressjs"]),
    "Django": ("Web development", ["django"]),
    "Flask": ("Web development", ["flask"]),
    "FastAPI": ("Web development", ["fastapi"]),
    "Spring Boot": ("Web development", ["spring boot", "springboot", "spring framework"]),
    "REST APIs": ("Web development", ["rest api", "rest apis", "restful", "restful api", "restful apis", "rest"]),
    "Bootstrap": ("Web development", ["bootstrap"]),
    "Tailwind CSS": ("Web development", ["tailwind", "tailwind css"]),
    # Data / ML
    "Pandas": ("Data and AI", ["pandas"]),
    "NumPy": ("Data and AI", ["numpy"]),
    "Machine Learning": ("Data and AI", ["machine learning", "ml"]),
    "Deep Learning": ("Data and AI", ["deep learning", "neural network", "neural networks"]),
    "TensorFlow": ("Data and AI", ["tensorflow", "keras"]),
    "PyTorch": ("Data and AI", ["pytorch"]),
    "Scikit-learn": ("Data and AI", ["scikit-learn", "sklearn", "scikit learn"]),
    "NLP": ("Data and AI", ["nlp", "natural language processing"]),
    "Statistics": ("Data and AI", ["statistics", "statistical analysis"]),
    "Data Visualization": ("Data and AI", ["data visualization", "data visualisation", "matplotlib", "seaborn"]),
    "Power BI": ("Data and AI", ["power bi", "powerbi"]),
    "Tableau": ("Data and AI", ["tableau"]),
    "Excel": ("Data and AI", ["excel", "microsoft excel", "advanced excel"]),
    # Databases
    "MySQL": ("Databases", ["mysql"]),
    "PostgreSQL": ("Databases", ["postgresql", "postgres"]),
    "MongoDB": ("Databases", ["mongodb", "mongo db"]),
    "SQLite": ("Databases", ["sqlite"]),
    "Redis": ("Databases", ["redis"]),
    # Tools / cloud
    "Git": ("Tools and cloud", ["git"]),
    "GitHub": ("Tools and cloud", ["github", "gitlab", "bitbucket"]),
    "Docker": ("Tools and cloud", ["docker"]),
    "Kubernetes": ("Tools and cloud", ["kubernetes", "k8s"]),
    "AWS": ("Tools and cloud", ["aws", "amazon web services"]),
    "Azure": ("Tools and cloud", ["azure", "microsoft azure"]),
    "Google Cloud": ("Tools and cloud", ["gcp", "google cloud"]),
    "Linux": ("Tools and cloud", ["linux", "ubuntu", "bash", "shell scripting"]),
    "CI/CD": ("Tools and cloud", ["ci/cd", "ci cd", "jenkins", "github actions", "continuous integration"]),
    "Jira": ("Tools and cloud", ["jira"]),
    "Postman": ("Tools and cloud", ["postman"]),
    # CS fundamentals
    "Data Structures": ("CS fundamentals", ["data structures", "data structure"]),
    "Algorithms": ("CS fundamentals", ["algorithms", "algorithm", "problem solving"]),
    "OOP": ("CS fundamentals", ["oop", "oops", "object oriented", "object-oriented"]),
    "DBMS": ("CS fundamentals", ["dbms", "database management", "database design"]),
    "Operating Systems": ("CS fundamentals", ["operating systems", "operating system"]),
    "Computer Networks": ("CS fundamentals", ["computer networks", "networking"]),
    # Testing
    "Unit Testing": ("Testing", ["unit testing", "unit tests", "pytest", "junit", "unittest"]),
    "Selenium": ("Testing", ["selenium"]),
    "Test Automation": ("Testing", ["test automation", "automation testing", "manual testing", "qa"]),
    # Professional skills
    "Communication": ("Professional skills", ["communication", "presentation skills"]),
    "Teamwork": ("Professional skills", ["teamwork", "team player", "collaboration", "collaborated"]),
    "Leadership": ("Professional skills", ["leadership", "led a team", "team lead"]),
    "Agile": ("Professional skills", ["agile", "scrum", "kanban"]),
}

# canonical -> compiled pattern, built once
def _compile(alias):
    return re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(alias) + r"(?![A-Za-z0-9+#])", re.IGNORECASE)

SKILL_PATTERNS = {
    skill: [_compile(alias) for alias in aliases]
    for skill, (_cat, aliases) in SKILLS.items()
}

# Skills whose short aliases are ambiguous ("c", "r", "go", "rest", "ml", "qa", "git") need
# stricter handling: they are only counted when the canonical form is explicit.
STRICT_ALIASES = {"Go", "C", "R", "REST APIs", "Machine Learning", "Test Automation", "Git"}

ROLES = {
    "Python Developer": {
        "keywords": ["python", "django", "flask", "fastapi"],
        "core": ["Python", "SQL", "Git", "REST APIs", "Data Structures", "OOP"],
        "nice": ["Django", "Flask", "FastAPI", "MySQL", "PostgreSQL", "Docker", "Unit Testing", "Linux"],
    },
    "Full Stack Developer": {
        "keywords": ["full stack", "fullstack", "mern", "mean", "web developer"],
        "core": ["HTML", "CSS", "JavaScript", "React", "Node.js", "SQL", "Git", "REST APIs"],
        "nice": ["TypeScript", "MongoDB", "Django", "Docker", "AWS", "Unit Testing"],
    },
    "Frontend Developer": {
        "keywords": ["frontend", "front end", "front-end", "ui developer", "react developer"],
        "core": ["HTML", "CSS", "JavaScript", "React", "Git", "REST APIs"],
        "nice": ["TypeScript", "Angular", "Vue", "Bootstrap", "Tailwind CSS", "Unit Testing"],
    },
    "Backend Developer": {
        "keywords": ["backend", "back end", "back-end", "api developer", "server side"],
        "core": ["SQL", "REST APIs", "Git", "Data Structures", "DBMS", "OOP"],
        "nice": ["Python", "Java", "Node.js", "Django", "Spring Boot", "Docker", "Redis", "Unit Testing"],
    },
    "Java Developer": {
        "keywords": ["java developer", "java", "spring"],
        "core": ["Java", "OOP", "SQL", "Data Structures", "Git", "REST APIs"],
        "nice": ["Spring Boot", "MySQL", "Docker", "Unit Testing", "CI/CD", "Agile"],
    },
    "Data Analyst": {
        "keywords": ["data analyst", "business analyst", "analytics", "bi developer"],
        "core": ["SQL", "Excel", "Python", "Statistics", "Data Visualization"],
        "nice": ["Power BI", "Tableau", "Pandas", "NumPy", "Communication"],
    },
    "Data Scientist / ML Engineer": {
        "keywords": ["data scientist", "machine learning", "ml engineer", "ai engineer", "deep learning"],
        "core": ["Python", "Machine Learning", "Statistics", "Pandas", "NumPy", "Scikit-learn", "SQL"],
        "nice": ["Deep Learning", "TensorFlow", "PyTorch", "NLP", "Data Visualization", "Git", "Docker"],
    },
    "DevOps / Cloud Engineer": {
        "keywords": ["devops", "cloud engineer", "sre", "site reliability", "platform engineer"],
        "core": ["Linux", "Git", "Docker", "CI/CD", "AWS"],
        "nice": ["Kubernetes", "Azure", "Google Cloud", "Python", "Computer Networks"],
    },
    "QA / Test Engineer": {
        "keywords": ["qa", "tester", "test engineer", "quality assurance", "sdet"],
        "core": ["Test Automation", "Selenium", "SQL", "Jira", "Agile"],
        "nice": ["Python", "Java", "Postman", "Unit Testing", "CI/CD", "Git"],
    },
}

SECTION_PATTERNS = {
    "Summary / Objective": r"^\s*(professional\s+)?(summary|objective|profile|career objective|about me)\b",
    "Education": r"^\s*(education|academic|qualification)",
    "Skills": r"^\s*((technical|key|core)\s+)?skills|^\s*technologies|^\s*competenc",
    "Experience": r"^\s*(work\s+|professional\s+)?experience|^\s*employment|^\s*internships?\b",
    "Projects": r"^\s*(academic\s+|personal\s+)?projects?\b",
    "Certifications": r"^\s*(certifications?|certificates?|courses|licen[sc]es)",
    "Achievements": r"^\s*(achievements?|awards?|accomplishments|honou?rs)",
}

ACTION_VERBS = {
    "achieved", "analyzed", "analysed", "architected", "automated", "built", "collaborated",
    "configured", "contributed", "created", "debugged", "delivered", "deployed", "designed",
    "developed", "engineered", "enhanced", "established", "evaluated", "executed", "implemented",
    "improved", "increased", "integrated", "launched", "led", "maintained", "managed", "migrated",
    "modelled", "modeled", "optimized", "optimised", "organized", "organised", "planned", "reduced",
    "refactored", "resolved", "scaled", "secured", "streamlined", "tested", "trained", "wrote",
    "coordinated", "presented", "mentored", "researched", "published", "won", "secured",
}

WEAK_PHRASES = [
    "responsible for", "worked on", "helped with", "duties included", "hard working",
    "hardworking", "team player", "good communication skills", "fast learner",
]

# Friendly, honest next steps per skill category.
LEARNING_HINTS = {
    "Programming languages": "Complete a structured course, then build and publish one small project in it.",
    "Web development": "Build a small app with it, deploy it, and link the GitHub repository on your resume.",
    "Data and AI": "Work through a public dataset end-to-end (clean, analyse, visualise) and document it in a notebook.",
    "Databases": "Design a schema for one of your projects and practise joins, indexes and aggregations.",
    "Tools and cloud": "Follow the official getting-started guide and use it in an existing project (for example containerise it or add CI).",
    "CS fundamentals": "Revise the core topics and practise 2-3 problems a week on a coding platform.",
    "Testing": "Add automated tests to one of your existing projects and mention the coverage.",
    "Professional skills": "Show it through a concrete example (team size, your role, result) instead of listing it.",
}

STOPWORDS = set("""
a about above after again all also am an and any are as at be because been before being below between both but by
can could did do does doing down during each few for from further had has have having he her here hers him his how
i if in into is it its just me more most my no nor not now of off on once only or other our out over own same she
should so some such than that the their theirs them then there these they this those through to too under until up
very was we were what when where which while who whom why will with would you your yours
experience work working role job responsibilities responsibility required requirements preferred ability strong
excellent good knowledge skills skill team years year plus including include etc must looking candidate company
position opportunity join using use used within across well new need needs build building services service
developer engineer software solutions develop developing seeking hiring ability scalable high quality able make
based related relevant understanding familiarity proficiency hands-on handson apply applying part day-to-day
""".split())
