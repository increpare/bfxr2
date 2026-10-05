(function () {
    'use strict';
    const feedback=window.BfxrListeningFeedback, helper=window.BfxrQuickChoice;
    const root=document.getElementById('quick-listening');
    const AudioContext=window.AudioContext || window.webkitAudioContext;
    if (!feedback || !helper || !root || !AudioContext) return;
    const {model,state}=feedback, targets=model.targets;
    const $=id=>document.getElementById('quick-'+id);
    const detailed=document.getElementById('detailed-listening');
    let index=helper.firstPendingIndex(targets,state,model.experimentId), options=[], heard=new Set();
    let pendingChoice=null;
    let revision=0, sequence=0, sequenceRunning=false, started=false, ready=false, loadFailed=false, block=0;
    const undo=[], letters=['A','B','C'];let endPlayback=null;
    const path=(target,file)=>encodeURIComponent(target.folder)+'/'+encodeURIComponent(file);
    const url=c=>path(targets[index],c.file), reference=()=>path(targets[index],'target.wav');
    const player=new window.BfxrQuickAudio.CachedAudioPlayer({context:new AudioContext(),fetch:window.fetch.bind(window),
        onAudition:audioURL=>{const candidate=options.find(c=>url(c)===audioURL);if(candidate)heard.add(candidate.id);},
        onState:(status,audioURL)=>{
            document.querySelectorAll('[data-quick-play]').forEach(button=>button.classList.toggle('is-playing',status==='playing' && button.dataset.quickPlay===audioURL));
            document.querySelectorAll('.quick-option').forEach(card=>card.classList.toggle('is-playing',status==='playing' && card.dataset.url===audioURL));
            if(status==='playing') {
                const option=options.findIndex(c=>url(c)===audioURL);
                $('status').textContent='Playing '+(option<0?'Reference':letters[option])+'…';
            }
            if(status==='ended' && !sequenceRunning)$('status').textContent=idlePrompt();
        }
    });
    function stop() {
        sequence++;sequenceRunning=false;player.stop();
        if(endPlayback){endPlayback();endPlayback=null;}
        $('sequence').textContent=started?'▶ Replay sequence (Space)':'▶ Start listening (Space)';
        if(ready)$('status').textContent=idlePrompt();
    }
    function idlePrompt() {return pendingChoice?'How close is it? Answer below, or replay anything.':'Choose the best feel, or replay anything.';}
    function showAdequacy(choice) {
        pendingChoice=helper.needsAdequacy(choice)?choice:null;
        const active=!!pendingChoice;
        $('adequacy').hidden=!active;$('other').hidden=active;
        root.querySelectorAll('.choose').forEach(button=>{button.hidden=active;});
        options.forEach((c,i)=>$('options').children[i].classList.toggle('is-selected',active &&
            (choice.kind==='tie' || choice.preferredCandidateIds.includes(c.id))));
        if(active) {
            const letter=letters[options.findIndex(c=>choice.preferredCandidateIds.includes(c.id))];
            $('adequacy-title').textContent=choice.kind==='tie'?'How close are these tied options to the reference?':
                'How close is '+letter+' to the reference?';
            $('adequacy-far').textContent=choice.kind==='tie'?'Still far off (3)':'Only the least-bad option (3)';
            $('status').textContent=idlePrompt();$('adequacy-title').focus?.();
        }
    }
    function pauseNative() {document.querySelectorAll('audio').forEach(a=>a.pause());}
    async function playOne(audioURL) {
        stop();started=true;pauseNative();
        const token=sequence, view=revision;
        try {await player.play(audioURL);}catch(error){if(token===sequence && view===revision)$('status').textContent=error.message;}
    }
    async function playSequence() {
        if(!ready || index>=targets.length)return;
        stop();started=true;sequenceRunning=true;pauseNative();
        const token=sequence;
        $('sequence').textContent='■ Stop sequence (Space)';
        for(const audioURL of [reference(),...options.map(url)]) {
            if(token!==sequence)return;
            const ended=new Promise(resolve=>{endPlayback=resolve;});
            player.onEnded=()=>{if(endPlayback){endPlayback();endPlayback=null;}};
            try {if(!await player.play(audioURL))return;}catch(error){
                if(token!==sequence)return;
                stop();$('status').textContent=error.message;return;
            }
            // Stop resolves this wait too; cancelled sources never need an ended event.
            await ended;
            if(token!==sequence)return;
            await new Promise(resolve=>setTimeout(resolve,350));
        }
        if(token===sequence){sequenceRunning=false;$('sequence').textContent='▶ Replay sequence (Space)';$('status').textContent=pendingChoice?idlePrompt():'Which feels closest? Choose below.';}
    }
    function refreshExport(payload=feedback.getPayload(),storageOK=feedback.storageOK) {
        $('feedback-json').value=JSON.stringify(payload,null,2);
        const count=targets.filter(t=>helper.completed(t,state,model.experimentId)).length;
        $('progress').textContent=count+' / '+targets.length+' judged';
        $('overall').max=targets.length;$('overall').value=count;
        $('saved').textContent=storageOK?'Saved in this browser':'Copy JSON before leaving — browser saving unavailable';
    }
    feedback.subscribe(refreshExport);
    function enable(value) {
        ready=value;
        root.querySelectorAll('#quick-trial button').forEach(b=>{b.disabled=!value;});
        $('stop').disabled=false;
    }
    function showBreak(finished=false) {
        stop();$('trial').hidden=true;$('break').hidden=false;
        $('break-title').textContent=finished?'All done. Thank you.':'Five done. Take a breather.';
        $('break-copy').textContent=finished?'Copy your feedback below when you’re ready. You can undo a choice or open detailed ratings.':
            feedback.storageOK?'Your choices are saved. Continue when you feel like it, or copy what you have.':
            'Your choices are held in memory. Copy feedback before closing or reloading this page.';
        $('continue').hidden=finished;
    }
    async function show(next,autoplay=false) {
        stop();pendingChoice=null;const token=++revision, playbackToken=sequence;index=next;loadFailed=false;refreshExport();
        if(index>=targets.length){showBreak(true);return;}
        $('trial').hidden=false;$('break').hidden=true;
        const target=targets[index];options=helper.primaryCandidates(target,model.experimentId);
        heard=new Set(helper.validatedChoice(target,state.choices[target.id])?.auditionedCandidateIds || []);
        $('name').textContent=target.name;
        $('reference').dataset.quickPlay=reference();
        $('options').replaceChildren();
        options.forEach((c,i)=>{
            const card=document.createElement('div');card.className='quick-option';card.dataset.url=url(c);
            const label=document.createElement('strong');label.textContent=letters[i];
            const play=document.createElement('button');play.className='quiet';play.dataset.quickPlay=url(c);play.textContent='▶ Play '+letters[i]+' ('+letters[i]+')';play.addEventListener('click',()=>playOne(url(c)));
            const choose=document.createElement('button');choose.className='choose';choose.textContent='Choose '+letters[i]+' ('+(i+1)+')';choose.addEventListener('click',()=>vote('best',c.id));
            card.append(label,play,choose);$('options').append(card);
        });
        showAdequacy(helper.validatedChoice(target,state.choices[target.id]));
        enable(false);$('status').textContent='Preparing audio…';
        try {
            await Promise.all([reference(),...options.map(url)].map(audioURL=>player.preload(audioURL)));
            if(token!==revision)return;
            enable(true);$('status').textContent=pendingChoice || started?idlePrompt():'Press Start once. Then listen and choose.';
            // Decode the next comparison while this one is being judged.
            const nextTarget=targets[index+1];
            if(nextTarget)[path(nextTarget,'target.wav'),...helper.primaryCandidates(nextTarget,model.experimentId).map(c=>path(nextTarget,c.file))].forEach(audioURL=>player.preload(audioURL).catch(()=>{}));
            if(autoplay && !pendingChoice && playbackToken===sequence && started && $('autoplay').checked && !document.hidden)playSequence();
        }catch(error){if(token===revision){
            loadFailed=true;$('skip').disabled=false;
            if(pendingChoice) {
                enable(true);
                $('status').textContent='Audio unavailable. Your choice is saved; choose Not sure or change your choice.';
            } else $('status').textContent='Audio unavailable. Skip this reference, or open detailed ratings.';
        }}
    }
    function vote(kind,preferred) {
        if(pendingChoice || (!ready && !(kind==='skip' && loadFailed)) || $('trial').hidden || index>=targets.length || detailed.hidden===false)return;
        stop();const target=targets[index];
        const choice={protocol:'feel-choice-v2',kind,presentedCandidateIds:options.map(c=>c.id),
            auditionedCandidateIds:options.filter(c=>heard.has(c.id)).map(c=>c.id),preferredCandidateIds:preferred?[preferred]:[],adequacy:null};
        if(!helper.validatedChoice(target,choice))return;
        undo.push({index,previous:state.choices[target.id] || null});
        feedback.setChoice(target.id,choice);$('undo').disabled=false;
        if(helper.needsAdequacy(choice)){showAdequacy(choice);return;}
        advance();
    }
    function advance() {
        pendingChoice=null;
        const next=helper.firstPendingIndex(targets,state,model.experimentId);
        if(++block>=5 && next<targets.length){index=next;showBreak();return;}
        show(next,true);
    }
    function assess(level) {
        if(!pendingChoice || !ready || $('trial').hidden || !detailed.hidden)return;
        stop();const choice={...pendingChoice,
            auditionedCandidateIds:options.filter(c=>heard.has(c.id)).map(c=>c.id),
            adequacy:{level,candidateIds:[...(pendingChoice.kind==='best'?pendingChoice.preferredCandidateIds:pendingChoice.presentedCandidateIds)]}};
        if(!helper.validatedChoice(targets[index],choice))return;
        // A resumed pending choice has no in-memory undo entry yet.
        if(!undo.length || undo[undo.length-1].index!==index)undo.push({index,previous:pendingChoice});
        feedback.setChoice(targets[index].id,choice);$('undo').disabled=false;advance();
    }
    root.querySelectorAll('[data-adequacy]').forEach(button=>button.addEventListener('click',()=>assess(button.dataset.adequacy)));
    $('change-choice').addEventListener('click',()=>{
        if(!pendingChoice)return;
        if(undo.length && undo[undo.length-1].index===index)undoLast();
        else {feedback.setChoice(targets[index].id,null);show(index);}
    });
    $('reference').addEventListener('click',()=>playOne(reference()));
    $('sequence').addEventListener('click',()=>sequenceRunning || player.current?stop():playSequence());
    $('stop').addEventListener('click',stop);
    root.querySelectorAll('[data-choice]').forEach(button=>button.addEventListener('click',()=>vote(button.dataset.choice)));
    $('continue').addEventListener('click',()=>{block=0;show(index,true);});
    function undoLast() {
        const last=undo.pop();if(!last)return;stop();if(!pendingChoice)block=Math.max(0,block-1);
        feedback.setChoice(targets[last.index].id,last.previous);$('undo').disabled=!undo.length;show(last.index);
    }
    $('undo').addEventListener('click',undoLast);$('undo').disabled=true;
    $('copy').addEventListener('click',async()=>{
        const output=$('feedback-json');
        try {await navigator.clipboard.writeText(output.value);$('copy-status').textContent='Copied. Paste it into our chat.';}
        catch(_){$('export').open=true;output.focus();output.select();$('copy-status').textContent='JSON selected. Press Ctrl+C or ⌘C.';}
    });
    $('details').addEventListener('click',()=>{
        stop();revision++;root.hidden=true;detailed.hidden=false;
        detailed.querySelectorAll('[data-target]').forEach(section=>{section.hidden=index<targets.length && section.dataset.target!==targets[index].id;});
    });
    document.getElementById('back-to-quick').addEventListener('click',()=>{pauseNative();detailed.hidden=true;root.hidden=false;show(helper.firstPendingIndex(targets,state,model.experimentId));});
    document.addEventListener('play',()=>{if(!detailed.hidden)stop();},true);
    document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
    window.addEventListener('pagehide',stop);
    document.addEventListener('keydown',event=>{
        if(root.hidden || event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.target.closest('input,textarea,select,[contenteditable="true"]'))return;
        const key=event.key.toLowerCase();let handled=true;
        if(key==='arrowleft')undoLast();
        else if(key==='s' && loadFailed && !pendingChoice && !$('trial').hidden)vote('skip');
        else if(key===' '){if(!ready || $('trial').hidden)return;sequenceRunning || player.current?stop():playSequence();}
        else if(!ready || $('trial').hidden)return;
        else if(key==='r')playOne(reference());
        else if(['a','b','c'].includes(key)){const c=options[letters.map(l=>l.toLowerCase()).indexOf(key)];if(c)playOne(url(c));}
        else if(pendingChoice && ['1','2','3','s'].includes(key))assess({'1':'very-close','2':'similar','3':'least-bad',s:'not-sure'}[key]);
        else if(['1','2','3'].includes(key)){const c=options[Number(key)-1];if(c)vote('best',c.id);}
        else if(key==='0')vote('none');else if(key==='t')vote('tie');else if(key==='s')vote('skip');else handled=false;
        if(handled)event.preventDefault();
    });
    function tick() {const progress=player.progress;$('audio-progress').value=progress?progress.elapsed/progress.duration:0;requestAnimationFrame(tick);}
    root.hidden=false;detailed.hidden=true;refreshExport();show(index);tick();
}());
