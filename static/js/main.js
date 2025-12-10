function loginRedirect() {
    window.location.href = "/login";
}

const loginMessageEl = document.getElementById("loginMessage");
function showLoginMessage(message = "", isError = true) {
    if (!loginMessageEl) return;
    loginMessageEl.textContent = message;
    loginMessageEl.hidden = !message;
    loginMessageEl.classList.toggle("text-danger", isError);
    loginMessageEl.classList.toggle("text-success", !isError);
}

async function handleLogin(event) {
    if (event) event.preventDefault();
    showLoginMessage("");

    const endpointInput = document.getElementById("apiEndpoint");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");

    if (!endpointInput || !emailInput || !passwordInput) {
        showLoginMessage("Login form elements missing.");
        return;
    }

    const baseEndpoint = (endpointInput.value || "http://127.0.0.1:5000").trim().replace(/\/$/, "");
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password || !baseEndpoint) {
        showLoginMessage("Email, password, and API endpoint are required.");
        return;
    }

    localStorage.setItem("baseEndpoint", baseEndpoint);

    try {
        const formData = new URLSearchParams();
        formData.append("email", email);
        formData.append("password", password);

        const response = await fetch(`${baseEndpoint}/api/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData.toString(),
        });

        if (!response.ok) {
            let errorText = "Login failed. Please try again.";
            try {
                const errorPayload = await response.json();
                errorText = errorPayload.message || errorPayload.error || errorText;
            } catch {
                errorText = `${errorText} (HTTP ${response.status})`;
            }
            showLoginMessage(errorText);
            return;
        }

        window.location.href = "/auth-redirect";
    } catch (err) {
        console.error("Login request failed", err);
        showLoginMessage("Unable to reach the server. Check the API endpoint and try again.");
    }
}

async function handleRegister(event) {
    if (event) event.preventDefault();
    showLoginMessage("");

    const target = event?.currentTarget;
    const form =
        target instanceof HTMLFormElement
            ? target
            : target instanceof HTMLElement
                ? target.closest("form")
                : document.getElementById("registerForm");

    if (!form) {
        showLoginMessage("Register form elements missing.");
        return;
    }

    const formData = new FormData(form);
    const endpointInput = form.querySelector("#registerEndpoint") || document.getElementById("apiEndpoint");
    const baseEndpoint = (formData.get("apiEndpoint") || endpointInput?.value || "http://127.0.0.1:5000").trim().replace(/\/$/, "");
    const name = (formData.get("name") || formData.get("fullName") || formData.get("registerName") || "").trim();
    const email = (formData.get("registerEmail") || formData.get("email") || "").trim();
    const username = (formData.get("registerUsername") || formData.get("username") || "").trim();
    const password = formData.get("registerPassword") || formData.get("password") || "";
    const confirmPassword = formData.get("confirmPassword") || formData.get("registerConfirmPassword") || "";

    if (!name || !username || !email || !password || !baseEndpoint) {
        showLoginMessage("Name, username, email, password, and API endpoint are required.");
        return;
    }

    if (confirmPassword && password !== confirmPassword) {
        showLoginMessage("Passwords do not match.");
        return;
    }

    try {
        const payload = new URLSearchParams();
        payload.append("name", name);
        payload.append("email", email);
        payload.append("username", username);
        payload.append("password", password);

        const response = await fetch(`${baseEndpoint}/api/register`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: payload.toString(),
        });

        if (!response.ok) {
            let errorText = "Registration failed. Please try again.";
            try {
                const errorPayload = await response.json();
                errorText = errorPayload.message || errorPayload.error || errorText;
            } catch {
                errorText = `${errorText} (HTTP ${response.status})`;
            }
            showLoginMessage(errorText);
            return;
        }

        showLoginMessage("Registration successful! You can log in now.", false);
        form.reset();
    } catch (err) {
        console.error("Registration request failed", err);
        showLoginMessage("Unable to reach the server. Check the API endpoint and try again.");
    }
}

window.loginRedirect = loginRedirect;
window.handleLogin = handleLogin;

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }

    const endpointInput = document.getElementById("apiEndpoint");
    const savedEndpoint = localStorage.getItem("baseEndpoint");
    if (endpointInput && savedEndpoint) {
        endpointInput.value = savedEndpoint;
    }
    
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", handleRegister);
    }
});