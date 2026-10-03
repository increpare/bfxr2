// The Soundboard's grid of verb buttons and the card describing the last sound.
class BoardEditor {
    static keys = [['1','2','3','4','5'],['q','w','e','r','t'],['a','s','d','f','g'],['z','x','c','v','b'],['6','7','8','9','0']];
    constructor(tab, parent) {
        this.tab = tab;
        this.pinned = false;
        this.root = document.createElement('section'); this.root.className = 'board-editor';
        parent.appendChild(this.root);
        const intro = document.createElement('p'); intro.className = 'board-intro';
        intro.textContent = 'Press a verb for a fresh game sound. Every press is a new take from a different corner of the suite.';
        this.root.appendChild(intro);
        this.grid = document.createElement('div'); this.grid.className = 'board-grid';
        this.root.appendChild(this.grid);
        this.buttons = {};
        const rows = [...new Set(GAME_VERBS.map(verb => verb.row))];
        rows.forEach((row, rowIndex) => {
            const label = document.createElement('div'); label.className = 'board-row-label'; label.textContent = row;
            this.grid.appendChild(label);
            GAME_VERBS.filter(verb => verb.row === row).forEach((verb, column) => {
                // The verb buttons already exist as preset buttons; move them into the grid.
                let button = document.getElementById(tab.name + '_generator_generate_' + verb.id);
                if (!button) { button = document.createElement('button'); button.textContent = verb.name; button.addEventListener('click', () => tab.template_clicked('generate_' + verb.id)); }
                button.classList.add('board-verb'); button.dataset.verb = verb.id;
                const key = (BoardEditor.keys[rowIndex] || [])[column];
                if (key) { const hint = document.createElement('span'); hint.className = 'board-key'; hint.textContent = key.toUpperCase(); button.appendChild(hint); button.title = verb.tip + ' [' + key.toUpperCase() + ']'; }
                this.grid.appendChild(button);
                this.buttons[verb.id] = button;
            });
        });
        this.card = document.createElement('div'); this.card.className = 'board-card';
        this.root.appendChild(this.card);
        this.description = document.createElement('div'); this.description.className = 'board-description';
        this.card.appendChild(this.description);
        const actions = document.createElement('div'); actions.className = 'board-actions';
        this.card.appendChild(actions);
        const action = (text, title, handler) => { const b = document.createElement('button'); b.textContent = text; b.title = title; b.addEventListener('click', handler); actions.appendChild(b); return b; };
        this.again = action('Again', 'Another take of the same verb. [Space]', () => this.again_clicked());
        this.variation = action('Variation', 'Nudge this take a little.', () => { tab.synth.mutate_params(); tab.create_new_sound_from_params(this.file_name(), tab.synth.params); });
        this.pin = action('Pin ingredients', 'Keep these ingredients; Again only re-rolls their details.', () => { this.pinned = !this.pinned; this.update(); });
        this.opens = document.createElement('div'); this.opens.className = 'board-opens';
        this.card.appendChild(this.opens);
        this.keydown = event => this.on_key_down(event);
        document.addEventListener('keydown', this.keydown);
        this.update();
    }
    file_name() {
        const verb = game_verb(this.tab.synth.verb());
        return verb ? verb.name : this.tab.get_current_file_name();
    }
    again_clicked() {
        const synth = this.tab.synth;
        const verb = synth.verb();
        if (this.pinned && synth.get_sources().some(Boolean)) {
            synth.regenerate_both();
            this.tab.create_new_sound_from_params(this.file_name(), synth.params);
        } else if (verb) this.tab.template_clicked('generate_' + verb);
        else synth.randomize_params(), this.tab.create_new_sound_from_params(this.file_name(), synth.params);
    }
    on_key_down(event) {
        if (!this.tab.active || event.ctrlKey || event.metaKey || event.altKey) return;
        const target = document.activeElement;
        if (target && (target.isContentEditable || ['SELECT','TEXTAREA','INPUT'].includes(target.tagName))) return;
        const key = event.key.toLowerCase();
        if (key === ' ') { event.preventDefault(); this.again_clicked(); return; }
        for (let row = 0; row < BoardEditor.keys.length; row++) {
            const column = BoardEditor.keys[row].indexOf(key);
            if (column < 0) continue;
            const rows = [...new Set(GAME_VERBS.map(verb => verb.row))];
            const verb = GAME_VERBS.filter(verb => verb.row === rows[row])[column];
            if (verb) { event.preventDefault(); this.tab.template_clicked('generate_' + verb.id); }
            return;
        }
    }
    open_source(source) {
        const tab = SaveLoad.tab_for_import(source.synth);
        if (!tab) return;
        tab.set_active_tab();
        tab.create_new_sound_from_params(source.name, source.params, true);
    }
    open_in_mixfxr() {
        const mix = tabs.find(tab => tab.name === 'Mixr');
        if (!mix) return;
        mix.set_active_tab();
        mix.create_new_sound_from_params(this.file_name(), {...this.tab.synth.params}, true);
    }
    update() {
        const synth = this.tab.synth;
        const verb = synth.verb();
        for (const [id, button] of Object.entries(this.buttons)) button.classList.toggle('board-active', id === verb);
        this.description.textContent = synth.describe();
        this.pin.classList.toggle('board-pinned', this.pinned);
        this.pin.textContent = this.pinned ? 'Pinned' : 'Pin ingredients';
        const sources = synth.get_sources().filter(Boolean);
        this.again.disabled = !verb && !sources.length;
        this.variation.disabled = !sources.length;
        this.pin.disabled = !sources.length;
        this.opens.replaceChildren();
        for (const source of sources) {
            const b = document.createElement('button');
            b.textContent = 'Open in ' + synth_display_name(source.synth);
            b.title = 'Edit this ingredient in its own tab.';
            b.addEventListener('click', () => this.open_source(source));
            this.opens.appendChild(b);
        }
        if (sources.length) {
            const b = document.createElement('button'); b.textContent = 'Open in Mixfxr'; b.title = 'Edit the whole mix in Mixfxr.';
            b.addEventListener('click', () => this.open_in_mixfxr()); this.opens.appendChild(b);
        }
    }
}
