// A compact instrument surface for a two-state parameter. Graph edits are
// painted while dragging; audition and persistence happen once on release.
class TransitionEditor {
    static width = 320;
    static height = 42;
    static left = 8;
    static right = 312;
    static top = 6;
    static bottom = 36;

    static valueAtY(y) {
        return Math.max(0, Math.min(1, (36 - y) / 30));
    }

    static shift(value, amount) {
        const delta = Math.max(-Math.min(value.start, value.end), Math.min(1 - Math.max(value.start, value.end), amount));
        return {...value, start:value.start + delta, end:value.end + delta};
    }

    static destinationTime(curve) {
        return curve === 'Triangle' || curve === 'Pulse' ? 0.5 : 1;
    }

    static path(curve, start, end, width, height, inset) {
        let result = '';
        for (let i = 0; i <= 96; i++) {
            const t = i / 96;
            const x = inset + t * (width - inset * 2);
            const y = height - inset - (start + (end - start) * curve(t)) * (height - inset * 2);
            result += (i ? 'L' : 'M') + x.toFixed(2) + ',' + y.toFixed(2);
        }
        return result;
    }

    constructor(tab, info, cell) {
        this.tab = tab;
        this.info = info;
        this.drag = null;
        const heading = document.createElement('div');
        heading.className = 'transition_heading';
        heading.appendChild(tab.create_param_label(info.display_name, info.tooltip));
        const values = document.createElement('div');
        values.className = 'transition_values';
        this.readouts = {};
        for (const side of ['start', 'end']) {
            const label = document.createElement('span');
            label.className = 'transition_value';
            const caption = document.createElement('span');
            caption.textContent = side === 'start' ? 'A' : 'B';
            const readout = document.createElement('output');
            label.append(caption, readout);
            values.appendChild(label);
            this.readouts[side] = readout;
        }
        heading.appendChild(values);
        cell.appendChild(heading);
        const graph = this.svg('svg', {viewBox:'0 0 320 42', preserveAspectRatio:'none', role:'group', tabindex:0,
            'aria-label':info.display_name + ' transition graph'});
        graph.classList.add('transition_graph');
        graph.id = tab.name + '_graph_' + info.name;
        const title = this.svg('title');
        title.textContent = 'Drag A or B to set its level. Drag the middle to move both. Arrow keys adjust a focused handle; Shift makes fine adjustments.';
        graph.appendChild(title);
        for (const y of [6, 21, 36]) graph.appendChild(this.svg('path', {d:`M8,${y}H312`, class:'transition_grid'}));
        for (const x of [8, 84, 160, 236, 312]) graph.appendChild(this.svg('path', {d:`M${x},6V36`, class:'transition_grid'}));
        this.fill = this.svg('path', {class:'transition_fill'});
        this.line = this.svg('path', {class:'transition_line'});
        graph.append(this.fill, this.line);
        this.handles = {};
        for (const side of ['start', 'end']) {
            const handle = this.svg('circle', {r:4, tabindex:0, role:'slider',
                'aria-label':info.display_name + ' ' + side, 'aria-valuemin':0, 'aria-valuemax':1, 'aria-orientation':'vertical'});
            handle.classList.add('transition_handle');
            handle.dataset.endpoint = side;
            handle.addEventListener('keydown', event => this.keydown(event, side));
            graph.appendChild(handle);
            this.handles[side] = handle;
        }
        this.graph = graph;
        graph.addEventListener('pointerdown', event => this.pointerdown(event));
        graph.addEventListener('pointermove', event => this.pointermove(event));
        graph.addEventListener('pointerup', event => this.finish(event));
        graph.addEventListener('pointercancel', event => this.finish(event, true));
        graph.addEventListener('lostpointercapture', event => this.finish(event));
        graph.addEventListener('keydown', event => { if (event.target === graph) this.keydown(event, 'both'); });
        cell.appendChild(graph);
        const choices = document.createElement('div');
        choices.className = 'transition_shapes';
        choices.setAttribute('role', 'group');
        choices.setAttribute('aria-label', info.display_name + ' curve shapes');
        this.buttons = [];
        for (const [name, curve] of tab.synth.constructor.tweenfunctions) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'transition_shape';
            button.title = name;
            button.setAttribute('aria-label', info.display_name + ' curve: ' + name);
            const icon = this.svg('svg', {viewBox:'0 0 32 18', 'aria-hidden':true});
            icon.appendChild(this.svg('path', {d:TransitionEditor.path(curve, 0, 1, 32, 18, 3)}));
            button.appendChild(icon);
            button.addEventListener('click', () => this.set({...this.value(), curve:name}, true));
            choices.appendChild(button);
            this.buttons.push({name, button});
        }
        cell.appendChild(choices);
        this.update();
    }

    svg(tag, attributes = {}) {
        const element = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value);
        return element;
    }

    value() { return this.tab.synth.params[this.info.name]; }

    set(value, commit = false) {
        this.tab.synth.set_param(this.info.name, value);
        this.update();
        if (commit) this.tab.parameter_changed();
    }

    update() {
        const value = this.value();
        const curve = this.tab.synth.constructor.tweenfunctions.find(c => c[0] === value.curve)[1];
        // Use separate horizontal/vertical insets so the large graph has room for its handles.
        let path = '';
        for (let i = 0; i <= 160; i++) {
            const t = i / 160;
            const y = 36 - (value.start + (value.end - value.start) * curve(t)) * 30;
            path += (i ? 'L' : 'M') + (8 + t * 304).toFixed(2) + ',' + y.toFixed(2);
        }
        this.line.setAttribute('d', path);
        this.fill.setAttribute('d', path + 'L312,36L8,36Z');
        for (const side of ['start', 'end']) {
            const handle = this.handles[side];
            const text = this.tab.synth.format_transition_value(this.info.name, value[side]);
            this.readouts[side].textContent = text;
            handle.setAttribute('cx', side === 'start' ? 8 : 8 + TransitionEditor.destinationTime(value.curve) * 304);
            handle.setAttribute('cy', 36 - value[side] * 30);
            handle.setAttribute('aria-valuenow', value[side]);
            handle.setAttribute('aria-valuetext', text);
        }
        for (const {name, button} of this.buttons) button.setAttribute('aria-pressed', name === value.curve);
    }

    position(event) {
        const bounds = this.graph.getBoundingClientRect();
        return {x:(event.clientX - bounds.left) / bounds.width * 320,
            y:(event.clientY - bounds.top) / bounds.height * 42};
    }

    pointerdown(event) {
        if (event.button !== 0 || this.drag) return;
        event.preventDefault();
        const point = this.position(event);
        const initial = {...this.value()};
        let side = event.target.dataset.endpoint;
        if (!side) {
            // A nearby dot gets first choice, including B at the peak of a returning curve.
            const endX = 8 + TransitionEditor.destinationTime(initial.curve) * 304;
            const near = (x, y) => Math.hypot(point.x - x, point.y - y) < 14;
            if (near(8, 36 - initial.start * 30)) side = 'start';
            else if (near(endX, 36 - initial.end * 30)) side = 'end';
            else side = point.x < 80 ? 'start' : point.x > 240 ? 'end' : 'both';
        }
        this.drag = {id:event.pointerId, side, initial, y:point.y, changed:false};
        this.graph.setPointerCapture(event.pointerId);
        this.graph.classList.add('dragging');
        if (side !== 'both') this.handles[side].focus();
        else this.graph.focus();
        this.pointermove(event);
    }

    pointermove(event) {
        if (!this.drag || this.drag.id !== event.pointerId) return;
        const point = this.position(event);
        const {side, initial} = this.drag;
        const next = side === 'both'
            ? TransitionEditor.shift(initial, (this.drag.y - point.y) / 30)
            : {...initial, [side]:TransitionEditor.valueAtY(point.y)};
        if (next.start === this.value().start && next.end === this.value().end) return;
        this.drag.changed = true;
        this.set(next);
    }

    finish(event, cancel = false) {
        if (!this.drag || this.drag.id !== event.pointerId) return;
        const drag = this.drag;
        this.drag = null;
        this.graph.classList.remove('dragging');
        if (this.graph.hasPointerCapture(event.pointerId)) this.graph.releasePointerCapture(event.pointerId);
        if (cancel) this.set(drag.initial);
        else if (drag.changed) this.tab.parameter_changed();
    }

    keydown(event, side) {
        if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        const value = this.value();
        const delta = (event.key === 'ArrowDown' ? -1 : 1) * (event.shiftKey ? 0.001 : 0.01);
        const amount = event.key === 'Home' ? -1 : event.key === 'End' ? 1 : delta;
        this.set(side === 'both' ? TransitionEditor.shift(value, amount)
            : {...value, [side]:event.key === 'Home' ? 0 : event.key === 'End' ? 1 : value[side] + delta}, true);
    }
}
