"""Identical subject folds, train-only scaling, nested tuning, honest reporting."""
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, ParameterGrid
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from xgboost import XGBClassifier

from .dataset import digest
from .features import FEATURES, LABELS, VERSION, rule_predictions


def candidates(seed, tune):
    rf = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=seed, n_jobs=1)
    svm = make_pipeline(StandardScaler(), SVC(kernel="rbf", C=10, gamma="scale", class_weight="balanced"))
    xgb = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=.05, subsample=.8,
                        colsample_bytree=.8, objective="multi:softprob", num_class=4,
                        eval_metric="mlogloss", random_state=seed, n_jobs=1, tree_method="hist")
    return {
        "Random_Forest": [clone(rf).set_params(**p) for p in ParameterGrid({"max_depth": [None, 12]} if tune else {})],
        "SVM_RBF": [clone(svm).set_params(**p) for p in ParameterGrid({"svc__C": [1, 10]} if tune else {})],
        "XGBoost": [clone(xgb).set_params(**p) for p in ParameterGrid({"max_depth": [3, 6]} if tune else {})],
    }


def metrics(y, pred):
    p, r, f, _ = precision_recall_fscore_support(y, pred, labels=range(4), average="macro", zero_division=0)
    return dict(accuracy=float(accuracy_score(y, pred)), precision_macro=float(p), recall_macro=float(r), macro_f1=float(f))


def tune_model(models, X, y, folds, groups):
    scores = []
    for estimator in models:
        subject_scores = []
        for train, val in folds:
            if set(y[train]) != set(range(4)):
                raise ValueError("a training fold is missing a posture class")
            model = clone(estimator).fit(X[train], y[train])
            pred = model.predict(X[val])
            # Selection weights held-out people equally, not their frame counts.
            for subject in np.unique(groups[val]):
                mask = groups[val] == subject
                subject_scores.append(metrics(y[val][mask], pred[mask])["macro_f1"])
        scores.append(float(np.mean(subject_scores)))
    best = int(np.argmax(scores))
    return clone(models[best]), scores[best], scores


def save_matrix(y, pred, path, labels=LABELS):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cm = confusion_matrix(y, pred, labels=range(len(labels)))
    pd.DataFrame(cm, index=labels, columns=labels).to_csv(path.with_suffix(".csv"))
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.imshow(cm, cmap="Blues")
    ax.set(xticks=range(len(labels)), yticks=range(len(labels)), xticklabels=labels,
           yticklabels=labels, xlabel="Predicted", ylabel="Actual", title=path.stem)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center")
    fig.tight_layout()
    fig.savefig(path.with_suffix(".png"), dpi=160)
    plt.close(fig)


def train(args):
    data = Path(args.data)
    review_path = Path(str(data) + ".review.json")
    if not review_path.exists() or json.loads(review_path.read_text())["clean_sha256"] != digest(data):
        raise ValueError("training requires an unchanged CSV from the clean review gate")
    df = pd.read_csv(data, dtype={"subject_id": str, "row_id": str})
    required = set(FEATURES) | {"subject_id", "posture", "row_id", "feature_version", "model_sha256"}
    if not required <= set(df) or df.empty or df[list(required)].isna().any().any():
        raise ValueError("missing required dataset fields or empty dataset")
    if set(df.feature_version) != {VERSION} or df.model_sha256.nunique() != 1 or df.row_id.duplicated().any():
        raise ValueError("mixed feature/model versions or duplicate frames")
    if set(df.posture) != set(LABELS):
        raise ValueError("dataset must contain exactly the four protocol labels")
    X = df.loc[:, list(FEATURES)].to_numpy(dtype=float)
    if not np.isfinite(X).all():
        raise ValueError("nonfinite input features")
    y = df.posture.map({label: i for i, label in enumerate(LABELS)}).to_numpy()
    groups = df.subject_id.to_numpy()
    subjects = sorted(set(groups))
    if len(subjects) < 3:
        raise ValueError("need at least 3 participants; aim for 10-20")
    if any(set(df.loc[df.subject_id == subject, "posture"]) != set(LABELS) for subject in subjects):
        raise ValueError("each participant must have reviewed frames in all four classes")
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("result directory is not empty; use a new --output to preserve experiments")
    output.mkdir(parents=True, exist_ok=True)
    estimators = candidates(args.seed, args.tune)
    fold_manifest, folds, selections, prediction_rows = [], [], [], []
    if args.mode == "holdout":
        if not args.split:
            raise ValueError("holdout requires --split JSON with train, validation, test subject lists")
        split = json.loads(Path(args.split).read_text())
        if set(split) != {"train", "validation", "test"} or any(not split[k] for k in split):
            raise ValueError("split needs three nonempty subject lists")
        flat = [s for key in split for s in split[key]]
        if len(flat) != len(set(flat)) or set(flat) != set(subjects):
            raise ValueError("split must cover every subject exactly once")
        train_idx, val_idx, test_idx = [np.flatnonzero(np.isin(groups, split[k])) for k in ("train", "validation", "test")]
        outer = [(np.concatenate([train_idx, val_idx]), test_idx)]
    else:
        outer = list(LeaveOneGroupOut().split(X, y, groups))
    for fold_number, (development, test) in enumerate(outer, 1):
        if set(groups[development]) & set(groups[test]):
            raise AssertionError("subject leakage")
        if args.mode == "holdout":
            # Indices relative to development; tuning uses training vs validation.
            inner = [(np.flatnonzero(np.isin(development, train_idx)), np.flatnonzero(np.isin(development, val_idx)))]
        else:
            inner = list(GroupKFold(n_splits=min(3, len(set(groups[development])))).split(X[development], y[development], groups[development]))
        fold_manifest.append({"fold": fold_number, "development_subjects": sorted(set(groups[development])),
                              "test_subjects": sorted(set(groups[test])), "inner": [
                                  {"train_subjects": sorted(set(groups[development][a])), "validation_subjects": sorted(set(groups[development][b]))}
                                  for a, b in inner]})
        selected_models, selection_scores = {}, {}
        for name, models in estimators.items():
            estimator, score, candidate_scores = tune_model(models, X[development], y[development], inner, groups[development])
            selection_scores[name] = score
            selected_models[name] = estimator
            started = time.perf_counter()
            fitted = estimator.fit(X[development], y[development])
            training_time = time.perf_counter() - started
            fitted.predict(X[test][:1])  # Warm up; timings exclude feature extraction.
            started = time.perf_counter()
            pred = fitted.predict(X[test])
            batch_ms = (time.perf_counter() - started) * 1000 / len(test)
            single_times = []
            for index in test[:min(len(test), 100)]:
                started = time.perf_counter()
                fitted.predict(X[index:index+1])
                single_times.append((time.perf_counter()-started)*1000)
            folds.append({"fold": fold_number, "model": name, **metrics(y[test], pred),
                          "selection_macro_f1": score, "training_seconds": training_time,
                          "batch_ms_per_frame": batch_ms, "single_frame_ms_median": float(np.median(single_times))})
            selections.append({"fold": fold_number, "model": name, "candidate_scores": candidate_scores,
                               "parameters": fitted.get_params()})
            for i, predicted in zip(test, pred):
                prediction_rows.append({"row_id": df.row_id.iloc[i], "subject_id": groups[i], "fold": fold_number,
                                        "model": name, "actual": int(y[i]), "predicted": int(predicted)})
            if args.mode == "holdout":
                joblib.dump(fitted, output / f"{name}.joblib")
        if args.mode == "holdout":
            winner = max(selection_scores, key=selection_scores.get)
        print(f"Fold {fold_number}/{len(outer)} complete; held out {sorted(set(groups[test]))}")
    results = pd.DataFrame(folds)
    results.to_csv(output / "fold_metrics.csv", index=False)
    predictions = pd.DataFrame(prediction_rows)
    predictions.to_csv(output / "predictions.csv", index=False)
    # All methods have exactly the same evaluated row IDs, including baselines.
    evaluated = sorted(set(predictions.row_id))
    baseline_df = df.set_index("row_id").loc[evaluated]
    truth = baseline_df.posture.map({s: i for i, s in enumerate(LABELS)}).to_numpy()
    baseline_rows = baseline_df.to_dict("records")
    start = time.perf_counter()
    exact, directional = rule_predictions(baseline_rows)
    rule_batch_ms = (time.perf_counter() - start) * 1000 / len(baseline_rows)
    rule_single_ms = []
    for row in baseline_rows[:100]:
        start = time.perf_counter()
        rule_predictions([row])
        rule_single_ms.append((time.perf_counter() - start) * 1000)
    mapping = {s: i for i, s in enumerate(LABELS)}
    dpred = np.array([mapping[s] for s in directional])
    collapsed_labels = ("Correct", "Slouch", "Lean")
    collapsed = {s: i for i, s in enumerate(collapsed_labels)}
    actual3 = np.array([min(i, 2) for i in truth])
    pred3 = np.array([collapsed[s] for s in exact])
    pd.DataFrame({"row_id": evaluated, "actual": baseline_df.posture.to_numpy(),
                  "original_rule": exact, "directional_extension": directional}).to_csv(output / "baseline_predictions.csv", index=False)
    save_matrix(actual3, pred3, output / "original_rule_3state", collapsed_labels)
    save_matrix(truth, dpred, output / "directional_rule_4class")
    baseline = {"original_rule_3state": {"accuracy": float(accuracy_score(actual3, pred3)),
                   "report": classification_report(actual3, pred3, labels=range(3), target_names=collapsed_labels, output_dict=True, zero_division=0)},
                "directional_extension_4class": metrics(truth, dpred),
                "rules_combined_timing": {"batch_ms_per_frame": rule_batch_ms, "single_frame_ms_median": float(np.median(rule_single_ms))},
                "note": "Original fixed-default rule merges left/right; directional extension is a new heuristic. No held-out upright calibration used."}
    (output / "baseline_metrics.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    summary_rows, subject_rows = [], []
    for name in estimators:
        part = predictions[predictions.model == name]
        report = classification_report(part.actual, part.predicted, labels=range(4), target_names=LABELS, output_dict=True, zero_division=0)
        baseline.setdefault("ml_collapsed_3state", {})[name] = {
            "accuracy": float(accuracy_score(np.minimum(part.actual, 2), np.minimum(part.predicted, 2))),
            "report": classification_report(np.minimum(part.actual, 2), np.minimum(part.predicted, 2),
                labels=range(3), target_names=collapsed_labels, output_dict=True, zero_division=0)}
        (output / f"{name}_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        save_matrix(part.actual, part.predicted, output / f"{name}_confusion")
        per_person = []
        for subject, group in part.groupby("subject_id"):
            entry = {"model": name, "subject_id": subject, **metrics(group.actual, group.predicted)}
            per_person.append(entry)
            subject_rows.append(entry)
        row = {"model": name, **{f"pooled_{k}": v for k, v in metrics(part.actual, part.predicted).items()}}
        for metric in ("accuracy", "precision_macro", "recall_macro", "macro_f1"):
            values = [r[metric] for r in per_person]
            row[metric + "_mean"] = float(np.mean(values))
            row[metric + "_sd"] = float(np.std(values, ddof=1)) if len(values) > 1 else None
        for metric in ("training_seconds", "batch_ms_per_frame", "single_frame_ms_median"):
            row[metric] = float(results.loc[results.model == name, metric].mean())
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_csv(output / "comparison.csv", index=False)
    (output / "baseline_metrics.json").write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    subject_metrics = pd.DataFrame(subject_rows)
    subject_metrics.to_csv(output / "subject_metrics.csv", index=False)
    # Paired subject differences are descriptive, avoiding frame-level pseudo-replication.
    paired = subject_metrics.pivot(index="subject_id", columns="model", values="macro_f1")
    differences = []
    names = list(estimators)
    for i, a in enumerate(names):
        for b in names[i+1:]:
            delta = paired[a] - paired[b]
            differences.append({"model_a": a, "model_b": b, "n_subjects": len(delta),
                "mean_macro_f1_difference": float(delta.mean()), "sd_difference": float(delta.std()) if len(delta) > 1 else None,
                "subjects_a_better": int((delta > 0).sum()), "subjects_b_better": int((delta < 0).sum())})
    pd.DataFrame(differences).to_csv(output / "paired_comparison.csv", index=False)
    if args.mode == "loso":
        # Deployment selection is a separate group-CV on all reviewed data.
        # Its scores are NOT claimed as an independent performance estimate.
        deployment_cv = list(GroupKFold(n_splits=min(3, len(subjects))).split(X, y, groups))
        deployment_models, deployment_scores = {}, {}
        for name, models in estimators.items():
            model, score, _ = tune_model(models, X, y, deployment_cv, groups)
            deployment_models[name], deployment_scores[name] = model, score
        winner = max(deployment_scores, key=deployment_scores.get)
        best = deployment_models[winner].fit(X, y)
    else:
        deployment_scores = selection_scores
        best = joblib.load(output / f"{winner}.joblib")
    joblib.dump({"model": best, "name": winner, "features": FEATURES, "labels": LABELS,
                 "feature_version": VERSION, "model_sha256": df.model_sha256.iloc[0]}, output / "best_model.joblib")
    provenance = {"mode": args.mode, "seed": args.seed, "tuned": args.tune, "features": FEATURES,
                  "labels": LABELS, "dataset_sha256": digest(data), "feature_version": VERSION,
                  "model_sha256": df.model_sha256.iloc[0], "folds": fold_manifest, "selections": selections,
                  "deployment_model": winner, "deployment_selection_scores": deployment_scores,
                  "python": platform.python_version(), "platform": platform.platform(),
                  "versions": {p: __import__(p).__version__ for p in ("numpy", "pandas", "sklearn", "xgboost", "joblib")},
                  "limitations": "Subject mean +/- sample SD is descriptive, not significance. LOSO estimates each model's nested selection procedure; selecting a winner on all data needs fresh subjects to independently evaluate that winner. Timings exclude pose/features and network."}
    (output / "experiment.json").write_text(json.dumps(provenance, indent=2, default=str), encoding="utf-8")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r["model"] for r in summary_rows], [r["macro_f1_mean"] for r in summary_rows],
           yerr=[r["macro_f1_sd"] or 0 for r in summary_rows], capsize=4)
    ax.set(ylabel="Subject macro F1 (mean +/- sample SD)", ylim=(0, 1.1))
    fig.tight_layout()
    fig.savefig(output / "comparison.png", dpi=160)
    plt.close(fig)
    print(f"Results saved to {output}. Deployment configuration selected by validation: {winner}")
