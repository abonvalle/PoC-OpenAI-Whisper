import numpy as np
import sounddevice as sd
import os
import scipy.io.wavfile as wav
import tempfile
import time
import torch
import tempfile
from fastapi import FastAPI, UploadFile, WebSocket, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
import whisper
import shutil

modelsType = Literal['tiny.en', 'tiny', 'base.en', 'base', 'small.en', 'small', 'medium.en', 'medium', 'large-v1', 'large-v2', 'large-v3', 'large', 'large-v3-turbo', 'turbo']
global model
model= whisper.load_model("turbo") 
app = FastAPI()
handled_audio_types=["audio/wav","audio/webm"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/transcribe')
def http_transcribe(file: UploadFile,x_audio_type: str = Header(None)):
    if file.filename == '':
        return "No selected file", 400
    print(x_audio_type[:x_audio_type.find(";")])
    try:
        audio_type=audio_type_from_mime(x_audio_type[:x_audio_type.find(";")])
    except ValueError as e:
        return "Unsupported audio type", 400
    print("Converting audio...")
    with tempfile.NamedTemporaryFile(delete=True, suffix="."+audio_type) as temp_input_audio:
        shutil.copyfileobj(file.file, temp_input_audio)
        temp_input_audio.flush()  # Ensure all data is written
        result = transcribe_audio(temp_input_audio.name)
        return ({"message": "Success", "transcription": result["transcription"], "duration": result["duration"]})

# Store metadata globally or in a class if using multiple connections
metadata_cache:bytes = None

async def ws_handler(data: bytes, is_first_chunk: bool, audio_type: str):
    global metadata_cache
    
    # If this is the first chunk, extract the metadata
    if is_first_chunk:
        # Create a temporary file for the first chunk
        with tempfile.NamedTemporaryFile(delete=True, suffix="."+audio_type) as temp_audio:
            temp_audio.write(data)
            temp_audio.flush()

            # Read the first chunk to extract metadata
            with open(temp_audio.name, "rb") as f:
                first_chunk = f.read()
                metadata_end = find_metadata_end(first_chunk,audio_type)
                metadata_cache = first_chunk[:metadata_end]

    # Prepend metadata to subsequent chunks
    if not is_first_chunk and metadata_cache:
        data = metadata_cache + data

    # Continue with audio processing
    with tempfile.NamedTemporaryFile(delete=True, suffix="."+audio_type) as temp_audio:
        temp_audio.write(data)
        temp_audio.flush()
        transcription_result = transcribe_audio(temp_audio.name)
    return {"message": "Success", "transcription": transcription_result["transcription"], "duration": transcription_result["duration"]}

def audio_type_from_mime(mime_type: str) -> str:
    if mime_type not in handled_audio_types:
        raise ValueError("Unsupported audio type")
    
    if mime_type == "audio/webm":
        return "webm"
    elif mime_type == "audio/wav":
        return "wav"
    
    raise ValueError("Unsupported audio type")

def find_metadata_end(data: bytes, audio_type:str) -> int:
    if audio_type == "webm":
        # WebM Cluster ID: 0x1F 0x43 0xB6 0x75
        cluster_id = b'\x1F\x43\xB6\x75'
        cluster_offset=0
    elif audio_type == "wav":
        # WAV Data Chunk ID: "data"
        cluster_id = b'data'
        cluster_offset=8
        
    cluster_index = data.find(cluster_id)

    # If Cluster ID is found, return its position
    if cluster_index != -1:
        return cluster_index + cluster_offset
    
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
    has_audio_type = False
    firstChunk = True
    while True:
        data = await websocket.receive();
        if has_audio_type == False:
            audio_type = audio_type_from_mime(data.get("text"))
            has_audio_type = True
            continue
            
        res = await ws_handler(data.get("bytes"),firstChunk,audio_type)
        firstChunk = False
        await websocket.send_json(res)
