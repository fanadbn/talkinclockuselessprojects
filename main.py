# Import necessary libraries
import cv2  # OpenCV for webcam access and face detection
from datetime import datetime  # To get and format the current time
import time  # To handle delays and cooldowns
import random  # To pick a random sarcastic joke
import threading  # To speak the jokes in a separate thread so the main loop doesn't freeze
from gtts import gTTS  # Google Text-to-Speech to generate audio from text
import os  # To handle temporary audio files
from playsound import playsound  # For playing the generated audio files
import requests  # To make HTTP requests for the Gemini API

# ---------------------- SETTINGS ----------------------
LANG = 'ml'  # Language code for Malayalam
# The number of seconds to wait before a new joke can be told, even if a face is still present
JOKE_COOLDOWN = 10
CAM_INDEX = 0  # The index of the webcam to use. Change if using a different camera (e.g., IVCam might be 1 or 2)

# Global variable for the API key.
# IMPORTANT: PASTE YOUR API KEY HERE. DO NOT SHARE THIS CODE WITH YOUR KEY IN IT.
apiKey = "#GEMINI_API_KEY"

# Check if the API key is available
if not apiKey:
    print("❌ Error: API key is not set. Please paste your key in the apiKey variable.")
    exit()

# ---------------------- FALLBACK JOKES ----------------------
# A small list of pre-written jokes to use if the Gemini API call fails.
fallback_jokes = [
    "നിങ്ങളുടെ ജീവിതം Netflix subscription പോലെ — പലിശ ഇല്ലാതെ പോകുന്നു.",
    "സമയം അറിയാൻ ഇവിടെ വന്നോ, അല്ലെങ്കിൽ എൻ്റെ തമാശ കേൾക്കാനോ?",
    "ഇവിടെ സമയം നോക്കി ഇരിക്കാതെ പോയി വിശ്രമിക്ക്. അല്ലെങ്കിൽ, അത് നിങ്ങൾക്ക് ഇഷ്ടമല്ലെങ്കിൽ, നിങ്ങൾക്ക് ജോലി ചെയ്യാം."
]


# ---------------------- JOKE GENERATION FUNCTION USING GEMINI API ----------------------
def get_gemini_joke(time_of_day, current_time_str):
    """
    Generates a sarcastic joke in Malayalam using the Gemini API based on the time of day.
    """
    prompt = ""
    if time_of_day == "morning":
        # The prompt is now more explicit about using the current time
        prompt = f"Create a short, sarcastic joke in Malayalam about the current time, which is {current_time_str}. The joke should be about a person starting their morning as if they are lazy. Respond with only the joke text in Malayalam."
    elif time_of_day == "afternoon":
        # The prompt is now more explicit about using the current time
        prompt = f"Create a short, sarcastic joke in Malayalam about the current time, which is {current_time_str}. The joke should be about a person being bored while working in the afternoon. Respond with only the joke text in Malayalam."
    else:  # evening/night
        # The prompt is now more explicit about using the current time
        prompt = f"Create a short, sarcastic joke in Malayalam about the current time, which is {current_time_str}. The joke should be about a person being idle in the evening or night. Respond with only the joke text in Malayalam."

    # Gemini API payload
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}]
    }
    
    # Using the gemini-2.5-flash-preview-05-20 model for fast response
    apiUrl = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={apiKey}"

    try:
        # Send the request to the Gemini API
        # Increased the timeout to 30 seconds to prevent Read timed out errors
        response = requests.post(apiUrl, json=payload, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        
        # Parse the JSON response
        result = response.json()
        
        # Extract the text from the response
        generated_text = result.get('candidates')[0].get('content').get('parts')[0].get('text')
        
        # Clean up any potential extra formatting that might have slipped through
        generated_text = generated_text.replace('**', '').replace('"', '').strip()
        
        return generated_text
    
    except requests.exceptions.RequestException as e:
        # Print a more detailed error message
        print(f"❌ Error calling Gemini API: {e}")
        return random.choice(fallback_jokes)
    except (KeyError, IndexError, TypeError) as e:
        print(f"❌ Unexpected API response format: {e}")
        return random.choice(fallback_jokes)

# ---------------------- SPEECH FUNCTION ----------------------
# A flag to prevent multiple jokes from being triggered at the same time
is_speaking = False

def speak(text):
    """
    Generates an audio file from the given text using gTTS and plays it.
    The audio file is saved temporarily and then deleted.
    """
    global is_speaking
    is_speaking = True  # Set the flag to true while speaking
    try:
        # Create a gTTS object with the specified text and language
        tts = gTTS(text=text, lang=LANG)
        tts.save("temp.mp3")  # Save the audio to a temporary file

        # Play the temporary audio file using the playsound library
        playsound("temp.mp3")

        # Remove the temporary audio file
        os.remove("temp.mp3")
    except Exception as e:
        # Print an error message if something goes wrong with the speech
        print("[❌] Error in speech:", e)
    finally:
        is_speaking = False  # Set the flag to false when done speaking

# ---------------------- JOKE THREADING FUNCTION ----------------------
def joke_thread_handler(time_of_day, current_time_str):
    """
    This function handles the joke generation and speaking in a separate thread.
    """
    global is_speaking
    if not is_speaking:
        message = get_gemini_joke(time_of_day, current_time_str)
        print(f"[👁️] Face detected. Saying: {message}")
        speak_thread(message)


def speak_thread(message):
    """
    Starts a new thread to run the speak function.
    This is important so the webcam feed doesn't freeze while the joke is being spoken.
    """
    th = threading.Thread(target=speak, args=(message,))
    th.start()

# ---------------------- INITIALIZE ----------------------
# Initialize the video capture (webcam) and the face detection classifier
cap = cv2.VideoCapture(CAM_INDEX)

# Corrected typo in the cascade file name
cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cascade_path)

# Check if the cascade classifier was loaded successfully
if face_cascade.empty():
    print(f"❌ Error: Could not load face cascade classifier from '{cascade_path}'.")
    exit()

print("🔧 Talking Clock is running... Press 'Q' to quit.")

# Variables to track the state of face detection
last_joke_time = 0  # New variable to track when the last joke was spoken
speak_count = 0

# ---------------------- MAIN LOOP ----------------------
while True:
    # Read a frame from the webcam
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to read from webcam.")
        break

    # Convert the frame to grayscale for face detection
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Detect faces in the grayscale frame
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    # Get the current time and format it
    now = datetime.now()
    current_time_str = now.strftime("%I:%M:%S %p")

    # Determine the time of day
    current_hour = now.hour
    time_of_day_str = "evening"
    if 5 <= current_hour < 12:
        time_of_day_str = "morning"
    elif 12 <= current_hour < 17:
        time_of_day_str = "afternoon"

    # FACE DETECTION LOGIC
    if len(faces) > 0:
        # If a face is detected and a joke is not currently speaking, and the cooldown has passed
        if (time.time() - last_joke_time) > JOKE_COOLDOWN:
            speak_count += 1
            # Start a new thread to handle the joke generation and speech
            joke_thread = threading.Thread(target=joke_thread_handler, args=(time_of_day_str, current_time_str))
            joke_thread.start()
            last_joke_time = time.time()  # Update the time the last joke was spoken
    
    # DISPLAY CLOCK + CAMERA
    # Draw a green rectangle around each detected face
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Put the current time text on the frame
    cv2.putText(frame, current_time_str, (10, 40), cv2.FONT_HERSHEY_SIMPLEX,
                1, (255, 255, 255), 2, cv2.LINE_AA)

    # Show the video feed with the clock and face detection
    cv2.imshow("🕰️ Talking Clock - Look at me!", frame)

    # Break the loop if the user presses 'q'. This is the kill switch.
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Clean up: release the webcam and destroy all OpenCV windows
cap.release()
cv2.destroyAllWindows()

