import sounddevice as sd
import os
import scipy.io.wavfile as wav
from flask import Flask, request, jsonify
import tempfile
import subprocess
from flask_cors import CORS
from typing import Literal
import argparse
import time
import torch
from transformers import pipeline
from flask_socketio import SocketIO
import tempfile
from pydub import AudioSegment, silence


app = Flask(__name__)
app.config['SECRET_KEY'] = 'whisper_websocket' 
socketio = SocketIO(app)
CORS(app) 

whisper = pipeline("automatic-speech-recognition", "openai/whisper-large-v3", torch_dtype=torch.float16, device="cuda:0")

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
            result = transcribeFile(temp_output_audio.name,model="base")
    return jsonify({"message": "Success", "transcription": result["transcription"], "duration": result["duration"]})

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('transcribe')
def handle_transcription(data):
    print("Received audio chunk")

    # Save chunk temporarily
    with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_audio:
        temp_audio.write(data)
        temp_audio.flush()

        # Convert to wav
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        os.system(f"ffmpeg -i {temp_audio.name} -ac 1 -ar 16000 -y {temp_wav.name}")

        # Load and buffer the audio
        chunk = AudioSegment.from_wav(temp_wav.name)
        audio_buffer.append(chunk)

    # Check if it's time to transcribe
    if len(audio_buffer) >= 3:  # For example, every 3 chunks
        joined_audio = sum(audio_buffer)

        # Detect natural silence points
        silence_thresh = -40  # Adjust as needed
        min_silence_len = 500  # 0.5 seconds
        chunks = silence.split_on_silence(joined_audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)

        # Only transcribe if there's at least one chunk
        if chunks:
            # Join chunks into a single audio segment
            final_audio = sum(chunks)
            with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as final_wav:
                final_audio.export(final_wav.name, format="wav")
                transcribeFile(final_wav.name)

                # Send transcription back to client
                socketio.emit('transcription', jsonify(transcription))

        # Clear the buffer after processing
        audio_buffer.clear()

def transcribeFile(file):
    print("Loading model...")
    model = whisper.load_model(model) 
    print("Transcribing...")
    start = time.time()
    transcription = whisper(file, language='fr', task='transcribe')
    end = time.time()
    print(transcription["text"])
    return {"transcription":transcription["text"],"duration":round(end-start,2)}

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
    socketio.run(app, debug=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration","-d", type=int,default=20, help="The duration of the recording in seconds")
    args = parser.parse_args()
    
    cli_transcribe(args.duration)