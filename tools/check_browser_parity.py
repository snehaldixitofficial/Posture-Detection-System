"""Generate private parity fixtures. Never put fixtures in the deployment."""
import json
from pathlib import Path
import joblib
from research.features import extract_features, FEATURES

source = Path('data/session_S01_20261006T191350Z_quality_v3/landmarks.jsonl')
rows = [json.loads(line) for line in source.read_text().splitlines()]
features = [[extract_features(r['landmarks'], r['width'], r['height'])[f] for f in FEATURES] for r in rows]
predictions = {name: joblib.load(f'results/pilot_S01/{name}.joblib').predict(features).tolist()
               for name in ('Random_Forest','SVM_RBF','XGBoost')}
Path('results/browser_parity').mkdir(exist_ok=True)
Path('results/browser_parity/fixtures.json').write_text(json.dumps(dict(rows=rows, features=features, predictions=predictions)))
