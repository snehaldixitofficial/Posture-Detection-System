"""Export the frozen, evaluated models for readable browser inference.

Only learned parameters and aggregate scores are public. Recordings stay private.
Run from the project root with the research virtual environment.
"""
import json
import shutil
from pathlib import Path
import joblib
import pandas as pd
from research.features import FEATURES, LABELS, VERSION

OUT = Path('assets/models')
OUT.mkdir(parents=True, exist_ok=True)
for name in ('Random_Forest', 'SVM_RBF', 'XGBoost'):
    model = joblib.load(f'results/pilot_S01/{name}.joblib')
    payload = dict(name=name, labels=LABELS, features=FEATURES, feature_version=VERSION)
    if name == 'Random_Forest':
        payload['trees'] = [dict(left=t.tree_.children_left.tolist(),
            right=t.tree_.children_right.tolist(), feature=t.tree_.feature.tolist(),
            threshold=t.tree_.threshold.tolist(), values=t.tree_.value[:, 0, :].tolist())
            for t in model.estimators_]
    elif name == 'SVM_RBF':
        scaler, svc = model.named_steps.values()
        payload.update(mean=scaler.mean_.tolist(), scale=scaler.scale_.tolist(),
            support=svc.support_vectors_.tolist(), counts=svc.n_support_.tolist(),
            coefficients=svc.dual_coef_.tolist(), intercept=svc.intercept_.tolist(), gamma=svc._gamma)
    else:
        learner = json.loads(model.get_booster().save_raw(raw_format='json'))['learner']
        booster = learner['gradient_booster']['model']
        payload.update(base=json.loads(learner['learner_model_param']['base_score']),
            groups=booster['tree_info'], trees=[dict(left=t['left_children'],
            right=t['right_children'], feature=t['split_indices'], threshold=t['split_conditions'])
            for t in booster['trees']])
    (OUT / f'{name}.json').write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')
scores = pd.read_csv('results/pilot_S01/comparison.csv').to_dict('records')
(OUT / 'comparison.json').write_text(json.dumps(scores), encoding='utf-8')
shutil.copyfile('models/pose_landmarker_lite.task', 'assets/pose_landmarker_lite.task')
Path('assets/paper').mkdir(exist_ok=True)
for filename in ('STAY_UPRIGHT_IEEE.pdf', 'STAY_UPRIGHT_IEEE.tex'):
    shutil.copyfile('docs/paper/' + filename, 'assets/paper/' + filename)
print('Exported three frozen models, pinned pose asset, aggregate scores and paper.')

Path("assets/docs").mkdir(exist_ok=True)
for filename in ("DEMO_GUIDE.md", "CODE_WALKTHROUGH.md"):
    shutil.copyfile("docs/" + filename, "assets/docs/" + filename)
