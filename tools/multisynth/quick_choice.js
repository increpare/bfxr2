(function () {
    'use strict';
    function validatedChoice(target, choice) {
        const fields = ['protocol','kind','presentedCandidateIds','auditionedCandidateIds','preferredCandidateIds'];
        if (!choice || Object.keys(choice).sort().join() !== fields.sort().join() ||
            choice.protocol !== 'feel-choice-v1' || !['best','tie','none','skip'].includes(choice.kind)) return null;
        for (const key of ['presentedCandidateIds','auditionedCandidateIds','preferredCandidateIds']) {
            const ids = choice[key];
            if (!Array.isArray(ids) || ids.some(id => typeof id !== 'string') || new Set(ids).size !== ids.length) return null;
        }
        const presented = choice.presentedCandidateIds, valid = new Set(target.candidates.map(c => c.id));
        if (presented.length < 1 || presented.length > 5 || presented.some(id => !valid.has(id)) ||
            choice.auditionedCandidateIds.some(id => !presented.includes(id)) ||
            choice.preferredCandidateIds.some(id => !presented.includes(id)) ||
            choice.preferredCandidateIds.length !== (choice.kind === 'best' ? 1 : 0)) return null;
        return choice;
    }
    function hash(s) { let h=2166136261; for (const c of s) h=Math.imul(h^c.charCodeAt(0),16777619); return h>>>0; }
    function primaryCandidates(target, experimentId) {
        const priority = {selected:0,automatic:0,original:1,bfxr:1,previous:2};
        const unique = new Map();
        target.candidates.filter(c => c.role !== 'raw').slice().sort((a,b) =>
            (priority[a.role] ?? 3) - (priority[b.role] ?? 3)).forEach(c => {
            const key=c.audioSha256 || c.id;
            if (!unique.has(key)) unique.set(key,c);
        });
        return [...unique.values()].slice(0,3).sort((a,b) =>
            hash(experimentId+target.id+a.id)-hash(experimentId+target.id+b.id) || a.id.localeCompare(b.id));
    }
    function completed(target,state,experimentId) {
        if (validatedChoice(target,state.choices?.[target.id])) return true;
        const primary=primaryCandidates(target,experimentId);
        return primary.length > 0 && primary.every(c => {
            const value=state.ratings?.[c.id]?.likeness;
            return Number.isInteger(value) && value >= 1 && value <= 5;
        });
    }
    function firstPendingIndex(targets,state,experimentId) {
        const index=targets.findIndex(t => !completed(t,state,experimentId));
        return index < 0 ? targets.length : index;
    }
    const api={validatedChoice,primaryCandidates,firstPendingIndex,completed};
    if (typeof module !== 'undefined') module.exports=api;
    if (typeof window !== 'undefined') window.BfxrQuickChoice=api;
}());
