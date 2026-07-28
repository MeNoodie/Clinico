document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatHistory = document.getElementById('chat-history');
    const sendBtn = document.getElementById('send-btn');
    
    // For testing without authentication, we use POST /chat/test which requires a patient_id
    // We will hardcode patient_id 1 for now (Test User)
    const PATIENT_ID = 1;
    // When deploying to Vercel, the API_URL should be the full URL of your deployed backend.
    // For local development, it's localhost:8000
    const API_URL = 'http://127.0.0.1:8000/chat/test';
    
    function addMessageToUI(content, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'agent-message'}`;
        
        let innerHTML = '';
        if (!isUser) {
            innerHTML += '<div class="avatar">A</div>';
        }
        
        innerHTML += `<div class="message-content">${escapeHTML(content)}</div>`;
        messageDiv.innerHTML = innerHTML;
        
        chatHistory.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function addSystemMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message system-message';
        messageDiv.innerHTML = `<div class="message-content">${escapeHTML(content)}</div>`;
        chatHistory.appendChild(messageDiv);
        scrollToBottom();
    }
    
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'loading-indicator';
        loadingDiv.id = 'loading';
        loadingDiv.innerHTML = `
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
            <div class="loading-dot"></div>
        `;
        chatHistory.appendChild(loadingDiv);
        scrollToBottom();
    }
    
    function hideLoading() {
        const loadingDiv = document.getElementById('loading');
        if (loadingDiv) {
            loadingDiv.remove();
        }
    }
    
    function scrollToBottom() {
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    function escapeHTML(str) {
        return str.replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag])
        );
    }
    
    async function sendMessage(message) {
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    patient_id: PATIENT_ID,
                    message: message
                })
            });
            
            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }
            
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error sending message:', error);
            throw error;
        }
    }
    
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Disable input and button while processing
        messageInput.value = '';
        messageInput.disabled = true;
        sendBtn.disabled = true;
        
        // Add user message to UI
        addMessageToUI(message, true);
        
        // Show loading state
        showLoading();
        
        try {
            // Send request to backend
            const data = await sendMessage(message);
            
            // Hide loading state
            hideLoading();
            
            // Add agent response to UI
            addMessageToUI(data.message || "I couldn't process that request.", false);
            
            // Show metadata if intent is detected
            if (data.intent && data.intent !== 'UNKNOWN') {
                let metaInfo = `Intent: ${data.intent} | Safety: ${data.safety_status}`;
                if (data.department) metaInfo += ` | Dept: ${data.department}`;
                if (data.appointment_id) metaInfo += ` | Appt ID: ${data.appointment_id}`;
                addSystemMessage(metaInfo);
            }
            
        } catch (error) {
            hideLoading();
            addSystemMessage('Connection error. Make sure your FastAPI server is running on port 8000 and CORS is configured.');
        } finally {
            // Re-enable input
            messageInput.disabled = false;
            sendBtn.disabled = false;
            messageInput.focus();
        }
    });
    
    // Initial focus
    messageInput.focus();
});
