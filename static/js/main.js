function getCookieValue(name) {
    const cookies = document.cookie ? document.cookie.split('; ') : [];
    const prefix = `${name}=`;
    for (const cookie of cookies) {
        if (cookie.startsWith(prefix)) {
            return decodeURIComponent(cookie.slice(prefix.length));
        }
    }
    return null;
}

/// a more secure way of fetching an API. sets up the csrf stuff. 
function apiFetch(url, options = {}) {
    const opts = {
        credentials: 'include',
        mode: 'cors',
        ...options
    };

    const method = (opts.method || 'GET').toUpperCase();
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
        const csrfToken = getCookieValue('csrf_access_token');
        if (csrfToken) {
            if (!opts.headers) {
                opts.headers = {};
            }

            if (opts.headers instanceof Headers) {
                opts.headers.set('X-CSRF-TOKEN', csrfToken);
            } else {
                opts.headers['X-CSRF-TOKEN'] = csrfToken;
            }
        }
    }

    return fetch(url, opts);
}

async function logout() {
    let apiEndpoint = localStorage.getItem('apiEndpoint');
    if (!apiEndpoint) {
        apiEndpoint = 'http://127.0.0.1:5000';
    }

    try {
        await apiFetch(`${apiEndpoint}/api/logout`, { method: 'POST' });

        window.location.href = '/login?message=Logged out successfully&message_type=success';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/login?message=Logged out successfully&message_type=success';
    }
}

function submitLogForm() {
    const form = document.getElementById('createLogForm');
    const errorDiv = document.getElementById('formError');
    errorDiv.classList.add('d-none');

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = new FormData(form);
    
    const startTime = formData.get('start_time');
    const endTime = formData.get('end_time');
    const logTimestamp = formData.get('log_timestamp');
    
    if (startTime && endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffMins = Math.round(diffMs / 60000);
        
        if (diffMins <= 0) {
            errorDiv.textContent = 'End time must be after start time';
            errorDiv.classList.remove('d-none');
            return;
        }
        
        formData.set('time_worked_minutes', diffMins.toString());
    }
    
    if (startTime) {
        formData.set('start_time', startTime.replace('T', ' '));
    }
    if (endTime) {
        formData.set('end_time', endTime.replace('T', ' '));
    }
    if (logTimestamp) {
        formData.set('log_timestamp', logTimestamp.replace('T', ' '));
    }

    const commits = formData.get('related_commits');
    if (commits && commits.trim()) {
        const commitArray = commits.split(',').map(c => c.trim()).filter(c => c);
        formData.set('related_commits', JSON.stringify(commitArray));
    } else {
        formData.delete('related_commits');
    }

    const apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://127.0.0.1:5000';

    apiFetch(`${apiEndpoint}/api/${window.PAGE_PROJECT_ID}/logs`, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json().then(data => ({status: response.status, data})))
    .then(({status, data}) => {
        if (status === 201) {
            window.location.reload();
        } else {
            errorDiv.textContent = data.cause || data.message || 'Failed to create log';
            errorDiv.classList.remove('d-none');
        }
    })
    .catch(error => {
        errorDiv.textContent = 'Network error: ' + error.message;
        errorDiv.classList.remove('d-none');
    });
}

function deleteLog(logId) {
    const apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://127.0.1:5000';
}

let currentLogData = null;

function viewLog(logId) {
    const apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://127.0.0.1:5000';
    
    apiFetch(`${apiEndpoint}/api/${window.PAGE_PROJECT_ID}/logs/${logId}`)
    .then(response => response.json())
    .then(data => {
        currentLogData = data;
        populateViewMode(data);
        
        document.getElementById('viewMode').classList.remove('d-none');
        document.getElementById('editMode').classList.add('d-none');
        document.getElementById('toggleEditBtn').classList.remove('d-none');
        document.getElementById('saveEditBtn').classList.add('d-none');
        document.getElementById('viewEditLogModalLabel').textContent = 'View Log Entry';
        
        const modal = new bootstrap.Modal(document.getElementById('viewEditLogModal'));
        modal.show();
    })
    .catch(error => {
        console.error('Error fetching log:', error);
    });
}

function editLog(logId) {
    const apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://127.0.0.1:5000';
    
    apiFetch(`${apiEndpoint}/api/${window.PAGE_PROJECT_ID}/logs/${logId}`)
    .then(response => response.json())
    .then(data => {
        currentLogData = data;
        populateEditMode(data);
        
        document.getElementById('viewMode').classList.add('d-none');
        document.getElementById('editMode').classList.remove('d-none');
        document.getElementById('toggleEditBtn').classList.add('d-none');
        document.getElementById('saveEditBtn').classList.remove('d-none');
        document.getElementById('viewEditLogModalLabel').textContent = 'Edit Log Entry';
        
        const modal = new bootstrap.Modal(document.getElementById('viewEditLogModal'));
        modal.show();
    })
    .catch(error => {
        console.error('Error fetching log:', error);
    });
}

function populateViewMode(data) {
    document.getElementById('view_start_time').textContent = data.start_time || 'N/A';
    document.getElementById('view_end_time').textContent = data.end_time || 'N/A';
    document.getElementById('view_time_worked').textContent = data.time_worked_minutes || 'N/A';
    const viewNotesEl = document.getElementById('view_notes');
    const rawNotes = data.developer_notes || '';

    if (window.marked && window.DOMPurify) {
        try {
            if (typeof window.marked.setOptions === 'function') {
                window.marked.setOptions({ breaks: true });
            }

            const rendered = window.marked.parse(rawNotes);
            const clean = window.DOMPurify.sanitize(rendered, { USE_PROFILES: { html: true } });
            viewNotesEl.innerHTML = clean || '<span class="text-muted">No notes</span>';
        } catch (e) {
            viewNotesEl.textContent = rawNotes || 'No notes';
        }
    } else {
        viewNotesEl.textContent = rawNotes || 'No notes';
    }
    document.getElementById('view_log_timestamp').textContent = data.log_timestamp || 'N/A';
    
    const commitsDiv = document.getElementById('view_commits');
    if (data.related_commits) {
        try {
            const commits = typeof data.related_commits === 'string' ? JSON.parse(data.related_commits) : data.related_commits;
            if (commits && commits.length > 0) {
                commitsDiv.textContent = '';
                commits.forEach((commit) => {
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-secondary me-1';
                    badge.textContent = String(commit).substring(0, 8);
                    commitsDiv.appendChild(badge);
                });
            } else {
                commitsDiv.innerHTML = '<span class="text-muted">None</span>';
            }
        } catch (e) {
            commitsDiv.innerHTML = '<span class="text-muted">None</span>';
        }
    } else {
        commitsDiv.innerHTML = '<span class="text-muted">None</span>';
    }
}

function populateEditMode(data) {
    document.getElementById('edit_log_id').value = data.log_id;
    
    if (data.start_time) {
        document.getElementById('edit_start_time').value = data.start_time.replace(' ', 'T');
    }
    if (data.end_time) {
        document.getElementById('edit_end_time').value = data.end_time.replace(' ', 'T');
    }
    
    document.getElementById('edit_developer_notes').value = data.developer_notes || '';
    
    if (data.related_commits) {
        try {
            const commits = typeof data.related_commits === 'string' ? JSON.parse(data.related_commits) : data.related_commits;
            if (commits && commits.length > 0) {
                document.getElementById('edit_related_commits').value = commits.join(', ');
            }
        } catch (e) {
            document.getElementById('edit_related_commits').value = '';
        }
    }
}

function toggleEditMode() {
    populateEditMode(currentLogData);
    
    document.getElementById('viewMode').classList.add('d-none');
    document.getElementById('editMode').classList.remove('d-none');
    document.getElementById('toggleEditBtn').classList.add('d-none');
    document.getElementById('saveEditBtn').classList.remove('d-none');
    document.getElementById('viewEditLogModalLabel').textContent = 'Edit Log Entry';
}

function saveLogEdit() {
    const form = document.getElementById('editLogForm');
    const errorDiv = document.getElementById('editFormError');
    errorDiv.classList.add('d-none');

    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = new FormData(form);
    const logId = document.getElementById('edit_log_id').value;
    
    const startTime = formData.get('start_time');
    const endTime = formData.get('end_time');
    
    if (startTime && endTime) {
        const start = new Date(startTime);
        const end = new Date(endTime);
        const diffMs = end - start;
        const diffMins = Math.round(diffMs / 60000);
        
        if (diffMins <= 0) {
            errorDiv.textContent = "You can't work negative minutes! End time must be after start time";
            errorDiv.classList.remove('d-none');
            return;
        }
        
        formData.set('time_worked_minutes', diffMins.toString());
    }
    
    if (startTime) {
        formData.set('start_time', startTime.replace('T', ' '));
    }
    if (endTime) {
        formData.set('end_time', endTime.replace('T', ' '));
    }

    const commits = formData.get('related_commits');
    if (commits && commits.trim()) {
        const commitArray = commits.split(',').map(c => c.trim()).filter(c => c);
        formData.set('related_commits', JSON.stringify(commitArray));
    } else {
        formData.set('related_commits', JSON.stringify([]));
    }

    const apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://127.0.0.1:5000';

    apiFetch(`${apiEndpoint}/api/${window.PAGE_PROJECT_ID}/logs/${logId}`, {
        method: 'PUT',
        body: formData
    })
    .then(response => response.json().then(data => ({status: response.status, data})))
    .then(({status, data}) => {
        if (status === 200) {
            window.location.reload();
        } else {
            errorDiv.textContent = data.cause || data.message || 'Failed to update log';
            errorDiv.classList.remove('d-none');
        }
    })
    .catch(error => {
        errorDiv.textContent = 'Network error: ' + error.message;
        errorDiv.classList.remove('d-none');
    });
}

function deleteLog(projectId, logId) {
    if (!confirm('Are you sure you want to delete this log entry? This action cannot be undone.')) {
        return;
    }

    const apiEndpoint = localStorage.getItem('apiEndpoint') || 'http://127.0.0.1:5000';

    apiFetch(`${apiEndpoint}/api/${projectId}/logs/${logId}`, {
        method: 'DELETE',
    })
    .then(response => response.json().then(data => ({status: response.status, data})))
    .then(({status, data}) => {
        if (status === 200) {
            window.location.reload();
        } else {
            alert('Failed to delete log: ' + (data.cause || data.message || 'Unknown error'));
        }
    })
    .catch(error => {
        alert('Network error: ' + error.message);
    });
}