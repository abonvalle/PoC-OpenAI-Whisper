import sounddevice as sd
import os
import scipy.io.wavfile as wav
from flask import Flask, request, jsonify
import tempfile
import subprocess
from flask_cors import CORS
import argparse
import time
import torch
from transformers import pipeline
import tempfile
import asyncio
from websockets.asyncio.server import serve

app = Flask(__name__)
CORS(app)

whisper = pipeline("automatic-speech-recognition", "openai/whisper-large-v3-turbo", torch_dtype=torch.float16,  device="cpu", batch_size=8)
torch.set_num_threads(16)  # Match the number of CPU cores
torch.set_num_interop_threads(16)
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
            result = transcribe_file(temp_output_audio.name)
    return jsonify({"message": "Success", "transcription": result["transcription"], "duration": result["duration"]})

async def ws_handler(websocket):
    audio_buffer = b""
    async for message in websocket:
        # Accumulate audio chunks
        audio_buffer += message

        # Process the audio buffer (you might want to handle this in a separate task)
        transcription_result = transcribe_file(audio_buffer)

        # Send the transcription result back to the client
        await websocket.send(jsonify({"message": "Success", "transcription": transcription_result["transcription"], "duration": transcription_result["duration"]}))

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
#                 audio_buffer.append(chunk)

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
    transcription = whisper(file, num_workers=16, batch_size=8)
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
    
# async def ws_handler(websocket):
#     while True:
#         message = await websocket.recv()
#         print(message)


async def ws_main():
    async with serve(ws_handler, "", 5000):
        await asyncio.get_running_loop().create_future()  # run forever

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode","-m", type=str, help="Whether to run the CLI, the HTTP server or the WebSocket server", choices=["cli","ws_server","http_server"], default="http_server")
    parser.add_argument("--duration","-d", type=int,default=20, help="The duration of the recording in seconds")
    args = parser.parse_args()
    if args.mode == "http_server":
        app.run()
    elif args.mode == "ws_server":
       asyncio.run(ws_main())
    elif args.mode == "cli":
        cli_transcribe(args.duration)