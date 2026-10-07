"""Exploratory S01 paper analyses; no deployment reselection."""
import json,sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from sklearn.base import clone
from research.dataset import digest
from research.features import FEATURES,LABELS
from research.pilot import split_pilot
from research.train import candidates,metrics
source=Path('data/session_S01_20261006T191350Z_quality_v3/features_clean.csv')
output=Path('results/paper_analysis_S01')
if output.exists() and any(output.iterdir()): raise ValueError('preserve existing analysis')
output.mkdir(parents=True,exist_ok=True)
df=pd.read_csv(source); receipt=json.loads(Path(str(source)+'.review.json').read_text()); assert receipt['clean_sha256']==digest(source)
a,b,dev,test,gap=split_pilot(df); frozen=json.loads(Path('results/pilot_S01/split.json').read_text())
for name,ids in zip(('tuning_train','validation','development_refit','test','gap'),(a,b,dev,test,gap)):
 assert df.row_id.iloc[ids].tolist()==frozen['row_ids'][name]
y=df.posture.map(dict(zip(LABELS,range(4)))).to_numpy()
sets={'Legacy_2':('f1','f2'),'Legacy_signed_3':('f1','f2','face_asymmetry'),'Head_shoulder_2D_18':tuple(f for f in FEATURES if f not in ('head_depth_proxy','ear_depth_proxy','face_shoulder_depth_asymmetry')),'Full_21':FEATURES}
rows,selected=[],[]
for group,features in sets.items():
 X=df[list(features)].to_numpy(float)
 for name,options in candidates(42,True).items():
  scores=[metrics(y[b],clone(model).fit(X[a],y[a]).predict(X[b]))['macro_f1'] for model in options]
  best=int(np.argmax(scores)); model=clone(options[best]).fit(X[dev],y[dev]); pred=model.predict(X[test])
  rows.append({'feature_set':group,'feature_count':len(features),'model':name,'validation_macro_f1':scores[best],**metrics(y[test],pred)})
  selected.append({'feature_set':group,'model':name,'features':features,'candidate_scores':scores,'parameters':model.get_params()})
pd.DataFrame(rows).to_csv(output/'feature_ablation.csv',index=False)
old=Path('data/session_S01_20261006T191350Z'); new=source.parent
om=json.loads((old/'extraction.json').read_text()); nm=json.loads((new/'extraction.json').read_text())
for key in ('manifest_sha256','model_sha256','sample_fps','visibility'): assert om[key]==nm[key]
o=pd.read_csv(old/'features.csv'); n=pd.read_csv(new/'features.csv'); assert set(o.row_id)<=set(n.row_id)
assert [v['video_sha256'] for v in om['videos']]==[v['video_sha256'] for v in nm['videos']]
quality=[]
for label in LABELS:
 before=int((o.posture==label).sum()); after=int((n.posture==label).sum()); quality.append({'class':label,'upright_assuming_gate_retained':before,'revised_gate_retained':after,'recovered':after-before,'historical_rejection_fraction':(after-before)/after})
pd.DataFrame(quality).to_csv(output/'quality_gate_audit.csv',index=False)
errors=[]; pred=pd.read_csv('results/pilot_S01/predictions.csv').merge(df[['row_id','timestamp_ms']],on='row_id',validate='many_to_one')
for (model,video),part in pred.groupby(['model','video_path']):
 wrong=part[part.actual!=part.predicted]; errors.append({'model':model,'video_path':video,'frames':len(part),'errors':len(wrong),'first_error_ms':wrong.timestamp_ms.min() if len(wrong) else None,'last_error_ms':wrong.timestamp_ms.max() if len(wrong) else None})
pd.DataFrame(errors).to_csv(output/'video_error_analysis.csv',index=False)
meta={'purpose':'Exploratory post hoc ablation and historical quality-gate audit; not fresh confirmatory evaluation','dataset_sha256':digest(source),'split_sha256':digest('results/pilot_S01/split.json'),'selection':selected,'limitations':'Same one-person held-out videos reused. No deployment model changed. Quality audit describes two historical extraction artifacts, not independently validated landmark ground truth.'}
(output/'analysis.json').write_text(json.dumps(meta,indent=2,default=str))
print(pd.DataFrame(rows).to_string(index=False)); print(pd.DataFrame(quality).to_string(index=False)); print(pd.DataFrame(errors).query('errors > 0').to_string(index=False))
