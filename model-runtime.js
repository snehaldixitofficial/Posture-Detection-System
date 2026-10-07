/* Readable inference for the actual exported Python models. No training here.
 * Random Forest votes via leaf probabilities; SVM uses pairwise RBF decisions;
 * XGBoost sums class-specific tree margins. All return the same four labels. */
(function (root) {
  "use strict";
  const argmax = (values) => values.indexOf(Math.max(...values)); // First class wins a tie.
  function leaf(tree, features, strict) {
    let node = 0;
    while (tree.left[node] !== -1) {
      const value = features[tree.feature[node]];
      const goLeft = strict
        ? value < Math.fround(tree.threshold[node])
        : value <= tree.threshold[node];
      node = goLeft ? tree.left[node] : tree.right[node];
    }
    return node;
  }
  function forest(model, features) {
    const scores = [0, 0, 0, 0],
      x = features.map(Math.fround);
    for (const tree of model.trees) {
      const values = tree.values[leaf(tree, x, false)];
      const total = values.reduce((a, b) => a + b, 0);
      values.forEach((value, i) => {
        scores[i] += value / total;
      });
    }
    return argmax(scores);
  }
  function svm(model, features) {
    const x = features.map((v, i) => (v - model.mean[i]) / model.scale[i]);
    const kernels = model.support.map((vector) =>
      Math.exp(
        -model.gamma * vector.reduce((sum, v, i) => sum + (v - x[i]) ** 2, 0),
      ),
    );
    const votes = [0, 0, 0, 0],
      starts = [0];
    model.counts.forEach((count) => starts.push(starts.at(-1) + count));
    let pair = 0;
    for (let i = 0; i < 4; i++)
      for (let j = i + 1; j < 4; j++) {
        let decision = model.intercept[pair++];
        for (let k = starts[i]; k < starts[i + 1]; k++)
          decision += model.coefficients[j - 1][k] * kernels[k];
        for (let k = starts[j]; k < starts[j + 1]; k++)
          decision += model.coefficients[i][k] * kernels[k];
        votes[decision > 0 ? i : j]++;
      }
    return argmax(votes);
  }
  function boosted(model, features) {
    const scores = model.base.map(Math.fround),
      x = features.map(Math.fround);
    model.trees.forEach((tree, i) => {
      const group = model.groups[i];
      scores[group] = Math.fround(
        scores[group] + Math.fround(tree.threshold[leaf(tree, x, true)]),
      );
    });
    return argmax(scores);
  }
  function predict(model, features) {
    if (
      model.feature_version !== "posture-head-shoulders-v2" ||
      features.length !== 21 ||
      !features.every(Number.isFinite)
    )
      throw Error("Model feature contract mismatch");
    const methods = { Random_Forest: forest, SVM_RBF: svm, XGBoost: boosted };
    if (!methods[model.name]) throw Error("Unsupported model");
    return model.labels[methods[model.name](model, features)];
  }
  if (typeof module !== "undefined") module.exports = { predict };
  else root.PostureModels = { predict };
})(globalThis);
