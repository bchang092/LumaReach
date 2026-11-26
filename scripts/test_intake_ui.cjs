// DOM behavior tests, not visual/browser or physical microphone verification.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('../.local/ui-tests/node_modules/jsdom');
const html=fs.readFileSync('templates/intake.html','utf8').replace('{{ max_need_text_length }}','10000').replace('{% csrf_token %}','<input name="csrfmiddlewaretoken" value="test-token">');
const script=fs.readFileSync('static/intake.js','utf8');
const next=()=>new Promise(resolve=>setTimeout(resolve,0));
function setup({voice=false,serverVoice=false,response={route:'follow_up',message:'Need more detail',questions:['Groceries or meals?'],matches:[],crisis_resources:[],fallback_resources:[]},failure=false}={}){
 const dom=new JSDOM(html,{url:'http://localhost/help/',runScripts:'outside-only'}),w=dom.window,requests=[];
 w.HTMLElement.prototype.scrollIntoView=function(){};
 w.fetch=async(url,opts)=>{requests.push({url,opts});if(failure)throw new Error('Offline');return {ok:true,json:async()=>response};};
 let speech,recorder,stopped=false;
 if(serverVoice){
  w.document.querySelector('form').dataset.voiceApi='true';
  Object.defineProperty(w.navigator,'mediaDevices',{value:{getUserMedia:async()=>({getTracks:()=>[{stop(){stopped=true;}}]})}});
  w.MediaRecorder=class{
   static isTypeSupported(type){return type==='audio/webm';}
   constructor(){recorder=this;this.state='inactive';}
   start(){this.state='recording';}
   stop(){this.state='inactive';this.ondataavailable({data:new w.Blob(['test audio'],{type:'audio/webm'})});this.onstop();}
  };
 }

 if(voice)w.SpeechRecognition=class{constructor(){speech=this;}start(){this.onstart();}stop(){this.onend();}abort(){this.onend();}};
 w.eval(script);
 return {w,dom,requests,get speech(){return speech;},get recorder(){return recorder;},get stopped(){return stopped;},q:s=>w.document.querySelector(s),async submit(){w.document.querySelector('form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await next();}};
}

test('POST body only, no query PII, CSRF and no cache',async()=>{const x=setup();x.q('#need-text').value='I need groceries';await x.submit();assert.equal(x.requests.length,1);const r=x.requests[0];assert.equal(r.opts.method,'POST');assert.equal(r.opts.headers['X-CSRFToken'],'test-token');assert.equal(r.opts.cache,'no-store');assert.equal(JSON.parse(r.opts.body).need_text,'I need groceries');assert.equal(x.w.location.search,'');assert.equal(x.q('#questions').textContent.includes('Groceries or meals?'),true);x.dom.window.close();});
test('microphone unavailable leaves text form usable',()=>{const x=setup();assert.equal(x.q('#mic').disabled,true);assert.equal(x.q('#submit').disabled,false);x.dom.window.close();});
test('voice transcript editable and never auto-submitted',async()=>{const x=setup({voice:true});x.q('#mic').click();const utterance=[{transcript:'Need a meal'}];utterance.isFinal=true;x.speech.onresult({results:[utterance]});assert.equal(x.q('#need-text').value,'Need a meal ');assert.equal(x.requests.length,0);await x.submit();assert.equal(x.requests.length,0);x.q('#mic').click();x.q('#need-text').value='Need groceries instead';await x.submit();assert.equal(JSON.parse(x.requests[0].opts.body).need_text,'Need groceries instead');x.dom.window.close();});
test('clear removes transcript, result and late audio',()=>{const x=setup({voice:true});x.q('#need-text').value='Private words';x.q('#mic').click();x.q('#clear').click();const utterance=[{transcript:'Late private words'}];utterance.isFinal=true;x.speech.onresult({results:[utterance]});assert.equal(x.q('#need-text').value,'');assert.equal(x.q('#results').textContent,'');x.dom.window.close();});
test('page exit clears text and location',()=>{const x=setup();x.q('#need-text').value='Private';x.q('#location').value='21229';x.w.dispatchEvent(new x.w.Event('pagehide'));assert.equal(x.q('#need-text').value,'');assert.equal(x.q('#location').value,'');x.dom.window.close();});
test('service selections search without entering text',async()=>{const x=setup();x.q('[name=service]').click();await x.submit();const body=JSON.parse(x.requests[0].opts.body);assert.deepEqual(body.selected_needs,['need:food.pantry']);assert.equal(body.need_text,'');x.q('#clear').click();assert.equal(x.q('[name=service]').getAttribute('aria-pressed'),'false');x.dom.window.close();});
test('network failure restores search button',async()=>{const x=setup({failure:true});x.q('#need-text').value='Food';await x.submit();assert.equal(x.q('#submit').disabled,false);assert.match(x.q('#status').textContent,/Offline/);x.dom.window.close();});
test('results use text nodes, safe links and original numeric reliability',async()=>{const x=setup({response:{route:'matches',message:'Found',questions:[],crisis_resources:[],fallback_resources:[],unmet_needs:[],matches:[{resource:{resource_id:87,name:'<img src=x onerror=alert(1)>',description:'A pantry',address:'Baltimore',phone:'410-555-0100',website:'javascript:alert(1)',reliability_score:73.126,classification:'Reliable',verified_date:'2026-09-08'},reason:'Pantry',next_step:'Contact provider'}]}});x.q('#need-text').value='groceries';await x.submit();assert.equal(x.q('#results img'),null);assert.equal(x.q('#results a[href^="javascript:"]'),null);assert.equal(x.q('.score').textContent,'73.1');assert.equal(x.requests.length,1);x.q('.feedback button').click();await next();assert.equal(JSON.parse(x.requests[1].opts.body).helpful,true);assert.equal('comment' in JSON.parse(x.requests[1].opts.body),false);x.dom.window.close();});
test('crisis result has emergency contacts and no normal cards',async()=>{const x=setup({response:{route:'crisis',message:'Immediate help',questions:[],matches:[],crisis_resources:[{name:'Emergency services',phone:'911',description:'Emergency response'}],fallback_resources:[]}});x.q('#need-text').value='Immediate danger';await x.submit();assert.ok(x.q('.crisis'));assert.equal(x.q('.resource-card'),null);assert.equal(x.q('.crisis a').href,'tel:911');x.dom.window.close();});


test('server voice transcribes only after stop and never searches automatically',async()=>{
 const x=setup({serverVoice:true,response:{text:'Need groceries'}});x.q('#mic').click();await next();
 assert.equal(x.recorder.state,'recording');assert.equal(x.requests.length,0);
 x.q('#mic').click();await next();
 assert.equal(x.stopped,true);assert.equal(x.requests.length,1);assert.match(x.requests[0].url,/transcribe/);
 assert.equal(x.requests[0].opts.headers['X-CSRFToken'],'test-token');assert.equal(x.q('#need-text').value,'Need groceries');
 assert.equal(x.q('#mic').getAttribute('aria-pressed'),'false');x.dom.window.close();
});
test('clearing a server recording discards audio and stops microphone',async()=>{
 const x=setup({serverVoice:true});x.q('#mic').click();await next();x.q('#clear').click();await next();
 assert.equal(x.stopped,true);assert.equal(x.requests.length,0);assert.equal(x.q('#need-text').value,'');x.dom.window.close();
});
test('late server transcript cannot restore cleared words',async()=>{
 const x=setup({serverVoice:true});let resolve;
 x.w.fetch=()=>new Promise(r=>{resolve=r;});x.q('#mic').click();await next();x.q('#mic').click();await next();
 x.q('#clear').click();resolve({ok:true,json:async()=>({text:'Late private words'})});await next();
 assert.equal(x.q('#need-text').value,'');assert.equal(x.q('#mic').disabled,false);x.dom.window.close();
});
test('microphone permission denial restores controls',async()=>{
 const x=setup({serverVoice:true});x.w.navigator.mediaDevices.getUserMedia=async()=>{throw new Error('Denied');};
 x.q('#mic').click();await next();assert.equal(x.q('#mic').disabled,false);assert.match(x.q('#voice-status').textContent,/permission/);
 assert.equal(x.requests.length,0);x.dom.window.close();
});
test('clearing while microphone permission is pending stops the acquired stream',async()=>{
 const x=setup({serverVoice:true});let resolve,stopped=false;
 x.w.navigator.mediaDevices.getUserMedia=()=>new Promise(r=>{resolve=r;});x.q('#mic').click();x.q('#clear').click();
 resolve({getTracks:()=>[{stop(){stopped=true;}}]});await next();assert.equal(stopped,true);assert.equal(x.requests.length,0);x.dom.window.close();
});
test('late search results cannot repopulate cleared page',async()=>{
 const x=setup();let resolve;x.w.fetch=()=>new Promise(r=>{resolve=r;});x.q('#need-text').value='groceries';
 const pending=x.submit();x.q('#clear').click();resolve({ok:true,json:async()=>({message:'Private result',questions:[],matches:[],crisis_resources:[],fallback_resources:[]})});
 await pending;assert.equal(x.q('#results').textContent,'');assert.equal(x.q('#status').textContent,'Your search has been cleared.');assert.equal(x.q('#submit').disabled,false);x.dom.window.close();
});
