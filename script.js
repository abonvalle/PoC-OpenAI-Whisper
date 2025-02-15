const recordButton = document.getElementById("recordButton");
const stopRecordButton = document.getElementById("stopRecordButton");
const uploadFileButton = document.getElementById("uploadFileButton");
const protocolSelect = document.getElementById("protocolSelect");
stopRecordButton.style.display = "none";
const textOutput = document.getElementById("textOutput");
const durationTxt = document.getElementById("duration");

let isRecording = false;
const apiURL = "localhost:5000";
let mediaRecorder;
let socket;

function startRecording() {
  isRecording = true;
  uploadFileButton.disabled = true;
  recordButton.style.display = "none";
  stopRecordButton.style.display = "block";
  protocolSelect.disabled = true;
  if (protocolSelect.value === "websocket") {
    this.connectToSocket(
      () =>
        this.recordMicrophone(1000, (audioChunk) => {
          socket.send(audioChunk);
        }),
      (result) => displayResult(result)
    );
  } else {
    this.recordMicrophone(1000, undefined, async (audioChunks) => {
      const result = await sendThroughHTTP(audioChunks, mediaRecorder.mimeType);
      displayResult(result, true);
    });
  }
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
  uploadFileButton.disabled = false;
}

function connectToSocket(connexionCallback, transcriptionCallback) {
  socket = new WebSocket(`ws://${apiURL}`);

  socket.addEventListener("open", () => {
    console.log("Connected to websocket");
    connexionCallback();
  });

  socket.addEventListener("message", (message) =>
    transcriptionCallback(message.data)
  );
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

async function sendThroughHTTP(audioChunks, mimeType) {
  const audioBlob = new Blob(audioChunks, {
    type: mimeType,
  });
  const formData = new FormData();
  formData.append("file", audioBlob, `recording.${mimeType.split("/")[1]}`);

  const response = await fetch(`http://${apiURL}/transcribe`, {
    method: "POST",
    body: formData,
  });

  return await response.json();
}

function uploadFile() {
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "audio/*";
  fileInput.click();

  fileInput.addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (protocolSelect.value === "websocket") {
      this.connectToSocket(
        () => {
          readFile(file, (chunk) => {
            socket.send(chunk);
          });
        },
        (result) => displayResult(result)
      );
    } else {
      const chunks = [];
      // readFile(
      //   file,
      //   (chunk) => {
      //     chunks.push(chunk);
      //   },
      //   async () => {
      //     const result = await sendThroughHTTP(chunks, file.type);
      //     displayResult(result, true);
      //   }
      // );
      const result = await sendThroughHTTP([file], file.type);
      displayResult(result, true);
    }
  });
}

function displayResult(result, clear = false) {
  textOutput.textContent = clear
    ? result.transcription
    : `${textOutput.textContent} ${result.transcription}`;
  durationTxt.textContent = result.duration;
}

function readFile(file, onloadCallback, onendCallback = () => {}) {
  if (file) {
    const chunkSize = 64 * 1024; // 64 KB chunks
    const fileReader = new FileReader();
    let offset = 0;

    fileReader.onload = function (e) {
      const chunk = e.target.result;
      onloadCallback(chunk);
      offset += chunk.byteLength;

      if (offset < file.size) {
        readSlice(offset);
      } else {
        onendCallback();
      }
    };

    function readSlice(o) {
      const slice = file.slice(offset, o + chunkSize);
      fileReader.readAsArrayBuffer(slice);
    }

    readSlice(0);
  }
}
