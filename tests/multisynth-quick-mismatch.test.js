const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const helper = require('../tools/multisynth/quick_choice.js');
const mismatch = require('../tools/multisynth/quick_mismatch.js');

function element(id = '') {
    return {
        id, hidden: false, disabled: false, dataset: {}, children: [], checked: true,
        listeners: {}, classList: {toggle() {}},
        append(...children) {this.children.push(...children);},
        replaceChildren() {this.children = [];},
        addEventListener(kind, handler) {this.listeners[kind] = handler;},
        querySelectorAll() {return [];}, closest() {return null;}
    };
}

function controller({deferFirstPlay=false,storageOK=true,failPreparation=false,initialChoices={}}={}) {
    const ids = ['status', 'sequence', 'trial', 'break', 'break-title', 'break-copy',
        'continue', 'name', 'reference', 'options', 'stop', 'autoplay', 'undo', 'copy',
        'copy-status', 'export', 'feedback-json', 'saved', 'progress', 'overall',
        'audio-progress', 'details', 'skip', 'adequacy', 'adequacy-title', 'adequacy-far', 'change-choice', 'other'];
    const nodes = Object.fromEntries(ids.map(id => ['quick-' + id, element('quick-' + id)]));
    for (const id of ['quick-listening', 'detailed-listening', 'back-to-quick']) nodes[id] = element(id);
    const listeners = {};
    const document = {
        hidden: false, getElementById: id => nodes[id] || Object.values(nodes).flatMap(n=>n.children).find(n=>n.id===id), querySelectorAll: () => [],
        createElement: () => element(), addEventListener: (kind, handler) => {listeners[kind] = handler;}
    };
    const targets = ['one', 'two'].map(id => ({id, name: id, folder: id,
        candidates: [{id: id + '-option', file: 'option.wav', role: 'selected'}]}));
    const state = {ratings: {}, notes: {one:'My own note'}, choices: {...initialChoices}};
    const played = [], deferred = new Map();let instance, rejectPlay;
    class Player {
        constructor(config) {this.current = null;this.config=config;instance=this;}
        stop() {this.current = null;}
        preload(url) {
            if(failPreparation && url==='one/option.wav')return Promise.reject(Error('unavailable'));
            if (!url.startsWith('two/')) return Promise.resolve();
            if (!deferred.has(url)) {
                let resolve;
                const promise = new Promise(done => {resolve = done;});
                deferred.set(url, {promise, resolve});
            }
            return deferred.get(url).promise;
        }
        play(url) {
            played.push(url); this.current = {};this.config.onState('playing',url);
            if(deferFirstPlay && played.length===1)return new Promise((_,reject)=>{rejectPlay=reject;});
            return Promise.resolve(true);
        }
        get progress() {return null;}
    }
    const window = {
        AudioContext: class {}, fetch() {}, addEventListener() {},
        BfxrQuickMismatch: mismatch, BfxrQuickChoice: helper, BfxrQuickAudio: {CachedAudioPlayer: Player},
        BfxrListeningFeedback: {
            storageOK,
            model: {experimentId: 'controller-test', targets}, state,
            getPayload: () => ({targets: []}), subscribe() {},
            setChoice(id, choice) {if(choice)state.choices[id] = choice;else delete state.choices[id];}
        }
    };
    const source = fs.readFileSync(path.join(__dirname, '../tools/multisynth/quick_listening_diagnostic.js'), 'utf8');
    vm.runInNewContext(source, {window, document, navigator: {}, requestAnimationFrame() {}, setTimeout});
    return {state, played, deferred, nodes, get player(){return instance;}, reject:()=>rejectPlay(Error('old playback failed')),
        click: id => nodes['quick-' + id].listeners.click(),
        key: key => listeners.keydown({key, target: element(), preventDefault() {}})};
}

const settle = () => new Promise(resolve => setImmediate(resolve));


test('diagnosis is optional and limited to explicitly imperfect judgments',()=>{
 for(const kind of ['best','tie']){
  assert.equal(mismatch.eligible({kind,adequacy:{level:'similar'}}),true);
  assert.equal(mismatch.eligible({kind,adequacy:{level:'least-bad'}}),true);
  for(const level of ['very-close','not-sure'])assert.equal(mismatch.eligible({kind,adequacy:{level}}),false);
  assert.equal(mismatch.eligible({kind,adequacy:null}),false);
 }
 assert.equal(mismatch.eligible({kind:'none'}),true);
 assert.equal(mismatch.eligible({kind:'skip'}),false);
});

test('notes preserve free text, identify exact scope, and replace only prior diagnostic line',()=>{
 const choice={kind:'best',preferredCandidateIds:['abc'],presentedCandidateIds:['abc','def']};
 const first=mismatch.note('My own note',choice,'pitch');
 assert.match(first,/My own note/);assert.match(first,/abc/);assert.doesNotMatch(first,/def/);
 const second=mismatch.note(first,{...choice,kind:'tie'},'texture/timbre');
 assert.match(second,/tied/);assert.match(second,/abc/);assert.match(second,/def/);
 assert.doesNotMatch(second,/pitch/);assert.equal(second.split('\n').length,2);
 assert.match(mismatch.note('',{...choice,kind:'none'},'several things'),/all presented/);
 assert.equal(mismatch.note(first,choice,null),first);
 assert.throws(()=>mismatch.note('',choice,'bogus'));
});

test('similar winner asks immediate diagnosis; replay remains available; undo restores original note and choice',async()=>{
 const f=controller();await settle();f.key('1');f.key('2');
 assert.equal(f.nodes['quick-name'].textContent,'one');
 assert.match(f.nodes['quick-status'].textContent,/mismatch/i);
 f.key('a');await settle();assert.deepEqual(f.played,['one/option.wav']);
 // Only the fake player's explicit audition notification counts as heard.
 f.player.config.onAudition('one/option.wav');
 f.key('1');
 assert.match(f.state.notes.one,/pitch/);assert.match(f.state.notes.one,/one-option/);
 assert.equal(f.nodes['quick-name'].textContent,'two');
 assert.deepEqual([...f.state.choices.one.auditionedCandidateIds],['one-option']);
 f.click('undo');await settle();assert.equal(f.state.notes.one,'My own note');
 assert.equal(f.state.choices.one,undefined);assert.equal(f.nodes['quick-name'].textContent,'one');f.click('stop');
});

test('none asks all-option mismatch; skip leaves notes and playback telemetry untouched',async()=>{
 const f=controller();await settle();f.key('0');
 assert.equal(f.nodes['quick-name'].textContent,'one');f.key('s');
 assert.equal(f.nodes['quick-name'].textContent,'two');assert.equal(f.state.notes.one,'My own note');
 assert.deepEqual([...f.state.choices.one.auditionedCandidateIds],[]);f.click('stop');
});

test('very close and unsure advance without diagnosis',async()=>{
 for(const key of ['1','s']){
  const f=controller();await settle();f.key('1');f.key(key);
  assert.equal(f.nodes['quick-name'].textContent,'two');assert.equal(f.state.notes.one,'My own note');f.click('stop');
 }
});

test('optional diagnosis remains skippable by keyboard after a resumed audio failure',async()=>{
 const choice={protocol:'feel-choice-v2',kind:'best',presentedCandidateIds:['one-option'],
  auditionedCandidateIds:['one-option'],preferredCandidateIds:['one-option'],adequacy:null};
 const f=controller({initialChoices:{one:choice},failPreparation:true});await settle();
 f.key('2');assert.match(f.nodes['quick-status'].textContent,/mismatch/i);
 f.key('s');assert.equal(f.nodes['quick-name'].textContent,'two');
 assert.equal(f.state.choices.one.adequacy.level,'similar');f.click('stop');
});
