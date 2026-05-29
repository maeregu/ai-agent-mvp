const API_BASE = "http://127.0.0.1:8000";

const uploadForm = document.querySelector("#uploadForm");
const fileInput = document.querySelector("#fileInput");
const targetLanguage = document.querySelector("#targetLanguage");
const clipDuration = document.querySelector("#clipDuration");
const clipCount = document.querySelector("#clipCount");
const submitButton = document.querySelector("#submitButton");
const statusText = document.querySelector("#statusText");
const errorBox = document.querySelector("#errorBox");
const highlightBox = document.querySelector("#highlightBox");
const clipLinks = document.querySelector("#clipLinks");
const transcriptOutput = document.querySelector("#transcriptOutput");
const translationOutput = document.querySelector("#translationOutput");
const downloadLink = document.querySelector("#downloadLink");
const shortVideoLink = document.querySelector("#shortVideoLink");

let pollTimer = null;

function setError(message) {
  errorBox.textContent = message || "";
  errorBox.classList.toggle("hidden", !message);
}

function setDownload(url) {
  if (!url) {
    downloadLink.classList.add("hidden");
    downloadLink.href = "#";
    return;
  }
  downloadLink.href = `${API_BASE}${url}`;
  downloadLink.classList.remove("hidden");
}

function setHighlight(job) {
  if (!job.highlights || job.highlights.length === 0) {
    highlightBox.textContent = "";
    highlightBox.classList.add("hidden");
    return;
  }
  const lines = job.highlights.map((highlight, index) => {
    const start = Number(highlight.start).toFixed(1);
    const end = Number(highlight.end).toFixed(1);
    const reason = highlight.reason || "Selected highlight";
    return `Clip ${index + 1}: ${start}s to ${end}s. ${reason}`;
  });
  highlightBox.textContent = lines.join("\n");
  highlightBox.classList.remove("hidden");
}

function setShortVideo(url) {
  if (!url) {
    shortVideoLink.classList.add("hidden");
    shortVideoLink.href = "#";
    return;
  }
  shortVideoLink.href = `${API_BASE}${url}`;
  shortVideoLink.classList.remove("hidden");
}

function setClipLinks(urls) {
  clipLinks.innerHTML = "";
  if (!urls || urls.length === 0) {
    clipLinks.classList.add("hidden");
    return;
  }
  urls.forEach((url, index) => {
    const link = document.createElement("a");
    link.href = `${API_BASE}${url}`;
    link.target = "_blank";
    link.textContent = `Download clip ${index + 1}`;
    clipLinks.appendChild(link);
  });
  clipLinks.classList.remove("hidden");
}

function renderJob(job) {
  statusText.textContent =
    job.status === "processing"
      ? `${job.progress || 0}% - ${job.progress_message || "Processing"}`
      : job.status;
  transcriptOutput.value = job.transcript || "";
  translationOutput.value =
    job.translation || (job.error && job.transcript ? "Translation failed. Transcript is still available above." : "");
  setDownload(job.download_url);
  setShortVideo(job.short_video_url);
  setClipLinks(job.short_video_urls);
  setHighlight(job);
  setError(job.error);

  const isRunning = job.status === "queued" || job.status === "processing";
  submitButton.disabled = isRunning;
  submitButton.textContent = isRunning ? "Processing..." : "Start transcription";
}

async function fetchJob(jobId) {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error("Could not fetch job status.");
  }
  return response.json();
}

function startPolling(jobId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const job = await fetchJob(jobId);
      renderJob(job);
      if (job.status === "completed" || job.status === "failed") {
        clearInterval(pollTimer);
      }
    } catch (error) {
      clearInterval(pollTimer);
      submitButton.disabled = false;
      submitButton.textContent = "Start transcription";
      setError(error.message);
    }
  }, 1500);
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setError("");
  setDownload("");
  setShortVideo("");
  setClipLinks([]);
  highlightBox.textContent = "";
  highlightBox.classList.add("hidden");
  transcriptOutput.value = "";
  translationOutput.value = "";
  statusText.textContent = "Uploading";

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("target_language", targetLanguage.value);
  formData.append("clip_duration_seconds", clipDuration.value);
  formData.append("clip_count", clipCount.value);

  submitButton.disabled = true;
  submitButton.textContent = "Uploading...";

  try {
    const response = await fetch(`${API_BASE}/uploads`, {
      method: "POST",
      body: formData,
    });
    const job = await response.json();
    if (!response.ok) {
      throw new Error(job.detail || "Upload failed.");
    }
    renderJob(job);
    startPolling(job.id);
  } catch (error) {
    submitButton.disabled = false;
    submitButton.textContent = "Start transcription";
    statusText.textContent = "Ready";
    setError(error.message);
  }
});
