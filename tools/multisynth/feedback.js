/* Embedded in the standalone gallery; no server or account required. */
(function () {
    'use strict';
    function feedbackPayload(model, state) {
        const ratings = state.ratings || {}, notes = state.notes || {};
        const rated = candidate => candidate ? {...candidate,
            rating: Number.isInteger(ratings[candidate.id]) && ratings[candidate.id] >= 1 && ratings[candidate.id] <= 5
                ? ratings[candidate.id] : null} : null;
        return {schemaVersion:1, experimentId:model.experimentId, provenance:model.provenance,
            ratingScale:{min:1,max:5,meaning:'Audible likeness to reference: 1 = far off, 5 = very close'},
            targets:model.targets.map(target => ({...target,selected:rated(target.selected),bfxr:rated(target.bfxr),
                note:typeof notes[target.id] === 'string' ? notes[target.id] : ''}))
                .filter(target => target.selected.rating !== null || target.bfxr?.rating != null || target.note.trim())};
    }
    if (typeof module !== 'undefined') module.exports = {feedbackPayload};
    if (typeof document === 'undefined') return;
    const model = JSON.parse(document.getElementById('feedback-data').textContent);
    const storageKey = 'bfxr-listening-feedback-v1:' + model.experimentId;
    let state = {ratings:{},notes:{}}, storageOK = true;
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || 'null');
        if (saved && typeof saved === 'object') {
            state.ratings = saved.ratings && typeof saved.ratings === 'object' ? saved.ratings : {};
            state.notes = saved.notes && typeof saved.notes === 'object' ? saved.notes : {};
        }
    } catch (_) { storageOK = false; }
    const output = document.getElementById('feedback-json');
    const status = document.getElementById('feedback-status');
    function update(save) {
        const payload = feedbackPayload(model,state);
        output.value = JSON.stringify(payload,null,2);
        document.querySelectorAll('input[data-candidate]').forEach(input => {
            input.checked = state.ratings[input.dataset.candidate] === Number(input.value);
        });
        if (save) {
            try {localStorage.setItem(storageKey,JSON.stringify(state));}
            catch (_) {storageOK = false;}
        }
        status.textContent = `${payload.targets.length} of ${model.targets.length} sounds have feedback. ` +
            (storageOK ? 'Saved in this browser.' : 'Browser saving is unavailable; copy your JSON before leaving.');
    }
    document.querySelectorAll('input[data-candidate]').forEach(input => input.addEventListener('change',() => {
        state.ratings[input.dataset.candidate] = Number(input.value); update(true);
    }));
    document.querySelectorAll('button[data-clear]').forEach(button => button.addEventListener('click',() => {
        delete state.ratings[button.dataset.clear]; update(true);
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
    update(false);
}());
