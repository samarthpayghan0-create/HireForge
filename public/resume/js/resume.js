"use strict";

// API root: same origin when served by Django, absolute when opened from Live Server (:5500).
const API_ROOT = window.HIREFORGE_API_ROOT ||
    (location.port === "5500" || location.protocol === "file:" ? "http://127.0.0.1:8000/api" : "/api");
const API = `${API_ROOT}/resume`;
const TOKEN_KEY = "hireforgeMember4Token";
// Member 1's login page stores its DRF token under this key.
const SHARED_TOKEN_KEY = "hireforgeToken";

let token = sessionStorage.getItem(TOKEN_KEY) || localStorage.getItem(SHARED_TOKEN_KEY) || "";
let resumes = [];

const $ = id => document.getElementById(id);

/* ---------- safe DOM helper: never uses innerHTML with server data ---------- */
function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
        if (value === null || value === undefined || value === false) continue;
        if (key === "class") node.className = value;
        else if (key === "text") node.textContent = value;
        else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
        else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat(Infinity)) {
        if (child === null || child === undefined || child === false) continue;
        node.append(child.nodeType ? child : document.createTextNode(String(child)));
    }
    return node;
}

function notify(message, type = "info") {
    const box = $("notice");
    box.textContent = message;
    box.className = `notice ${type}`;
    box.hidden = !message;
}

function setBusy(button, busy, label) {
    if (!button) return;
    if (busy) { button.dataset.label = button.textContent; button.textContent = label; }
    else if (button.dataset.label) button.textContent = button.dataset.label;
    button.disabled = busy;
}

/* ---------- API ---------- */
async function api(path, options = {}) {
    if (!token) throw new Error("Please connect your account first.");
    const headers = { Accept: "application/json", Authorization: `Token ${token}` };
    if (options.json) headers["Content-Type"] = "application/json";

    let response;
    try {
        response = await fetch(`${API}${path}`, {
            method: options.method || "GET",
            headers,
            body: options.json ? JSON.stringify(options.json) : options.body,
        });
    } catch {
        throw new Error("Cannot reach the server. Make sure the Django backend is running.");
    }

    if (response.status === 204) return null;
    let data = {};
    try { data = await response.json(); } catch { data = {}; }

    if (response.status === 401) {
        throw new Error("Your session is invalid or expired. Please connect your account again.");
    }
    if (!response.ok) {
        const fieldErrors = data.errors ? Object.values(data.errors).flat().join(" ") : "";
        throw new Error(fieldErrors || data.detail || `Request failed (${response.status}).`);
    }
    return data;
}

/* ---------- authentication ---------- */
function updateAuthButton() { $("authButton").textContent = token ? "Disconnect" : "Connect account"; }

async function loginWithPassword(email, password) {
    let response;
    try {
        response = await fetch(`${API_ROOT}/login/`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ email, password }),
        });
    } catch {
        throw new Error("Cannot reach the backend. Make sure Django is running.");
    }
    let data = {};
    try { data = await response.json(); } catch { data = {}; }
    if (!response.ok || !data.token) {
        throw new Error(data.detail || "Login failed. Check your email and password, or paste a token instead.");
    }
    return data.token;
}

async function connect(event) {
    event.preventDefault();
    const email = $("loginEmail").value.trim();
    const password = $("loginPassword").value;
    const pasted = $("apiToken").value.trim();
    const message = $("authMessage");

    if (!pasted && !(email && password)) {
        message.textContent = "Enter your email and password, or paste an authentication token.";
        message.hidden = false;
        return;
    }
    const previous = token;
    const submit = $("authForm").querySelector('[type="submit"]');
    setBusy(submit, true, "Connecting...");
    try {
        token = pasted || await loginWithPassword(email, password);
        await api("/resumes/"); // verify the token before keeping it
        sessionStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(SHARED_TOKEN_KEY, token);
        $("apiToken").value = ""; $("loginPassword").value = "";
        message.hidden = true;
        $("authDialog").close();
        updateAuthButton();
        notify("Account connected.", "success");
        await refreshAll();
    } catch (error) {
        token = previous;
        message.textContent = error.message;
        message.hidden = false;
    } finally {
        setBusy(submit, false);
    }
}

function disconnect() {
    token = "";
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(SHARED_TOKEN_KEY);
    resumes = [];
    renderResumes();
    $("historyBody").replaceChildren(h("tr", {}, h("td", { colspan: 6, class: "muted", text: "Connect your account to see history." })));
    $("results").hidden = true;
    updateAuthButton();
    notify("Disconnected.", "info");
}

/* ---------- resumes ---------- */
function renderResumes() {
    const list = $("resumeList");
    const select = $("resumeSelect");
    list.replaceChildren();
    select.replaceChildren();

    if (!resumes.length) {
        list.append(h("li", { class: "muted", text: token ? "No resumes yet. Upload one above." : "Connect your account to see resumes." }));
        select.append(h("option", { value: "", text: "No resumes uploaded" }));
        return;
    }
    for (const resume of resumes) {
        const date = new Date(resume.created_at).toLocaleDateString();
        list.append(h("li", {},
            h("span", {}, `${resume.original_filename} · ${resume.word_count} words · ${date}`),
            h("button", { class: "btn btn-small btn-danger", type: "button", "aria-label": `Delete ${resume.original_filename}`,
                onclick: () => deleteResume(resume) }, "Delete")));
        select.append(h("option", { value: resume.id, text: resume.original_filename }));
    }
}

async function loadResumes() {
    resumes = await api("/resumes/");
    renderResumes();
}

async function uploadResume(event) {
    event.preventDefault();
    const file = $("resumeFile").files[0];
    if (!file) return notify("Choose a PDF or DOCX file.", "error");
    if (file.size > 4 * 1024 * 1024) return notify("The file is too large. The maximum size is 4 MB.", "error");

    const button = event.target.querySelector("button");
    setBusy(button, true, "Uploading...");
    try {
        const body = new FormData();
        body.append("file", file);
        const data = await api("/upload/", { method: "POST", body });
        $("resumeFile").value = "";
        notify(`Uploaded ${data.resume.original_filename}.`, "success");
        await loadResumes();
        $("resumeSelect").value = data.resume.id;
    } catch (error) {
        notify(error.message, "error");
    } finally {
        setBusy(button, false);
    }
}

async function deleteResume(resume) {
    if (!confirm(`Delete ${resume.original_filename} and all its analyses?`)) return;
    try {
        await api(`/resumes/${resume.id}/`, { method: "DELETE" });
        notify("Resume deleted.", "success");
        await refreshAll();
    } catch (error) { notify(error.message, "error"); }
}

/* ---------- results rendering ---------- */
function scoreClass(value) { return value >= 70 ? "good" : value >= 45 ? "ok" : "low"; }

function scoreBox(label, value) {
    return h("div", { class: `score ${scoreClass(value)}` }, h("strong", {}, `${Math.round(value)}`), h("span", { class: "muted" }, label));
}

function chips(items, kind) {
    if (!items || !items.length) return h("p", { class: "muted" }, "None");
    return h("ul", { class: "chips" }, items.map(item => h("li", { class: `chip ${kind}` }, item)));
}

function textList(items) { return h("ul", { class: "suggestions" }, (items || []).map(t => h("li", {}, t))); }

function learningPlan(plan) {
    if (!plan || !plan.length) return null;
    return h("div", {}, h("h3", {}, "Learning plan"),
        h("ul", { class: "suggestions" }, plan.map(p => h("li", {}, h("strong", {}, p.skill), `: ${p.suggestion}`))));
}

function aiBox(ai) {
    if (!ai) return null;
    return h("div", { class: "ai-box" }, h("h3", {}, "AI review (Gemini)"), h("p", {}, ai.summary),
        ai.strengths && ai.strengths.length ? [h("strong", {}, "Strengths"), textList(ai.strengths)] : null,
        ai.improvements && ai.improvements.length ? [h("strong", {}, "Improvements"), textList(ai.improvements)] : null,
        ai.rewritten_bullets && ai.rewritten_bullets.length ? [h("strong", {}, "Suggested rewrites"),
            h("ul", { class: "suggestions" }, ai.rewritten_bullets.map(b =>
                h("li", {}, h("span", { class: "muted" }, "Before: "), b.original, h("br"), h("span", { class: "muted" }, "After: "), b.improved)))] : null);
}

function renderGeneral(analysis) {
    const r = analysis.result;
    const contactLabels = { email: "Email", phone: "Phone", linkedin: "LinkedIn", github: "GitHub" };
    return [
        h("h2", {}, `Resume analysis${r.target_role ? " · " + r.target_role : ""}`),
        h("div", { class: "scores" }, scoreBox("Overall quality", r.scores.overall), scoreBox("ATS readiness", r.scores.ats),
            h("div", { class: "score" }, h("strong", {}, r.stats.word_count), h("span", { class: "muted" }, "words"))),
        h("div", { class: "two-col" },
            h("div", {}, h("h3", {}, "Strengths"), r.strengths.length ? textList(r.strengths) : h("p", { class: "muted" }, "No standout strengths detected yet."),
                h("h3", {}, "Contact & links"),
                h("ul", { class: "chips" }, Object.entries(contactLabels).map(([k, label]) =>
                    h("li", { class: `chip ${r.contact[k] ? "have" : "miss"}` }, `${r.contact[k] ? "✓" : "✗"} ${label}`))),
                h("h3", {}, "Sections"),
                h("ul", { class: "chips" }, [...r.sections_found.map(s => h("li", { class: "chip have" }, `✓ ${s}`)),
                    ...r.sections_missing.map(s => h("li", { class: "chip miss" }, `✗ ${s}`))])),
            h("div", {}, h("h3", {}, "Improvements"),
                h("ul", { class: "suggestions" }, r.improvements.map(i => h("li", {}, h("span", { class: `tag ${i.priority}` }, i.priority), i.text))))),
        h("h3", {}, "Skills detected"),
        Object.keys(r.skills_by_category).length
            ? Object.entries(r.skills_by_category).map(([cat, skills]) => h("div", {}, h("strong", {}, cat), chips(skills, "have")))
            : h("p", { class: "muted" }, "No recognised skills found. Add a Skills section."),
        r.role_gap ? h("div", {}, h("h3", {}, `Skill gap for ${r.role_gap.role}`),
            h("strong", {}, "Missing core skills"), chips(r.role_gap.missing_core_skills, "miss"),
            h("strong", {}, "Nice to have"), chips(r.role_gap.missing_nice_skills, "miss"), learningPlan(r.role_gap.learning_plan)) : null,
        h("h3", {}, "Career recommendations"),
        h("div", { class: "two-col" }, (r.career_recommendations || []).map(c =>
            h("div", { class: "score", style: "text-align:left" },
                h("strong", { style: "font-size:1.1rem" }, c.role),
                h("div", { class: "bar", role: "img", "aria-label": `${c.fit_percent}% fit` }, h("span", { style: `width:${c.fit_percent}%` })),
                h("p", { class: "muted" }, `${c.fit_percent}% skill fit`),
                c.missing_core_skills.length ? [h("span", {}, "Next to learn:"), chips(c.missing_core_skills, "miss")] : h("p", {}, "You cover all core skills."),
                c.next_steps.length ? textList(c.next_steps.map(s => `${s.skill}: ${s.suggestion}`)) : null))),
        aiBox(r.ai_feedback),
    ];
}

function renderMatch(analysis) {
    const r = analysis.result;
    return [
        h("h2", {}, `Job match${r.job_title ? " · " + r.job_title : ""}`),
        h("div", { class: "scores" }, scoreBox("Match score", r.match_score),
            r.skill_match_percent !== null ? scoreBox("Skill match", r.skill_match_percent) : null,
            scoreBox("Keyword overlap", r.keyword_overlap_percent)),
        h("div", { class: "two-col" },
            h("div", {}, h("h3", {}, "Matched skills"), chips(r.matched_skills, "have"),
                h("h3", {}, "Missing skills"), chips(r.missing_skills, "miss"),
                r.missing_keywords.length ? [h("h3", {}, "Keywords in the posting but not in your resume"), chips(r.missing_keywords, "miss")] : null),
            h("div", {}, h("h3", {}, "Suggestions"), textList(r.suggestions), learningPlan(r.learning_plan))),
        aiBox(r.ai_feedback),
    ];
}

function showAnalysis(analysis) {
    const box = $("results");
    box.replaceChildren(...[analysis.kind === "job_match" ? renderMatch(analysis) : renderGeneral(analysis)].flat(Infinity).filter(Boolean));
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------- actions ---------- */
async function runAnalyze(event) {
    event.preventDefault();
    const resumeId = Number($("resumeSelect").value);
    if (!resumeId) return notify("Upload and select a resume first.", "error");
    const button = event.target.querySelector("button");
    setBusy(button, true, "Analyzing...");
    try {
        const analysis = await api("/analyze/", { method: "POST", json: { resume_id: resumeId, target_role: $("targetRole").value.trim() } });
        notify("Analysis complete and saved to your history.", "success");
        showAnalysis(analysis);
        await loadHistory();
    } catch (error) { notify(error.message, "error"); }
    finally { setBusy(button, false); }
}

async function runMatch(event) {
    event.preventDefault();
    const resumeId = Number($("resumeSelect").value);
    if (!resumeId) return notify("Upload and select a resume first.", "error");
    const button = event.target.querySelector("button");
    setBusy(button, true, "Matching...");
    try {
        const analysis = await api("/job-match/", { method: "POST",
            json: { resume_id: resumeId, job_title: $("jobTitle").value.trim(), job_description: $("jobDescription").value.trim() } });
        notify("Job match complete and saved to your history.", "success");
        showAnalysis(analysis);
        await loadHistory();
    } catch (error) { notify(error.message, "error"); }
    finally { setBusy(button, false); }
}

/* ---------- history ---------- */
async function loadHistory() {
    const filter = $("historyFilter").value;
    const rows = await api(`/history/${filter ? `?kind=${encodeURIComponent(filter)}` : ""}`);
    const body = $("historyBody");
    body.replaceChildren();
    if (!rows.length) {
        body.append(h("tr", {}, h("td", { colspan: 6, class: "muted", text: "No analyses yet." })));
        return;
    }
    for (const row of rows) {
        body.append(h("tr", {},
            h("td", {}, new Date(row.created_at).toLocaleString()),
            h("td", {}, row.kind === "job_match" ? "Job match" : "Analysis"),
            h("td", {}, row.resume_filename),
            h("td", {}, row.target_role || "-"),
            h("td", {}, `${Math.round(Number(row.overall_score))}`),
            h("td", {},
                h("button", { class: "btn btn-small btn-secondary", type: "button", onclick: () => openHistory(row.id) }, "View"), " ",
                h("button", { class: "btn btn-small btn-danger", type: "button", "aria-label": "Delete analysis", onclick: () => deleteHistory(row.id) }, "Delete"))));
    }
}

async function openHistory(id) {
    try { showAnalysis(await api(`/history/${id}/`)); } catch (error) { notify(error.message, "error"); }
}

async function deleteHistory(id) {
    if (!confirm("Delete this analysis?")) return;
    try { await api(`/history/${id}/`, { method: "DELETE" }); await loadHistory(); }
    catch (error) { notify(error.message, "error"); }
}

async function refreshAll() {
    if (!token) return;
    try { await Promise.all([loadResumes(), loadHistory()]); }
    catch (error) { notify(error.message, "error"); }
}

/* ---------- init ---------- */
$("authButton").addEventListener("click", () => (token ? disconnect() : $("authDialog").showModal()));
$("authCancel").addEventListener("click", () => $("authDialog").close());
$("authForm").addEventListener("submit", connect);
$("uploadForm").addEventListener("submit", uploadResume);
$("analyzeForm").addEventListener("submit", runAnalyze);
$("matchForm").addEventListener("submit", runMatch);
$("historyFilter").addEventListener("change", () => loadHistory().catch(e => notify(e.message, "error")));

updateAuthButton();
renderResumes();
if (token) refreshAll();
