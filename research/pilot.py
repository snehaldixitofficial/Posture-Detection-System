"""One-person pilot: whole take 03 held out; selection uses only take 02."""
import json
import platform
import re
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import classification_report, accuracy_score

from .dataset import digest
from .features import FEATURES, LABELS, VERSION, rule_predictions
from .train import candidates, metrics, save_matrix


def split_pilot(df, gap_ms=2000):
    """Chronological 70/30 tuning blocks with a temporal gap; disjoint test videos."""
    if df.subject_id.nunique() != 1:
        raise ValueError("pilot mode requires exactly one participant")
    parsed = df.video_path.map(lambda p: re.search(r'_(\d+)\.mp4$', p))
    if parsed.isna().any():
        raise ValueError('video names must end with a numbered MP4 take')
    takes = parsed.map(lambda m: int(m.group(1)))
    if set(takes) != {2, 3}:
        raise ValueError("pilot protocol requires takes 02 and 03")
    for take in (2, 3):
        counts = df.loc[takes == take].groupby('posture').video_path.nunique()
        if set(counts.index) != set(LABELS) or not (counts == 1).all():
            raise ValueError('each take requires exactly one video per posture class')
    development = np.flatnonzero(takes == 2)
    test = np.flatnonzero(takes == 3)
    training, validation, excluded = [], [], []
    for video, part in df.loc[development].groupby("video_path"):
        boundary = part.timestamp_ms.min() + .7 * (part.timestamp_ms.max() - part.timestamp_ms.min())
        training.extend(part.index[part.timestamp_ms < boundary - gap_ms / 2])
        validation.extend(part.index[part.timestamp_ms > boundary + gap_ms / 2])
        excluded.extend(part.index[(part.timestamp_ms >= boundary - gap_ms / 2) & (part.timestamp_ms <= boundary + gap_ms / 2)])
    indices = tuple(np.array(a, dtype=int) for a in (training, validation, development, test, excluded))
    for subset in indices[:4]:
        if set(df.iloc[subset].posture) != set(LABELS):
            raise ValueError("each split must contain all four classes")
    assert not set(df.iloc[development].video_path) & set(df.iloc[test].video_path)
    assert not set(training) & set(validation)
    return indices


def train(args):
    source = Path(args.data)
    receipt = json.loads(Path(str(source) + '.review.json').read_text())
    if receipt['clean_sha256'] != digest(source):
        raise ValueError('reviewed dataset changed')
    df = pd.read_csv(source, dtype={'subject_id': str, 'row_id': str}).reset_index(drop=True)
    if df.row_id.duplicated().any() or set(df.feature_version) != {VERSION} or df.model_sha256.nunique() != 1:
        raise ValueError('duplicate rows or incompatible feature/model versions')
    if set(df.posture) != set(LABELS) or df[list(FEATURES)].isna().any().any():
        raise ValueError('all four labels and finite complete features are required')
    X = df[list(FEATURES)].to_numpy(float)
    if not np.isfinite(X).all():
        raise ValueError('nonfinite features')
    y = df.posture.map(dict(zip(LABELS, range(4)))).to_numpy()
    a, b, development, test, excluded = split_pilot(df)
    output = Path(args.output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('preserve existing experiment; use an empty output directory')
    output.mkdir(parents=True, exist_ok=True)
    split = {'mode': 'single_person_video_holdout', 'subject': df.subject_id.iloc[0], 'seed': args.seed,
             'selection': 'first 70% versus last 30% of take 02, with 2-second exclusion gap',
             'test': 'all take 03 videos; never used for selection',
             'row_ids': {k: df.row_id.iloc[v].tolist() for k, v in
                         [('tuning_train', a), ('validation', b), ('development_refit', development), ('test', test), ('gap', excluded)]},
             'videos': {k: sorted(set(df.video_path.iloc[v])) for k, v in [('development', development), ('test', test)]}}
    # Persist the split before fitting or evaluating any model.
    (output / 'split.json').write_text(json.dumps(split, indent=2), encoding='utf-8')
    chosen, selection = {}, {}
    for name, options in candidates(args.seed, args.tune).items():
        scores = []
        for option in options:
            fitted = clone(option).fit(X[a], y[a])
            scores.append(metrics(y[b], fitted.predict(X[b]))['macro_f1'])
        index = int(np.argmax(scores))
        chosen[name] = clone(options[index])
        selection[name] = {'validation_macro_f1': scores[index], 'candidate_scores': scores,
                           'parameters': chosen[name].get_params()}
    winner = max(selection, key=lambda n: selection[n]['validation_macro_f1'])
    (output / 'selection.json').write_text(json.dumps({'winner': winner, 'models': selection}, indent=2, default=str), encoding='utf-8')
    comparison, predictions, fitted_models = [], [], {}
    for name, estimator in chosen.items():
        started = time.perf_counter()
        fitted = estimator.fit(X[development], y[development])
        seconds = time.perf_counter() - started
        fitted_models[name] = fitted
        joblib.dump(fitted, output / f'{name}.joblib')
        fitted.predict(X[test][:1])
        started = time.perf_counter()
        pred = fitted.predict(X[test])
        batch_ms = 1000 * (time.perf_counter() - started) / len(test)
        times = []
        for i in test[:100]:
            started = time.perf_counter()
            fitted.predict(X[i:i+1])
            times.append(1000 * (time.perf_counter() - started))
        comparison.append({'model': name, **metrics(y[test], pred), 'validation_macro_f1': selection[name]['validation_macro_f1'],
                           'training_seconds': seconds, 'batch_ms_per_frame': batch_ms, 'single_frame_ms_median': float(np.median(times))})
        predictions.extend({'row_id': df.row_id.iloc[i], 'video_path': df.video_path.iloc[i], 'model': name,
                            'actual': LABELS[y[i]], 'predicted': LABELS[int(p)]} for i, p in zip(test, pred))
        report = classification_report(y[test], pred, labels=range(4), target_names=LABELS, output_dict=True, zero_division=0)
        (output / f'{name}_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        save_matrix(y[test], pred, output / f'{name}_confusion')
    pd.DataFrame(comparison).to_csv(output / 'comparison.csv', index=False)
    pd.DataFrame(predictions).to_csv(output / 'predictions.csv', index=False)
    exact, directional = rule_predictions(df.iloc[test].to_dict('records'))
    actual3 = np.minimum(y[test], 2)
    pred3 = np.array([{'Correct': 0, 'Slouch': 1, 'Lean': 2}[p] for p in exact])
    pred4 = np.array([LABELS.index(p) for p in directional])
    labels3 = ('Correct', 'Slouch', 'Lean')
    baseline = {'original_rule_3state': classification_report(actual3, pred3, labels=range(3), target_names=labels3, output_dict=True, zero_division=0),
                'directional_extension_4class': metrics(y[test], pred4), 'ml_collapsed_3state': {}}
    save_matrix(actual3, pred3, output / 'original_rule_3state', labels3)
    save_matrix(y[test], pred4, output / 'directional_rule_4class')
    for name, model in fitted_models.items():
        p = np.minimum(model.predict(X[test]), 2)
        baseline['ml_collapsed_3state'][name] = classification_report(actual3, p, labels=range(3), target_names=labels3, output_dict=True, zero_division=0)
    pd.DataFrame({'row_id': df.row_id.iloc[test].to_numpy(), 'actual': df.posture.iloc[test].to_numpy(),
                  'original_rule': exact, 'directional_extension': directional}).to_csv(output / 'baseline_predictions.csv', index=False)
    (output / 'baseline_metrics.json').write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    # The scored models above remain frozen. This separate refit is for personal live use.
    started = time.perf_counter()
    deployment = clone(chosen[winner]).fit(X, y)
    refit_seconds = time.perf_counter() - started
    joblib.dump({'model': deployment, 'name': winner, 'features': FEATURES, 'labels': LABELS,
                 'feature_version': VERSION, 'model_sha256': df.model_sha256.iloc[0],
                 'evaluation_mode': 'single-person pilot; deployment refit uses all recordings'}, output / 'best_model.joblib')
    limitations = ('One person, one environment, two takes per class. Test videos are disjoint but from the same recording session. '
                   'Tuning blocks share training videos; temporal dependence remains despite the gap. '
                   'No between-person generalization, subject SD, significance test, or clinical slouch assessment is supported. '
                   'Slouch is the recorded head/shoulder protocol gesture. Assistant sample review is not exhaustive human video review. '
                   'Deployment refit includes test data, so test scores describe the frozen take-02 models only. Timings exclude pose extraction and transport.')
    experiment = {'mode': 'single_person_video_holdout', 'winner': winner, 'rows': len(df), 'development_rows': len(development),
                  'test_rows': len(test), 'tuning_train_rows': len(a), 'validation_rows': len(b), 'gap_rows': len(excluded),
                  'class_counts': df.posture.value_counts().to_dict(), 'features': FEATURES, 'labels': LABELS,
                  'feature_version': VERSION, 'model_sha256': df.model_sha256.iloc[0], 'dataset_sha256': digest(source),
                  'review': receipt, 'seed': args.seed, 'tuned': args.tune, 'deployment_refit_seconds': refit_seconds,
                  'python': platform.python_version(), 'platform': platform.platform(),
                  'versions': {p: __import__(p).__version__ for p in ('numpy', 'pandas', 'sklearn', 'xgboost', 'joblib')},
                  'limitations': limitations}
    (output / 'experiment.json').write_text(json.dumps(experiment, indent=2), encoding='utf-8')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([r['model'] for r in comparison], [r['macro_f1'] for r in comparison])
    ax.set(ylabel='Macro F1 on S01 take 03', ylim=(0, 1.05), title='Single-person pilot: video holdout')
    fig.tight_layout()
    fig.savefig(output / 'comparison.png', dpi=160)
    plt.close(fig)
    lines = ['# S01 head-and-shoulders pilot results', '',
             f'Trained Random Forest, RBF SVM and XGBoost on {len(development)} take-02 frames; evaluated on {len(test)} separate take-03 frames. '
             f'The complete reviewed dataset contains {len(df)} frames from eight videos, one participant and four protocol classes.', '',
             f'Hyperparameters and the live model ({winner}) were chosen using {len(a)} early training frames and {len(b)} late validation frames from take 02. '
             f'{len(excluded)} frames in the two-second boundary gaps were excluded from tuning. No take-03 frames entered model selection.', '',
             '| Model | Test accuracy | Macro precision | Macro recall | Macro F1 | Validation F1 | Training seconds | Median prediction ms |',
             '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in comparison:
        lines.append(f"| {r['model']} | {r['accuracy']:.4f} | {r['precision_macro']:.4f} | {r['recall_macro']:.4f} | {r['macro_f1']:.4f} | {r['validation_macro_f1']:.4f} | {r['training_seconds']:.3f} | {r['single_frame_ms_median']:.3f} |")
    lines += ['', f"Original three-state rules: accuracy {baseline['original_rule_3state']['accuracy']:.4f}, macro F1 {baseline['original_rule_3state']['macro avg']['f1-score']:.4f}. "
              f"The separately named four-class directional extension: accuracy {baseline['directional_extension_4class']['accuracy']:.4f}, macro F1 {baseline['directional_extension_4class']['macro_f1']:.4f}. "
              'The JSON also reports each ML model collapsed to three states for a fair comparison with the original rule.', '',
              'Saved outputs include all three frozen test models, a separately refitted live winner, per-class reports, confusion matrices, predictions, '
              'comparison chart, selected parameters, split row IDs and checksum provenance. The feature extractor uses only visible head/shoulder landmarks; hidden hips are ignored.', '',
              limitations, '', 'Completed for this pilot: collection, landmark extraction, sample review, cleaning, model fitting/tuning, '
              'held-out-video evaluation, baseline comparisons, saved artifacts and local live integration. '
              'Multi-person collection and subject-independent evaluation remain future work.']
    report_text = '\n'.join(lines) + '\n'
    (output / 'REPORT.md').write_text(report_text, encoding='utf-8')
    Path('docs/PILOT_RESULTS_S01.md').write_text(report_text, encoding='utf-8')
    print(pd.DataFrame(comparison).to_string(index=False))
    print(f'Validation-selected live model: {winner}. Results: {output}')
