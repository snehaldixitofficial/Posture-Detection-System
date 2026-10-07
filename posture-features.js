/* Same 21-feature contract as research/features.py. Only seven visible joints
 * are used. The other 26 MediaPipe landmarks can be missing, including hips. */
(function (root) {
  "use strict";
  const required = [0, 2, 5, 7, 8, 11, 12];
  const distance = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  const midpoint = (a, b) => a.map((v, i) => (v + b[i]) / 2);
  const degrees = (radians) => (radians * 180) / Math.PI;
  const vertical = (top, bottom) =>
    degrees(Math.atan2(top[0] - bottom[0], bottom[1] - top[1]));
  function incenter(a, b, c) {
    const weights = [distance(b, c), distance(a, c), distance(a, b)];
    const total = weights.reduce((sum, v) => sum + v, 0);
    if (total < 1e-8) throw Error("Degenerate face geometry");
    return [0, 1].map(
      (i) =>
        (weights[0] * a[i] + weights[1] * b[i] + weights[2] * c[i]) / total,
    );
  }
  function extract(landmarks, width, height) {
    if (!landmarks || landmarks.length !== 33 || width <= 0 || height <= 0)
      throw Error("Show your head and both shoulders");
    for (const i of required) {
      const p = landmarks[i];
      if (
        !p ||
        !["x", "y", "z", "visibility"].every((k) => Number.isFinite(p[k])) ||
        !Number.isFinite(p.presence ?? 1) ||
        p.visibility < 0.65 ||
        (p.presence ?? 1) < 0.65 ||
        p.x < 0 ||
        p.x > 1 ||
        p.y < 0 ||
        p.y > 1
      )
        throw Error("Show your head, ears and both shoulders clearly");
    }
    const aspect = width / height;
    const points = Object.fromEntries(
      required.map((i) => [
        i,
        [landmarks[i].x * aspect, landmarks[i].y, landmarks[i].z * aspect],
      ]),
    );
    const [n, le, re, ls, rs] = [0, 7, 8, 11, 12].map((i) => points[i]);
    const sm = midpoint(ls, rs),
      em = midpoint(le, re),
      eyes = midpoint(points[2], points[5]);
    const sw = distance(ls, rs);
    if (sw < 0.1 * aspect || distance(n, sm) / sw > 3)
      throw Error("Move closer and show both shoulders");
    const raw = Object.fromEntries(
      required.map((i) => [i, [landmarks[i].x, landmarks[i].y]]),
    );
    const dl = distance(incenter(raw[2], raw[7], raw[0]), raw[11]);
    const dr = distance(incenter(raw[5], raw[8], raw[0]), raw[12]);
    const rawWidth = distance(raw[11], raw[12]);
    const features = [
      (Math.abs(dl - dr) * 10) / rawWidth,
      (dl + dr) / rawWidth,
      (dl - dr) / rawWidth,
      distance(n, sm) / sw,
      distance(le, ls) / sw,
      distance(re, rs) / sw,
      vertical(em, sm),
      vertical(n, em),
      degrees(Math.atan2(rs[1] - ls[1], ls[0] - rs[0])),
      (ls[1] - rs[1]) / sw,
      distance(n, ls) / sw,
      distance(n, rs) / sw,
      distance(eyes, sm) / sw,
      distance(le, re) / sw,
      distance(points[2], points[5]) / sw,
      (sm[1] - n[1]) / sw,
      (sm[2] - n[2]) / sw,
      (sm[2] - em[2]) / sw,
      (n[0] - sm[0]) / sw,
      (sm[1] - em[1]) / sw,
      (le[2] - ls[2] - (re[2] - rs[2])) / sw,
    ];
    if (!features.every(Number.isFinite)) throw Error("Invalid geometry");
    return features;
  }
  const api = { extract, required, version: "posture-head-shoulders-v2" };
  if (typeof module !== "undefined") module.exports = api;
  else root.PostureFeatures = api;
})(globalThis);
