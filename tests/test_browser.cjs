// Controller contracts with mocked camera and deterministic pose output.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const features=require('../posture-features.js'),runtime=require('../model-runtime.js');
const fixture=JSON.parse(fs.readFileSync('results/browser_parity/fixtures.json'));
const ids=[...fs.readFileSync('index.html','utf8').matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
const elements=new Map(ids.map(id=>[id,{textContent:'',hidden:false,disabled:false,style:{},checked:true,
 value:id==='classifier-mode'?'Random_Forest':'',selectedIndex:0,options:[{text:'Random Forest'}],
 handlers:{},addEventListener(event,fn){this.handlers[event]=fn;},classList:{toggle(){}},
 getContext(){return {drawImage(){},clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},arc(){},fill(){}};},
 width:640,height:480,videoWidth:640,videoHeight:480,readyState:2,currentTime:1,async play(){}}]));
let ticks=100,stopped=false;
const sandbox={document:{getElementById:id=>elements.get(id)},window:{addEventListener(){}},
 navigator:{mediaDevices:{async getUserMedia(){return {getTracks:()=>[{stop(){stopped=true;}}]};}}},
 performance:{now:()=>ticks++},setInterval(){},requestAnimationFrame(){},console,
 PostureFeatures:features,PostureModels:runtime};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync('script.js','utf8'),sandbox);
sandbox.models=Object.fromEntries(['Random_Forest','SVM_RBF','XGBoost'].map(name=>[name,JSON.parse(fs.readFileSync('assets/models/'+name+'.json'))]));
sandbox.landmarks=structuredClone(fixture.rows[0].landmarks);
for(let i=13;i<33;i++) sandbox.landmarks[i]=null;
vm.runInContext('state.models=models;state.pose={detectForVideo:()=>({landmarks:[landmarks]})};',sandbox);
(async()=>{
 await vm.runInContext('startCamera()',sandbox);
 assert.equal(vm.runInContext('state.running',sandbox),true);
 assert.equal(elements.get('start-btn').disabled,true);
 assert.equal(elements.get('stop-btn').disabled,false);
 assert.equal(elements.get('live-Random_Forest').textContent,'Correct posture');
 elements.get('classifier-mode').value='SVM_RBF';elements.get('classifier-mode').handlers.change();
 assert.match(elements.get('model-status').textContent,/SVM RBF/);
 elements.get('input_video').currentTime++;
 vm.runInContext('processFrame()',sandbox);
 assert.equal(elements.get('status-overlay').textContent,'Correct posture');
 vm.runInContext("showPrediction('Slouch');showPrediction('Slouch')",sandbox);
 assert.equal(elements.get('slouch-count').textContent,1);
 sandbox.landmarks[11].visibility=.1;elements.get('input_video').currentTime++;
 vm.runInContext('processFrame()',sandbox);
 assert.match(elements.get('status-overlay').textContent,/Show your head/);
 assert.equal(elements.get('live-SVM_RBF').textContent,'Waiting');
 assert.equal(vm.runInContext('state.features',sandbox),null);
 elements.get('classifier-mode').value='rules';elements.get('classifier-mode').handlers.change();
 assert.equal(elements.get('calibrate-btn').hidden,false);
 sandbox.landmarks[11].visibility=.99;elements.get('input_video').currentTime++;
 vm.runInContext('processFrame()',sandbox);elements.get('calibrate-btn').handlers.click();
 assert.equal(elements.get('calibration-status').textContent,'Calibrated');
 vm.runInContext('stopCamera()',sandbox);
 assert.equal(stopped,true);assert.equal(elements.get('input_video').srcObject,null);
 assert.equal(elements.get('status-overlay').textContent,'Camera stopped');
 console.log('Controller checks passed: startup, switching, events, invalid tracking, rule calibration, camera release.');
})().catch(error=>{console.error(error);process.exitCode=1;});
