document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-current-year], .current-year").forEach((element) => {
    element.textContent = new Date().getFullYear();
  });

  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const id = link.getAttribute("href");
      if (!id || id === "#") return;

      const target = document.querySelector(id);
      if (!target) return;

      event.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      history.replaceState(null, "", id);
    });
  });

  const header = document.querySelector(".site-header");

  if (header) {
    const updateHeader = () => {
      header.classList.toggle("scrolled", window.scrollY > 10);
    };

    updateHeader();
    window.addEventListener("scroll", updateHeader, { passive: true });
  }

  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.togglePassword);
      if (!input) return;

      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.textContent = show ? "Hide" : "Show";
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  // Same origin when deployed (Vercel) or served by Django; absolute only for Live Server (:5500).
  const API_BASE = window.HIREFORGE_API_ROOT ||
    (location.port === "5500" || location.protocol === "file:" ? "http://127.0.0.1:8000/api" : "/api");


  const getToken = () => localStorage.getItem("hireforgeToken");

  const showMessage = (element, message) => {
    if (!element) return;

    element.textContent = message;
    element.classList.add("visible", "is-visible", "is-info");
  };


  // Store drafts separately for each logged-in account.
  const getDraftKey = () => {
    const token = getToken();
    return token ? `hireforgeProfileDraft:${token}` : null;
  };

  const readDraft = () => {
    try {
      const key = getDraftKey();
      if (!key) return {};

      return JSON.parse(sessionStorage.getItem(key) || "{}");
    } catch {
      return {};
    }
  };

  const saveDraft = (data) => {
    try {
      const key = getDraftKey();
      if (!key) return false;

      sessionStorage.setItem(
        key,
        JSON.stringify({ ...readDraft(), ...data })
      );

      return true;
    } catch {
      return false;
    }
  };

  // Remove the old shared draft.
  sessionStorage.removeItem("hireforgeProfileDraft");

  const apiRequest = async (path, options = {}) => {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };


    const token = getToken();

    const isPublicAuthRequest =
      path === "/login/" || path === "/register/";

    if (token && !isPublicAuthRequest && !headers.Authorization) {
      headers.Authorization = `Token ${token}`;
    }


    let response;

    try {
      response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers
      });
    } catch {
      throw new Error(
        "Cannot connect to Django. Start the backend and check your frontend server."
      );
    }

    const responseText = await response.text();
    let data = {};

    try {
      data = responseText ? JSON.parse(responseText) : {};
    } catch {
      data = { detail: responseText };
    }

    if (!response.ok) {
      const messages = [];

      const collectMessages = (value) => {
        if (Array.isArray(value)) {
          value.forEach(collectMessages);
        } else if (value && typeof value === "object") {
          Object.values(value).forEach(collectMessages);
        } else if (typeof value === "string") {
          messages.push(value);
        }
      };

      collectMessages(data);

      throw new Error(
        messages.join(" ") || `Request failed with status ${response.status}.`
      );
    }

    return data;
  };

  const setBusy = (form, busy) => {
    const submit = form.querySelector('[type="submit"]');
    if (!submit) return;

    if (busy) {
      if (!submit.disabled) {
        submit.dataset.originalText = submit.textContent;
      }

      submit.disabled = true;
      submit.textContent = "Please wait...";
    } else {
      submit.disabled = false;

      if (submit.dataset.originalText) {
        submit.textContent = submit.dataset.originalText;
      }
    }
  };

  const signupForm = document.getElementById("signupForm");
  const signupPassword = document.getElementById("password");
  const confirmPassword = document.getElementById("confirmPassword");

  if (signupForm && signupPassword && confirmPassword) {
    const validatePasswords = () => {
      confirmPassword.setCustomValidity(
        confirmPassword.value &&
          signupPassword.value !== confirmPassword.value
          ? "Passwords do not match."
          : ""
      );
    };

    signupPassword.addEventListener("input", validatePasswords);
    confirmPassword.addEventListener("input", validatePasswords);

    signupForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      validatePasswords();

      if (!signupForm.reportValidity()) return;

      const fullName = document.getElementById("fullName")?.value.trim();
      const email = document.getElementById("email")?.value.trim();
      const terms = document.getElementById("agreeTerms");

      if (!fullName || !email) {
        showMessage(
          document.getElementById("signupMessage"),
          "Enter your full name and email address."
        );
        return;
      }

      if (terms && !terms.checked) {
        showMessage(
          document.getElementById("signupMessage"),
          "Please accept the terms and conditions."
        );
        return;
      }

      setBusy(signupForm, true);

      const message = document.getElementById("signupMessage");

      try {
        const data = await apiRequest("/register/", {
          method: "POST",
          body: JSON.stringify({
            full_name: fullName,
            email,
            password: signupPassword.value
          })
        });

        if (!data.token) {
          throw new Error(
            "The server did not return an authentication token. Please log in."
          );
        }

        sessionStorage.removeItem("hireforgeProfileDraft");
        localStorage.setItem("hireforgeToken", data.token);

        if (data.email) {
          localStorage.setItem("hireforgeEmail", data.email);
        }

        if (data.username) {
          localStorage.setItem("hireforgeUsername", data.username);
        }

        saveDraft({ fullName });

        showMessage(
          message,
          "Account created successfully. Opening your student profile..."
        );

        window.setTimeout(() => {
          window.location.href = "profile.html";
        }, 700);
      } catch (error) {
        showMessage(
          message,
          error.message || "Signup failed. Please try again."
        );
      } finally {
        setBusy(signupForm, false);
      }
    });
  }

  const loginForm = document.getElementById("loginForm");

  if (loginForm) {
    loginForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      if (!loginForm.reportValidity()) return;

      const email = document.getElementById("email")?.value.trim();
      const password = document.getElementById("password")?.value;
      const message = document.getElementById("loginMessage");

      setBusy(loginForm, true);

      try {
        const data = await apiRequest("/login/", {
          method: "POST",
          body: JSON.stringify({ email, password })
        });

        if (!data.token) {
          throw new Error("The server did not return an authentication token.");
        }

        sessionStorage.removeItem("hireforgeProfileDraft");
        localStorage.setItem("hireforgeToken", data.token);

        if (data.email) {
          localStorage.setItem("hireforgeEmail", data.email);
        }

        if (data.username) {
          localStorage.setItem("hireforgeUsername", data.username);
        }

        showMessage(message, "Login successful. Opening your dashboard...");

        window.setTimeout(() => {
          window.location.href = "dashboard.html";
        }, 500);
      } catch (error) {
        showMessage(
          message,
          error.message || "Login failed. Check your email and password."
        );
      } finally {
        setBusy(loginForm, false);
      }
    });
  }

  const forgotForm = document.getElementById("forgotPasswordForm");

  if (forgotForm) {
    forgotForm.addEventListener("submit", (event) => {
      event.preventDefault();

      if (!forgotForm.reportValidity()) return;

      showMessage(
        document.getElementById("forgotPasswordMessage"),
        "Password recovery is not connected yet. The Django email and password-reset service must be configured."
      );
    });
  }

  const ratingPairs = [
    ["dsaLevel", "dsaValue"],
    ["aptitudeLevel", "aptitudeValue"],
    ["communicationLevel", "communicationValue"]
  ];

  ratingPairs.forEach(([inputId, outputId]) => {
    const slider = document.getElementById(inputId);
    const output = document.getElementById(outputId);

    if (!slider || !output) return;

    const update = () => {
      output.textContent = `${slider.value}/10`;
    };

    slider.addEventListener("input", update);
    update();
  });

  const skillList = document.getElementById("technicalSkillList");
  const addSkillButton = document.getElementById("addTechnicalSkill");
  const profileForm = document.getElementById("profileForm");

  const addSkillRow = (skillName = "", skillRating = 5) => {
    if (!skillList) return;

    const row = document.createElement("div");
    row.className = "skill-row";

    const input = document.createElement("input");
    input.type = "text";
    input.name = "technicalSkillName";
    input.placeholder = "e.g. Python";
    input.setAttribute("list", "technicalSkillSuggestions");
    input.maxLength = 80;
    input.required = true;
    input.value = skillName;
    input.setAttribute("aria-label", "Technical skill name");

    const slider = document.createElement("input");
    slider.type = "range";
    slider.name = "technicalSkillRating";
    slider.min = "1";
    slider.max = "10";
    slider.value = String(
      Math.min(10, Math.max(1, Number(skillRating) || 5))
    );
    slider.setAttribute("aria-label", "Technical skill rating");

    const rating = document.createElement("output");
    rating.className = "skill-rating";
    rating.textContent = `${slider.value}/10`;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-skill";
    remove.textContent = "×";
    remove.setAttribute("aria-label", "Remove technical skill");

    slider.addEventListener("input", () => {
      rating.textContent = `${slider.value}/10`;
    });

    remove.addEventListener("click", () => row.remove());

    row.append(input, slider, rating, remove);
    skillList.appendChild(row);
  };

  const collectSkills = () => {
    if (!skillList) return [];

    return [...skillList.querySelectorAll(".skill-row")].map((row) => ({
      name: row.querySelector('[name="technicalSkillName"]').value.trim(),
      rating: Number(
        row.querySelector('[name="technicalSkillRating"]').value
      )
    }));
  };

  const restoreProfile = () => {
    if (!profileForm || !skillList) return;

    const saved = readDraft();

    ["degree", "college", "cgpa", "graduationYear"].forEach((id) => {
      const input = document.getElementById(id);

      if (input && saved[id] !== undefined && saved[id] !== null) {
        input.value = String(saved[id]);
      }
    });

    [
      ["dsaLevel", "dsaLevel"],
      ["aptitudeLevel", "aptitudeLevel"],
      ["communicationLevel", "communicationLevel"]
    ].forEach(([inputId, dataKey]) => {
      const input = document.getElementById(inputId);

      if (input && saved[dataKey] !== undefined) {
        input.value = String(saved[dataKey]);
      }
    });

    skillList.replaceChildren();

    if (Array.isArray(saved.technicalSkills) && saved.technicalSkills.length) {
      saved.technicalSkills.forEach((skill) => {
        addSkillRow(skill.name || "", skill.rating || 5);
      });
    } else {
      addSkillRow("Python", 5);
    }

    ratingPairs.forEach(([inputId, outputId]) => {
      const input = document.getElementById(inputId);
      const output = document.getElementById(outputId);

      if (input && output) {
        output.textContent = `${input.value}/10`;
      }
    });
  };

  if (skillList && addSkillButton) {
    restoreProfile();

    addSkillButton.addEventListener("click", () => {
      addSkillRow();

      const rows = skillList.querySelectorAll(".skill-row");
      rows[rows.length - 1]
        .querySelector('[name="technicalSkillName"]')
        .focus();
    });
  }

  if (profileForm && skillList) {
    profileForm.addEventListener("submit", (event) => {
      event.preventDefault();

      if (!profileForm.reportValidity()) return;

      const cgpaInput = document.getElementById("cgpa");
      const cgpa = Number(cgpaInput.value);

      if (!Number.isFinite(cgpa) || cgpa < 0 || cgpa > 10) {
        cgpaInput.setCustomValidity("Enter a CGPA between 0 and 10.");
        profileForm.reportValidity();
        cgpaInput.setCustomValidity("");
        return;
      }

      const skills = collectSkills();

      if (!skills.length) {
        showMessage(
          document.getElementById("profileMessage"),
          "Add at least one technical skill before continuing."
        );
        return;
      }

      if (skills.some((skill) => !skill.name)) {
        showMessage(
          document.getElementById("profileMessage"),
          "Enter a name for every technical skill or remove empty rows."
        );
        return;
      }

      const normalizedNames = skills.map((skill) => skill.name.toLowerCase());

      if (new Set(normalizedNames).size !== normalizedNames.length) {
        showMessage(
          document.getElementById("profileMessage"),
          "Remove duplicate technical skills before continuing."
        );
        return;
      }

      const profileData = {
        degree: document.getElementById("degree").value,
        college: document.getElementById("college").value.trim(),
        cgpa,
        graduationYear: Number(
          document.getElementById("graduationYear").value
        ),
        dsaLevel: Number(document.getElementById("dsaLevel").value),
        aptitudeLevel: Number(
          document.getElementById("aptitudeLevel").value
        ),
        communicationLevel: Number(
          document.getElementById("communicationLevel").value
        ),
        technicalSkills: skills
      };

      if (!saveDraft(profileData)) {
        showMessage(
          document.getElementById("profileMessage"),
          "Unable to save your temporary profile draft in this browser session."
        );
        return;
      }

      window.location.href = "profile-details.html";
    });
  }

  const detailsForm = document.getElementById("detailsForm");

  if (detailsForm) {
    const definitions = {
      projects: {
        countId: "projectCount",
        listId: "projectEntries",
        max: 20,
        title: "Project",
        fields: [
          {
            name: "title",
            label: "Project title",
            placeholder: "Project name",
            required: true
          },
          {
            name: "technologies",
            label: "Technologies used",
            placeholder: "Python, Django, MySQL",
            required: true
          },
          {
            name: "description",
            label: "Description",
            placeholder: "What did you build and what was your contribution?",
            type: "textarea",
            required: true
          },
          {
            name: "link",
            label: "Project link (optional)",
            placeholder: "https://...",
            type: "url",
            required: false
          }
        ]
      },
      internships: {
        countId: "internshipCount",
        listId: "internshipEntries",
        max: 20,
        title: "Internship / Experience",
        fields: [
          {
            name: "organization",
            label: "Company / organization",
            placeholder: "Organization name",
            required: true
          },
          {
            name: "role",
            label: "Role",
            placeholder: "Intern / Developer",
            required: true
          },
          {
            name: "duration",
            label: "Duration",
            placeholder: "e.g. 2 months",
            required: true
          },
          {
            name: "description",
            label: "Responsibilities and achievements",
            placeholder: "Describe your work",
            type: "textarea",
            required: true
          }
        ]
      },
      certifications: {
        countId: "certificationCount",
        listId: "certificationEntries",
        max: 30,
        title: "Certification",
        fields: [
          {
            name: "name",
            label: "Certification name",
            placeholder: "Certification title",
            required: true
          },
          {
            name: "issuer",
            label: "Issuing organization",
            placeholder: "Organization name",
            required: true
          },
          {
            name: "date",
            label: "Completion date (optional)",
            placeholder: "",
            type: "month",
            required: false
          },
          {
            name: "credential",
            label: "Credential link (optional)",
            placeholder: "https://...",
            type: "url",
            required: false
          }
        ]
      }
    };

    const createField = (field, category, index) => {
      const wrapper = document.createElement("div");
      wrapper.className = "details-field";

      if (field.type === "textarea") {
        wrapper.classList.add("full");
      }

      const id = `${category}-${index}-${field.name}`;
      const label = document.createElement("label");
      label.htmlFor = id;
      label.textContent = field.label;

      let input;

      if (field.type === "textarea") {
        input = document.createElement("textarea");
        input.maxLength = 2000;
      } else {
        input = document.createElement("input");
        input.type = field.type || "text";
        input.maxLength = field.type === "url" ? 500 : 200;
      }

      input.id = id;
      input.name = field.name;
      input.placeholder = field.placeholder;
      input.required = field.required;

      wrapper.append(label, input);
      return wrapper;
    };

    const updateEntries = (category) => {
      const definition = definitions[category];
      const list = document.getElementById(definition.listId);

      [...list.children].forEach((card, index) => {
        card.querySelector("h3").textContent =
          `${definition.title} ${index + 1}`;
      });

      document.getElementById(definition.countId).value = list.children.length;
    };

    const addEntry = (category, values = {}) => {
      const definition = definitions[category];
      const list = document.getElementById(definition.listId);
      const index = list.children.length;

      if (index >= definition.max) {
        showMessage(
          document.getElementById("detailsMessage"),
          `You can add up to ${definition.max} ${category} entries.`
        );
        return;
      }

      const card = document.createElement("article");
      card.className = "entry-card";

      const heading = document.createElement("div");
      heading.className = "entry-heading";

      const title = document.createElement("h3");
      title.textContent = `${definition.title} ${index + 1}`;

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-entry";
      remove.textContent = "Remove";

      remove.addEventListener("click", () => {
        card.remove();
        updateEntries(category);
      });

      heading.append(title, remove);

      const grid = document.createElement("div");
      grid.className = "details-grid";

      definition.fields.forEach((field) => {
        const wrapper = createField(field, category, index);
        const input = wrapper.querySelector("input, textarea");

        if (values[field.name] !== undefined) {
          input.value = values[field.name];
        }

        grid.appendChild(wrapper);
      });

      card.append(heading, grid);
      list.appendChild(card);
      updateEntries(category);
    };

    const restoreDetails = () => {
      const saved = readDraft();

      Object.entries(definitions).forEach(([category, definition]) => {
        const existingEntries = Array.isArray(saved[category])
          ? saved[category]
          : [];

        existingEntries.forEach((entry) => addEntry(category, entry));
        updateEntries(category);
      });

      const targetRole = document.getElementById("targetRole");

      if (targetRole && saved.targetRole) {
        targetRole.value = saved.targetRole;
      }
    };

    Object.entries(definitions).forEach(([category, definition]) => {
      const countInput = document.getElementById(definition.countId);
      const list = document.getElementById(definition.listId);
      const addButton = document.querySelector(
        `[data-add-entry="${category}"]`
      );

      if (!countInput || !list || !addButton) return;

      const syncCount = () => {
        const desired = Number(countInput.value);

        if (
          !Number.isInteger(desired) ||
          desired < 0 ||
          desired > definition.max
        ) {
          countInput.setCustomValidity(
            `Enter a number from 0 to ${definition.max}.`
          );
          return;
        }

        countInput.setCustomValidity("");

        while (list.children.length < desired) {
          addEntry(category);
        }

        while (list.children.length > desired) {
          list.lastElementChild.remove();
        }

        updateEntries(category);
      };

      countInput.addEventListener("change", syncCount);
      countInput.addEventListener("input", () => {
        countInput.setCustomValidity("");
      });

      addButton.addEventListener("click", () => {
        if (list.children.length >= definition.max) {
          showMessage(
            document.getElementById("detailsMessage"),
            `You can add up to ${definition.max} entries.`
          );
          return;
        }

        addEntry(category);
      });
    });

    restoreDetails();

    detailsForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      if (!detailsForm.reportValidity()) return;

      const pageOneData = readDraft();

      if (
        !pageOneData.degree ||
        !pageOneData.college ||
        !Number.isFinite(Number(pageOneData.cgpa)) ||
        !Number.isFinite(Number(pageOneData.graduationYear)) ||
        !Array.isArray(pageOneData.technicalSkills) ||
        pageOneData.technicalSkills.length === 0
      ) {
        showMessage(
          document.getElementById("detailsMessage"),
          "Complete Page 1 first. Return to Page 1 and submit your education and skills."
        );
        return;
      }

      const entries = (category) =>
        [
          ...document.getElementById(definitions[category].listId).children
        ].map((card) => {
          const entry = {};

          card.querySelectorAll("input, textarea").forEach((input) => {
            entry[input.name] = input.value.trim();
          });

          return entry;
        });

      const targetRole = document.getElementById("targetRole");

      if (!targetRole || !targetRole.value) {
        showMessage(
          document.getElementById("detailsMessage"),
          "Please select your target role."
        );
        return;
      }

      const finalData = {
        ...pageOneData,
        projects: entries("projects"),
        internships: entries("internships"),
        certifications: entries("certifications"),
        targetRole: targetRole.value
      };

      if (!saveDraft(finalData)) {
        showMessage(
          document.getElementById("detailsMessage"),
          "Unable to save the temporary profile draft in this browser session."
        );
        return;
      }

      if (!getToken()) {
        showMessage(
          document.getElementById("detailsMessage"),
          "Your draft is saved temporarily. Please sign up or log in before saving it to your HireForge account."
        );
        return;
      }

      const message = document.getElementById("detailsMessage");
      const submitButton = detailsForm.querySelector('[type="submit"]');

      if (submitButton) {
        submitButton.dataset.originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = "Saving profile...";
      }

      try {
        const response = await apiRequest("/profile/", {
          method: "PATCH",
          body: JSON.stringify({
            full_name: readDraft().fullName || "",
            college_name: finalData.college,
            degree: finalData.degree,
            graduation_year: finalData.graduationYear,
            cgpa: finalData.cgpa,
            dsa_rating: finalData.dsaLevel,
            aptitude_rating: finalData.aptitudeLevel,
            communication_rating: finalData.communicationLevel,
            technical_skills: finalData.technicalSkills,
            projects: finalData.projects,
            internships: finalData.internships,
            certifications: finalData.certifications,
            target_role: finalData.targetRole
          })
        });

        saveDraft({
          backendProfileSaved: true,
          backendProfile: response
        });

        showMessage(
          message,
          "Your student profile has been saved to your HireForge account successfully."
        );
      } catch (error) {
        showMessage(
          message,
          `${error.message || "Could not save profile to the server."} Your draft remains saved in this browser session.`
        );
      } finally {
        if (submitButton) {
          submitButton.disabled = false;

          if (submitButton.dataset.originalText) {
            submitButton.textContent = submitButton.dataset.originalText;
          }
        }
      }
    });
  }
});