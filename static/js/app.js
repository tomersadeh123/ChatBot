// DOM Elements
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const suggestedQuestions = document.getElementById('suggested-questions');

// Event Listeners
sendBtn.addEventListener('click', sendMessage);

userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Suggested questions
document.querySelectorAll('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const question = chip.getAttribute('data-question');
        userInput.value = question;
        sendMessage();
    });
});

// Remove suggestions after first message
let firstMessage = true;

async function sendMessage() {
    const message = userInput.value.trim();

    if (!message) return;

    // Remove suggested questions after first interaction
    if (firstMessage && suggestedQuestions) {
        suggestedQuestions.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => suggestedQuestions.remove(), 300);
        firstMessage = false;
    }

    // Add user message to chat
    addMessage(message, 'user');
    userInput.value = '';

    // Show typing indicator
    const typingIndicator = showTypingIndicator();

    // Disable input while waiting for response
    userInput.disabled = true;
    sendBtn.disabled = true;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();

        // Remove typing indicator
        typingIndicator.remove();

        if (response.ok) {
            addMessage(data.response, 'bot');
        } else {
            addMessage('Sorry, I encountered an error: ' + data.error, 'bot');
        }
    } catch (error) {
        typingIndicator.remove();
        addMessage('Sorry, I encountered an error: ' + error.message, 'bot');
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-robot"></i>
        </div>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return typingDiv;
}

function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;

    // Create avatar
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = type === 'user'
        ? '<i class="fas fa-user"></i>'
        : '<i class="fas fa-robot"></i>';

    // Create message wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'message-wrapper';

    // Create message content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;

    wrapper.appendChild(messageContent);

    // Add copy button for bot messages
    if (type === 'bot') {
        const actions = document.createElement('div');
        actions.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
        copyBtn.onclick = () => copyToClipboard(content, copyBtn);

        actions.appendChild(copyBtn);
        wrapper.appendChild(actions);
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(wrapper);
    chatMessages.appendChild(messageDiv);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('copied');

        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    });
}

// Add fadeOut animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-10px); }
    }
`;
document.head.appendChild(style);

