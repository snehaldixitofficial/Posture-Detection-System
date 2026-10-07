// Full recorded-sample parity against Python, plus invalid-input checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const features = require('../posture-features.js');
const runtime = require('../model-runtime.js');
const fixture = JSON.parse(fs.readFileSync('results/browser_parity/fixtures.json'));
const models = Object.fromEntries(Object.keys(fixture.predictions).map(name => [name,
    JSON.parse(fs.readFileSync(`assets/models/${name}.json`))]));
let maximumFeatureError = 0;
fixture.rows.forEach((row,index) => {
    const values = features.extract(row.landmarks,row.width,row.height);
    values.forEach((value,i) => {
        const error = Math.abs(value-fixture.features[index][i]);
        maximumFeatureError = Math.max(maximumFeatureError,error);
        assert.ok(error < 1e-10, `Feature mismatch row ${index} feature ${i}`);
    });
    for (const [name,model] of Object.entries(models)) {
        assert.equal(runtime.predict(model,values),model.labels[fixture.predictions[name][index]], `${name} row ${index}`);
    }
});
const upperOnly = structuredClone(fixture.rows[0].landmarks);
for (let i=13;i<33;i++) upperOnly[i]=null;
assert.doesNotThrow(() => features.extract(upperOnly,640,480));
upperOnly[11].visibility=.1;
assert.throws(() => features.extract(upperOnly,640,480));
assert.throws(() => features.extract(null,640,480));
assert.throws(() => runtime.predict(models.Random_Forest,[NaN]));
const receipt = { samples: fixture.rows.length, predictionsChecked: fixture.rows.length*3,
    allLabelsMatch: true, maximumFeatureError, scope: 'Recorded sample parity; not a fresh webcam accuracy evaluation' };
fs.writeFileSync('results/browser_parity/verification.json',JSON.stringify(receipt,null,2));
console.log(receipt);
