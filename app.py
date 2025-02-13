import whisper 
import sounddevice as sd
import os
import scipy.io.wavfile as wav
from flask import Flask, request, jsonify
import tempfile
import subprocess
from flask_cors import CORS
from typing import Literal
import argparse

app = Flask(__name__)
CORS(app) 

modelsType = Literal['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'large-v3-turbo', 'turbo']
# print(whisper.available_models())

# Availables models are ['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'large-v3-turbo', 'turbo']

# TODO : Add CLI record and websocket record 

@app.route('/transcribe', methods=['POST'])
def http_transcribe():
    if 'file' not in request.files:
        return "No file part", 400
    
    file = request.files['file']
    
    if file.filename == '':
        return "No selected file", 400
    
    print("Converting audio...")

    with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_input_audio:
        file.save(temp_input_audio.name)  # Save uploaded WebM file
        temp_input_audio.flush()  # Ensure all data is written
        
        # Convert to 16 kHz mono WAV using ffmpeg
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_output_audio:
            # Build ffmpeg command
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", temp_input_audio.name,  # Input file
                "-ac", "1",                  # Convert to mono
                "-ar", "16000",              # Set sample rate to 16 kHz
                "-y",                        # Overwrite output if exists
                "-loglevel", "error",        # Suppress verbose output
                "-nostats",                  # Disable progress statistics
                temp_output_audio.name       # Output file
            ]
            
            # Run ffmpeg command
            subprocess.run(ffmpeg_cmd, check=True)
            
            # Pass converted file to Whisper model
            result = transcribeFile(temp_output_audio.name)
    return jsonify({"message": "Success", "transcription": result})


    
def transcribeFile(file,model:modelsType="base"):
    model = whisper.load_model(model) 
    print("Transcribing...")
    result = model.transcribe(file, language='fr', task='transcribe') 
    print(result["text"])
    return result["text"]

def cli_transcribe(max_duration_in_seconds = 20):
    fs = 44100  # Sample rate

    print("Recording...")
    recording = sd.rec(int(max_duration_in_seconds * fs), samplerate=fs, channels=2, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording finished")

    wav_file = "output.wav"
    wav.write(wav_file, fs, recording)

    transcribeFile(wav_file)
    os.remove(wav_file)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration","-d", type=int,default=20, help="The duration of the recording in seconds")
    args = parser.parse_args()
    
    cli_transcribe(args.duration)