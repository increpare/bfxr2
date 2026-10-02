// Text entry and a tiny speaking companion. The synth owns all persistent state.
class SpeechEditor {
    constructor(tab, info, parent) {
        this.tab = tab;
        this.info = info;
        this.frame = null;
        const row = parent.children[0].insertRow();
        const cell = row.insertCell();
        cell.colSpan = 3;
        this.card = document.createElement('div');
        this.card.className = 'speech-card';
        cell.appendChild(this.card);

        const heading = document.createElement('div');
        heading.className = 'speech-heading';
        this.face = document.createElement('div');
        this.face.className = 'speech-face';
        this.face.setAttribute('aria-hidden','true');
        this.face.title = 'This little friend changes shape with the voice controls.';
        this.portrait = new SpeechPortrait(this.face);
        heading.appendChild(this.face);
        const greeting = document.createElement('div');
        const title = document.createElement('strong');
        title.textContent = 'Small talk. Big personality.';
        const subtitle = document.createElement('span');
        subtitle.textContent = 'Give an imaginary friend a voice.';
        greeting.append(title,subtitle);
        heading.appendChild(greeting);
        this.card.appendChild(heading);

        const label = document.createElement('label');
        label.textContent = info.display_name;
        const id = tab.name + '_text_' + info.name;
        label.htmlFor = id;
        this.card.appendChild(label);
        this.input = document.createElement('textarea');
        this.input.id = id;
        this.input.maxLength = info.max_length;
        this.input.rows = 2;
        this.input.placeholder = 'Hello, little world!';
        this.input.spellcheck = false;
        this.card.appendChild(this.input);

        const meta = document.createElement('div');
        meta.className = 'speech-meta';
        this.status = document.createElement('span');
        this.status.id = id + '_hint';
        this.input.setAttribute('aria-describedby',this.status.id);
        this.counter = document.createElement('span');
        meta.append(this.status,this.counter);
        this.card.appendChild(meta);

        const buttons = document.createElement('div');
        buttons.className = 'speech-actions';
        this.say = this.button('Say it!', 'Speak this line. Ctrl/Cmd + Enter also works.', () => tab.play_sound());
        this.say.className = 'speech-say';
        this.stopButton = this.button('Stop', 'Let the little voice rest.', () => this.stop());
        const surprise = this.button('Surprise line', 'A small thought to try with this voice.', () => {
            const phrases = tab.synth.constructor.phrases;
            const choices = phrases.filter(text => text !== this.input.value);
            this.input.value = choices[Math.floor(Math.random() * choices.length)];
            this.save_words();
            if (tab.play_on_change) tab.play_sound();
            else this.refresh_waveform();
        });
        buttons.append(this.say,this.stopButton,surprise);
        this.card.appendChild(buttons);
        const note = document.createElement('p');
        note.className = 'speech-note';
        note.textContent = 'Articulation: chatter ↔ speech. English words; try Clear Speaker.';
        this.card.appendChild(note);

        this.input.addEventListener('input', () => this.save_words());
        this.input.addEventListener('change', () => this.refresh_waveform());
        this.input.addEventListener('keydown', event => {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !event.isComposing) {
                event.preventDefault(); event.stopPropagation(); tab.play_sound();
            } else if (event.key === 'Escape') this.stop();
        });
        this.update();
    }

    button(text, title, action) {
        const button = document.createElement('button');
        button.type = 'button'; button.textContent = text; button.title = title;
        button.addEventListener('click',action);
        return button;
    }

    save_words() {
        this.stop();
        const tab = this.tab;
        tab.synth.set_param(this.info.name,this.input.value);
        const state = JSON.stringify(tab.synth.params);
        if (tab.selected_file_index < 0) {
            tab.files.push([tab.find_unique_filename('SmallTalk'),state,state]);
            tab.selected_file_index = tab.files.length - 1;
            tab.update_ui_file_list();
        } else tab.files[tab.selected_file_index][1] = state;
        tab.update_ablements();
        SaveLoad.save_all_collections();
        this.update();
    }

    refresh_waveform() {
        if (this.tab.synth.sound_params === JSON.stringify(this.tab.synth.params)) return;
        this.tab.synth.generate_sound();
        this.tab.redraw_waveform();
    }

    update() {
        const text = this.tab.synth.params[this.info.name];
        if (this.input.value !== text) this.input.value = text;
        this.counter.textContent = text.length + ' / ' + this.info.max_length;
        this.say.disabled = !Chattr_Pronunciation.tokenize(text).some(token => token.phones && token.phones.length);
        if (this.frame === null) this.status.textContent = this.say.disabled ? 'A little quiet. Add some words.' : 'Ctrl/Cmd + Enter to speak';
        this.preview_params(this.tab.synth.params);
        if (this.frame === null) this.stopButton.disabled = true;
    }

    preview_params(params) {
        this.portrait.update(params);
    }

    stop_animation() {
        if (this.frame !== null) cancelAnimationFrame(this.frame);
        this.frame = null;
        this.portrait.speak(null,0);
        this.stopButton.disabled = true;
        this.status.textContent = this.say.disabled ? 'A little quiet. Add some words.' : 'Ctrl/Cmd + Enter to speak';
    }

    stop() {
        if (this.tab.synth.sound) this.tab.synth.sound.stop();
        this.stop_animation();
    }

    play() {
        this.stop_animation();
        this.preview_params(this.tab.synth.params);
        const sound = this.tab.synth.sound;
        const source = sound.source;
        const score = this.tab.synth.score;
        if (!score || !score.events.length) return;
        const started = AUDIO_CONTEXT.currentTime;
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        let eventIndex = 0;
        this.stopButton.disabled = false;
        this.status.textContent = score.truncated ? 'A long line — speaking the first part.' : 'A very important conversation...';
        const animate = () => {
            const time = AUDIO_CONTEXT.currentTime - started;
            if (time >= score.duration || this.tab.synth.sound !== sound || sound.source !== source || !this.tab.active) {
                // A tab switch also ends the voice, rather than leaving invisible chatter running.
                if (!this.tab.active && sound.source === source) sound.stop();
                this.stop_animation();
                return;
            }
            while (eventIndex < score.events.length && time > score.events[eventIndex].start + score.events[eventIndex].duration) eventIndex++;
            const event = score.events[eventIndex];
            const speaking = event && time >= event.start;
            this.portrait.speak(speaking ? event : null,time,reducedMotion);
            this.frame = requestAnimationFrame(animate);
        };
        this.frame = requestAnimationFrame(animate);
    }
}
