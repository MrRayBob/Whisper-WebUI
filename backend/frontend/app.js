const panels = ["file", "youtube", "mic", "utilities"];
const state = {
  activePanel: "file",
  tasks: new Map(),
  latestResults: new Map(),
  mic: {
    stream: null,
    recorder: null,
    chunks: [],
    blob: null,
  },
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const TRANSCRIPTION_FIELDS = {
  basic: [
    {
      title: "Media",
      className: "grid basic",
      fields: [
        {
          kind: "file",
          name: "file",
          label: "Media file",
          accept: "audio/*,video/*",
          hint: "Upload one local file. The server generates the subtitle artifact for download.",
        },
        {
          kind: "select",
          name: "model_size",
          label: "Model",
          options: ["large-v2", "large-v3", "medium", "small", "base", "tiny"],
          value: "large-v2",
          hint: "Choose a lighter model if you want faster turnaround.",
        },
        {
          kind: "text",
          name: "lang",
          label: "Language code",
          placeholder: "auto",
          hint: "Leave blank for auto detection or enter a code like `en`.",
        },
        {
          kind: "checkbox",
          name: "is_translate",
          label: "Translate to English",
          hint: "Whisper's end-to-end translation mode.",
          value: false,
        },
        {
          kind: "select",
          name: "file_format",
          label: "Subtitle format",
          options: ["SRT", "WebVTT", "txt", "LRC"],
          value: "SRT",
          hint: "Choose the subtitle format before you queue the task.",
        },
        {
          kind: "checkbox",
          name: "add_timestamp",
          label: "Add timestamp to filename",
          hint: "Keeps output names unique.",
          value: true,
        },
      ],
    },
  ],
  advanced: [
    {
      title: "Whisper tuning",
      className: "grid tight",
      fields: [
        {
          kind: "select",
          name: "compute_type",
          label: "Compute type",
          options: ["float16", "float32", "int8", "int16"],
          value: "float16",
        },
        { kind: "number", name: "beam_size", label: "Beam size", value: 5, min: 1, step: 1 },
        { kind: "number", name: "best_of", label: "Best of", value: 5, min: 1, step: 1 },
        { kind: "number", name: "patience", label: "Patience", value: 1.0, min: 0.1, step: 0.1 },
        { kind: "number", name: "log_prob_threshold", label: "Log prob threshold", value: -1.0, step: 0.1 },
        { kind: "number", name: "no_speech_threshold", label: "No speech threshold", value: 0.6, min: 0, max: 1, step: 0.01 },
        {
          kind: "checkbox",
          name: "condition_on_previous_text",
          label: "Condition on previous text",
          value: true,
        },
        { kind: "number", name: "prompt_reset_on_temperature", label: "Prompt reset temperature", value: 0.5, min: 0, max: 1, step: 0.01 },
        { kind: "text", name: "initial_prompt", label: "Initial prompt", placeholder: "Optional hint text" },
        { kind: "number", name: "temperature", label: "Temperature", value: 0, min: 0, max: 1, step: 0.01 },
        { kind: "number", name: "compression_ratio_threshold", label: "Compression ratio threshold", value: 2.4, min: 0.1, step: 0.1 },
        { kind: "number", name: "length_penalty", label: "Length penalty", value: 1.0, min: 0.1, step: 0.1 },
        { kind: "number", name: "repetition_penalty", label: "Repetition penalty", value: 1.0, min: 0.1, step: 0.1 },
        { kind: "number", name: "no_repeat_ngram_size", label: "No repeat n-gram size", value: 0, min: 0, step: 1 },
        { kind: "text", name: "prefix", label: "Prefix", placeholder: "Optional prefix" },
        { kind: "checkbox", name: "suppress_blank", label: "Suppress blank", value: true },
        { kind: "text", name: "suppress_tokens", label: "Suppress tokens", placeholder: "[-1]", value: "[-1]" },
        { kind: "number", name: "max_initial_timestamp", label: "Max initial timestamp", value: 1.0, min: 0, step: 0.1 },
        { kind: "checkbox", name: "word_timestamps", label: "Word timestamps", value: false },
        { kind: "text", name: "prepend_punctuations", label: "Prepend punctuations", value: "\"'“¿([{-" },
        { kind: "text", name: "append_punctuations", label: "Append punctuations", value: "\"'.。,，!！?？:：”)]}、" },
        { kind: "number", name: "max_new_tokens", label: "Max new tokens", placeholder: "Leave blank", step: 1 },
        { kind: "number", name: "chunk_length", label: "Chunk length (s)", value: 30, min: 1, step: 1 },
        { kind: "number", name: "hallucination_silence_threshold", label: "Hallucination silence threshold", placeholder: "Leave blank", step: 0.1 },
        { kind: "text", name: "hotwords", label: "Hotwords", placeholder: "Optional keywords" },
        { kind: "number", name: "language_detection_threshold", label: "Language detection threshold", placeholder: "Leave blank", min: 0, max: 1, step: 0.01 },
        { kind: "number", name: "language_detection_segments", label: "Language detection segments", value: 1, min: 1, step: 1 },
        { kind: "number", name: "batch_size", label: "Batch size", value: 24, min: 1, step: 1 },
        {
          kind: "checkbox",
          name: "enable_offload",
          label: "Offload when finished",
          hint: "Shared offload flag for the current task.",
          value: true,
        },
      ],
    },
    {
      title: "Voice detection",
      className: "grid tight",
      fields: [
        { kind: "checkbox", name: "vad_filter", label: "Enable VAD", value: false },
        { kind: "number", name: "threshold", label: "Speech threshold", value: 0.5, min: 0, max: 1, step: 0.01 },
        { kind: "number", name: "min_speech_duration_ms", label: "Min speech duration (ms)", value: 250, min: 0, step: 1 },
        { kind: "number", name: "max_speech_duration_s", label: "Max speech duration (s)", placeholder: "Leave blank", step: 0.5 },
        { kind: "number", name: "min_silence_duration_ms", label: "Min silence duration (ms)", value: 2000, min: 0, step: 1 },
        { kind: "number", name: "speech_pad_ms", label: "Speech padding (ms)", value: 400, min: 0, step: 1 },
      ],
    },
    {
      title: "Background music",
      className: "grid tight",
      fields: [
        { kind: "checkbox", name: "is_separate_bgm", label: "Separate background music", value: false },
        {
          kind: "select",
          name: "uvr_model_size",
          label: "BGM model",
          options: ["UVR-MDX-NET-Inst_HQ_4", "UVR-MDX-NET-Inst_3"],
          value: "UVR-MDX-NET-Inst_HQ_4",
        },
        {
          kind: "select",
          name: "uvr_device",
          label: "BGM device",
          options: ["cpu", "cuda", "xpu", "mps"],
          value: "cpu",
        },
        { kind: "number", name: "segment_size", label: "Segment size", value: 256, min: 1, step: 1 },
        { kind: "checkbox", name: "save_file", label: "Save separated files", value: false },
      ],
    },
    {
      title: "Diarization",
      className: "grid tight",
      fields: [
        { kind: "checkbox", name: "is_diarize", label: "Enable diarization", value: false },
        {
          kind: "select",
          name: "diarization_device",
          label: "Diarization device",
          options: ["cpu", "cuda", "xpu", "mps"],
          value: "cpu",
        },
        { kind: "text", name: "hf_token", label: "Hugging Face token", placeholder: "Only needed for model download" },
      ],
    },
  ],
  youtubeBasic: [
    {
      title: "Link",
      className: "grid basic",
      fields: [
        {
          kind: "text",
          inputType: "url",
          name: "url",
          label: "YouTube URL",
          placeholder: "https://www.youtube.com/watch?v=...",
          hint: "Paste the video URL you want to transcribe.",
        },
        {
          kind: "select",
          name: "model_size",
          label: "Model",
          options: ["large-v2", "large-v3", "medium", "small", "base", "tiny"],
          value: "large-v2",
          hint: "Choose a lighter model if you want faster turnaround.",
        },
        {
          kind: "text",
          name: "lang",
          label: "Language code",
          placeholder: "auto",
          hint: "Leave blank for auto detection or enter a code like `en`.",
        },
        {
          kind: "checkbox",
          name: "is_translate",
          label: "Translate to English",
          hint: "Whisper's end-to-end translation mode.",
          value: false,
        },
        {
          kind: "select",
          name: "file_format",
          label: "Subtitle format",
          options: ["SRT", "WebVTT", "txt", "LRC"],
          value: "SRT",
          hint: "Choose the subtitle format before you queue the task.",
        },
        {
          kind: "checkbox",
          name: "add_timestamp",
          label: "Add timestamp to filename",
          hint: "Keeps output names unique.",
          value: true,
        },
      ],
    },
  ],
  bgmBasic: [
    {
      title: "Input",
      className: "grid basic",
      fields: [
        {
          kind: "file",
          name: "file",
          label: "Audio or video file",
          accept: "audio/*,video/*",
          hint: "Upload one file to separate vocals from the instrumental track.",
        },
        {
          kind: "select",
          name: "uvr_model_size",
          label: "Model",
          options: ["UVR-MDX-NET-Inst_HQ_4", "UVR-MDX-NET-Inst_3"],
          value: "UVR-MDX-NET-Inst_HQ_4",
        },
        {
          kind: "select",
          name: "uvr_device",
          label: "Device",
          options: ["cpu", "cuda", "xpu", "mps"],
          value: "cpu",
        },
        { kind: "number", name: "segment_size", label: "Segment size", value: 256, min: 1, step: 1 },
        { kind: "checkbox", name: "save_file", label: "Save separated files", value: false },
      ],
    },
  ],
  bgmAdvanced: [
    {
      title: "Cleanup",
      className: "grid one",
      fields: [
        {
          kind: "checkbox",
          name: "enable_offload",
          label: "Offload when finished",
          hint: "Release memory after the separation job.",
          value: true,
        },
      ],
    },
  ],
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function panelKeyFromForm(form) {
  return form.dataset.job;
}

function formatTimestamp(seconds, format) {
  const total = Math.max(0, Number(seconds) || 0);
  const whole = Math.floor(total);
  const fraction = Math.round((total - whole) * 1000);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const secs = whole % 60;

  if (format === "vtt") {
    return `${pad(hours)}:${pad(minutes)}:${pad(secs)}.${pad(fraction, 3)}`;
  }

  if (format === "lrc") {
    const allMinutes = Math.floor(whole / 60);
    return `${pad(allMinutes)}:${pad(secs)}.${pad(Math.floor(fraction / 10), 2)}`;
  }

  return `${pad(hours)}:${pad(minutes)}:${pad(secs)},${pad(fraction, 3)}`;
}

function pad(value, size = 2) {
  return String(value).padStart(size, "0");
}

function titleCase(value) {
  return value
    .split(/[_-]/g)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function renderField(field) {
  if (field.kind === "checkbox") {
    const label = document.createElement("label");
    label.className = "toggle";

    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = field.name;
    input.checked = Boolean(field.value);

    const copy = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = field.label;
    copy.appendChild(strong);

    if (field.hint) {
      const hint = document.createElement("span");
      hint.textContent = field.hint;
      copy.appendChild(hint);
    }

    label.appendChild(input);
    label.appendChild(copy);
    return label;
  }

  const label = document.createElement("label");
  label.className = "field";

  const span = document.createElement("span");
  span.textContent = field.label;
  label.appendChild(span);

  let input;
  if (field.kind === "select") {
    input = document.createElement("select");
    for (const option of field.options || []) {
      const opt = document.createElement("option");
      opt.value = option;
      opt.textContent = option;
      input.appendChild(opt);
    }
    if (field.value !== undefined) {
      input.value = field.value;
    }
  } else if (field.kind === "textarea") {
    input = document.createElement("textarea");
    if (field.rows) {
      input.rows = field.rows;
    }
    if (field.value !== undefined) {
      input.value = field.value;
    }
  } else {
    input = document.createElement("input");
    input.type = field.kind === "file" ? "file" : field.kind === "number" ? "number" : field.inputType || "text";
    if (field.value !== undefined && field.kind !== "file") {
      input.value = field.value;
    }
  }

  input.name = field.name;
  if (field.placeholder) {
    input.placeholder = field.placeholder;
  }
  if (field.accept) {
    input.accept = field.accept;
  }
  if (field.min !== undefined) {
    input.min = field.min;
  }
  if (field.max !== undefined) {
    input.max = field.max;
  }
  if (field.step !== undefined) {
    input.step = field.step;
  }

  label.appendChild(input);

  if (field.hint) {
    const hint = document.createElement("small");
    hint.className = "hint";
    hint.textContent = field.hint;
    label.appendChild(hint);
  }

  return label;
}

function renderSchema(container, sections) {
  container.innerHTML = "";
  for (const section of sections) {
    const wrapper = document.createElement("section");
    wrapper.className = "stack";

    if (section.title) {
      const title = document.createElement("div");
      title.className = "section-title";
      title.textContent = section.title;
      wrapper.appendChild(title);
    }

    const grid = document.createElement("div");
    grid.className = section.className || "grid.one";
    for (const field of section.fields) {
      grid.appendChild(renderField(field));
    }
    wrapper.appendChild(grid);
    container.appendChild(wrapper);
  }
}

function collectParams(form) {
  const params = new URLSearchParams();

  for (const element of $$("input[name], select[name], textarea[name]", form)) {
    if (element.disabled || element.type === "file") {
      continue;
    }

    if (element.type === "checkbox") {
      params.set(element.name, element.checked ? "true" : "false");
      continue;
    }

    const value = element.value.trim();
    if (!value) {
      continue;
    }

    params.set(element.name, value);
  }

  return params;
}

function setPanelStatus(panel, message, meta = "") {
  const status = $(`[data-status="${panel}"]`);
  const metaNode = $(`[data-meta="${panel}"]`);
  if (status) {
    status.textContent = message;
  }
  if (metaNode) {
    metaNode.textContent = meta;
  }
}

function setProgress(panel, value) {
  const bar = $(`[data-progress="${panel}"]`);
  if (bar) {
    const clamped = Math.max(0, Math.min(1, value || 0));
    bar.style.width = `${Math.round(clamped * 100)}%`;
  }
}

function setPreview(panel, htmlOrNode) {
  const preview = $(`[data-preview="${panel}"]`);
  if (!preview) {
    return;
  }
  preview.innerHTML = "";
  if (typeof htmlOrNode === "string") {
    preview.innerHTML = htmlOrNode;
    return;
  }
  preview.appendChild(htmlOrNode);
}

function clearDownloads(panel) {
  const target = $(`[data-download="${panel}"]`);
  if (target) {
    target.innerHTML = "";
  }
}

function setDownload(panel, identifier, name) {
  clearDownloads(panel);
  const target = $(`[data-download="${panel}"]`);
  if (!target) {
    return;
  }

  const link = document.createElement("a");
  link.href = `/task/file/${identifier}`;
  link.download = name;
  link.textContent = `Download ${name}`;
  target.appendChild(link);
}

function renderSegmentsPreview(panel, segments) {
  const wrapper = document.createElement("div");
  wrapper.className = "stack";

  const summary = document.createElement("div");
  summary.className = "helper";
  summary.textContent = `${segments.length} segment${segments.length === 1 ? "" : "s"} completed.`;
  wrapper.appendChild(summary);

  const list = document.createElement("div");
  list.className = "stack";

  const maxSegments = 24;
  for (const segment of segments.slice(0, maxSegments)) {
    const row = document.createElement("div");
    row.className = "note-box";
    const time = `${formatTimestamp(segment.start || 0, "srt")} → ${formatTimestamp(segment.end || 0, "srt")}`;
    row.innerHTML = `<strong>${escapeHtml(time)}</strong><br>${escapeHtml(segment.text || "")}`;
    list.appendChild(row);
  }

  if (segments.length > maxSegments) {
    const more = document.createElement("div");
    more.className = "helper";
    more.textContent = `Showing the first ${maxSegments} segments only.`;
    list.appendChild(more);
  }

  wrapper.appendChild(list);
  return wrapper;
}

async function pollTask(panel, identifier) {
  if (state.tasks.has(panel)) {
    clearInterval(state.tasks.get(panel));
  }

  const interval = setInterval(async () => {
    try {
      const response = await fetch(`/task/${identifier}`);
      if (!response.ok) {
        throw new Error(`Task lookup failed (${response.status})`);
      }

      const task = await response.json();
      const progress = Number(task.progress ?? 0);
      const percent = progress > 1 ? progress / 100 : progress;
      setProgress(panel, percent);
      setPanelStatus(panel, titleCase(task.status), task.duration ? `${Math.round(task.duration)}s` : "");

      if (task.status === "failed" || task.status === "cancelled") {
        clearInterval(interval);
        state.tasks.delete(panel);
        setPanelStatus(panel, "Failed", task.error || "The job did not complete.");
        setPreview(panel, `<div class="helper error">${escapeHtml(task.error || "The task failed.")}</div>`);
        return;
      }

      if (task.status !== "completed") {
        return;
      }

      clearInterval(interval);
      state.tasks.delete(panel);
      setProgress(panel, 1);

      if (panel === "bgm") {
        setPanelStatus(panel, "Completed", task.duration ? `${Math.round(task.duration)}s` : "");
        const preview = document.createElement("div");
        preview.className = "stack";
        preview.innerHTML = `
          <div class="helper">Background music separation finished. Download the archive below.</div>
          <div class="note-box">
            <strong>Instrumental hash</strong><br>${escapeHtml(task.result?.instrumental_hash || "n/a")}
          </div>
          <div class="note-box">
            <strong>Vocal hash</strong><br>${escapeHtml(task.result?.vocal_hash || "n/a")}
          </div>
        `;
        setPreview(panel, preview);
        const download = $(`[data-download="${panel}"]`);
        if (download) {
          download.innerHTML = "";
          const link = document.createElement("a");
          link.href = `/task/file/${identifier}`;
          link.textContent = "Download ZIP";
          link.setAttribute("download", "");
          download.appendChild(link);
        }
        return;
      }

      const segments = Array.isArray(task.result?.segments) ? task.result.segments : [];
      const output = task.result?.output || null;
      state.latestResults.set(panel, segments);
      const meta = [task.duration ? `${Math.round(task.duration)}s` : "", output?.filename || ""]
        .filter(Boolean)
        .join(" · ");
      setPanelStatus(panel, "Completed", meta);
      setPreview(panel, renderSegmentsPreview(panel, segments));
      if (output?.filename) {
        setDownload(panel, identifier, output.filename);
      }
    } catch (error) {
      clearInterval(interval);
      state.tasks.delete(panel);
      setPanelStatus(panel, "Error", "");
      setPreview(panel, `<div class="helper error">${escapeHtml(error.message)}</div>`);
    }
  }, 1500);

  state.tasks.set(panel, interval);
}

async function submitTranscription(form, panel) {
  const query = collectParams(form);
  const requestOptions = { method: "POST" };

  if (panel === "mic") {
    const body = new FormData();
    if (!state.mic.blob) {
      throw new Error("Record audio before submitting the mic form.");
    }
    body.append("file", new File([state.mic.blob], "recording.webm", { type: state.mic.blob.type || "audio/webm" }));
    requestOptions.body = body;
  } else if (panel === "youtube") {
    if (!query.get("url")) {
      throw new Error("Paste a YouTube URL before submitting.");
    }
  } else {
    const fileInput = $('input[type="file"][name="file"]', form);
    const file = fileInput?.files?.[0];
    if (!file) {
      throw new Error("Choose a media file before submitting.");
    }
    const body = new FormData();
    body.append("file", file, file.name);
    requestOptions.body = body;
  }

  setPanelStatus(panel, "Queued", "");
  setProgress(panel, 0);
  clearDownloads(panel);
  state.latestResults.delete(panel);
  setPreview(panel, `<div class="helper">Job queued. Waiting for updates...</div>`);

  const response = await fetch(`${form.dataset.endpoint}?${query.toString()}`, requestOptions);

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  const payload = await response.json();
  setPanelStatus(panel, titleCase(payload.status || "queued"), payload.message || "");
  await pollTask(panel, payload.identifier);
}

async function submitBgm(form) {
  const fileInput = $('input[type="file"][name="file"]', form);
  const file = fileInput?.files?.[0];
  if (!file) {
    throw new Error("Choose a file before running BGM separation.");
  }

  const query = collectParams(form);
  const body = new FormData();
  body.append("file", file, file.name);

  setPanelStatus("bgm", "Queued", "");
  setProgress("bgm", 0);
  clearDownloads("bgm");
  state.latestResults.delete("bgm");
  setPreview("bgm", `<div class="helper">Job queued. Waiting for updates...</div>`);

  const response = await fetch(`${form.dataset.endpoint}?${query.toString()}`, {
    method: "POST",
    body,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  const payload = await response.json();
  setPanelStatus("bgm", titleCase(payload.status || "queued"), payload.message || "");
  await pollTask("bgm", payload.identifier, form);
}

function attachFormHandlers() {
  for (const form of $$(".job-form")) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        if (panelKeyFromForm(form) === "bgm") {
          await submitBgm(form);
          return;
        }
        await submitTranscription(form, panelKeyFromForm(form));
      } catch (error) {
        const panel = panelKeyFromForm(form);
        setPanelStatus(panel, "Error", "");
        setPreview(panel, `<div class="helper error">${escapeHtml(error.message)}</div>`);
      }
    });
  }
}

function attachPanelTabs() {
  for (const button of $$(".tab")) {
    button.addEventListener("click", () => {
      const panel = button.dataset.panel;
      state.activePanel = panel;
      for (const tabButton of $$(".tab")) {
        tabButton.classList.toggle("active", tabButton === button);
      }
      for (const section of $$(".panel")) {
        section.classList.toggle("active", section.dataset.panel === panel);
      }
    });
  }
}

function getMicSupportError() {
  const reasons = [];
  if (!window.isSecureContext) {
    reasons.push("open the app on https or http://localhost");
  }
  if (!("MediaRecorder" in window)) {
    reasons.push("use a browser that supports MediaRecorder");
  }
  if (!(navigator.mediaDevices?.getUserMedia) && !navigator.getUserMedia && !navigator.webkitGetUserMedia && !navigator.mozGetUserMedia) {
    reasons.push("allow microphone APIs in this browser");
  }

  if (!reasons.length) {
    return "";
  }

  return `Microphone recording is unavailable here. ${reasons.join(", ")}.`;
}

async function requestMicrophoneStream() {
  if (navigator.mediaDevices?.getUserMedia) {
    return navigator.mediaDevices.getUserMedia({ audio: true });
  }

  const legacyGetUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
  if (!legacyGetUserMedia) {
    throw new Error(getMicSupportError() || "Microphone recording is unavailable in this browser.");
  }

  return new Promise((resolve, reject) => {
    legacyGetUserMedia.call(navigator, { audio: true }, resolve, reject);
  });
}

async function setupRecorder() {
  const recorderShell = $("[data-recorder]");
  if (!recorderShell) {
    return;
  }

  const startBtn = $('[data-action="record-start"]', recorderShell);
  const stopBtn = $('[data-action="record-stop"]', recorderShell);
  const clearBtn = $('[data-action="record-clear"]', recorderShell);
  const stateLabel = $('[data-recorder-state]', recorderShell);
  const playback = $('[data-recorder-playback]', recorderShell);

  const setRecorderUi = (message) => {
    if (stateLabel) {
      stateLabel.textContent = message;
    }
  };

  const refreshPlayback = () => {
    if (state.mic.blob && playback) {
      playback.src = URL.createObjectURL(state.mic.blob);
      playback.hidden = false;
      clearBtn.disabled = false;
    } else if (playback) {
      playback.removeAttribute("src");
      playback.hidden = true;
      clearBtn.disabled = true;
    }
  };

  const supportError = getMicSupportError();
  if (supportError) {
    setRecorderUi(supportError);
    if (startBtn) {
      startBtn.disabled = true;
    }
    if (stopBtn) {
      stopBtn.disabled = true;
    }
    if (clearBtn) {
      clearBtn.disabled = true;
    }
    return;
  }

  startBtn?.addEventListener("click", async () => {
    try {
      state.mic.stream = await requestMicrophoneStream();
      state.mic.chunks = [];
      state.mic.recorder = new MediaRecorder(state.mic.stream);

      state.mic.recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          state.mic.chunks.push(event.data);
        }
      };

      state.mic.recorder.onstop = () => {
        state.mic.blob = new Blob(state.mic.chunks, { type: state.mic.recorder?.mimeType || "audio/webm" });
        refreshPlayback();
        setRecorderUi(`Recorded ${Math.round(state.mic.blob.size / 1024)} KB`);
        stopBtn.disabled = true;
        startBtn.disabled = false;
      };

      state.mic.recorder.start();
      setRecorderUi("Recording...");
      startBtn.disabled = true;
      stopBtn.disabled = false;
      clearBtn.disabled = true;
    } catch (error) {
      setRecorderUi(error?.message || "Could not start microphone capture.");
      if (state.mic.stream) {
        state.mic.stream.getTracks().forEach((track) => track.stop());
        state.mic.stream = null;
      }
      stopBtn.disabled = true;
      startBtn.disabled = false;
    }
  });

  stopBtn?.addEventListener("click", () => {
    if (state.mic.recorder && state.mic.recorder.state !== "inactive") {
      state.mic.recorder.stop();
    }
    if (state.mic.stream) {
      state.mic.stream.getTracks().forEach((track) => track.stop());
      state.mic.stream = null;
    }
  });

  clearBtn?.addEventListener("click", () => {
    state.mic.blob = null;
    state.mic.chunks = [];
    state.mic.recorder = null;
    refreshPlayback();
    setRecorderUi("Idle");
  });
}

function renderAllSchemas() {
  renderSchema($('[data-fields="file-basic"]'), TRANSCRIPTION_FIELDS.basic);
  renderSchema($('[data-fields="youtube-basic"]'), TRANSCRIPTION_FIELDS.youtubeBasic);
  renderSchema($('[data-fields="mic-basic"]'), TRANSCRIPTION_FIELDS.basic.map((section) => ({
    ...section,
    fields: section.fields.filter((field) => field.kind !== "file"),
  })));
  for (const container of $$('[data-fields="transcription-advanced"]')) {
    renderSchema(container, TRANSCRIPTION_FIELDS.advanced);
  }
  renderSchema($('[data-fields="bgm-basic"]'), TRANSCRIPTION_FIELDS.bgmBasic);
  renderSchema($('[data-fields="bgm-advanced"]'), TRANSCRIPTION_FIELDS.bgmAdvanced);
}

function markConnectionReady() {
  const badge = $("#connectionStatus");
  if (badge) {
    badge.textContent = "Local shell";
  }
}

function wireGlobalState() {
  if (!state.mic.blob) {
    state.mic.blob = null;
  }
}

function init() {
  renderAllSchemas();
  attachPanelTabs();
  attachFormHandlers();
  setupRecorder();
  wireGlobalState();
  markConnectionReady();
  setProgress("file", 0);
  setProgress("youtube", 0);
  setProgress("mic", 0);
  setProgress("bgm", 0);
}

init();
