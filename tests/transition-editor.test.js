const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function editor() {
    const ctx = vm.createContext({});
    const file = path.resolve(__dirname, '../js/TransitionEditor.js');
    if (fs.existsSync(file)) vm.runInContext(fs.readFileSync(file, 'utf8'), ctx);
    return source => vm.runInContext(source, ctx);
}
const plain = value => JSON.parse(JSON.stringify(value));

test('graph positions map to bounded endpoint values', () => {
    const run = editor();
    assert.deepEqual(plain(run(`[TransitionEditor.valueAtY(6), TransitionEditor.valueAtY(36),
        TransitionEditor.valueAtY(21), TransitionEditor.valueAtY(-20), TransitionEditor.valueAtY(70)]`)),
        [1, 0, 0.5, 1, 0]);
});

test('dragging the whole transition preserves the interval at either limit', () => {
    const run = editor();
    const raised=plain(run(`TransitionEditor.shift({start:0.2,end:0.8,curve:'Smooth'},0.5)`));
    assert.ok(Math.abs(raised.start-0.4)<1e-12);
    assert.equal(raised.end,1);
    assert.equal(raised.curve,'Smooth');
    const lowered=plain(run(`TransitionEditor.shift({start:0.2,end:0.8,curve:'Smooth'},-0.5)`));
    assert.equal(lowered.start,0);
    assert.ok(Math.abs(lowered.end-0.6)<1e-12);
});

test('returning curves put the destination handle at the peak', () => {
    const run = editor();
    assert.deepEqual(plain(run(`['Linear','Pulse','Triangle','Bounce','Steps'].map(TransitionEditor.destinationTime)`)),
        [1,0.5,0.5,1,1]);
});

test('shape icons depict the full normalized curve independently of endpoint values', () => {
    const run=editor();
    const result=run(`TransitionEditor.path(t=>t,0,1,32,18,3)`);
    assert.ok(result.startsWith('M3.00,15.00'));
    assert.ok(result.endsWith('L29.00,3.00'));
});

function gestures() {
    const run=editor();
    run(`var value={start:0.2,end:0.8,curve:'Smooth'},commits=0;
        var e=Object.create(TransitionEditor.prototype); e.info={name:'pitch'}; e.drag=null;
        e.tab={synth:{params:{pitch:value},set_param(name,next){this.params[name]=next;}},parameter_changed(){commits++;}};
        e.update=()=>{};
        e.handles={start:{focus(){}},end:{focus(){}}};
        e.graph={getBoundingClientRect(){return {left:0,top:0,width:320,height:42};},
            setPointerCapture(){},hasPointerCapture(){return true;},releasePointerCapture(){},focus(){},
            classList:{add(){},remove(){}}};
        function event(x,y,side){return {clientX:x,clientY:y,pointerId:1,button:0,
            target:{dataset:side?{endpoint:side}:{}},preventDefault(){}};}`);
    return run;
}

test('graph dragging updates the endpoint immediately and commits only on release', () => {
    const run=gestures();
    run(`e.pointerdown(event(8,30,'start')); e.pointermove(event(8,15,'start'));`);
    assert.equal(run('e.value().start'),0.7);
    assert.equal(run('e.value().end'),0.8);
    assert.equal(run('commits'),0);
    run('e.finish(event(8,15));');
    assert.equal(run('commits'),1);
    run('e.finish(event(8,15));');
    assert.equal(run('commits'),1);
});

test('cancelling a pointer gesture restores both values without committing', () => {
    const run=gestures();
    run(`e.pointerdown(event(150,25)); e.pointermove(event(150,19)); e.finish(event(150,19),true);`);
    assert.deepEqual(plain(run('e.value()')),{start:0.2,end:0.8,curve:'Smooth'});
    assert.equal(run('commits'),0);
});

test('keyboard gestures offer fine endpoint edits and whole-curve movement', () => {
    const run=gestures();
    run(`e.keydown({key:'ArrowDown',shiftKey:true,preventDefault(){},stopPropagation(){}},'end');`);
    assert.ok(Math.abs(run('e.value().end')-0.799)<1e-12);
    run(`e.keydown({key:'End',shiftKey:false,preventDefault(){},stopPropagation(){}},'both');`);
    assert.equal(run('e.value().end'),1);
    assert.ok(Math.abs(run('e.value().start')-0.401)<1e-12);
});
