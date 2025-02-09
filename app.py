import whisper 
import sounddevice as sd
import os
import scipy.io.wavfile as wav
from flask import Flask, request, jsonify
import tempfile
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 


# print(whisper.available_models())

# Availables models are ['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'large-v3-turbo', 'turbo']
model = whisper.load_model("base") 



@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'file' not in request.files:
        return "No file part", 400
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file", 400
    
    print("Transcribing...")

    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_audio:
        file.save(temp_audio.name)  # Save uploaded file
        temp_audio.flush()  # Ensure all data is written
        result = model.transcribe(temp_audio.name)  # Pass file path to model

    print(result["text"])
    return jsonify({"message": "Success", "transcription": result["text"]})


    
def transcribeFile(file):
    print("Transcribing...")
    result = model.transcribe(file) 
    print(result["text"])

def record_microphone():
    fs = 44100  # Sample rate
    seconds = 10  # Duration of recording

    print("Recording...")
    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=2, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording finished")

    wav_file = "output.wav"
    wav.write(wav_file, fs, recording)

    transcribeFile(wav_file)
    os.remove(wav_file)
    

