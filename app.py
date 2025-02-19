import sounddevice as sd
import os
import scipy.io.wavfile as wav
import tempfile
import subprocess
import argparse
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
            result = transcribe_file(temp_output_audio.name)
    return ({"message": "Success", "transcription": result["transcription"], "duration": result["duration"]})

async def ws_handler(websocket):
    audio_buffer = b""
    async for message in websocket:
        # Accumulate audio chunks
        audio_buffer += message

        # Process the audio buffer (you might want to handle this in a separate task)
        transcription_result = transcribe_file(audio_buffer)

        # Send the transcription result back to the client
        await websocket.send(({"message": "Success", "transcription": transcription_result["transcription"], "duration": transcription_result["duration"]}))

        # Optionally, clear the buffer after processing
        audio_buffer = b""

# audio_buffer = []
# # @socketio.on('transcribe')
# async def ws_handler(websocket):
#     while True:
#         message = await websocket.recv()
#         print("Received audio chunk")

#         # Save chunk temporarily
#         with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as temp_audio:
#             temp_audio.write(message)
#             temp_audio.flush()

#             # Convert to wav
#             with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
#                 os.system(f"ffmpeg -i {temp_audio.name} -ac 1 -ar 16000 -y -loglevel error -nostats {temp_wav.name}")
#                 # ffmpeg_cmd = [
#                 #     "ffmpeg",
#                 #     "-i", temp_audio.name,  # Input file
#                 #     "-ac", "1",                  # Convert to mono
#                 #     "-ar", "16000",              # Set sample rate to 16 kHz
#                 #     "-y",                        # Overwrite output if exists
#                 #     "-loglevel", "error",        # Suppress verbose output
#                 #     "-nostats",                  # Disable progress statistics
#                 #     temp_wav.name       # Output file
#                 # ]

#                 # # Run ffmpeg command
#                 # subprocess.run(ffmpeg_cmd, check=True)

#                 # Load and buffer the audio
#                 chunk = AudioSegment.from_wav(temp_wav)
#                 audio_buffer.append(chunk)import whisper

#             # Check if it's time to transcribe
#             if len(audio_buffer) >= 3:  # For example, every 3 chunks
#                 joined_audio = sum(audio_buffer)

#                 # Detect natural silence points
#                 silence_thresh = -40  # Adjust as needed
#                 min_silence_len = 500  # 0.5 seconds
#                 chunks = silence.split_on_silence(joined_audio, min_silence_len=min_silence_len, silence_thresh=silence_thresh)

#                 # Only transcribe if there's at least one chunk
#                 if chunks:
#                     # Join chunks into a single audio segment
#                     final_audio = sum(chunks)
#                     with tempfile.NamedTemporaryFile(delete=True, suffix=".wav") as final_wav:
#                         final_audio.export(final_wav.name, format="wav")
#                         transcription = transcribeFile(final_wav.name)

#                         # Send transcription back to client
#                         await websocket.send(jsonify(transcription))

#                 # Clear the buffer after processing
#                 audio_buffer.clear()

def transcribe_file(file):
    print("Transcribing...")
    start = time.time()
    transcription = model.transcribe(file, language='fr', task='transcribe') 
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

    transcribe_file(wav_file)
    os.remove(wav_file)
    
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")
