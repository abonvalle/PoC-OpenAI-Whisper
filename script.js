const recordButton = document.getElementById("recordButton");
const stopRecordButton = document.getElementById("stopRecordButton");
const protocolSelect = document.getElementById("protocolSelect");
stopRecordButton.style.display = "none";
const textOutput = document.getElementById("textOutput");
const durationTxt = document.getElementById("duration");

let isRecording = false;
const apiURL = "http://localhost:5000";
let mediaRecorder;
let socket;

function startRecording() {
  isRecording = true;
  if (protocolSelect.value === "websocket") {
    this.connectToSocket();
    this.recordMicrophone(1000, (audioChunk) => {
      socket.send(audioChunk);
    });
  } else {
    this.recordMicrophone(1000, undefined, async (audioChunks) => {
      const audioBlob = new Blob(audioChunks, {
        type: mediaRecorder.mimeType,
      });
      const formData = new FormData();
      formData.append(
        "file",
        audioBlob,
        `recording.${mediaRecorder.mimeType.split("/")[1]}`
      );

      const response = await fetch(`${apiURL}/transcribe`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();
      textOutput.textContent = `${textOutput.textContent} ${result.transcription}`;
      durationTxt.textContent = result.duration;
    });
  }
  recordButton.style.display = "none";
  stopRecordButton.style.display = "block";
  protocolSelect.disabled = true;
}

function stopRecording() {
  mediaRecorder.stop();
  if (protocolSelect.value === "websocket") {
    this.closeConnectSocket();
  } else {
  }
  isRecording = false;
  recordButton.style.display = "block";
  stopRecordButton.style.display = "none";
  protocolSelect.disabled = false;
}

function connectToSocket() {
  socket = new WebSocket(`ws://${apiURL}`);

  socket.addEventListener("connect", function () {
    console.log("Connected to the server");
  });

  socket.addEventListener("transcription", function (result) {
    durationTxt.textContent = result.duration;
    textOutput.textContent = `${textOutput.textContent} ${result.transcription}`;
  });
}

function closeConnectSocket() {
  socket.close();
}

async function recordAndSendToWebSocket() {}

async function recordMicrophone(timeslice = 1000, ondataavailable, onstop) {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Your browser does not support audio recording.");
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  });
  mediaRecorder = new MediaRecorder(stream);
  const audioChunks = [];

  mediaRecorder.ondataavailable = (event) => {
    ondataavailable(event.data);
    audioChunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    onstop(audioChunks);
  };

  mediaRecorder.start(timeslice);
}
