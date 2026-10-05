const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const helper = require('../tools/multisynth/quick_choice.js');

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
        hidden: false, getElementById: id => nodes[id], querySelectorAll: () => [],
        createElement: () => element(), addEventListener: (kind, handler) => {listeners[kind] = handler;}
    };
    const targets = ['one', 'two'].map(id => ({id, name: id, folder: id,
        candidates: [{id: id + '-option', file: 'option.wav', role: 'selected'}]}));
    const state = {ratings: {}, choices: {...initialChoices}};
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
        BfxrQuickChoice: helper, BfxrQuickAudio: {CachedAudioPlayer: Player},
        BfxrListeningFeedback: {
            storageOK,
            model: {experimentId: 'controller-test', targets}, state,
            getPayload: () => ({targets: []}), subscribe() {},
            setChoice(id, choice) {if(choice)state.choices[id] = choice;else delete state.choices[id];}
        }
    };
    const source = fs.readFileSync(path.join(__dirname, '../tools/multisynth/quick_listening.js'), 'utf8');
    vm.runInNewContext(source, {window, document, navigator: {}, requestAnimationFrame() {}, setTimeout});
    return {state, played, deferred, nodes, get player(){return instance;}, reject:()=>rejectPlay(Error('old playback failed')),
        click: id => nodes['quick-' + id].listeners.click(),
        key: key => listeners.keydown({key, target: element(), preventDefault() {}})};
}

const settle = () => new Promise(resolve => setImmediate(resolve));

test('Stop during preparation cancels next-reference autoplay while retaining explicit replay', async () => {
    const fixture = controller();
    await settle();
    fixture.click('sequence');
    await settle();
    assert.deepEqual(fixture.played, ['one/target.wav']);
    fixture.key('1');
    assert.equal(fixture.state.choices.one.kind, 'best');
    fixture.key('2'); // Answer immediate likeness before advancing.
    fixture.click('stop');
    for (const request of fixture.deferred.values()) request.resolve();
    await settle();
    assert.deepEqual(fixture.played, ['one/target.wav'], 'finishing preparation must not restart stopped playback');
    fixture.click('sequence');
    await settle();
    assert.deepEqual(fixture.played, ['one/target.wav', 'two/target.wav']);
    fixture.click('stop');
});

test('failure of a cancelled sequence cannot stop a newer manual replay', async()=>{
    const fixture=controller({deferFirstPlay:true});await settle();
    fixture.click('sequence');await settle();
    fixture.click('reference');await settle();
    fixture.reject();await settle();
    assert.ok(fixture.player.current,'stale playback failure must not stop current playback');
    assert.equal(fixture.nodes['quick-status'].textContent,'Playing Reference…');
    fixture.click('stop');
});

test('manual replay completion clears the playing message',async()=>{
    const fixture=controller();await settle();fixture.click('reference');await settle();
    fixture.player.config.onState('ended','one/target.wav');
    assert.equal(fixture.nodes['quick-status'].textContent,'Choose the best feel, or replay anything.');
    fixture.click('stop');
});

test('failed persistence warning survives a vote and advance',async()=>{
    const fixture=controller({storageOK:false});await settle();
    assert.match(fixture.nodes['quick-saved'].textContent,/saving unavailable/);
    fixture.key('1');await settle();
    assert.match(fixture.nodes['quick-saved'].textContent,/saving unavailable/);
    fixture.click('stop');
});

test('an unavailable clip can be explicitly skipped without pretending it was heard',async()=>{
    const fixture=controller({failPreparation:true});await settle();
    fixture.key('s');
    assert.equal(fixture.state.choices.one?.kind,'skip');
    assert.deepEqual([...fixture.state.choices.one.auditionedCandidateIds],[]);
    fixture.click('stop');
});


test('winner stays on screen for adequacy, saves pending, then advances once',async()=>{
 const f=controller();await settle();f.key('1');
 assert.equal(f.state.choices.one.adequacy,null);
 assert.equal(f.nodes['quick-name'].textContent,'one');
 assert.equal(f.nodes['quick-adequacy'].hidden,false);
 assert.match(f.nodes['quick-adequacy-title'].textContent,/A/);
 f.key('2');
 assert.equal(f.state.choices.one.adequacy.level,'similar');
 assert.deepEqual([...f.state.choices.one.adequacy.candidateIds],['one-option']);
 assert.equal(f.nodes['quick-name'].textContent,'two');
 f.click('undo');await settle();
 assert.equal(f.nodes['quick-name'].textContent,'one');
 assert.equal(f.state.choices.one,undefined);
 f.click('stop');
});

test('reload resumes pending adequacy on the same reference and not-sure advances',async()=>{
 const choice={protocol:'feel-choice-v2',kind:'best',presentedCandidateIds:['one-option'],
   auditionedCandidateIds:['one-option'],preferredCandidateIds:['one-option'],adequacy:null};
 const f=controller({initialChoices:{one:choice}});await settle();
 assert.equal(f.nodes['quick-name'].textContent,'one');
 assert.equal(f.nodes['quick-adequacy'].hidden,false);
 f.key('s');assert.equal(f.state.choices.one.adequacy.level,'not-sure');
 assert.equal(f.nodes['quick-name'].textContent,'two');
 assert.equal(f.nodes['quick-undo'].disabled,false);f.click('undo');await settle();
 assert.equal(f.state.choices.one.adequacy,null);
 assert.equal(f.nodes['quick-name'].textContent,'one');
 assert.equal(f.nodes['quick-adequacy'].hidden,false);f.click('stop');
});

test('ties ask immediate likeness for displayed candidates; none needs no follow-up',async()=>{
 const f=controller();await settle();f.key('t');
 assert.match(f.nodes['quick-adequacy-title'].textContent,/tied options/);
 f.click('change-choice');await settle();
 assert.equal(f.nodes['quick-adequacy'].hidden,true);
 f.key('0');assert.equal(f.state.choices.one.kind,'none');
 assert.equal(f.state.choices.one.adequacy,null);
 assert.equal(f.nodes['quick-name'].textContent,'two');f.click('stop');
});

test('pending choice remains escapable when audio fails after reload',async()=>{
 const choice={protocol:'feel-choice-v2',kind:'best',presentedCandidateIds:['one-option'],
   auditionedCandidateIds:['one-option'],preferredCandidateIds:['one-option'],adequacy:null};
 const f=controller({initialChoices:{one:choice},failPreparation:true});await settle();
 assert.match(f.nodes['quick-status'].textContent,/choice is saved/);
 f.key('s');assert.equal(f.state.choices.one.adequacy.level,'not-sure');
 assert.equal(f.nodes['quick-name'].textContent,'two');f.click('stop');
});
