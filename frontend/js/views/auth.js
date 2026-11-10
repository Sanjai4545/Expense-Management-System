import { el, toast } from "../ui.js";
import { request, ApiError } from "../api.js";
import { setToken, setUser } from "../state.js";

export async function renderAuth(container, params = {}, isSignup = false) {
  const flashMessage = sessionStorage.getItem("halfway.flash_message");
  if (flashMessage) {
    sessionStorage.removeItem("halfway.flash_message");
    toast(flashMessage, { type: "error" });
  }

  let showPassword = false;
  let isSubmitting = false;

  const nameInput = el("input", {
    type: "text",
    id: "auth-name",
    name: "name",
    className: "input",
    autocomplete: "name",
    required: true,
    placeholder: "e.g. Sanjai Kumar",
  });
  const nameError = el("div", { className: "input-error-msg", style: { display: "none" } });

  const emailInput = el("input", {
    type: "email",
    id: "auth-email",
    name: "email",
    className: "input",
    autocomplete: "email",
    required: true,
    placeholder: "name@example.com",
  });
  const emailError = el("div", { className: "input-error-msg", style: { display: "none" } });

  const passwordInput = el("input", {
    type: "password",
    id: "auth-password",
    name: "password",
    className: "input",
    autocomplete: isSignup ? "new-password" : "current-password",
    required: true,
    placeholder: "••••••••",
  });
  const passwordError = el("div", { className: "input-error-msg", style: { display: "none" } });

  const generalError = el("div", {
    className: "input-error-msg",
    style: { display: "none", marginBottom: "var(--s3)", textAlign: "center", justifyContent: "center" },
  });

  const togglePasswordBtn = el(
    "button",
    {
      type: "button",
      className: "password-toggle-btn",
      "aria-label": "Toggle password visibility",
      "aria-pressed": "false",
      onClick: () => {
        showPassword = !showPassword;
        passwordInput.type = showPassword ? "text" : "password";
        togglePasswordBtn.setAttribute("aria-pressed", showPassword ? "true" : "false");
        togglePasswordBtn.textContent = showPassword ? "🙈" : "👁";
      },
    },
    "👁"
  );

  const submitBtn = el(
    "button",
    {
      type: "submit",
      className: "btn btn-primary",
      style: { width: "100%", marginTop: "var(--s4)" },
    },
    isSignup ? "Create account" : "Log in"
  );

  function clearErrors() {
    nameError.style.display = "none";
    nameError.textContent = "";
    nameInput.classList.remove("is-error");

    emailError.style.display = "none";
    emailError.textContent = "";
    emailInput.classList.remove("is-error");

    passwordError.style.display = "none";
    passwordError.textContent = "";
    passwordInput.classList.remove("is-error");

    generalError.style.display = "none";
    generalError.textContent = "";
  }

  const form = el(
    "form",
    {
      onSubmit: async (e) => {
        e.preventDefault();
        if (isSubmitting) return;

        clearErrors();
        isSubmitting = true;
        submitBtn.disabled = true;
        submitBtn.textContent = isSignup ? "Creating account…" : "Logging in…";

        const payload = {
          email: emailInput.value.trim(),
          password: passwordInput.value,
        };
        if (isSignup) {
          payload.name = nameInput.value.trim();
        }

        try {
          const endpoint = isSignup ? "/api/auth/signup" : "/api/auth/login";
          const res = await request("POST", endpoint, payload);

          setToken(res.token);
          setUser(res.user);
          window.location.hash = "#/groups";
        } catch (err) {
          isSubmitting = false;
          submitBtn.disabled = false;
          submitBtn.textContent = isSignup ? "Create account" : "Log in";

          if (err instanceof ApiError) {
            if (err.fields) {
              if (err.fields.name) {
                nameError.textContent = err.fields.name;
                nameError.style.display = "flex";
                nameInput.classList.add("is-error");
              }
              if (err.fields.email) {
                emailError.textContent = err.fields.email;
                emailError.style.display = "flex";
                emailInput.classList.add("is-error");
              }
              if (err.fields.password) {
                passwordError.textContent = err.fields.password;
                passwordError.style.display = "flex";
                passwordInput.classList.add("is-error");
              }
            } else {
              generalError.textContent = err.message;
              generalError.style.display = "flex";
            }
          } else {
            generalError.textContent = "Something went wrong on our side. Try again in a moment.";
            generalError.style.display = "flex";
          }
        }
      },
    },
    isSignup
      ? el(
          "div",
          { className: "form-group" },
          el("label", { className: "form-label", htmlFor: "auth-name" }, "Your name"),
          nameInput,
          nameError
        )
      : null,
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "auth-email" }, "Email address"),
      emailInput,
      emailError
    ),
    el(
      "div",
      { className: "form-group" },
      el("label", { className: "form-label", htmlFor: "auth-password" }, "Password"),
      el("div", { className: "input-wrapper" }, passwordInput, togglePasswordBtn),
      passwordError
    ),
    generalError,
    submitBtn
  );

  const tabs = el(
    "div",
    {
      style: {
        display: "flex",
        borderBottom: "1px solid var(--line)",
        marginBottom: "var(--s5)",
      },
    },
    el(
      "a",
      {
        href: "#/login",
        style: {
          flex: 1,
          textAlign: "center",
          padding: "var(--s3) 0",
          fontWeight: !isSignup ? "700" : "500",
          color: !isSignup ? "var(--lagoon)" : "var(--slate)",
          borderBottom: !isSignup ? "2px solid var(--lagoon)" : "none",
          textDecoration: "none",
        },
      },
      "Log in"
    ),
    el(
      "a",
      {
        href: "#/signup",
        style: {
          flex: 1,
          textAlign: "center",
          padding: "var(--s3) 0",
          fontWeight: isSignup ? "700" : "500",
          color: isSignup ? "var(--lagoon)" : "var(--slate)",
          borderBottom: isSignup ? "2px solid var(--lagoon)" : "none",
          textDecoration: "none",
        },
      },
      "Create account"
    )
  );

  const card = el(
    "div",
    {
      className: "card",
      style: {
        width: "100%",
        maxWidth: "400px",
        margin: "auto",
        boxShadow: "var(--shadow)",
      },
    },
    el(
      "div",
      { style: { textAlign: "center", marginBottom: "var(--s5)" } },
      el("h1", { className: "wordmark", style: { fontSize: "var(--fs-2xl)" } }, "Halfway"),
      el("p", { style: { color: "var(--slate)", marginTop: "var(--s1)" } }, "Share costs, keep friends.")
    ),
    tabs,
    form
  );

  const wrapper = el(
    "main",
    {
      style: {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "var(--s4)",
      },
    },
    card
  );

  container.appendChild(wrapper);
}
