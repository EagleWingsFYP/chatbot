"""
Main entrypoint for the EagleWings chatbot system, integrating AIML, drone control,
face detection, and user authentication. Handles Flask routes, drone commands,
and user queries.
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, make_response
import aiml
import time
import os
from dotenv import load_dotenv
import threading
import subprocess
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


# --- Flask App and AIML Kernel ---
app = Flask(__name__)
kernel = aiml.Kernel()


# AIML brain caching
def initialize_aiml(aiml_folder: str, brain_file: str = "bot.brn"):
    """
    Initialize the AIML kernel with brain caching.

    Args:
        aiml_folder (str): Path to AIML files.
        brain_file (str): Path to cached brain file.

    Returns:
        None
    """
    if os.path.exists(brain_file):
        print(f"[INFO] Loading AIML brain from {brain_file}...")
        kernel.bootstrap(brainFile=brain_file)
        print("[INFO] AIML brain loaded.")
    else:
        if not os.path.isdir(aiml_folder):
            print(f"⚠️ AIML folder not found: {aiml_folder}")
            return
        print(f"[INFO] Learning AIML files from {aiml_folder}...")
        for filename in os.listdir(aiml_folder):
            if filename.endswith(".aiml"):
                kernel.learn(os.path.join(aiml_folder, filename))
        print(f"[INFO] Saving AIML brain to {brain_file}...")
        kernel.saveBrain(brain_file)
        print("[INFO] AIML brain saved.")




# --- Drone connection state and camera/model initialization ---
tello = Tello()
drone_connected = False
drone_lock = threading.Lock()
camera = None
fd_model = None
active_camera_type = None  # 'WebCam' or 'TelloCam'


def initialize_camera_and_model_on_startup():
    """
    Initialize camera and face detection model at startup.

    Tries to connect to the drone and use TelloCam if available, otherwise falls back to WebCam.

    Returns:
        None
    """
    global camera, fd_model, active_camera_type, drone_connected
    try:
        import sys, os
        face_detection_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../faceDetection'))
        if face_detection_path not in sys.path:
            sys.path.insert(0, face_detection_path)
        from run import model as fd_model_ref
        fd_model = fd_model_ref
        # Try to connect to drone at startup
        if _DRONE_AVAILABLE:
            try:
                tello.connect()
                drone_connected = True
                from object_detector.input.TelloCam import TelloCam
                camera = TelloCam(tello)
                active_camera_type = 'TelloCam'
                print("[INFO] Drone connected at startup. Using TelloCam.")
                return
            except Exception as e:
                drone_connected = False
                print(f"[INFO] Drone not connected at startup: {e}")
        # Fallback to WebCam
        from object_detector.input.WebCam import WebCam
        camera = WebCam()
        active_camera_type = 'WebCam'
        print("[INFO] Using WebCam at startup.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize camera/model at startup: {e}")
        import sys
        print(f"[ERROR] sys.path at failure: {sys.path}")

def switch_to_tello_camera():
    """
    Switch to TelloCam, closing WebCam if open.

    Returns:
        None
    """
    global camera, active_camera_type
    try:
        import sys, os
        face_detection_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../faceDetection'))
        if face_detection_path not in sys.path:
            sys.path.insert(0, face_detection_path)
        if active_camera_type == 'WebCam' and camera is not None:
            # Attempt to release/close the webcam
            if hasattr(camera, 'release'):
                camera.release()
            camera = None
        from object_detector.input.TelloCam import TelloCam
        camera = TelloCam(tello)
        active_camera_type = 'TelloCam'
        print("[INFO] Switched to TelloCam.")
    except Exception as e:
        print(f"[ERROR] Failed to switch to TelloCam: {e}")

def ensure_camera_and_model():
    """
    Ensure camera and model are initialized (WebCam or TelloCam depending on connection).

    Returns:
        None
    """
    global camera, fd_model, active_camera_type
    if camera is None or fd_model is None:
        if drone_connected:
            switch_to_tello_camera()
        else:
            initialize_camera_and_model_on_startup()

def connect_tello():
    """
    Try to connect to Tello drone.

    Returns:
        bool: True if connected, False otherwise.
    """
    global drone_connected
    with drone_lock:
        if _DRONE_AVAILABLE:
            try:
                tello.connect()
                drone_connected = True
                print("✅ Tello Connected!")
                # Switch to TelloCam and close WebCam if needed
                switch_to_tello_camera()
                return True
            except Exception as e:
                drone_connected = False
                print(f"⚠️ Tello Connection Failed: {e}")
                return False
        else:
            drone_connected = False
            print("⚠️ Tello module unavailable; running in dummy mode.")
            return False


# Initialize camera/model at startup (TelloCam if drone is connected, else WebCam)
initialize_camera_and_model_on_startup()


# Prepare AIML
AINML_FOLDER = os.getenv("AIML_FOLDER", "./aiml")
BRAIN_FILE = os.getenv("AIML_BRAIN", "bot.brn")
print(f"[INFO] Using AIML folder: {AINML_FOLDER}")
initialize_aiml(AINML_FOLDER, BRAIN_FILE)

# Public API for main integration

def start_chatbot(host="0.0.0.0", port=5000):
    """
    Run the Flask chatbot server.

    Args:
        host (str): Host address.
        port (int): Port number.

    Returns:
        None
    """
    app.run(host=host, port=port)

# Internal helpers


# --- Drone command lock to serialize commands ---
drone_command_lock = threading.Lock()

def perform_action(drone_state: str):
    """
    Perform drone action or dummy output based on the parsed state.

    Args:
        drone_state (str): The command/state to execute.

    Returns:
        None
    """
    def execute_command():
        with drone_command_lock:
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
    """
    Query the AIML kernel and return the response.

    Handles drone status, connection, face detection, attack, and user identity queries.

    Args:
        user_input (str): The user's message.

    Returns:
        str: The bot's response.
    """

    # Add drone status and connect intent handling
    msg = user_input.strip().lower()
    # FaceBot: handle face recognition and user DB queries
    who_patterns = [
        "who is the person in camera", "who is in camera", "who is in the frame", "who am i", "what's my name", "what is my name", "my name", "who is that person", "who is that", "who was detected", "who is detected", "person in camera", "person detected"
    ]
    followup_patterns = [
        "tell me more about them", "tell me more about that person", "more about them", "more about that person"
    ]
    # 1. Face/person identity queries
    if any(p in msg for p in who_patterns):
        last_person = db.get_last_detected_person()
        best_match = last_person['name'] if last_person and 'name' in last_person and last_person['name'] and last_person['name'].lower() != 'unknown' else None
        user_record = None
        # Try to get user from face, else from session
        if best_match:
            user_record = db.get_user_by_email(best_match) if '@' in best_match else db.get_user_by_full_name(best_match) if hasattr(db, 'get_user_by_full_name') else None
        if not best_match:
            # Try to get logged-in user from session
            from flask import request
            email = request.cookies.get('email')
            if email:
                user_record = db.get_user_by_email(email)
        # Compose response
        if best_match:
            if user_record and user_record.get('full_name') and user_record['full_name'].lower() == best_match.lower():
                return f"I see {best_match} in the camera. Your full name in my records is {user_record['full_name']}."
            else:
                return f"I see {best_match} in the camera."
        elif user_record and user_record.get('full_name'):
            return f"According to my database, you are {user_record['full_name']}."
        else:
            return "I'm sorry, I don't see anyone in the camera right now."
    # 2. Follow-up about detected person
    if any(p in msg for p in followup_patterns):
        last_person = db.get_last_detected_person()
        best_match = last_person['name'] if last_person and 'name' in last_person and last_person['name'] and last_person['name'].lower() != 'unknown' else None
        user_record = None
        if best_match:
            user_record = db.get_user_by_email(best_match) if '@' in best_match else db.get_user_by_full_name(best_match) if hasattr(db, 'get_user_by_full_name') else None
        if user_record:
            created = user_record.get('created_at', '')
            email = user_record.get('email', '')
            return f"They joined on {created} and use email {email}."
        else:
            return "Sorry, I don't have more information about them."

    # Existing chatbot logic
    if any(x in msg for x in ["is drone connected", "drone status", "are you connected to drone", "drone connection status"]):
        with drone_lock:
            return "Drone is connected." if drone_connected else "Drone is not connected."
    if any(x in msg for x in ["connect to drone", "connect drone", "reconnect drone", "please connect to drone"]):
        success = connect_tello()
        return "Drone connected successfully!" if success else "Failed to connect to drone."

    # Detect person intent
    if any(x in msg for x in ["detect the person", "recognize person"]):
        # If live detection (run.py) is running, just read the latest detected person from db
        last_person = db.get_last_detected_person()
        if last_person and last_person.get('name') and last_person['name'].lower() != 'unknown':
            return f"Person detected: {last_person['name']}"
        else:
            return "No person detected or identity unknown. Please ensure live face detection is running."

    # Attack person intent
    if any(x in msg for x in ["attack person", "attack detected person", "attack the person", "attack target"]):
        def attack_person_async():
            """
            Start attack in a background thread and store the result.
            """
            try:
                from modules.models.attack import attack as attack_func
                last_person = db.get_last_detected_person()
                if last_person and last_person.get('face') is not None:
                    attack_func()
                    result = "Attack sequence started!"
                else:
                    result = "No detected person to attack. Please detect a person first."
            except Exception as e:
                result = f"Attack error: {e}"
            db.set_last_attack_result(result)

        db.set_last_attack_result("Starting attack...")
        threading.Thread(target=attack_person_async, daemon=True).start()
        return "Attack sequence initiated. (processing in background, please check attack result in a few seconds)"


    # Check for last detection result
    if any(x in msg for x in ["person detection result", "who was detected", "detection result"]):
        return db.get_last_person_detection_result() or "No detection result yet."

    # Check for last attack result
    if any(x in msg for x in ["attack result", "attack status", "was attack successful"]):
        return db.get_last_attack_result() or "No attack result yet."

    response = kernel.respond(user_input)
    return response if response else "Sorry, I don't understand that."



# --- Auth Routes: Register/Login always available ---
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

# --- Main Index Route: Always after auth, always protected ---
@app.route("/")
def home():
    # If not authenticated, redirect to sign in/up page
    if not request.cookies.get('isAuthenticated'):
        return redirect(url_for('sign_in_up'))
    return render_template("index.html")


# --- API and Module Launch Routes: Always protected ---
# --- API and Module Launch Routes: Always protected ---
def is_authenticated():
    # Simple cookie check; replace with flask-login for production
    return request.cookies.get('isAuthenticated')

def require_auth():
    if not is_authenticated():
        return redirect(url_for('sign_in_up'))

# --- Drone status and connect endpoints ---
@app.route("/drone_status", methods=["GET"])
def drone_status():
    """Return JSON with drone connection status."""
    with drone_lock:
        return jsonify({"connected": bool(drone_connected)})

@app.route("/connect_drone", methods=["POST"])
def connect_drone():
    """Try to connect to the drone. Returns status."""
    if not is_authenticated():
        return jsonify({"error": "Not authenticated"}), 401
    success = connect_tello()
    return jsonify({"connected": success})

@app.route("/get_response", methods=["POST"])
def get_response():
    if not is_authenticated():
        return jsonify({"error": "Not authenticated"}), 401
    user_message = request.form.get("message", "")
    bot_reply = get_bot_response(user_message)

    drone_state = kernel.getPredicate("direction").lower()
    if drone_state and drone_state != "none":
        perform_action(drone_state)
        kernel.setPredicate("direction", "none")  # reset after execution

    return jsonify({"reply": bot_reply})



@app.route("/start_face_detection", methods=["POST"])
def start_face_detection():
    if not is_authenticated():
        return jsonify({"error": "Not authenticated"}), 401
    try:
        import subprocess
        import sys, os
        # Path to run.py
        face_detection_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../faceDetection'))
        run_py_path = os.path.join(face_detection_path, 'run.py')
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, run_py_path],
            cwd=face_detection_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        output = result.stdout.strip()
        error = result.stderr.strip()
        if result.returncode != 0:
            return jsonify({"error": f"run.py failed", "stderr": error, "stdout": output}), 500
        return jsonify({"message": "run.py executed successfully", "output": output})
    except subprocess.TimeoutExpired:
        return jsonify({"error": "run.py timed out"}), 500
    except Exception as e:
        return jsonify({"message": f"Failed to run face detection: {e}"}), 500

@app.route("/start_gesture_control", methods=["POST"])
def start_gesture_control():
    if not is_authenticated():
        return jsonify({"error": "Not authenticated"}), 401
    try:
        subprocess.Popen(
            ["python", "modules/gestureControl/gesture.py"],
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
        )
        return jsonify({"message": "Gesture control module started!"})
    except Exception as e:
        return jsonify({"message": f"Failed to start gesture control: {e}"}), 500

if __name__ == "__main__":
    start_chatbot()
