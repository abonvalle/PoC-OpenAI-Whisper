const recordButton = document.getElementById("recordButton");
const stopRecordButton = document.getElementById("stopRecordButton");
stopRecordButton.style.display = "none";
const textOutput = document.getElementById("textOutput");
let isRecording = false;

recordButton.addEventListener("click", () => {
  isRecording = true;
  record();
  recordButton.style.display = "none";
  stopRecordButton.style.display = "block";
});

async function record() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Your browser does not support audio recording.");
    return;
  }

  textOutput.textContent = "Recording...";
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  });
  const mediaRecorder = new MediaRecorder(stream);
  const audioChunks = [];

  mediaRecorder.ondataavailable = (event) => {
    audioChunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    const audioBlob = new Blob(audioChunks, {
      type: mediaRecorder.mimeType,
    });
    const formData = new FormData();
    formData.append(
      "file",
      audioBlob,
      `recording.${mediaRecorder.mimeType.split("/")[1]}`
    );
    textOutput.textContent = "Waiting for transcription...";

    const response = await fetch("http://localhost:5000/transcribe", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();
    console.log(result);
    textOutput.textContent = result.transcription;
  };

  mediaRecorder.start();

  stopRecordButton.addEventListener("click", () => {
    mediaRecorder.stop();
    isRecording = false;
    recordButton.style.display = "block";
    stopRecordButton.style.display = "none";
  });
}
