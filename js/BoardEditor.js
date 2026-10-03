// The Soundboard's grid of verb buttons and the card describing the last sound.
class BoardEditor {
    static keys = [['1','2','3','4','5'],['q','w','e','r','t'],['a','s','d','f','g'],['z','x','c','v','b'],['6','7','8','9','0']];
    constructor(tab, parent) {
        this.tab = tab;
        this.root = document.createElement('section'); this.root.className = 'board-editor';
        parent.appendChild(this.root);
        this.grid = document.createElement('div'); this.grid.className = 'board-grid';
        this.root.appendChild(this.grid);
        this.buttons = {};
        const rows = [...new Set(GAME_VERBS.map(verb => verb.row))];
        rows.forEach((row, rowIndex) => {
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
        this.keydown = event => this.on_key_down(event);
        document.addEventListener('keydown', this.keydown);
        this.update();
    }
    file_name() {
        const verb = game_verb(this.tab.synth.verb());
        return verb ? verb.name : this.tab.get_current_file_name();
    }
    again_clicked() {
        const verb = this.tab.synth.verb();
        if (verb) this.tab.template_clicked('generate_' + verb);
        else this.tab.template_clicked('randomize_params');
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
    update() {}
}
