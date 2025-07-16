import os
import json
import re
import sqlite3
import struct
import subprocess
import time
import webbrowser
from playsound import playsound
import eel
import pyaudio
import pyautogui
import requests
from urllib.parse import quote  # quote import করা হচ্ছে

from api import SERPAPI_KEY  # শুধু SerpApi key
from engine.command import speak
from engine.config import ASSISTANT_NAME
from engine.helper import extract_yt_term, remove_words

# ডাটাবেজ কানেকশন
con = sqlite3.connect("jarvis.db")
cursor = con.cursor()

# commands.json ফাইলের path (root থেকে)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMANDS_FILE = os.path.join(BASE_DIR, "commands.json")

# commands.json থেকে ডাটা লোড
with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
    commands_dict = json.load(f)


@eel.expose
def playAssistantSound():
    audio_path = os.path.abspath("www/assets/audio/start_sound.mp3")
    audio_path = audio_path.replace('\\', '/')
    try:
        playsound(audio_path)
    except Exception as e:
        print("Sound play error:", e)


def openCommand(query):
    query = query.replace(ASSISTANT_NAME, "").replace("open", "").strip().lower()
    if not query:
        speak("Please specify what to open.")
        return

    full_command = "open " + query
    if full_command in commands_dict:
        cmd_or_url = commands_dict[full_command]
        try:
            if cmd_or_url.startswith("http"):
                speak(f"Opening {query}")
                webbrowser.open(cmd_or_url)
            else:
                speak(f"Opening {query}")
                os.system(cmd_or_url)
        except Exception as e:
            speak(f"Failed to open {query}")
            print("Open command error:", e)
        return

    speak(f"Command {query} not found.")


def PlayYoutube(query):
    search_term = extract_yt_term(query)
    speak("Playing " + search_term + " on YouTube")
    import pywhatkit as kit
    kit.playonyt(search_term)


def hotword():
    import pvporcupine
    porcupine = None
    paud = None
    audio_stream = None
    try:
        porcupine = pvporcupine.create(keywords=["jarvis", "alexa"])
        paud = pyaudio.PyAudio()
        audio_stream = paud.open(rate=porcupine.sample_rate, channels=1,
                                 format=pyaudio.paInt16, input=True, frames_per_buffer=porcupine.frame_length)
        while True:
            keyword = audio_stream.read(porcupine.frame_length)
            keyword = struct.unpack_from("h" * porcupine.frame_length, keyword)
            keyword_index = porcupine.process(keyword)
            if keyword_index >= 0:
                print("Hotword detected")
                pyautogui.keyDown("win")
                pyautogui.press("j")
                time.sleep(2)
                pyautogui.keyUp("win")
    except:
        if porcupine:
            porcupine.delete()
        if audio_stream:
            audio_stream.close()
        if paud:
            paud.terminate()


def findContact(query):
    words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to',
                       'phone', 'call', 'send', 'message', 'wahtsapp', 'video']
    query = remove_words(query, words_to_remove).strip().lower()
    try:
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?",
                       ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        mobile_number = str(results[0][0])
        if not mobile_number.startswith('+91'):
            mobile_number = '+91' + mobile_number
        return mobile_number, query
    except:
        speak('Contact does not exist')
        return 0, 0


def whatsApp(mobile_no, message, flag, name):
    if flag == 'message':
        target_tab = 12
        final_message = f"Message sent successfully to {name}"
    elif flag == 'call':
        target_tab = 7
        message = ''
        final_message = f"Calling {name}"
    else:
        target_tab = 6
        message = ''
        final_message = f"Starting video call with {name}"

    encoded_message = quote(message)
    whatsapp_url = f"whatsapp://send?phone={mobile_no}&text={encoded_message}"
    command = f'start "" "{whatsapp_url}"'
    subprocess.run(command, shell=True)
    time.sleep(5)
    subprocess.run(command, shell=True)

    pyautogui.hotkey('ctrl', 'f')
    for _ in range(1, target_tab):
        pyautogui.hotkey('tab')
    pyautogui.hotkey('enter')
    speak(final_message)


def chatBot(query):
    user_input = query.lower()
    if any(keyword in user_input for keyword in ["search", "google", "find", "look for"]):
        params = {
            "q": user_input,
            "api_key": SERPAPI_KEY,
            "engine": "google"
        }
        try:
            response = requests.get("https://serpapi.com/search", params=params)
            results = response.json()
            if "organic_results" in results and len(results["organic_results"]) > 0:
                top_result = results["organic_results"][0].get("snippet", "No results found.")
                speak(top_result)
                return top_result
            else:
                speak("No results found.")
                return "No results found"
        except Exception as e:
            speak("Search failed.")
            return str(e)
    else:
        speak("Please use search keywords like 'search', 'google', 'find', or 'look for'.")
        return "No valid search query."


def makeCall(name, mobileNo):
    mobileNo = mobileNo.replace(" ", "")
    speak(f"Calling {name}")
    command = 'adb shell am start -a android.intent.action.CALL -d tel:' + mobileNo
    os.system(command)


def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("Sending message...")
    goback(4)
    time.sleep(1)
    keyEvent(3)
    tapEvents(136, 2220)
    tapEvents(819, 2192)
    adbInput(mobileNo)
    tapEvents(601, 574)
    tapEvents(390, 2270)
    adbInput(message)
    tapEvents(957, 1397)
    speak(f"Message sent successfully to {name}")
