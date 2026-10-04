/* Standalone schema-2 diagnostic feedback. No network dependency. */
(function () {
    'use strict';
    const dimensions = ['likeness', 'usefulness'];
    const choiceAPI = typeof module !== 'undefined' ? require('./quick_choice.js') :
        typeof window !== 'undefined' ? window.BfxrQuickChoice : null;
    function feedbackPayload(model, state) {
        const ratings = state.ratings || {}, notes = state.notes || {};
        const rated = candidate => {
            const values = ratings[candidate.id] || {};
            return {...candidate, ...Object.fromEntries(dimensions.map(key => [key,
                Number.isInteger(values[key]) && values[key] >= 1 && values[key] <= 5 ? values[key] : null]))};
        };
        const targets=model.targets.map(target => {
            const choice=choiceAPI?.validatedChoice(target,state.choices?.[target.id]);
            return {...target,candidates:target.candidates.map(rated),
                note:typeof notes[target.id] === 'string' ? notes[target.id] : '',...(choice ? {choice} : {})};
        }).filter(target => target.choice || target.note.trim() || target.candidates.some(c => dimensions.some(key => c[key] !== null)));
        return {schemaVersion:targets.some(t => t.choice) ? 3 : 2, experimentId:model.experimentId, provenance:model.provenance,
            ratingScales:{likeness:{min:1,max:5,meaning:'Likeness to reference: 1 = far off, 5 = very close'},
                usefulness:{min:1,max:5,meaning:'Useful/fun game sound: 1 = not useful, 5 = very useful or fun'}},
            targets};
    }
    if (typeof module !== 'undefined') module.exports = {feedbackPayload};
    if (typeof document === 'undefined') return;
    document.addEventListener('play',event => {
        document.querySelectorAll('audio').forEach(player => {
            if (player !== event.target) player.pause();
        });
    },true);
    const model = JSON.parse(document.getElementById('feedback-data').textContent);
    const storageKey = 'bfxr-listening-feedback-v2:' + model.experimentId;
    let state = {ratings:{},notes:{},choices:{}}, storageOK = true;
    const subscribers=[];
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
        if (saved && typeof saved === 'object') {
            for (const key of ['ratings','notes','choices']) {
                if (saved[key] && typeof saved[key] === 'object' && !Array.isArray(saved[key])) state[key] = saved[key];
            }
        }
    } catch (_) { storageOK = false; }
    const output = document.getElementById('feedback-json'), status = document.getElementById('feedback-status');
    function update(save) {
        const payload = feedbackPayload(model,state);
        output.value = JSON.stringify(payload,null,2);
        document.querySelectorAll('input[data-candidate]').forEach(input => {
            input.checked = state.ratings[input.dataset.candidate]?.[input.dataset.dimension] === Number(input.value);
        });
        if (save) {
            try {localStorage.setItem(storageKey,JSON.stringify(state));}
            catch (_) {storageOK = false;}
        }
        status.textContent = `${payload.targets.length} of ${model.targets.length} references have feedback. ` +
            (storageOK ? 'Saved in this browser.' : 'Browser saving is unavailable; copy your JSON before leaving.');
        subscribers.forEach(fn => fn(payload,storageOK));
    }
    document.querySelectorAll('input[data-candidate]').forEach(input => input.addEventListener('change',() => {
        const id = input.dataset.candidate;
        state.ratings[id] = {...state.ratings[id], [input.dataset.dimension]:Number(input.value)};
        update(true);
    }));
    document.querySelectorAll('button[data-clear]').forEach(button => button.addEventListener('click',() => {
        if (state.ratings[button.dataset.clear]) delete state.ratings[button.dataset.clear][button.dataset.dimension];
        update(true);
    }));
    document.querySelectorAll('textarea[data-note]').forEach(input => {
        input.value = typeof state.notes[input.dataset.note] === 'string' ? state.notes[input.dataset.note] : '';
        input.addEventListener('input',() => {state.notes[input.dataset.note] = input.value; update(true);});
    });
    document.getElementById('copy-feedback').addEventListener('click',async () => {
        try {await navigator.clipboard.writeText(output.value); status.textContent = 'Feedback JSON copied.';}
        catch (_) {output.focus(); output.select(); status.textContent = 'JSON selected. Press Ctrl+C or ⌘C to copy.';}
    });
    document.getElementById('select-feedback').addEventListener('click',() => {output.focus();output.select();});
    if (typeof window !== 'undefined') window.BfxrListeningFeedback={model,state,
        get storageOK(){return storageOK;},
        getPayload:()=>feedbackPayload(model,state),
        subscribe:fn=>subscribers.push(fn),
        setChoice:(id,choice)=>{if(choice)state.choices[id]=choice;else delete state.choices[id];update(true);}};
    update(false);
}());
