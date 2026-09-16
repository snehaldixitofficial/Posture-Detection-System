const videoElement = document.getElementById('input_video');
const canvasElement = document.getElementById('output_canvas');
const canvasCtx = canvasElement.getContext('2d');
const statusOverlay = document.getElementById('status-overlay');
const calibrateBtn = document.getElementById('calibrate-btn');
const sessionTimeEl = document.getElementById('session-time');
const slouchCountEl = document.getElementById('slouch-count');
const leanCountEl = document.getElementById('lean-count');
const calibrationStatusEl = document.getElementById('calibration-status');

const DEFAULT_BASELINE = { f1: 0.031, f2: 1.352 };
const SLOUCH_DELTA = -0.12;
const LEAN_DELTA = 0.55;

let baselineF1 = DEFAULT_BASELINE.f1;
let baselineF2 = DEFAULT_BASELINE.f2;
let currentF1 = baselineF1;
let currentF2 = baselineF2;
let isCalibrated = false;
let hasCurrentMeasurement = false;
let slouchCount = 0;
let leanCount = 0;
let isCurrentlySlouching = false;
let isCurrentlyLeaning = false;
let sessionStartTime = null;
let aiReady = false;

function distance(p1, p2) {
    return Math.hypot(p1.x - p2.x, p1.y - p2.y);
}

function incenter(aPoint, bPoint, cPoint) {
    const a = distance(bPoint, cPoint);
    const b = distance(aPoint, cPoint);
    const c = distance(aPoint, bPoint);
    const perimeter = a + b + c;

    if (perimeter === 0) return aPoint;

    return {
        x: (a * aPoint.x + b * bPoint.x + c * cPoint.x) / perimeter,
        y: (a * aPoint.y + b * bPoint.y + c * cPoint.y) / perimeter
    };
}

function predictPosture(f1, f2) {
    const leanDifference = Math.abs(f1 - baselineF1);
    const slouchDifference = f2 - baselineF2;

    if (slouchDifference < SLOUCH_DELTA) return 1;
    if (leanDifference > LEAN_DELTA) return 2;
    return 0;
}

function isVisible(landmark, threshold) {
    return Boolean(landmark) && (landmark.visibility ?? 0) > threshold;
}

function isRealHumanUpperBody(landmarks) {
    const nose = landmarks[0];
    const leftEye = landmarks[2];
    const rightEye = landmarks[5];
    const leftEar = landmarks[7];
    const rightEar = landmarks[8];
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const criticalJoints = [nose, leftEye, rightEye, leftShoulder, rightShoulder];

    if (!criticalJoints.every((joint) => isVisible(joint, 0.65))) return false;
    if (!isVisible(leftEar, 0.4) && !isVisible(rightEar, 0.4)) return false;

    const shoulderMidpoint = {
        x: (leftShoulder.x + rightShoulder.x) / 2,
        y: (leftShoulder.y + rightShoulder.y) / 2
    };
    if (shoulderMidpoint.y < nose.y) return false;

    const shoulderWidth = Math.abs(leftShoulder.x - rightShoulder.x);
    if (shoulderWidth < 0.10) return false;

    const headToShoulderRatio = distance(nose, shoulderMidpoint) / shoulderWidth;
    return headToShoulderRatio >= 0.15 && headToShoulderRatio <= 3.0;
}

function resetDetectionState() {
    isCurrentlySlouching = false;
    isCurrentlyLeaning = false;
}

function setStatus(message, color) {
    statusOverlay.innerText = message;
    statusOverlay.style.color = color;
}

calibrateBtn.addEventListener('click', () => {
    if (!hasCurrentMeasurement) return;

    baselineF1 = currentF1;
    baselineF2 = currentF2;
    isCalibrated = true;
    calibrationStatusEl.innerText = 'Calibrated';
    calibrationStatusEl.style.color = '#34c759';
    calibrateBtn.innerText = 'Calibrated';
    calibrateBtn.style.backgroundColor = '#34c759';

    setTimeout(() => {
        calibrateBtn.innerText = 'Recalibrate';
        calibrateBtn.style.backgroundColor = '';
    }, 1500);
});

function onResults(results) {
    aiReady = true;
    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);

    const landmarks = results.poseLandmarks;
    if (!landmarks || !isRealHumanUpperBody(landmarks)) {
        hasCurrentMeasurement = false;
        calibrateBtn.disabled = true;
        resetDetectionState();
        setStatus('Show your face and upper body', '#f5f5f7');
        canvasCtx.restore();
        return;
    }

    const nose = landmarks[0];
    const leftEye = landmarks[2];
    const rightEye = landmarks[5];
    const leftEar = landmarks[7];
    const rightEar = landmarks[8];
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const leftFaceCenter = incenter(leftEye, leftEar, nose);
    const rightFaceCenter = incenter(rightEye, rightEar, nose);
    const leftFaceToShoulder = distance(leftFaceCenter, leftShoulder);
    const rightFaceToShoulder = distance(rightFaceCenter, rightShoulder);
    const shoulderWidth = distance(leftShoulder, rightShoulder);

    if (shoulderWidth > 0) {
        currentF1 = Math.abs((leftFaceToShoulder - rightFaceToShoulder) * 10) / shoulderWidth;
        currentF2 = (leftFaceToShoulder + rightFaceToShoulder) / shoulderWidth;
        hasCurrentMeasurement = true;
        calibrateBtn.disabled = false;

        const prediction = predictPosture(currentF1, currentF2);
        if (prediction === 1) {
            setStatus('Slouching detected', '#ff453a');
            if (!isCurrentlySlouching) {
                slouchCount += 1;
                slouchCountEl.innerText = slouchCount;
            }
            isCurrentlySlouching = true;
            isCurrentlyLeaning = false;
        } else if (prediction === 2) {
            setStatus('Leaning detected', '#ff9f0a');
            if (!isCurrentlyLeaning) {
                leanCount += 1;
                leanCountEl.innerText = leanCount;
            }
            isCurrentlyLeaning = true;
            isCurrentlySlouching = false;
        } else {
            setStatus(isCalibrated ? 'Great posture' : 'Good posture - calibrate when ready', '#30d158');
            resetDetectionState();
        }
    }

    const skeletonColor = statusOverlay.style.color || '#30d158';
    canvasCtx.globalCompositeOperation = 'lighter';
    canvasCtx.shadowColor = skeletonColor;
    canvasCtx.shadowBlur = 15;
    drawConnectors(canvasCtx, landmarks, POSE_CONNECTIONS, {
        color: skeletonColor,
        lineWidth: 4
    });
    drawLandmarks(canvasCtx, landmarks, {
        color: '#ffffff',
        lineWidth: 2,
        radius: 3
    });
    canvasCtx.globalCompositeOperation = 'source-over';
    canvasCtx.restore();
}

function startSessionTimer() {
    sessionStartTime = Date.now();
    setInterval(() => {
        const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
        const minutes = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const seconds = String(elapsed % 60).padStart(2, '0');
        sessionTimeEl.innerText = `${minutes}:${seconds}`;
    }, 1000);
}

function renderPreview() {
    if (aiReady) return;
    if (videoElement.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
        canvasCtx.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
    }
    requestAnimationFrame(renderPreview);
}

async function initializePose() {
    const pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
    });
    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
    });
    pose.onResults(onResults);

    async function processFrame() {
        try {
            if (videoElement.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
                await pose.send({ image: videoElement });
            }
            requestAnimationFrame(processFrame);
        } catch (error) {
            console.error('Pose processing failed:', error);
            setStatus('Posture tracking stopped. Reload to retry.', '#ff453a');
        }
    }

    processFrame();
}

async function startApplication() {
    if (!navigator.mediaDevices?.getUserMedia) {
        setStatus('Camera access requires HTTPS or localhost', '#ff453a');
        return;
    }

    try {
        setStatus('Starting camera...', '#f5f5f7');
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: 800, height: 600, facingMode: 'user' },
            audio: false
        });
        videoElement.srcObject = stream;
        await videoElement.play();
        setStatus('Camera ready. Loading posture tracking...', '#f5f5f7');
        renderPreview();
        startSessionTimer();
        await initializePose();
    } catch (error) {
        console.error('Camera startup failed:', error);
        setStatus('Allow camera access and reload the page', '#ff453a');
    }
}

startApplication();
