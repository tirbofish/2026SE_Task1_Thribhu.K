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

window.loginRedirect = loginRedirect;
window.handleLogin = handleLogin;

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }
});