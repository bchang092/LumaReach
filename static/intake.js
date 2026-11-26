(() => {
  'use strict';
  const form=document.querySelector('#intake-form'), text=document.querySelector('#need-text');
  const location=document.querySelector('#location'), status=document.querySelector('#status');
  const results=document.querySelector('#results'), questions=document.querySelector('#questions');
  const submit=document.querySelector('#submit'), mic=document.querySelector('#mic');
  const csrf=form.querySelector('[name=csrfmiddlewaretoken]').value;
  let recognition=null, listening=false, prefix='', requestController=null, generation=0;
  let cancelVoice=()=>{};
  const el=(tag,content,cls)=>{const n=document.createElement(tag);if(content)n.textContent=content;if(cls)n.className=cls;return n;};
  function link(label,url){const n=el('a',label);try{const u=new URL(url,window.location.origin);if(['http:','https:','tel:','sms:'].includes(u.protocol)){n.href=u.href;n.rel='noreferrer noopener';}}catch{}return n;}
  async function post(url,data,signal){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(data),cache:'no-store',credentials:'same-origin',signal});const d=await r.json();if(!r.ok)throw new Error(d.error||'Please try again.');return d;}
  function contact(r){const links=el('div','', 'resource-links');if(r.phone)links.append(link(`Call ${r.phone}`,r.phone_link||'tel:'+String(r.phone).replace(/[^+\d]/g,'')));if(r.website)links.append(link('Provider website',r.website));return links;}
  function showContacts(items,heading,cls){if(!items.length)return;const section=el('section','',cls);section.append(el('h2',heading));for(const r of items){const a=el('article');a.append(el('h3',r.name),el('p',r.description),contact(r));section.append(a);}results.append(section);}
  function render(data){results.replaceChildren();questions.replaceChildren();status.textContent=data.message;
    for(const question of data.questions){questions.append(el('p',question));}
    if(data.questions.length){questions.append(el('p','Choose a service or add details above, then search again.'));}
    showContacts(data.crisis_resources,'Get immediate support / Ayuda inmediata','crisis');
    if(data.extraction_mode==='local_fallback')questions.append(el('p','We used keyword matching because AI-assisted matching was unavailable.'));
    else if(data.extraction_mode==='llm')questions.append(el('p','AI interpreted your description to search the resource directory.'));
    else if(data.extraction_mode==='local')questions.append(el('p','Using basic keyword matching. Review the service details before contacting a provider.'));
    if(data.priorities?.length) renderPriorities(data);
    else for(const match of data.matches)results.append(resourceCard(match));
    if(data.route!=='crisis')showContacts(data.fallback_resources,'Need more help?','fallback');
    if(data.priorities?.length||data.crisis_resources.length){results.focus();results.scrollIntoView({behavior:'auto',block:'start'});}
  }
  function resourceCard(match){
    const r=match.resource,card=el('article','', 'resource-card'),main=el('div'),meta=el('aside','', 'resource-meta');
      main.append(el('h3',(match.rank?match.rank+'. ':'')+r.name),el('p',match.reason),el('p',match.next_step,'small'),contact(r));
      if(match.matched_needs?.length)main.append(el('p','Matches: '+match.matched_needs.map(n=>n.replace('need:','').replace(/[._]/g,' ')).join(' · '),'small'));
      if(match.distance_miles_approx!=null)main.append(el('p',`About ${match.distance_miles_approx} miles from ${match.distance_origin}. Straight-line estimate; travel and service area must be confirmed.`,'small'));
      if(match.score_breakdown){const why=el('details');why.append(el('summary','Why this position?'));why.append(el('p','Relative match score: '+match.match_score+'. Among equally suitable services, source reliability and estimated proximity carry equal weight. This is not an eligibility or quality rating.'));main.append(why);}
      if(r.address)main.append(el('p',String(r.address),'small'));
      const details=el('details'),summary=el('summary','Service details & requirements');details.append(summary,el('p',r.display_description||r.description));if(r.restrictions)details.append(el('p','Reported requirements: '+r.restrictions));if(r.hours)details.append(el('p','Reported site hours (confirm program intake): '+r.hours));main.append(details);
      meta.append(el('p','SOURCE RELIABILITY','eyebrow'),el('p',typeof r.reliability_score==='number'?r.reliability_score.toFixed(1)+' / 100':'Not scored','score'),el('p',r.classification),el('p','Checked '+(r.verified_date||'date unknown')));
      meta.append(el('p','Original scraped score. It is not a guarantee of eligibility or availability.','small'));
      const feedback=el('div','Was this helpful?','feedback');for(const [label,helpful] of [['Yes',true],['No',false]]){const b=el('button',label);b.type='button';b.addEventListener('click',async()=>{feedback.querySelectorAll('button').forEach(x=>x.disabled=true);try{await post('/api/recommendation-feedback/',{resource_id:r.resource_id,helpful});feedback.textContent='Thank you. Your response was saved.';}catch{feedback.textContent='Could not save your response. Please try later.';}});feedback.append(b);}main.append(feedback);card.append(main,meta);return card;
  }
  const needLabels = {
    'housing.emergency_shelter':'Emergency shelter', 'housing.supportive_transitional':'Transitional housing',
    'housing.rental':'Affordable rental housing', 'housing.rent_eviction_help':'Rent and eviction help',
    'food.prepared_meals':'Ready-to-eat meals', 'food.pantry':'Groceries and food pantries',
    'food.general_assistance':'Food assistance', 'benefits.enrollment_navigation':'Help applying for benefits',
    'legal.identity_documents':'Replacing ID and documents', 'employment.training_search':'Finding work and job training',
    'transportation.assistance':'Transportation help', 'digital.computers_internet':'Computer and internet access',
    'medical.dental':'Dental care', 'medical.general':'General medical care', 'medical.cost_assistance':'Help paying for medical care',
    'mental_health.clinical':'Mental health care', 'mental_health.peer_support':'Peer support groups',
    'essentials.clothing_supplies':'Clothing and hygiene supplies', 'legal.assistance':'Legal help',
    'legal.housing_disputes':'Tenant rights and housing disputes', 'financial.counseling':'Financial counseling',
    'financial.emergency_assistance':'Emergency financial assistance', 'utilities.bill_assistance':'Utility bill help'
  };
  function needLabel(need){
    const key=need.replace(/^need:/,'');
    const label=needLabels[key] || key.replaceAll('_',' ').replace('.', ' – ');
    return label.charAt(0).toUpperCase()+label.slice(1);
  }
  function renderPriorities(data){
    const records=new Map(data.matches.map(m=>[m.resource.resource_id,m.resource]));
    for(const record of Object.values(data.additional_sources))records.set(record.resource_id,record);
    results.append(el('h2','Your help priorities'));
    const list=el('ol','','priorities');
    for(const [index,priority] of data.priorities.entries()){
      const item=el('li'), panel=el('details'), summary=el('summary');
      const count=priority.sources.length;
      const leads=Boolean(priority.sources[0]?.unverified_requirements);
      summary.append(el('strong', (index+1)+'. '+needLabel(priority.need)),
        el('span',count ? count+(leads?' to contact':' resource'+(count===1?'':'s')) : 'No confirmed matches','small'));
      const content=el('div');
      function fill(){
        if(content.childElementCount)return;
        if(!count)content.append(el('p','The directory could not confirm a provider for this need with the requirements in your search.'));
        for(const [i,source] of priority.sources.entries()){
          content.append(resourceCard({...source,resource:records.get(source.resource_id),rank:i+1,
            score_breakdown:!leads,next_step:leads
              ? 'Before you go, ask about '+source.unverified_requirements.map(value=>value.replaceAll('_',' ')).join(', ')+'. The directory could not verify these requirements.'
              : 'Contact the provider to confirm intake, availability and eligibility.'}));
        }
      }
      panel.addEventListener('toggle',()=>{if(panel.open)fill();});
      panel.append(summary,content);
      if(data.priorities.length===1){panel.open=true;fill();}
      item.append(panel);list.append(item);
    }
    results.append(list);
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(listening){status.textContent='Stop listening and review your words before searching.';return;}
    const selected = Array.from(form.querySelectorAll('[name=service]:checked'), input => input.value);
    if (!selected.length && !text.value.trim()) {
      status.textContent = 'Choose a service or add your own words to search.';
      form.querySelector('[name=service]').focus();
      return;
    }
    requestController?.abort();const controller=new AbortController();requestController=controller;
    const version=++generation;submit.disabled=true;questions.replaceChildren();results.replaceChildren();status.textContent='Looking for resources…';
    try{const data=await post(form.action,{selected_needs:selected,need_text:text.value.trim(),location:location.value.trim()||null,limit:10},controller.signal);if(version===generation)render(data);}
    catch(error){if(version===generation&&error.name!=='AbortError')status.textContent=error.message||'Guided help is unavailable. Try the map or questionnaire.';}
    finally{if(version===generation)submit.disabled=false;}
  });
  function clearPrivate(){generation++;requestController?.abort();cancelVoice();listening=false;prefix='';form.reset();text.value='';location.value='';results.replaceChildren();questions.replaceChildren();submit.disabled=false;}
  document.querySelector('#clear').addEventListener('click',()=>{clearPrivate();status.textContent='Your search has been cleared.';form.querySelector('[name=service]').focus();});
  const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
  const voiceStatus=document.querySelector('#voice-status');
  const mediaType=['audio/webm','audio/mp4'].find(type=>window.MediaRecorder?.isTypeSupported(type));
  const serverVoice=form.dataset.voiceApi==='true'&&navigator.mediaDevices?.getUserMedia&&mediaType;
  function idleVoice(){listening=false;mic.disabled=false;mic.textContent='🎙 Speak instead';mic.setAttribute('aria-pressed','false');}
  if(serverVoice){
    let recorder=null,stream=null,chunks=[],timer=null,voiceVersion=0,upload=null;
    function release(){clearTimeout(timer);stream?.getTracks().forEach(track=>track.stop());stream=null;}
    cancelVoice=()=>{voiceVersion++;upload?.abort();if(recorder?.state==='recording')recorder.stop();release();chunks=[];idleVoice();voiceStatus.textContent='';};
    mic.addEventListener('click',async()=>{
      if(recorder?.state==='recording'){recorder.stop();return;}
      if(listening)return;
      const version=++voiceVersion;prefix=text.value+(text.value?' ':'');listening=true;mic.disabled=true;
      voiceStatus.textContent='Waiting for microphone permission…';
      const language=document.querySelector('#voice-language').value.startsWith('es')?'es':'en';
      try{
        const acquired=await navigator.mediaDevices.getUserMedia({audio:true});
        if(version!==voiceVersion){acquired.getTracks().forEach(track=>track.stop());return;}
        stream=acquired;chunks=[];let bytes=0;
        recorder=new MediaRecorder(stream,{mimeType:mediaType,audioBitsPerSecond:64000});
        recorder.ondataavailable=event=>{if(version!==voiceVersion)return;if(event.data.size){chunks.push(event.data);bytes+=event.data.size;if(bytes>2000000){cancelVoice();voiceStatus.textContent='Recording is too large. Please try a shorter message.';}}};
        recorder.onerror=()=>{cancelVoice();voiceStatus.textContent='Recording failed. Please type or try again.';};
        recorder.onstop=async()=>{
          if(version!==voiceVersion)return;
          release();mic.disabled=true;voiceStatus.textContent='Turning your recording into editable words…';
          const blob=new Blob(chunks,{type:mediaType});chunks=[];upload=new AbortController();
          try{
            if(!blob.size)throw new Error('No audio was recorded. Please try again.');
            const response=await fetch('/api/transcribe/?language='+language,{method:'POST',headers:{'Content-Type':mediaType,'X-CSRFToken':csrf},body:blob,credentials:'same-origin',cache:'no-store',signal:upload.signal});
            const data=await response.json();if(!response.ok)throw new Error(data.error||'Voice unavailable. Please type.');
            if(version!==voiceVersion)return;
            text.value=(prefix+data.text).slice(0,text.maxLength);voiceStatus.textContent='Review and edit your words before searching.';
          }catch(error){if(version===voiceVersion&&error.name!=='AbortError')voiceStatus.textContent=error.message||'Voice unavailable. Please type.';}
          finally{if(version===voiceVersion)idleVoice();}
        };
        recorder.start(1000);mic.disabled=false;mic.textContent='Stop recording';mic.setAttribute('aria-pressed','true');voiceStatus.textContent='Recording, up to 60 seconds. Stop to transcribe and review.';
        timer=setTimeout(()=>{if(recorder.state==='recording')recorder.stop();},60000);
      }catch{if(version===voiceVersion){release();idleVoice();voiceStatus.textContent='Microphone unavailable. Check permission or type instead.';}}
    });
  }else if(!Speech){mic.disabled=true;voiceStatus.textContent='Voice is unavailable in this browser. You can type above.';}
  else{
    if(form.dataset.voiceApi==='true')document.querySelector('#voice-notice').textContent='This browser uses its own speech service, which may process audio remotely. Review your words before searching.';
    recognition=new Speech();recognition.continuous=true;recognition.interimResults=false;
    let permissionPending=false;
    cancelVoice=()=>{permissionPending=false;listening=false;recognition.abort();idleVoice();voiceStatus.textContent='';};
    recognition.onstart=()=>{if(!permissionPending){recognition.abort();return;}permissionPending=false;listening=true;mic.textContent='Stop listening';mic.setAttribute('aria-pressed','true');voiceStatus.textContent='Listening. Your words will appear above for you to edit.';};
    recognition.onresult=event=>{if(!listening)return;let words='';for(let i=0;i<event.results.length;i++){if(event.results[i].isFinal)words+=event.results[i][0].transcript+' ';}text.value=(prefix+words).slice(0,text.maxLength);};
    recognition.onend=()=>{permissionPending=false;idleVoice();if(!voiceStatus.textContent.includes('could not'))voiceStatus.textContent='Review and edit your words before searching.';};
    recognition.onerror=()=>{permissionPending=false;idleVoice();voiceStatus.textContent='Voice could not start. Check microphone permission or type instead.';};
    mic.addEventListener('click',()=>{if(listening){recognition.stop();return;}prefix=text.value+(text.value?' ':'');recognition.lang=document.querySelector('#voice-language').value;permissionPending=true;listening=true;try{recognition.start();}catch{permissionPending=false;idleVoice();voiceStatus.textContent='Please type while voice is unavailable.';}});
  }
  window.addEventListener('pagehide',clearPrivate);
})();
