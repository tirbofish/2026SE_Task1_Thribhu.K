function loginRedirect() {
    window.location.href = "/login";
}

async function handleLogin(event) {
    if (event) event.preventDefault();

    const loginForm = document.getElementById("loginForm");
    const endpointInput = document.getElementById("apiEndpoint");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");

    if (!loginForm || !endpointInput || !emailInput || !passwordInput) {
        console.error("Login form elements missing");
        return;
    }

    const base = (endpointInput.value || "http://127.0.0.1:5000").replace(/\/$/, "");
    const email = emailInput.value.trim();
    const password = passwordInput.value;

    try {
        const res = await fetch(`${base}/api/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
        });

        if (!res.ok) {
            alert("Login failed");
            return;
        }

        const data = await res.json().catch(() => ({}));
        const userName = data.name || email.split("@")[0];
        window.location.href = `/auth-redirect?mode=login&name=${encodeURIComponent(userName)}`;
    } catch (err) {
        console.error("Login request failed", err);
        alert("Unable to reach the API endpoint.");
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