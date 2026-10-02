class PhraseEditor {
    constructor(tab, parent) {
        this.tab = tab;
        this.card = document.createElement('section');
        this.card.className = 'phrase-editor';
        this.card.setAttribute('aria-label', 'Jinglr seeds');
        parent.appendChild(this.card);

        const row = document.createElement('div'); row.className = 'phrase-seed-row';
        const label = document.createElement('label'); label.className = 'phrase-seed-label'; label.textContent = 'Seed';
        this.seedInput = document.createElement('input');
        this.seedInput.type = 'text'; this.seedInput.inputMode = 'numeric';
        this.seedInput.maxLength = 10; this.seedInput.spellcheck = false;
        this.seedInput.title = 'Melody / instrument'; this.seedInput.setAttribute('aria-label', 'Seed');
        this.seedInput.addEventListener('change', () => {
            const code = this.seedInput.value.trim();
            if (!/^\d{10}$/.test(code)) { this.update(); return; }
            const melody = Number(code.slice(0, 5)), instrument = Number(code.slice(5));
            this.edit(['phrase','seed'], () => {
                if (melody !== Math.round(tab.synth.params.seed * 99999)) tab.synth.set_param('seed', melody / 99999);
                tab.synth.set_param('instrumentSeed', instrument);
            });
        });
        this.seedInput.addEventListener('keydown', event => {
            if (event.key === 'Enter' && !event.ctrlKey && !event.metaKey) { event.preventDefault(); this.seedInput.blur(); }
        });
        label.appendChild(this.seedInput); row.appendChild(label);
        this.generateButton = this.button('Reseed melody', () => {
            this.edit(['phrase','seed'], () => tab.synth.generate_phrase(true));
        });
        row.appendChild(this.generateButton); this.card.appendChild(row);

        const heading = document.createElement('div'); heading.className = 'phrase-section-label';
        heading.textContent = 'Reseed instrument'; this.card.appendChild(heading);
        const instruments = document.createElement('div'); instruments.className = 'phrase-instruments';
        this.instrumentButtons = tab.synth.get_param_info('instrument').values.map(([name, tip, value]) => {
            const button = this.button(name, () => {
                this.edit(['instrument','instrumentSeed'], () => tab.synth.generate_instrument(value));
            });
            button.title = tip;
            instruments.appendChild(button); return {button, value};
        });
        this.card.appendChild(instruments);
        this.card.addEventListener('keydown', event => {
            event.stopPropagation();
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); tab.play_sound(); }
        });
        this.update();
    }
    button(text, action) {
        const button = document.createElement('button'); button.type = 'button';
        button.textContent = text; button.addEventListener('click', action); return button;
    }
    edit(names, action) {
        // Explicit edits work even when generation locks were restored from an older file.
        const synth = this.tab.synth, locks = names.map(name => synth.locked_param(name));
        try {
            names.forEach(name => synth.set_locked_param(name, false));
            action();
        } finally { names.forEach((name, i) => synth.set_locked_param(name, locks[i])); }
        this.tab.parameter_changed(); this.update();
    }
    update() {
        const p = this.tab.synth.params;
        this.seedInput.value = String(Math.round(p.seed * 99999)).padStart(5, '0') +
            String(Math.round(p.instrumentSeed)).padStart(5, '0');
        for (const {button, value} of this.instrumentButtons) {
            button.setAttribute('aria-pressed', String(value === p.instrument));
        }
    }
}
