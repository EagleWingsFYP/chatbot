# Chatbot Module: modules/chatbot/bot.py
# The main Chatbot entrypoint, with exception handling for Tello availability and dummy fallback.

from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
import aiml
import os
from dotenv import load_dotenv
import threading
# Import database functions
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))
import db

# Try to import Tello; fallback to dummy if unavailable
try:
    from djitellopy import Tello
    _DRONE_AVAILABLE = True
except ImportError:
    # djitellopy not installed, or import failed
    _DRONE_AVAILABLE = False
    class Tello:
        # Dummy Tello stub
        def connect(self):
            print("[Dummy Tello] connect() called")
        def takeoff(self):
            print("[Dummy Tello] takeoff() called")
        def land(self):
            print("[Dummy Tello] land() called")
        def move_forward(self, x):
            print(f"[Dummy Tello] move_forward({x}) called")
        def move_back(self, x):
            print(f"[Dummy Tello] move_back({x}) called")
        def move_left(self, x):
            print(f"[Dummy Tello] move_left({x}) called")
        def move_right(self, x):
            print(f"[Dummy Tello] move_right({x}) called")
        def move_up(self, x):
            print(f"[Dummy Tello] move_up({x}) called")
        def move_down(self, x):
            print(f"[Dummy Tello] move_down({x}) called")
        def flip_back(self):
            print("[Dummy Tello] flip_back() called")
        def rotate_counter_clockwise(self, x):
            print(f"[Dummy Tello] rotate_counter_clockwise({x}) called")
        def rotate_clockwise(self, x):
            print(f"[Dummy Tello] rotate_clockwise({x}) called")


# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)
kernel = aiml.Kernel()

def initialize_aiml(aiml_folder: str):
    if not os.path.isdir(aiml_folder):
        print(f"⚠️ AIML folder not found: {aiml_folder}")
        return
    for filename in os.listdir(aiml_folder):
        if filename.endswith(".aiml"):
            kernel.learn(os.path.join(aiml_folder, filename))

# Initialize Tello (or dummy) asynchronously
tello = Tello()
drone_connected = False

def connect_tello():
    global drone_connected
    if _DRONE_AVAILABLE:
        try:
            tello.connect()
            drone_connected = True
            print("✅ Tello Connected!")
        except Exception as e:
            drone_connected = False
            print(f"⚠️ Tello Connection Failed: {e}")
    else:
        # Dummy mode
        drone_connected = False
        print("⚠️ Tello module unavailable; running in dummy mode.")

threading.Thread(target=connect_tello, daemon=True).start()


# Prepare AIML
AIML_FOLDER = os.getenv("AIML_FOLDER", "./aiml")
print(f"[INFO] Using AIML folder: {AIML_FOLDER}")
initialize_aiml(AIML_FOLDER)

# Public API for main integration

def start_chatbot(host="0.0.0.0", port=5000):
    """Run the Flask chatbot server."""
    app.run(host=host, port=port)

# Internal helpers

def perform_action(drone_state: str):
    """Perform drone action or dummy output based on the parsed state."""
    def execute_command():
        cmd = drone_state
        safe = lambda fn, *args: fn(*args) if drone_connected else print(f"[Dummy Action] {fn.__name__}({args})")

        if "take off" in cmd:
            print("→ Taking Off")
            safe(tello.takeoff)
        elif "land" in cmd:
            print("→ Landing")
            safe(tello.land)
        elif "forward" in cmd or "pitch up" in cmd:
            print("→ Moving Forward")
            safe(tello.move_forward, 30)
        elif "backward" in cmd or "pitch down" in cmd:
            print("→ Moving Backward")
            safe(tello.move_back, 30)
        elif "left" in cmd and all(x not in cmd for x in ("yaw","roll")):
            print("→ Moving Left")
            safe(tello.move_left, 30)
        elif "right" in cmd and all(x not in cmd for x in ("yaw","roll")):
            print("→ Moving Right")
            safe(tello.move_right, 30)
        elif "up" in cmd:
            print("→ Ascending")
            safe(tello.move_up, 50)
        elif "down" in cmd:
            print("→ Descending")
            safe(tello.move_down, 30)
        elif "flip" in cmd:
            print("→ Flipping")
            safe(tello.flip_back)
        elif "yaw left" in cmd:
            print("→ Rotating CCW")
            safe(tello.rotate_counter_clockwise, 45)
        elif "yaw right" in cmd:
            print("→ Rotating CW")
            safe(tello.rotate_clockwise, 45)
        elif "roll left" in cmd:
            print("→ Rolling Left")
            safe(tello.move_left, 30)
        elif "roll right" in cmd:
            print("→ Rolling Right")
            safe(tello.move_right, 30)
        else:
            print(f"⚠️ Unknown drone command: {cmd}")

    threading.Thread(target=execute_command, daemon=True).start()


def get_bot_response(user_input: str) -> str:
    """Query the AIML kernel and return the response."""
    response = kernel.respond(user_input)
    return response if response else "Sorry, I don't understand that."


# Flask routes
@app.route("/")
def home():
    # If not authenticated, redirect to sign in/up page
    # For demo: check a cookie (in real app, use session or flask-login)
    from flask import request, redirect, url_for
    if not request.cookies.get('isAuthenticated'):
        return redirect(url_for('sign_in_up'))
    return render_template("index.html")

@app.route("/Sign_in_&_up", methods=["GET", "POST"])
def sign_in_up():
    if request.method == "POST":
        # Determine if this is a register or login
        action = request.form.get('action')
        email = request.form.get('email')
        provider = request.form.get('provider', 'local')
        provider_id = request.form.get('provider_id')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        # Registration
        if action == 'register':
            # For local, hash password; for social, skip
            password_hash = password if provider == 'local' else None
            user_id = db.create_user(full_name, email, password_hash, provider, provider_id)
            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('isAuthenticated', 'true')
            return resp
        # Login
        elif action == 'login':
            user = db.get_user_by_email(email) if provider == 'local' else db.get_user_by_provider(provider, provider_id)
            if user:
                # For local, check password (in real app, hash check!)
                if provider == 'local' and user['password_hash'] != password:
                    return render_template("Sign_in_&_up.html", error="Invalid credentials")
                resp = make_response(redirect(url_for('home')))
                resp.set_cookie('isAuthenticated', 'true')
                return resp
            else:
                return render_template("Sign_in_&_up.html", error="User not found")
    return render_template("Sign_in_&_up.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    user_message = request.form.get("message", "")
    bot_reply = get_bot_response(user_message)

    drone_state = kernel.getPredicate("direction").lower()
    if drone_state and drone_state != "none":
        perform_action(drone_state)
        kernel.setPredicate("direction", "none")  # reset after execution

    return jsonify({"reply": bot_reply})

if __name__ == "__main__":
    start_chatbot()
