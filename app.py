import numpy as np
import sounddevice as sd
import os
import scipy.io.wavfile as wav
import tempfile
import subprocess
import time
import torch
import tempfile
from fastapi import FastAPI, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import whisper
import shutil

modelsType = Literal['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'large-v3-turbo', 'turbo']
global model
model= whisper.load_model("turbo") 
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/transcribe')
def http_transcribe(file: UploadFile):
    if file.filename == '':
        return "No selected file", 400
    
    print("Converting audio...")

    with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_input_audio:
        shutil.copyfileobj(file.file, temp_input_audio)
        # file.save(temp_input_audio.name)  # Save uploaded WebM file
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
            result = transcribe_audio(temp_output_audio.name)
    return ({"message": "Success", "transcription": result["transcription"], "duration": result["duration"]})

import tempfile
import subprocess

# Store metadata globally or in a class if using multiple connections
metadata_cache:bytes = None

async def ws_handler(data: bytes, is_first_chunk: bool):
    global metadata_cache
    
    # If this is the first chunk, extract the metadata
    if is_first_chunk:
        # Create a temporary file for the first chunk
        with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_audio:
            temp_audio.write(data)
            temp_audio.flush()

            # Read the first chunk to extract metadata
            with open(temp_audio.name, "rb") as f:
                first_chunk = f.read()
                metadata_end = find_metadata_end(first_chunk)
                metadata_cache = first_chunk[:metadata_end]

    # Prepend metadata to subsequent chunks
    if not is_first_chunk and metadata_cache:
        data = metadata_cache + data

    # Continue with audio processing
    with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_audio:
        temp_audio.write(data)
        temp_audio.flush()
        
        with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as temp_output_audio:
            # Build ffmpeg command
            ffmpeg_cmd = [
                "ffmpeg",
                "-i", temp_audio.name,  # Input file
                "-ac", "1",             # Convert to mono
                "-ar", "16000",         # Set sample rate to 16 kHz
                "-y",                   # Overwrite output if exists
                "-loglevel", "error",   # Suppress verbose output
                "-nostats",             # Disable progress statistics
                temp_output_audio.name  # Output file
            ]
            
            # Run ffmpeg command
            subprocess.run(ffmpeg_cmd, check=True)

            # Now, process the converted WAV file
            with open(temp_output_audio.name, "rb") as wav_file:
                # wav_data = wav_file.read()
                transcription_result = transcribe_audio(wav_file.name)
                return {"message": "Success", "transcription": transcription_result["transcription"], "duration": transcription_result["duration"]}
                # Do something with the WAV data, like sending it to another service


def find_metadata_end(data: bytes) -> int:
    # WebM Cluster ID: 0x1F 0x43 0xB6 0x75
    cluster_id = b'\x1F\x43\xB6\x75'
    cluster_index = data.find(cluster_id)

    # If Cluster ID is found, return its position
    if cluster_index != -1:
        return cluster_index
    
    # If Cluster ID is not found, assume the whole chunk is metadata
    return len(data)

def transcribe_audio(audio:str | np.ndarray | torch.Tensor):
    print("Transcribing...")
    start = time.time()
    transcription = model.transcribe(audio, language='fr', task='transcribe', fp16=torch.cuda.is_available()) 
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

    transcribe_audio(wav_file)
    os.remove(wav_file)
    
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    firstChunk = True
    while True:
        data = await websocket.receive_bytes()
        res = await ws_handler(data,firstChunk)
        firstChunk = False
        await websocket.send_json(res)
