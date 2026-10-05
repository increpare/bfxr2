(function () {
    'use strict';
    function validatedChoice(target, choice) {
        const fields = ['protocol','kind','presentedCandidateIds','auditionedCandidateIds','preferredCandidateIds'];
        if(choice?.protocol==='feel-choice-v2')fields.push('adequacy');
        if (!choice || Object.keys(choice).sort().join() !== fields.sort().join() ||
            !['feel-choice-v1','feel-choice-v2'].includes(choice.protocol) || !['best','tie','none','skip'].includes(choice.kind)) return null;
        for (const key of ['presentedCandidateIds','auditionedCandidateIds','preferredCandidateIds']) {
            const ids = choice[key];
            if (!Array.isArray(ids) || ids.some(id => typeof id !== 'string') || new Set(ids).size !== ids.length) return null;
        }
        const presented = choice.presentedCandidateIds, valid = new Set(target.candidates.map(c => c.id));
        if (presented.length < 1 || presented.length > 5 || presented.some(id => !valid.has(id)) ||
            choice.auditionedCandidateIds.some(id => !presented.includes(id)) ||
            choice.preferredCandidateIds.some(id => !presented.includes(id)) ||
            choice.preferredCandidateIds.length !== (choice.kind === 'best' ? 1 : 0)) return null;
        if(choice.protocol==='feel-choice-v2' && choice.adequacy!==null) {
            const a=choice.adequacy, expected=choice.kind==='best'?choice.preferredCandidateIds:presented;
            if(!['best','tie'].includes(choice.kind) || !a || Object.keys(a).sort().join()!=='candidateIds,level' ||
                !['very-close','similar','least-bad','not-sure'].includes(a.level) || !Array.isArray(a.candidateIds) ||
                a.candidateIds.length!==expected.length || new Set(a.candidateIds).size!==a.candidateIds.length ||
                a.candidateIds.some(id=>!expected.includes(id)))return null;
        }
        return choice;
    }
    function needsAdequacy(choice) {
        return choice?.protocol==='feel-choice-v2' && ['best','tie'].includes(choice.kind) && choice.adequacy===null;
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
        const choice=validatedChoice(target,state.choices?.[target.id]);
        if(choice)return !needsAdequacy(choice);
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
    const api={validatedChoice,needsAdequacy,primaryCandidates,firstPendingIndex,completed};
    if (typeof module !== 'undefined') module.exports=api;
    if (typeof window !== 'undefined') window.BfxrQuickChoice=api;
}());
