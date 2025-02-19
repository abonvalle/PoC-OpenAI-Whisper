# Audio Transcription PoC 🎤 → 📝

A simple Proof of Concept (PoC) application that records audio from the microphone in a web front-end, sends it to a Flask API, and transcribes it using OpenAI's Whisper model.

## 📌 Features

- Record audio directly from the browser
- Send recorded audio to a Flask backend
- Use OpenAI Whisper for speech-to-text transcription
- Display the transcribed text in the UI

## 📦 Tech Stack

- Frontend: JavaScript (Vanilla JS) + HTML + CSS
- Backend: Python + Flask
- Transcription Model: OpenAI Whisper
- Audio Processing: ffmpeg

## 🚀 Setup & Installation

### 1️⃣ Install Backend Dependencies

Make sure you have Python 3.8+ installed.

#### 1. Clone the repository

```sh
git clone https://github.com/abonvalle/PoC-OpenAI-Whisper.git
cd PoC-OpenAI-Whisper
```

#### 2. Create a virtual environment (optional but recommended)

```sh
python -m venv .poc_openai_whisper_env
source .poc_openai_whisper_env/bin/activate # On Windows: .poc_openai_whisper_env\Scripts\activate
```

#### 3. Install Python dependencies

```sh
pip install -r requirements.txt
```

#### 4. Install ffmpeg (Required for audio processing)

Linux (Ubuntu/Debian):

```sh
sudo apt install ffmpeg
```

macOS:

```sh
brew install ffmpeg
```

Windows (Chocolatey):

```sh
choco install ffmpeg
```

---

### 2️⃣ Run the Flask Backend

#### 1. Set environment variables for Flask (first time only to enable debug mode and set the app entry point):

```sh
export FLASK_APP=app
export FLASK_ENV=development
```

---

#### 2. Run Flask

```sh
flask run
```

The API should now be running at: http://localhost:5000

---

### 3️⃣ Run the Frontend

Simply open index.html in a browser (Chrome recommended).

## 🛠️ API Endpoints

### 🎙️ Transcribe Audio

#### Endpoint:

```sh
POST /transcribe
```

#### Request:

- Content-Type: multipart/form-data
- Body:
  - file: The recorded audio file (WebM/WAV)

#### Response (JSON):

```json
{
  "message": "Success",
  "transcription": "Hello, this is a test transcription."
}
```

## 📜 Project Structure

```sh
/PoC-OpenAI-Whisper
│── index.html # Main UI
│── script.js # Handles recording & API calls
│── app.py # Flask application
└── requirements.txt # Python dependencies
```

# TODO : update readme with fastapi

fastapi dev app.py --port 5000;
