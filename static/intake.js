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
  const paths={
    basket:'M3 10h18l-2 10H5z M7 10l5-7 5 7', meal:'M4 3v6q3 4 6 0V3 M7 3v18 M18 3q-4 6-3 10h4 M19 3v18',
    house:'M2 11l10-8 10 8 M5 10v11h14V10 M10 21v-7h4v7', bolt:'M14 2L4 14h7l-1 8 10-13h-7z',
    heart:'M12 21L4 13C-2 5 7 0 12 7c5-7 14-2 8 6z M9 12h6 M12 9v6',
    chat:'M3 4h18v13H9l-6 4z M7 9h10 M7 13h6', work:'M3 7h18v13H3z M8 7V4h8v3 M3 12q9 5 18 0',
    bus:'M5 4q7-3 14 0v15H5z M5 11h14 M8 15h1 M15 15h1 M7 19v2 M17 19v2',
    check:'M4 12l5 5L20 6', shield:'M12 2l8 3v6c0 6-4 9-8 11-4-2-8-5-8-11V5z M8 11l3 3 5-6',
    mic:'M9 5a3 3 0 016 0v7a3 3 0 01-6 0z M5 11a7 7 0 0014 0 M12 18v4 M8 22h8',
    arrow:'M3 12h17 M14 5l7 7-7 7', right:'M9 5l7 7-7 7', down:'M5 9l7 7 7-7',
    list:'M8 6h12 M8 12h12 M8 18h12 M3 6h1 M3 12h1 M3 18h1', map:'M2 5l7-3 6 3 7-3v17l-7 3-6-3-7 3z M9 2v17 M15 5v17',
    key:'M14 4a5 5 0 107 7 5 5 0 00-7-7z M13 11L3 21v-4l2-2h3v-3',
    building:'M5 21V3h14v18z M8 7h2 M14 7h2 M8 11h2 M14 11h2 M10 21v-6h4v6',
    doc:'M5 2h9l5 5v15H5z M14 2v6h5 M8 12h8 M8 16h6', id:'M2 5h20v14H2z M5 10h4 M5 14h4 M13 10h6 M13 14h5',
    laptop:'M4 4h16v13H4z M2 20h20', tooth:'M12 5C5 0 1 5 5 13c2 12 5 9 6 3q1-4 2 0c1 6 4 9 6-3 4-8 0-13-7-8z'
  };
  function icon(name){
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
    svg.innerHTML='<path d="'+(paths[name]||paths.list)+'" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>';
    return svg;
  }
  document.querySelectorAll('[data-icon]').forEach(node=>node.append(icon(node.dataset.icon)));
  const choices=[...form.querySelectorAll('button[name=service]')];
  function selectedChoices(){return choices.filter(button=>button.getAttribute('aria-pressed')==='true');}
  function updateCount(){
    const n=selectedChoices().length;
    document.querySelector('#choice-count').textContent=n ? n+' need'+(n===1?'':'s')+' selected':'Nothing selected yet';
  }
  for(const button of choices)button.addEventListener('click',()=>{
    button.setAttribute('aria-pressed',button.getAttribute('aria-pressed')!=='true');updateCount();
  });
  function link(label,url){const n=el('a',label);try{const u=new URL(url,window.location.origin);if(['http:','https:','tel:','sms:'].includes(u.protocol)){n.href=u.href;n.rel='noreferrer noopener';}}catch{}return n;}
  async function post(url,data,signal){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify(data),cache:'no-store',credentials:'same-origin',signal});const d=await r.json();if(!r.ok)throw new Error(d.error||'Please try again.');return d;}
  function contact(r){const links=el('div','', 'resource-links');if(r.phone)links.append(link(`Call ${r.phone}`,r.phone_link||'tel:'+String(r.phone).replace(/[^+\d]/g,'')));if(r.website)links.append(link('Provider website',r.website));return links;}
  function showContacts(items,heading,cls){if(!items.length)return;const section=el('section','',cls);section.append(el('h2',heading));for(const r of items){const a=el('article');a.append(el('h3',r.name),el('p',r.description),contact(r));section.append(a);}results.append(section);}
  function render(data){results.replaceChildren();questions.replaceChildren();status.textContent=data.message;
    for(const question of data.questions){questions.append(el('p',question));}
    if(data.questions.length){questions.append(el('p','Choose a service or add details above, then search again.'));}
    showContacts(data.crisis_resources,'Get immediate support / Ayuda inmediata','crisis');
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
      meta.classList.add('source-rating');
      const ring=el('span','','rating-ring'), valid=Number.isFinite(r.reliability_score);
      const dial=document.createElementNS('http://www.w3.org/2000/svg','svg');
      dial.setAttribute('viewBox','0 0 80 80');dial.setAttribute('aria-hidden','true');
      const value=valid?Math.max(0,Math.min(100,r.reliability_score)):0;
      dial.innerHTML='<circle cx="40" cy="40" r="36" fill="none" stroke="#202934" stroke-width="8"/>';
      if(value>0){
        const arc=dial.firstElementChild.cloneNode();
        arc.setAttribute('stroke','#5eead4');arc.setAttribute('stroke-linecap','round');
        arc.setAttribute('pathLength','100');arc.setAttribute('stroke-dasharray',value+' 100');
        arc.setAttribute('transform','rotate(-90 40 40)');dial.append(arc);
      }
      ring.append(dial);
      ring.append(el('strong',valid?r.reliability_score.toFixed(1):'—','score'));
      const rating=el('div','','rating-row'), caption=el('div');
      if(r.classification){
        const badge=el('strong',r.classification,'rating-badge');
        if(/^reliable$/i.test(r.classification))badge.prepend(icon('check'));
        caption.append(badge);
      }
      caption.append(el('span',valid?'out of 100':'Not scored'));rating.append(ring,caption);
      const date=r.verified_date && new Date(r.verified_date+'T00:00:00Z');
      const checked=date && Number.isFinite(date.valueOf())?date.toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'date unknown';
      meta.append(el('strong','Source reliability'),rating,el('p','Checked '+checked),el('small','Score reflects the source, not eligibility or availability.'));
      const feedback=el('div','Was this helpful?','feedback');for(const [label,helpful] of [['Yes',true],['No',false]]){const b=el('button',label);b.type='button';b.addEventListener('click',async()=>{feedback.querySelectorAll('button').forEach(x=>x.disabled=true);try{await post('/api/recommendation-feedback/',{resource_id:r.resource_id,helpful});feedback.textContent='Thank you. Your response was saved.';}catch{feedback.textContent='Could not save your response. Please try later.';}});feedback.append(b);}main.append(feedback);card.append(main,meta);return card;
  }
  const needLabels = {
    'housing.emergency_shelter':'Emergency shelter', 'housing.supportive_transitional':'Transitional housing',
    'housing.rental':'Affordable rental housing', 'housing.rent_eviction_help':'Rent and eviction help',
    'food.prepared_meals':'Ready-to-eat meals', 'food.pantry':'Groceries and food pantries',
    'food.delivery':'Food delivery', 'food.general_assistance':'General food assistance', 'benefits.enrollment_navigation':'Help applying for benefits',
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
    results.append(el('h2','Your help priorities','priority-title'),el('p','Click or tap a priority below to see its resources.','priority-sub'));
    const total=data.priorities.length, found=data.priorities.filter(p=>p.sources.length).length;
    const pills=el('div','','priority-stats');
    pills.append(el('span',total+' need'+(total===1?'':'s'),'pill'),el('span',found+' with places to contact','pill has'),el('span',(total-found)+' still searching','pill empty'));
    results.append(pills);
    const list=el('ol','','priorities');
    for(const [index,priority] of data.priorities.entries()){
      const item=el('li'), summary=el('button','','priority-toggle'), content=el('div','','priority-content');
      const count=priority.sources.length, leads=Boolean(priority.sources[0]?.unverified_requirements);
      const key=priority.need.replace('need:','');
      const symbols={'housing.emergency_shelter':'house','housing.rental':'key','housing.supportive_transitional':'building','food.pantry':'basket','food.prepared_meals':'meal','legal.identity_documents':'id','medical.dental':'tooth'};
      const categories={benefits:'doc',employment:'work',transportation:'bus',digital:'laptop',medical:'heart',mental_health:'chat',utilities:'bolt',housing:'house',food:'meal'};
      const tile=el('i','','tile');tile.append(icon(symbols[key]||categories[key.split('.')[0]]||'list'));
      const title=el('strong',needLabel(priority.need));
      if(!index)title.append(el('small','Start here','start-here'));
      const caret=el('i','','caret');caret.append(icon('down'));
      summary.type='button';content.id='priority-'+index;
      summary.setAttribute('aria-controls',content.id);
      summary.append(el('span',String(index+1),'rank'),tile,title,el('span',count?count+' to contact':'No matches yet',count?'pill has':'pill empty'),caret);
      item.classList.toggle('no-matches',!count);
      function fill(){
        if(content.childElementCount)return;
        if(!count){
          const box=el('div',"We haven't confirmed a place for this yet. Know one?",'empty-box');
          box.append(link('Suggest a resource',document.querySelector('#main').dataset.feedbackUrl));content.append(box);
        }
        for(const [i,source] of priority.sources.entries()){
          content.append(resourceCard({...source,resource:records.get(source.resource_id),rank:i+1,
            score_breakdown:!leads,next_step:leads
              ? 'Before you go, ask about '+source.unverified_requirements.map(value=>value.replaceAll('_',' ')).join(', ')+'. The directory could not verify these requirements.'
              : 'Contact the provider to confirm intake, availability and eligibility.'}));
        }
      }
      function expand(open){
        summary.setAttribute('aria-expanded',String(open));content.hidden=!open;
        if(open)fill();
      }
      summary.addEventListener('click',()=>expand(content.hidden));
      item.append(summary,content);expand(false);list.append(item);
    }
    results.append(list);
  }
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if(listening){status.textContent='Stop listening and review your words before searching.';return;}
    const selected = selectedChoices().map(button=>button.value);
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
  function clearPrivate(){generation++;requestController?.abort();cancelVoice();listening=false;prefix='';form.reset();choices.forEach(b=>b.setAttribute('aria-pressed','false'));updateCount();text.value='';location.value='';results.replaceChildren();questions.replaceChildren();submit.disabled=false;}
  document.querySelector('#clear').addEventListener('click',()=>{clearPrivate();status.textContent='Your search has been cleared.';form.querySelector('[name=service]').focus();});
  const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
  const voiceStatus=document.querySelector('#voice-status');
  const mediaType=['audio/webm','audio/mp4'].find(type=>window.MediaRecorder?.isTypeSupported(type));
  const serverVoice=form.dataset.voiceApi==='true'&&navigator.mediaDevices?.getUserMedia&&mediaType;
  function idleVoice(){listening=false;mic.disabled=false;mic.replaceChildren(icon('mic'), 'Speak instead');mic.setAttribute('aria-pressed','false');}
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
