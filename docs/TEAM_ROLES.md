# Team Roles & Technical Breakdown
**Posture Monitor Application**

This document summarizes the technical areas assigned to each member of the engineering team. It describes the current implementation so each member can explain their portion of the codebase.

---

## 1. Snehal Dixit — Architecture & DevOps (Team Lead)

### The Role
Snehal was responsible for the high-level system architecture, technology stack selection, and deployment infrastructure. The primary challenge was designing a system that was robust, zero-latency, and capable of being deployed to a serverless cloud environment (Vercel).

### Technical Implementation (A to Z)
*   **The Architectural Pivot:** Initially, the project was scoped as a Python/Flask monolith using OpenCV. Snehal identified a critical infrastructure conflict: cloud providers like Vercel (which run on AWS Lambda) cannot access a client's local webcam hardware. Snehal spearheaded the architectural pivot from a Python Server-Side model to a Client-Side Rendering (CSR) JavaScript model.
*   **Static Web Architecture:** By moving the computational load to the browser, Snehal removed the need for an application backend. Camera frames remain on the device, while MediaPipe assets and fonts are loaded from public CDNs.
*   **Deployment Pipeline:** Snehal managed the integration with Vercel, ensuring the static assets (`index.html`, `style.css`, `script.js`) were properly structured in the root directory for instant deployment without requiring complex build steps or continuous integration actions.

---

## 2. Geetesh Parashar — Machine Learning Integration

### The Role
Geetesh was responsible for the core computer vision engine. The job was to evaluate, integrate, and tune the machine learning model that tracks human skeletal joints in real-time within a web browser.

### Technical Implementation (A to Z)
*   **Model Selection:** Geetesh selected Google's **MediaPipe Pose** model due to its high performance on Edge devices via WebAssembly (Wasm) and WebGL.
*   **Parameter Tuning:** Geetesh instantiated the `Pose` object and configured its execution parameters. The `modelComplexity` was set to `1` for optimal balance between accuracy and loading speed.
*   **Data Extraction:** The MediaPipe model returns 33 landmarks for each processed frame. Geetesh engineered the extraction pipeline to isolate the nodes required for posture analysis: Nose `[0]`, Eyes `[2, 5]`, Ears `[7, 8]`, and Shoulders `[11, 12]`.
*   **Thresholding:** Geetesh set `minDetectionConfidence` and `minTrackingConfidence` to `0.5` to ensure reliable skeleton tracking even in low-light or backlit environments like dorm rooms.

---

## 3. Vaishnavi Dixit — Applied Mathematics

### The Role
Vaishnavi was responsible for the geometric logic that distinguishes the supported posture states. The implementation uses normalized Euclidean distance features instead of a single neck-angle measurement.

### Technical Implementation (A to Z)
*   **Euclidean Distance Matrix:** Vaishnavi wrote the `distance(p1, p2)` function, which utilizes the Pythagorean theorem (`Math.sqrt(x^2 + y^2)`) to measure exact pixel distances between joints.
*   **Facial Geometry (Incenters):** To track head movement robustly, Vaishnavi implemented the `incenter(A, B, C)` formula. This algorithm calculates the perimeter-weighted center of the triangle formed by the user's Eye, Ear, and Nose on each side of the face.
*   **Spatial Feature Extraction:** Using the derived facial incenters (`LFaceCenter`, `RFaceCenter`), Vaishnavi calculated the distances to the shoulders (`s1`, `s2`) and the distance between the shoulders (`s3`).
*   **Classification Math (`f1` and `f2`):** Vaishnavi engineered the final metrics:
    *   `f1 = Math.abs((s1 - s2) * 10) / s3` : This metric identifies lateral leaning (if the user tilts left or right).
    *   `f2 = (s1 + s2) / s3` : This metric identifies forward slouching.
*   **Calibrated Thresholds:** The browser compares each metric with the user's upright baseline. This heuristic approach is intentionally described as a posture aid rather than a trained diagnostic model.

---

## 4. Jhanvi Gaur — Systems & Data Pipeline

### The Role
Jhanvi managed the flow of data from the user's hardware (the webcam) into the application, and managed the visual output on the screen. This role required interfacing with browser security protocols and handling edge-case errors.

### Technical Implementation (A to Z)
*   **Hardware Interfacing:** Jhanvi used `navigator.mediaDevices.getUserMedia` to create one camera stream. A request-animation-frame loop feeds frames to MediaPipe with `pose.send({ image: videoElement })`, avoiding a duplicate camera stream.
*   **Instant Camera Startup:** Jhanvi implemented a two-phase startup strategy: the raw webcam feed is piped directly to the canvas immediately using `requestAnimationFrame`, while the heavy MediaPipe model loads in the background. This eliminates the long "black screen" wait.
*   **Canvas Rendering:** Instead of showing a raw video element, Jhanvi managed the HTML5 `<canvas>` context (`canvasCtx`). Every frame, the canvas is cleared, the raw video is painted as the background, and MediaPipe's `drawConnectors` and `drawLandmarks` functions are layered on top to create the skeletal overlay.

---

## 5. Pratyasha Singh — Frontend & State Management

### The Role
Pratyasha was responsible for the User Interface, User Experience, and the Dynamic Calibration system. The goal was to take the complex math and machine learning and present it in a clean, minimalist aesthetic.

### Technical Implementation (A to Z)
*   **UI/UX Architecture:** Pratyasha built the layout using semantic HTML5 and vanilla CSS3. By utilizing a dark color scheme (`#121212` background, `#1e1e1e` card surfaces), the `Outfit` font family, and simple `box-shadow` for depth, the application achieved a highly professional look without relying on heavy frameworks like React or Bootstrap.
*   **Stats Dashboard:** Pratyasha built a real-time stats dashboard below the video feed that tracks Session Time, Slouch Count, Lean Count, and Calibration Status using basic JavaScript `setInterval` and DOM manipulation.
*   **Dynamic Calibration System:** Because fixed thresholds vary across body proportions and camera angles, Pratyasha engineered a stateful calibration feature.
    *   Variables (`baselineF1`, `baselineF2`, `isCalibrated`) were introduced to store the user's personal posture metrics.
    *   An event listener was attached to the "Calibrate" button. When clicked, it captures the user's current `f1` and `f2` metrics, overwriting the default paper thresholds with the user's exact physical proportions.
*   **Real-Time State Transitions:** Pratyasha managed the DOM updates for the status overlay. The UI uses red for slouching, orange for leaning, and green for upright posture, and exposes status changes through an ARIA live region.
