// A voice made visible. Fixed part layers stay intact while the whole puppet moves.
class SpeechPortrait {
    constructor(root) {
        this.root = root;
        this.puppet = this.part(root,'speech-puppet');
        this.part(this.puppet,'ear left');
        this.part(this.puppet,'ear right');
        this.part(this.puppet,'tuft left');
        this.part(this.puppet,'tuft right');
        const head = this.part(this.puppet,'head');
        for (const name of ['brow left','brow right','eye left','eye right',
            'cheek left','cheek right','muzzle','mouth']) this.part(head,name);
    }

    part(parent, className) {
        const part = document.createElement('span');
        part.className = className;
        parent.appendChild(part);
        return part;
    }

    update(p) {
        const n = name => Number.isFinite(p[name]) ? Math.max(0,Math.min(1,p[name])) : 0.5;
        const pitch = n('pitch'), mouth = n('mouth'), expression = n('expression');
        const grit = n('grit'), breath = n('breath'), seed = n('seed');
        const robot = p.texture === 2, squeak = p.texture === 1;
        const inflection = Number.isFinite(p.inflection) ? Math.max(-1,Math.min(1,p.inflection)) : 0;
        const width = 68 - pitch * 24;
        const height = 42 + pitch * 11 + mouth * 5;
        const earHeight = robot ? 12 : 13 + pitch * 16 + (squeak ? 7 : 0);
        const values = {
            '--head-width': width + 'px',
            '--head-height': height + 'px',
            '--head-top': (71 - height) + 'px',
            '--head-roundness': (robot ? 13 : 43 + expression * 6) + '%',
            '--jaw-roundness': (robot ? 10 : 30 + mouth * 20) + '%',
            '--ear-width': (robot ? 11 : 21 - pitch * 8 - (squeak ? 4 : 0)) + 'px',
            '--ear-height': earHeight + 'px',
            '--ear-top': (76 - height - earHeight * 0.65) + 'px',
            '--ear-inset': ((84 - width) / 2 + (robot ? -4 : 1)) + 'px',
            '--ear-roundness': (robot ? 15 : squeak ? 25 : 65) + '%',
            '--ear-left-angle': (-18 - inflection * 18 - n('wobble') * 12) + 'deg',
            '--ear-right-angle': (18 + inflection * 18 + (seed - 0.5) * 20) + 'deg',
            '--eye-width': (robot ? 7 : 4 + expression * 2) + 'px',
            '--eye-height': (3 + n('speed') * 5 + expression * 3 - n('spacing') * 1.5) + 'px',
            '--eye-inset': (23 + seed * 8) + '%',
            '--eye-roundness': (robot ? 15 : 50) + '%',
            '--brow-angle': (-inflection * 16 + grit * 18 - expression * 10) + 'deg',
            '--brow-opacity': 0.2 + expression * 0.5 + grit * 0.3,
            '--muzzle-width': (15 + mouth * 25) + 'px',
            '--muzzle-height': (9 + mouth * 10) + 'px',
            '--mouth-width': (5 + mouth * 17) + 'px',
            '--mouth-rest': (2 + breath * 2) + 'px',
            '--tuft-height': (4 + grit * 13) + 'px',
            '--tuft-opacity': grit,
            '--voice-hue': Math.round(25 + seed * 285),
            '--voice-saturation': (robot ? 15 : 36 - breath * 16) + '%',
            '--voice-lightness': (59 + breath * 16) + '%',
            '--cheek-opacity': 0.55 - breath * 0.25
        };
        for (const [name,value] of Object.entries(values)) this.root.style.setProperty(name,String(value));
        this.wobble = n('wobble');
        this.expression = expression;
        this.volume = n('masterVolume');
    }

    speak(event, time, reducedMotion = false) {
        const active = !!event && !reducedMotion && this.volume > 0;
        this.root.style.setProperty('--speech-open', active ? (3 + event.vowel * 1.5) * Math.sqrt(this.volume) + 'px' : '0px');
        this.root.style.setProperty('--speech-lift', active ? (-0.5 - this.expression * 1.5) + 'px' : '0px');
        this.root.style.setProperty('--speech-tilt', active ? Math.sin(time * 12) * this.wobble * 4 + 'deg' : '0deg');
    }
}
