(function () {
    'use strict';
    const reasons=['pitch','movement/rhythm','texture/timbre','attack/decay','several things','unsure'];
    const prefix='[quick-mismatch-v1] ';
    function eligible(choice) {
        return choice?.kind==='none' || (['best','tie'].includes(choice?.kind) &&
            ['similar','least-bad'].includes(choice?.adequacy?.level));
    }
    function note(previous,choice,reason) {
        if(reason===null)return previous;
        if(!reasons.includes(reason))throw Error('Unknown mismatch reason');
        const scope=choice.kind==='best'?'chosen':choice.kind==='tie'?'tied':'all presented';
        const ids=choice.kind==='best'?choice.preferredCandidateIds:choice.presentedCandidateIds;
        const text=(previous || '').split('\n').filter(line=>!line.startsWith(prefix)).join('\n');
        return (text?text+'\n':'')+prefix+scope+' '+JSON.stringify(ids)+': '+reason;
    }
    const api={reasons,eligible,note};
    if(typeof module!=='undefined')module.exports=api;
    if(typeof window!=='undefined')window.BfxrQuickMismatch=api;
}());
