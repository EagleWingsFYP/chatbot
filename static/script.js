// Sound for notifications
const notificationSound = new Audio('https://www.soundjay.com/button/beep-07.wav');

let userScrolled = false; // Flag to track if the user manually scrolled
const chatContainer = document.getElementById('chat-container');
const chatHistory = document.getElementById('chat-history');
const MAX_MESSAGES = 10; // Maximum number of messages to show at a time
const scrollToBottomBtn = document.getElementById('scroll-to-bottom-btn');
const themeToggleBtn = document.getElementById('theme-toggle');
const chatWrapper = document.getElementById('chat-wrapper');
const body = document.body;

// Logout button: redirect to sign in/up page
const logoutBtn = document.getElementById('logout-btn');
if (logoutBtn) {
    logoutBtn.addEventListener('click', function () {
        window.location.href = '/Sign_in_&_up';
    });
}

// Toggle Dark/Light Mode
themeToggleBtn.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    chatWrapper.classList.toggle('dark-mode');
    themeToggleBtn.textContent = body.classList.contains('dark-mode') ? '🌞' : '🌙';
});

// Function to send a message and handle user input
function sendMessage() {
    var userMessage = document.getElementById('user-input').value.trim();

    if (userMessage === '') return;

    // User message with icon
    var userMsg = document.createElement('p');
    userMsg.classList.add('user-msg');
    userMsg.innerHTML = `<img src="/static/images/user.png" alt="User" /> ${userMessage}`;
    chatHistory.appendChild(userMsg);

    // Play notification sound
    notificationSound.play();

    // Keep only the last MAX_MESSAGES messages
    while (chatHistory.children.length > MAX_MESSAGES) {
        chatHistory.removeChild(chatHistory.firstChild);
    }

    // Clear the input field
    document.getElementById('user-input').value = '';

    // Fetch response from server
    fetch('/get_response', {
        method: 'POST',
        body: new URLSearchParams({ message: userMessage }),
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
        .then((response) => response.json())
        .then((data) => {
            // Bot response with icon
            var botMsg = document.createElement('p');
            botMsg.classList.add('bot-msg');
            botMsg.innerHTML = `<img src="/static/images/bot.png" alt="Bot" /> ${data.reply}`;
            chatHistory.appendChild(botMsg);

            // Play notification sound
            notificationSound.play();

            // Keep only the last MAX_MESSAGES messages
            while (chatHistory.children.length > MAX_MESSAGES) {
                chatHistory.removeChild(chatHistory.firstChild);
            }

            // Scroll to bottom if not manually scrolled
            if (!userScrolled) {
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        });
}

// Event listener for the send button
document.getElementById('send-btn').addEventListener('click', sendMessage);

// Event listener for Enter key
document.getElementById('user-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Scroll to bottom button visibility
chatContainer.addEventListener('scroll', () => {
    if (chatContainer.scrollTop + chatContainer.clientHeight < chatContainer.scrollHeight - 50) {
        scrollToBottomBtn.style.display = 'block';
        userScrolled = true;
    } else {
        scrollToBottomBtn.style.display = 'none';
        userScrolled = false;
    }
});

// Scroll to bottom when the button is clicked
scrollToBottomBtn.addEventListener('click', () => {
    chatContainer.scrollTop = chatContainer.scrollHeight;
    userScrolled = false;
    scrollToBottomBtn.style.display = 'none';
});

// Speech Recognition
const micBtn = document.getElementById('mic-btn');
let recognition;

if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    micBtn.addEventListener('click', () => {
        recognition.start();
    });

    recognition.addEventListener('result', (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('user-input').value = transcript;
        sendMessage();
    });

    recognition.addEventListener('error', (event) => {
        console.error('Speech recognition error:', event.error);
    });
} else {
    micBtn.disabled = true;
    micBtn.title = 'Speech recognition not supported in this browser.';
}

document.querySelectorAll('.quick-reply').forEach(btn => {
    btn.addEventListener('click', function() {
        if (btn.textContent.trim() === 'Track Face') {
            fetch('/start_face_detection', { method: 'POST' })
                .then(res => res.json())
                .then(data => alert(data.message || 'Please wait Face detection will be started!'));
        } else if (btn.textContent.trim() === 'Gesture Control') {
            fetch('/start_gesture_control', { method: 'POST' })
                .then(res => res.json())
                .then(data => alert(data.message || 'Please wait Gesture control will be started!'));
        } else {
            document.getElementById('user-input').value = btn.textContent.trim();
            sendMessage();
        }
    });
});
