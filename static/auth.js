// auth.js - Smart Auth UI Interactions

document.addEventListener('DOMContentLoaded', function() {
    // Theme Toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            document.body.classList.toggle('dark-mode');
            const authContainer = document.querySelector('.auth-container');
            if (authContainer) authContainer.classList.toggle('dark-mode');
            // Update icon
            const icon = themeToggle.querySelector('i');
            if (icon) {
                if (document.body.classList.contains('dark-mode')) {
                    icon.classList.replace('fa-moon', 'fa-sun');
                } else {
                    icon.classList.replace('fa-sun', 'fa-moon');
                }
            }
        });
    }

    // Tab Switching
    const loginTab = document.getElementById('login-tab');
    const registerTab = document.getElementById('register-tab');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const toggleFormText = document.getElementById('toggle-form');

    if (loginTab && registerTab && loginForm && registerForm && toggleFormText) {
        loginTab.addEventListener('click', () => {
            loginTab.classList.add('active');
            registerTab.classList.remove('active');
            loginForm.classList.add('active');
            registerForm.classList.remove('active');
            toggleFormText.innerHTML = `Don't have an account? <a href="#">Sign Up</a>`;
        });

        registerTab.addEventListener('click', () => {
            registerTab.classList.add('active');
            loginTab.classList.remove('active');
            registerForm.classList.add('active');
            loginForm.classList.remove('active');
            toggleFormText.innerHTML = `Already have an account? <a href="#">Sign In</a>`;
        });

        // Toggle between forms
        toggleFormText.addEventListener('click', (e) => {
            if (e.target.tagName === 'A') {
                e.preventDefault();
                if (loginForm.classList.contains('active')) {
                    registerTab.click();
                } else {
                    loginTab.click();
                }
            }
        });
    }

    // Show/Hide Password
    const showPasswordBtns = document.querySelectorAll('.show-password');
    showPasswordBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const input = this.parentElement.querySelector('input');
            const icon = this.querySelector('i');
            if (input && icon) {
                if (input.type === 'password') {
                    input.type = 'text';
                    icon.classList.replace('fa-eye', 'fa-eye-slash');
                } else {
                    input.type = 'password';
                    icon.classList.replace('fa-eye-slash', 'fa-eye');
                }
            }
        });
    });


    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const passwords = this.querySelectorAll('input[type="password"]');
            if (passwords.length === 2 && passwords[0].value !== passwords[1].value) {
                e.preventDefault();
                alert('Passwords do not match!');
                return false;
            }
        });
    }
});
