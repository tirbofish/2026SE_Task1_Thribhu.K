async function logout() {
    let apiEndpoint = localStorage.getItem('apiEndpoint');
    if (!apiEndpoint) {
        apiEndpoint = 'http://127.0.0.1:5000';
    }

    try {
        const response = await fetch(`${apiEndpoint}/api/logout`, {
            method: 'POST',
            credentials: 'include',
            mode: 'cors'
        });

        window.location.href = '/login?message=Logged out successfully&message_type=success';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/login?message=Logged out successfully&message_type=success';
    }
}