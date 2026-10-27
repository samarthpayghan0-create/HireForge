#!/usr/bin/env python3
"""End-to-end smoke test for a running HireForge deployment (standard library only).

    python scripts/smoke_test.py https://your-project.vercel.app

It creates ONE throw-away user (smoke+<random>@example.com), then exercises every
module with that single login token. Exit code 0 = everything required works.
AI features are reported as SKIP (not FAIL) when GEMINI_API_KEY is not configured.
"""

import io
import json
import sys
import urllib.error
import urllib.request
import uuid
import zipfile

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
results = []


def record(name, status, detail=""):
    results.append((name, status))
    print(f"  [{status:4}] {name}" + (f"  -> {detail}" if detail and status != "PASS" else ""))


def request(method, path, body=None, token=None, raw=None, content_type=None):
    headers = {"Accept": "application/json"}
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    if token:
        headers["Authorization"] = f"Token {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            payload = resp.read()
            code = resp.status
    except urllib.error.HTTPError as exc:
        payload, code = exc.read(), exc.code
    except Exception as exc:  # network / TLS / timeout
        return 0, {"detail": f"{type(exc).__name__}: {exc}"}, b""
    try:
        parsed = json.loads(payload) if payload else {}
    except ValueError:
        parsed = {}
    return code, parsed, payload


def check(name, cond, detail=""):
    record(name, "PASS" if cond else "FAIL", detail)
    return cond


def make_docx():
    text = ("Asha Rao\nasha.rao@example.com | +91 98765 43210 | github.com/asharao\n"
            "SUMMARY\nComputer science student.\nEDUCATION\nB.Tech Computer Science 2025\n"
            "SKILLS\nPython, Django, SQL, MySQL, Git, REST APIs, HTML, CSS, JavaScript\n"
            "PROJECTS\n- Built a task tracker with Django used by 200 students\n"
            "- Designed REST APIs and reduced response time by 30%\n")
    paragraphs = "".join(f"<w:p><w:r><w:t xml:space=\"preserve\">{l}</w:t></w:r></w:p>" for l in text.split("\n"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paragraphs}</w:body></w:document>')
    return buf.getvalue()


def multipart(filename, data):
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def main():
    print(f"HireForge smoke test against {BASE}\n")

    print("Infrastructure")
    code, body, _ = request("GET", "/api/health/")
    if not check("API health + database connection", code == 200 and body.get("database") == "ok", f"HTTP {code} {body}"):
        print("\nThe API/database is not reachable - fix this first (see DEPLOY.md > Troubleshooting).")
        return 1

    print("Pages")
    for path in ("/", "/login.html", "/signup.html", "/dashboard.html", "/assessments/", "/resume/", "/interview/", "/static/admin/css/base.css"):
        code, _, payload = request("GET", path)
        check(f"GET {path}", code == 200 and len(payload) > 200, f"HTTP {code}")

    print("Authentication (Member 1)")
    email = f"smoke+{uuid.uuid4().hex[:10]}@example.com"
    password = "Sm0ke!" + uuid.uuid4().hex[:10]
    code, body, _ = request("POST", "/api/register/", {"email": email, "password": password, "full_name": "Smoke Test"})
    check("register", code == 201 and body.get("token"), f"HTTP {code} {body}")
    code, body, _ = request("POST", "/api/login/", {"email": email, "password": password})
    token = body.get("token")
    if not check("login returns a token", code == 200 and token, f"HTTP {code} {body}"):
        return 1
    code, _, _ = request("GET", "/api/profile/")
    check("API rejects requests without a token", code == 401, f"HTTP {code}")
    code, body, _ = request("PATCH", "/api/profile/", {"target_role": "Python Developer", "technical_skills": ["Python", "Django"]}, token)
    check("save profile", code == 200 and body.get("target_role") == "Python Developer", f"HTTP {code} {body}")
    code, body, _ = request("POST", "/api/assessment/", token=token)
    if code == 200:
        record("AI readiness assessment (Gemini)", "PASS")
    elif code == 502:
        record("AI readiness assessment (Gemini)", "SKIP", "Gemini not configured/unavailable: " + str(body.get("detail", ""))[:80])
    else:
        record("AI readiness assessment (Gemini)", "FAIL", f"HTTP {code} {body}")

    print("Skill assessments (Member 2)")
    code, body, _ = request("POST", "/api/assessments/start/", {"assessment_type": "dsa", "difficulty": "medium", "question_count": 25}, token)
    ok = code == 201 and len(body.get("questions", [])) == 25 and "correct_answer" not in body["questions"][0]
    check("start assessment (25 questions, no answer keys)", ok, f"HTTP {code}")
    if ok:
        answers = {q["id"]: "A" for q in body["questions"]}
        code, res, _ = request("POST", f"/api/assessments/submit/{body['attempt_id']}/", {"answers": answers}, token)
        check("submit and score assessment", code == 200 and "score_percentage" in res, f"HTTP {code} {res}")
    code, res, _ = request("GET", "/api/assessments/performance/", token=token)
    check("performance summary", code == 200, f"HTTP {code}")

    print("Resume analysis (Member 4)")
    docx = make_docx()
    raw, ctype = multipart("smoke.docx", docx)
    code, up, _ = request("POST", "/api/resume/upload/", raw=raw, content_type=ctype, token=token)
    check("upload DOCX resume", code == 201, f"HTTP {code} {up}")
    if code == 201:
        rid = up["resume"]["id"]
        code, an, _ = request("POST", "/api/resume/analyze/", {"resume_id": rid, "use_ai": False}, token)
        check("analyze resume (uses target role from profile)", code == 201 and an.get("target_role") == "Python Developer", f"HTTP {code} {an}")
        jd = "Looking for a backend developer with Python, Django, Docker, AWS and PostgreSQL and REST API experience."
        code, jm, _ = request("POST", "/api/resume/job-match/", {"resume_id": rid, "job_description": jd, "use_ai": False}, token)
        check("job description match", code == 201 and "AWS" in jm.get("result", {}).get("missing_skills", []), f"HTTP {code} {jm}")
        code, hist, _ = request("GET", "/api/resume/history/", token=token)
        check("analysis history", code == 200 and len(hist) == 2, f"HTTP {code}")
        code, _, _ = request("DELETE", f"/api/resume/resumes/{rid}/", token=token)
        check("delete resume", code == 204, f"HTTP {code}")

    print("Mock interview (Member 3)")
    code, iv, _ = request("POST", "/api/interviews/sessions/", {"interview_type": "TECHNICAL", "difficulty": "EASY"}, token)
    ok = code == 201 and len(iv.get("session", {}).get("questions", [])) == 10
    check("create interview (10 questions, role from profile)", ok and iv["session"]["job_role"] == "Python Developer", f"HTTP {code} {str(iv)[:150]}")
    if ok:
        qid = iv["session"]["questions"][0]["id"]
        code, ans, _ = request("POST", f"/api/interviews/questions/{qid}/answer/", {"answer_text": "A list is mutable and a tuple is immutable."}, token)
        if code == 201:
            record("AI answer evaluation (Gemini)", "PASS")
        elif code == 503:
            record("AI answer evaluation (Gemini)", "SKIP", str(ans.get("detail", ""))[:80])
        else:
            record("AI answer evaluation (Gemini)", "FAIL", f"HTTP {code} {ans}")

    failed = [n for n, s in results if s == "FAIL"]
    passed = sum(1 for _, s in results if s == "PASS")
    skipped = sum(1 for _, s in results if s == "SKIP")
    print(f"\n{passed} passed, {skipped} skipped, {len(failed)} failed")
    if failed:
        print("FAILED:", "; ".join(failed))
    print(f"(Test user {email} was created; remove it in /admin/ if you like.)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
