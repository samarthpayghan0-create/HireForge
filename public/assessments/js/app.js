
// All HireForge members share one Django API root once merged:
//   /api/               -> Member 1 (register, login, profile, AI readiness)
//   /api/assessments/   -> Member 2 (this page)
//   /api/interviews/    -> Member 3 (mock interviews)
const API_ROOT = window.HIREFORGE_API_ROOT ||
    (location.port === "5500" || location.protocol === "file:" ? "http://127.0.0.1:8000/api" : "/api");
const API_BASE_URL = `${API_ROOT}/assessments`;
const TOKEN_KEY = "hireforgeMember2Token";
// Member 1's login page stores its DRF token under this key, so a student who
// has already logged in there is connected here automatically.
const SHARED_TOKEN_KEY = "hireforgeToken";

const elements = {
    authButton: document.getElementById("authButton"),
    authDialog: document.getElementById("authDialog"),
    authForm: document.getElementById("authForm"),
    closeAuthDialog: document.getElementById("closeAuthDialog"),
    apiToken: document.getElementById("apiToken"),
    loginEmail: document.getElementById("loginEmail"),
    loginPassword: document.getElementById("loginPassword"),
    authMessage: document.getElementById("authMessage"),
    assessmentForm: document.getElementById("assessmentForm"),
    assessmentType: document.getElementById("assessmentType"),
    difficulty: document.getElementById("difficulty"),
    questionCount: document.getElementById("questionCount"),
    assessmentMessage: document.getElementById("assessmentMessage"),
    quizSection: document.getElementById("quizSection"),
    quizTitle: document.getElementById("quizTitle"),
    questionProgress: document.getElementById("questionProgress"),
    questionContainer: document.getElementById("questionContainer"),
    previousQuestion: document.getElementById("previousQuestion"),
    nextQuestion: document.getElementById("nextQuestion"),
    submitAssessment: document.getElementById("submitAssessment"),
    quizMessage: document.getElementById("quizMessage"),
    results: document.getElementById("results"),
    resultSummary: document.getElementById("resultSummary"),
    answerReview: document.getElementById("answerReview"),
    refreshPerformance: document.getElementById("refreshPerformance"),
    performanceMessage: document.getElementById("performanceMessage"),
    performanceSummary: document.getElementById("performanceSummary"),
    categoryPerformance: document.getElementById("categoryPerformance"),
    difficultyPerformance: document.getElementById("difficultyPerformance"),
    assessmentHistory: document.getElementById("assessmentHistory")
};

let token =
    sessionStorage.getItem(TOKEN_KEY) ||
    localStorage.getItem(SHARED_TOKEN_KEY) ||
    "";
let currentAttempt = null;
let currentQuestions = [];
let currentQuestionIndex = 0;
let selectedAnswers = {};
let requestInProgress = false;

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[character]);
}

function setMessage(element, message, type = "") {
    if (!element) return;
    element.textContent = message;
    element.className = `status-message ${type}`.trim();
}

function setBusy(button, busy, busyText = "Please wait...") {
    if (!button) return;

    if (!button.dataset.originalText) {
        button.dataset.originalText = button.textContent.trim();
    }

    button.disabled = busy;
    button.textContent = busy ? busyText : button.dataset.originalText;
}

async function apiRequest(path, options = {}) {
    const headers = {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Token ${token}` } : {}),
        ...options.headers
    };

    let response;

    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            ...options,
            headers
        });
    } catch {
        throw new Error(
            "Cannot reach the backend. Make sure the HireForge backend is running."
        );
    }

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
        ? await response.json()
        : await response.text();

    if (!response.ok) {
        let message = typeof data === "string"
            ? data
            : data.error || data.detail || data.message;

        if (response.status === 401 || response.status === 403) {
            message = "Your session is invalid or expired. Please connect your account again.";
        }

        throw new Error(message || `Request failed (${response.status}).`);
    }

    return data;
}

function categoryLabel(type) {
    const labels = {
        aptitude: "Aptitude",
        dsa: "Data Structures & Algorithms",
        technical: "Technical"
    };

    return labels[type] || type || "Assessment";
}

function formatScore(value) {
    const score = Number(value);
    return Number.isFinite(score) ? `${score.toFixed(2)}%` : "—";
}

function formatDate(value) {
    if (!value) return "—";

    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function renderEmpty(message) {
    return `<div class="empty-state"><p>${escapeHTML(message)}</p></div>`;
}

function renderStat(label, value) {
    return `
        <article class="stat-card">
            <p class="stat-label">${escapeHTML(label)}</p>
            <div class="stat-value">${escapeHTML(value)}</div>
        </article>
    `;
}

function updateAuthButton() {
    if (!elements.authButton) return;

    elements.authButton.textContent = token ? "Connected" : "Connect Account";
    elements.authButton.classList.toggle("button-soft", Boolean(token));
    elements.authButton.setAttribute(
        "aria-label",
        token ? "Account connected. Click to manage connection." : "Connect your account"
    );
}

function showQuizSection() {
    elements.quizSection.hidden = false;
    elements.quizSection.removeAttribute("hidden");
    elements.quizSection.style.removeProperty("display");
    elements.quizSection.style.visibility = "visible";

    elements.results.hidden = true;
    elements.results.style.removeProperty("display");

    requestAnimationFrame(() => {
        elements.quizSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    });
}

function hideQuizSection() {
    elements.quizSection.hidden = true;
    elements.quizSection.style.display = "none";
}

function showResultsSection() {
    elements.results.hidden = false;
    elements.results.removeAttribute("hidden");
    elements.results.style.removeProperty("display");

    requestAnimationFrame(() => {
        elements.results.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    });
}

async function loginWithPassword(email, password) {
    let response;

    try {
        response = await fetch(`${API_ROOT}/login/`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Accept: "application/json" },
            body: JSON.stringify({ email, password })
        });
    } catch {
        throw new Error(
            "Cannot reach the backend. Make sure the HireForge backend is running."
        );
    }

    let data = {};

    try {
        data = await response.json();
    } catch {
        data = {};
    }

    if (!response.ok || !data.token) {
        throw new Error(
            data.detail ||
            "Login failed. Check your email and password, or paste a token instead."
        );
    }

    return data.token;
}

async function connectAccount(event) {
    event.preventDefault();

    const email = elements.loginEmail.value.trim();
    const password = elements.loginPassword.value;
    const pastedToken = elements.apiToken.value.trim();

    if (!pastedToken && !(email && password)) {
        setMessage(
            elements.authMessage,
            "Enter your email and password, or paste an authentication token.",
            "error"
        );
        return;
    }

    const submitButton = elements.authForm.querySelector('[type="submit"]');
    setBusy(submitButton, true, "Connecting...");

    const previousToken = token;

    try {
        token = pastedToken || await loginWithPassword(email, password);

        // Verify the token against this API before keeping it.
        await apiRequest("/history/");

        sessionStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(SHARED_TOKEN_KEY, token);
        elements.apiToken.value = "";
        elements.loginPassword.value = "";
        elements.authDialog.close();

        updateAuthButton();
        setMessage(
            elements.assessmentMessage,
            "Account connected. You can start an assessment.",
            "success"
        );

        await refreshPerformance();
    } catch (error) {
        token = previousToken;
        setMessage(elements.authMessage, error.message, "error");
    } finally {
        setBusy(submitButton, false);
    }
}

function disconnectAccount() {
    token = "";
    sessionStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(SHARED_TOKEN_KEY);

    currentAttempt = null;
    currentQuestions = [];
    currentQuestionIndex = 0;
    selectedAnswers = {};

    hideQuizSection();

    elements.results.hidden = true;
    elements.results.style.removeProperty("display");

    elements.performanceSummary.innerHTML = "";
    elements.categoryPerformance.innerHTML = "";
    elements.difficultyPerformance.innerHTML = "";
    elements.assessmentHistory.innerHTML = "";

    updateAuthButton();

    setMessage(elements.assessmentMessage, "Account disconnected. Connect again to continue.");
    setMessage(elements.performanceMessage, "Connect your account to load your performance.");
}

async function startAssessment(event) {
    event.preventDefault();

    if (!token) {
        elements.authDialog.showModal();
        setMessage(elements.authMessage, "Connect your account before starting.", "error");
        return;
    }

    if (requestInProgress) return;

    requestInProgress = true;

    const startButton = elements.assessmentForm.querySelector('[type="submit"]');
    setBusy(startButton, true, "Starting...");
    setMessage(elements.assessmentMessage, "Preparing your assessment...");

    try {
        const data = await apiRequest("/start/", {
            method: "POST",
            body: JSON.stringify({
                assessment_type: elements.assessmentType.value,
                difficulty: elements.difficulty.value,
                question_count: Number(elements.questionCount.value)
            })
        });

        if (
            !data.attempt_id ||
            !Array.isArray(data.questions) ||
            data.questions.length === 0
        ) {
            throw new Error("The backend returned no usable assessment questions.");
        }

        const validQuestions = data.questions.every(question =>
            question &&
            question.id !== undefined &&
            typeof question.question === "string" &&
            Array.isArray(question.options) &&
            question.options.length === 4
        );

        if (!validQuestions) {
            throw new Error("The backend returned questions in an unexpected format.");
        }

        currentAttempt = data;
        currentQuestions = data.questions;
        currentQuestionIndex = 0;
        selectedAnswers = {};

        elements.quizTitle.textContent =
            `${categoryLabel(data.assessment_type)} · ${data.difficulty}`;

        elements.questionContainer.innerHTML = "";
        setMessage(elements.quizMessage, "");

        renderQuestion();
        showQuizSection();

        setMessage(elements.assessmentMessage, "Assessment started.", "success");
    } catch (error) {
        setMessage(elements.assessmentMessage, error.message, "error");
    } finally {
        requestInProgress = false;
        setBusy(startButton, false);
    }
}

function renderQuestion() {
    const question = currentQuestions[currentQuestionIndex];

    if (!question) {
        setMessage(elements.quizMessage, "The current question could not be loaded.", "error");
        return;
    }

    const total = currentQuestions.length;
    const selected = selectedAnswers[question.id] || "";

    elements.questionProgress.textContent =
        `Question ${currentQuestionIndex + 1} of ${total}`;

    elements.questionContainer.innerHTML = `
        <article class="question-card">
            <p class="eyebrow">${escapeHTML(question.topic || "Assessment question")}</p>
            <h3>${escapeHTML(question.question)}</h3>
            <div class="option-list">
                ${question.options.map((option, index) => {
                    const letter = String.fromCharCode(65 + index);

                    return `
                        <label class="option-label">
                            <input
                                type="radio"
                                name="answer"
                                value="${letter}"
                                ${selected === letter ? "checked" : ""}
                            >
                            <span><strong>${letter}.</strong> ${escapeHTML(option)}</span>
                        </label>
                    `;
                }).join("")}
            </div>
        </article>
    `;

    elements.questionContainer.querySelectorAll('input[name="answer"]').forEach(input => {
        input.addEventListener("change", () => {
            selectedAnswers[question.id] = input.value;
            setMessage(elements.quizMessage, "");
        });
    });

    elements.previousQuestion.disabled = currentQuestionIndex === 0;
    elements.nextQuestion.hidden = currentQuestionIndex === total - 1;
    elements.submitAssessment.hidden = currentQuestionIndex !== total - 1;
}

function goToPreviousQuestion() {
    if (currentQuestionIndex > 0) {
        currentQuestionIndex -= 1;
        renderQuestion();
    }
}

function goToNextQuestion() {
    if (currentQuestionIndex < currentQuestions.length - 1) {
        currentQuestionIndex += 1;
        renderQuestion();
    }
}

async function submitAssessment() {
    if (!currentAttempt || requestInProgress) return;

    const unanswered = currentQuestions.filter(
        question => !selectedAnswers[question.id]
    ).length;

    if (unanswered > 0) {
        const confirmedUnanswered = window.confirm(
            `You have ${unanswered} unanswered question(s). Submit anyway? Unanswered questions will be scored as incorrect.`
        );

        if (!confirmedUnanswered) return;
    }

    const confirmed = window.confirm("Submit this assessment? You cannot submit it again.");

    if (!confirmed) return;

    requestInProgress = true;
    setBusy(elements.submitAssessment, true, "Submitting...");
    setMessage(elements.quizMessage, "Submitting your answers...");

    try {
        const data = await apiRequest(
            `/submit/${encodeURIComponent(currentAttempt.attempt_id)}/`,
            {
                method: "POST",
                body: JSON.stringify({ answers: selectedAnswers })
            }
        );

        renderResults(data);

        currentAttempt = null;
        hideQuizSection();
        showResultsSection();

        setMessage(
            elements.assessmentMessage,
            "Assessment submitted successfully.",
            "success"
        );

        await refreshPerformance();
    } catch (error) {
        setMessage(elements.quizMessage, error.message, "error");
    } finally {
        requestInProgress = false;
        setBusy(elements.submitAssessment, false);
    }
}

function renderResults(data) {
    elements.resultSummary.innerHTML = [
        renderStat("Score", formatScore(data.score_percentage)),
        renderStat("Correct answers", `${data.correct_answers} / ${data.total_questions}`),
        renderStat("Incorrect or unanswered", data.incorrect_or_unanswered),
        renderStat("Questions", data.total_questions)
    ].join("");

    const results = Array.isArray(data.results) ? data.results : [];

    if (!results.length) {
        elements.answerReview.innerHTML = renderEmpty("No answer review was returned.");
        return;
    }

    elements.answerReview.innerHTML = results.map((result, index) => {
        const question = result.question || "Question text unavailable";
        const options = Array.isArray(result.options) ? result.options : [];
        const submitted = result.submitted_answer || "";
        const correct = result.correct_answer || "";

        const selectedOption = /^[A-D]$/.test(submitted)
            ? options[submitted.charCodeAt(0) - 65]
            : null;

        const correctOption = /^[A-D]$/.test(correct)
            ? options[correct.charCodeAt(0) - 65]
            : null;

        return `
            <article class="review-card">
                <h4>${index + 1}. ${escapeHTML(question)}</h4>
                <p class="${result.is_correct ? "review-correct" : "review-incorrect"}">
                    ${result.is_correct ? "Correct" : "Incorrect"}
                </p>
                <p><strong>Your answer:</strong> ${
                    submitted
                        ? `${escapeHTML(submitted)}. ${escapeHTML(selectedOption ?? "")}`
                        : "Not answered"
                }</p>
                <p><strong>Correct answer:</strong> ${escapeHTML(correct || "Unavailable")}${
                    correctOption !== null && correctOption !== undefined
                        ? `. ${escapeHTML(correctOption)}`
                        : ""
                }</p>
                <p><strong>Explanation:</strong> ${escapeHTML(
                    result.explanation || "No explanation provided."
                )}</p>
            </article>
        `;
    }).join("");
}

async function refreshPerformance() {
    if (!token) {
        setMessage(elements.performanceMessage, "Connect your account to load your performance.");
        elements.performanceSummary.innerHTML = "";
        elements.categoryPerformance.innerHTML = "";
        elements.difficultyPerformance.innerHTML = "";
        elements.assessmentHistory.innerHTML = "";
        return;
    }

    setMessage(elements.performanceMessage, "Loading your performance...");

    try {
        const [performance, history] = await Promise.all([
            apiRequest("/performance/"),
            apiRequest("/history/")
        ]);

        renderPerformance(performance);
        renderHistory(history);

        const total = performance.summary?.total_assessments || 0;

        setMessage(
            elements.performanceMessage,
            total
                ? "Your performance is up to date."
                : "No completed assessments yet. Complete your first assessment to see your results.",
            total ? "success" : ""
        );
    } catch (error) {
        setMessage(elements.performanceMessage, error.message, "error");
    }
}

function renderPerformance(data) {
    const summary = data.summary || {};

    elements.performanceSummary.innerHTML = [
        renderStat("Completed assessments", summary.total_assessments ?? 0),
        renderStat("Average score", formatScore(summary.average_score ?? 0)),
        renderStat("Highest score", formatScore(summary.highest_score ?? 0)),
        renderStat("Correct answers", summary.total_correct_answers ?? 0)
    ].join("");

    const categories = Array.isArray(data.category_performance)
        ? data.category_performance
        : [];

    elements.categoryPerformance.innerHTML = categories.length
        ? categories.map(item => `
            <div class="performance-row">
                <span>
                    ${escapeHTML(item.label || categoryLabel(item.assessment_type))}<br>
                    <small>${escapeHTML(item.attempts ?? 0)} completed</small>
                </span>
                <strong>${formatScore(item.average_score)}</strong>
            </div>
        `).join("")
        : renderEmpty("No category results available yet.");

    const difficulties = Array.isArray(data.difficulty_performance)
        ? data.difficulty_performance.filter(item => Number(item.attempts) > 0)
        : [];

    elements.difficultyPerformance.innerHTML = difficulties.length
        ? difficulties.map(item => `
            <div class="performance-row">
                <span>
                    ${escapeHTML(item.category || categoryLabel(item.assessment_type))}
                    · ${escapeHTML(item.difficulty_label || item.difficulty)}
                    <br>
                    <small>${escapeHTML(item.attempts)} completed</small>
                </span>
                <strong>${formatScore(item.average_score)}</strong>
            </div>
        `).join("")
        : renderEmpty("Complete an assessment to see difficulty performance.");
}

function renderHistory(history) {
    if (!Array.isArray(history) || !history.length) {
        elements.assessmentHistory.innerHTML = renderEmpty("No assessments found for this account.");
        return;
    }

    const completed = history.filter(item =>
        String(item.status || "").toLowerCase() === "completed"
    );

    if (!completed.length) {
        elements.assessmentHistory.innerHTML = renderEmpty("No completed assessments yet.");
        return;
    }

    elements.assessmentHistory.innerHTML = `
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Difficulty</th>
                        <th>Questions</th>
                        <th>Correct</th>
                        <th>Score</th>
                        <th>Completed</th>
                    </tr>
                </thead>
                <tbody>
                    ${completed.map(item => `
                        <tr>
                            <td>${escapeHTML(categoryLabel(item.assessment_type))}</td>
                            <td><span class="badge">${escapeHTML(item.difficulty)}</span></td>
                            <td>${escapeHTML(item.question_count)}</td>
                            <td>${escapeHTML(item.correct_answers)} / ${escapeHTML(item.question_count)}</td>
                            <td><strong>${formatScore(item.score_percentage)}</strong></td>
                            <td>${escapeHTML(formatDate(item.completed_at))}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

elements.authButton.addEventListener("click", () => {
    if (token) {
        const disconnect = window.confirm("Disconnect the current account?");
        if (disconnect) disconnectAccount();
        return;
    }

    elements.authDialog.showModal();
});

elements.closeAuthDialog.addEventListener("click", () => {
    elements.authDialog.close();
});

elements.authForm.addEventListener("submit", connectAccount);
elements.assessmentForm.addEventListener("submit", startAssessment);
elements.previousQuestion.addEventListener("click", goToPreviousQuestion);
elements.nextQuestion.addEventListener("click", goToNextQuestion);
elements.submitAssessment.addEventListener("click", submitAssessment);
elements.refreshPerformance.addEventListener("click", refreshPerformance);

hideQuizSection();
elements.results.hidden = true;
elements.results.style.removeProperty("display");

updateAuthButton();

if (token) {
    setMessage(elements.assessmentMessage, "Account connected. You can start an assessment.");
    refreshPerformance();
}
