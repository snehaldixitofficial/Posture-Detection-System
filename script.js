/* Camera -> landmarks -> features -> selected model -> feedback.
 * Geometry is in posture-features.js; classifier math is in model-runtime.js.
 * Camera images and landmark coordinates never leave this device. */
"use strict";
const $ = (id) => document.getElementById(id);
const video = $("input_video"),
  canvas = $("output_canvas"),
  ctx = canvas.getContext("2d");
const selector = $("classifier-mode"),
  names = ["Random_Forest", "SVM_RBF", "XGBoost"];
const labels = {
  Correct: "Correct posture",
  Slouch: "Slouching",
  Lean_Left: "Leaning left",
  Lean_Right: "Leaning right",
  Lean: "Leaning",
};
const colors = {
  Correct: "#48e6b0",
  Slouch: "#ff7e83",
  Lean_Left: "#ffc66d",
  Lean_Right: "#ffc66d",
  Lean: "#ffc66d",
};
const state = {
  pose: null,
  models: {},
  stream: null,
  running: false,
  starting: false,
  lastVideoTime: -1,
  features: null,
  previousLabel: null,
  slouches: 0,
  leans: 0,
  baseline: [0.031, 1.352],
  calibrated: false,
  startedAt: 0,
  elapsed: 0,
  epoch: 0,
};
function status(message, color = "#e9edf6") {
  $("status-overlay").textContent = message;
  $("status-overlay").style.color = color;
}
function resetFeedback() {
  state.features = null;
  state.previousLabel = null;
  $("calibrate-btn").disabled = true;
  $("inference-time").textContent = "—";
  names.forEach((name) => ($("live-" + name).textContent = "Waiting"));
}
function updateMode() {
  resetFeedback();
  const name = selector.value;
  $("model-status").textContent =
    name === "rules"
      ? "Sit upright, then set your reference position. These rules detect upright, slouch and lean."
      : "Using the " +
        name.replaceAll("_", " ") +
        " model from the study. You don't need to calibrate it.";
  $("calibrate-btn").hidden = name !== "rules";
  $("calibration-status").textContent =
    name === "rules"
      ? state.calibrated
        ? "Calibrated"
        : "Defaults"
      : "21 features";
  $("active-model").textContent = selector.options[selector.selectedIndex].text;
  if (state.running) status("Reading the next camera frame…");
}
selector.addEventListener("change", updateMode);
// Original rule baseline has three states; ML models distinguish lean direction.
function rulePrediction(features) {
  if (features[1] - state.baseline[1] < -0.12) return "Slouch";
  if (Math.abs(features[0] - state.baseline[0]) > 0.55) return "Lean";
  return "Correct";
}
$("calibrate-btn").addEventListener("click", () => {
  if (!state.features || selector.value !== "rules") return;
  state.baseline = state.features.slice(0, 2);
  state.calibrated = true;
  $("calibration-status").textContent = "Calibrated";
});
$("mirror-toggle").addEventListener("change", () =>
  canvas.classList.toggle("mirrored", $("mirror-toggle").checked),
);
$("reset-btn").addEventListener("click", () => {
  state.slouches = state.leans = 0;
  state.previousLabel = null;
  state.elapsed = 0;
  state.startedAt = performance.now();
  $("slouch-count").textContent = $("lean-count").textContent = "0";
  $("session-time").textContent = "00:00";
});
$("fullscreen-btn").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await $("camera-panel").requestFullscreen();
  } catch {
    $("model-status").textContent =
      "Fullscreen is unavailable in this browser.";
  }
});
// Mirror only the preview, never feature coordinates. Labels mean anatomical left/right.
function drawFrame(landmarks, color) {
  if (
    canvas.width !== video.videoWidth ||
    canvas.height !== video.videoHeight
  ) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  }
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  if (!$("landmarks-toggle").checked || !landmarks) return;
  const visible = (i) =>
    landmarks[i] &&
    landmarks[i].visibility >= 0.65 &&
    landmarks[i].x >= 0 &&
    landmarks[i].x <= 1 &&
    landmarks[i].y >= 0 &&
    landmarks[i].y <= 1;
  const point = (i) => [
    landmarks[i].x * canvas.width,
    landmarks[i].y * canvas.height,
  ];
  ctx.strokeStyle = color;
  ctx.fillStyle = "#fff";
  ctx.lineWidth = 3;
  for (const [a, b] of [
    [7, 2],
    [2, 0],
    [0, 5],
    [5, 8],
    [11, 12],
    [7, 11],
    [8, 12],
  ]) {
    if (!visible(a) || !visible(b)) continue;
    ctx.beginPath();
    ctx.moveTo(...point(a));
    ctx.lineTo(...point(b));
    ctx.stroke();
  }
  for (const i of PostureFeatures.required) {
    if (!visible(i)) continue;
    ctx.beginPath();
    ctx.arc(...point(i), 4, 0, 2 * Math.PI);
    ctx.fill();
  }
}
function showPrediction(label) {
  status(labels[label], colors[label]);
  if (label !== state.previousLabel) {
    if (label === "Slouch") $("slouch-count").textContent = ++state.slouches;
    if (label.startsWith("Lean")) $("lean-count").textContent = ++state.leans;
  }
  state.previousLabel = label;
}
// Every new frame gets fresh predictions. Invalid tracking clears old feedback.
function processFrame(epoch = state.epoch) {
  if (!state.running || epoch !== state.epoch) return;
  try {
    if (video.readyState >= 2 && video.currentTime !== state.lastVideoTime) {
      state.lastVideoTime = video.currentTime;
      const landmarks = state.pose.detectForVideo(video, performance.now())
        .landmarks[0];
      let color = "#e9edf6";
      try {
        state.features = PostureFeatures.extract(
          landmarks,
          video.videoWidth,
          video.videoHeight,
        );
        const predictions = {},
          timings = {};
        for (const [name, model] of Object.entries(state.models)) {
          const start = performance.now();
          predictions[name] = PostureModels.predict(model, state.features);
          timings[name] = performance.now() - start;
          $("live-" + name).textContent = labels[predictions[name]];
        }
        const start = performance.now();
        const label =
          selector.value === "rules"
            ? rulePrediction(state.features)
            : predictions[selector.value];
        const duration =
          selector.value === "rules"
            ? performance.now() - start
            : timings[selector.value];
        $("inference-time").textContent = duration.toFixed(2) + " ms";
        $("calibrate-btn").disabled = selector.value !== "rules";
        showPrediction(label);
        color = colors[label];
      } catch (error) {
        resetFeedback();
        status(error.message);
      }
      drawFrame(landmarks, color);
    }
    requestAnimationFrame(() => processFrame(epoch));
  } catch (error) {
    stopCamera();
    status("Tracking stopped: " + error.message, "#ff7e83");
  }
}
async function loadModels() {
  if (state.pose) return;
  $("model-status").textContent = "Loading trained models and posture tracker…";
  const models = await Promise.all(
    names.map(async (name) => {
      const response = await fetch("assets/models/" + name + ".json");
      if (!response.ok) throw Error("Unable to load " + name);
      const model = await response.json();
      if (model.feature_version !== PostureFeatures.version)
        throw Error("Feature version mismatch");
      return [name, model];
    }),
  );
  const { PoseLandmarker, FilesetResolver } = await import(
    "./assets/mediapipe/vision_bundle.mjs"
  );
  const files = await FilesetResolver.forVisionTasks("assets/mediapipe/wasm");
  state.pose = await PoseLandmarker.createFromOptions(files, {
    baseOptions: { modelAssetPath: "assets/pose_landmarker_lite.task" },
    runningMode: "VIDEO",
    numPoses: 1,
    minPoseDetectionConfidence: 0.5,
    minPosePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
  state.models = Object.fromEntries(models);
}
async function startCamera() {
  if (state.running || state.starting) return;
  state.starting = true;
  $("start-btn").disabled = true;
  try {
    if (!navigator.mediaDevices?.getUserMedia)
      throw Error("Camera access requires HTTPS or localhost");
    status("Loading posture tracking…");
    await loadModels();
    status("Allow camera access to start");
    state.stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: "user" },
      audio: false,
    });
    video.srcObject = state.stream;
    await video.play();
    state.running = true;
    state.epoch++;
    state.lastVideoTime = -1;
    state.startedAt = performance.now();
    $("stop-btn").disabled = false;
    selector.disabled = false;
    updateMode();
    processFrame();
  } catch (error) {
    stopCamera();
    status(
      error.name === "NotAllowedError"
        ? "Allow camera permission, then click Start camera."
        : error.message,
      "#ff7e83",
    );
    $("model-status").textContent =
      "Check camera permission and internet access, then retry.";
  } finally {
    state.starting = false;
    $("start-btn").disabled = state.running;
  }
}
function stopCamera() {
  if (state.running) state.elapsed += performance.now() - state.startedAt;
  state.running = false;
  state.epoch++;
  state.stream?.getTracks().forEach((track) => track.stop());
  state.stream = null;
  video.srcObject = null;
  resetFeedback();
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  $("start-btn").disabled = false;
  $("stop-btn").disabled = true;
  status("Camera stopped");
}
$("start-btn").addEventListener("click", startCamera);
$("stop-btn").addEventListener("click", stopCamera);
window.addEventListener("pagehide", stopCamera);
setInterval(() => {
  const seconds = Math.floor(
    (state.elapsed +
      (state.running ? performance.now() - state.startedAt : 0)) /
      1000,
  );
  $("session-time").textContent =
    String(Math.floor(seconds / 60)).padStart(2, "0") +
    ":" +
    String(seconds % 60).padStart(2, "0");
}, 1000);
updateMode();
