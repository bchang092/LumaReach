const {test}=require('node:test');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {JSDOM}=require('../.local/ui-tests/node_modules/jsdom');
test('rendered map subtype filter, reset and reliability sidebar',()=>{
 const html=execFileSync('.venv/bin/python',['-B','-c',`import os,io,contextlib
os.environ.setdefault('DJANGO_SETTINGS_MODULE','BmoreLline.settings')
import django
django.setup()
from django.test import Client
with contextlib.redirect_stdout(io.StringIO()):
 r=Client(HTTP_HOST='localhost').get('/map/')
assert r.status_code==200
print(r.content.decode())`],{encoding:'utf8',maxBuffer:15000000});
 const dom=new JSDOM(html,{url:'http://localhost/map/',runScripts:'outside-only'}),w=dom.window;
 let markers=[];
 const map={on(){},fitBounds(){},setView(){},invalidateSize(){}};
 const layer={addTo(){return this;},clearLayers(){markers=[];}};
 w.L={map:()=>map,control:{zoom:()=>({addTo(){}})},tileLayer:()=>({addTo(){}}),layerGroup:()=>layer,divIcon:x=>x,marker:(pos,opts)=>({on(event,fn){this.click=fn;},addTo(){markers.push(this);}})};
 w.fetch=async()=>({ok:true,json:async()=>({count:1341})});
 for(const script of w.document.querySelectorAll('script'))if(!script.src&&script.type!=='application/json')w.eval(script.textContent);
 const select=w.document.querySelector('#serviceFilter');
 assert.ok(select.options.length>30);
 assert.equal(markers.length,1341);
 select.value='need:food.prepared_meals';select.dispatchEvent(new w.Event('change',{bubbles:true}));
 assert.ok(markers.length>0&&markers.length<20);
 assert.ok(w.document.querySelector('#resetBtn').classList.contains('active'));
 markers[0].click();assert.match(w.document.querySelector('#sidebar').textContent,/\/100/);
 w.document.querySelector('#resetBtn').click();assert.equal(select.value,'');assert.equal(markers.length,1341);
 dom.window.close();
});
