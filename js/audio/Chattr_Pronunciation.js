// English text to stressed ARPABET. Dictionary entries take precedence over spelling rules.
class Chattr_Pronunciation {
    static vowels = new Set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split(' '));
    static inventory = new Set('AA AE AH AO AW AY B CH D DH EH ER EY F G HH IH IY JH K L M N NG OW OY P R S SH T TH UH UW V W Y Z ZH'.split(' '));
    static smallNumbers = ['zero','one','two','three','four','five','six','seven','eight','nine',
        'ten','eleven','twelve','thirteen','fourteen','fifteen','sixteen','seventeen','eighteen','nineteen'];
    static tens = ['','','twenty','thirty','forty','fifty','sixty','seventy','eighty','ninety'];
    static spelling = [
        ['tion','SH AH N'], ['sion','ZH AH N'], ['tch','CH'], ['dge','JH'], ['igh','AY'],
        ['air','EH R'], ['ear','IH R'], ['ph','F'], ['sh','SH'], ['ch','CH'], ['th','TH'],
        ['ng','NG'], ['qu','K W'], ['ck','K'], ['wh','W'], ['zh','ZH'], ['dh','DH'],
        ['ee','IY'], ['ea','IY'], ['oo','UW'], ['ai','EY'], ['ay','EY'], ['ei','EY'], ['ey','EY'],
        ['oa','OW'], ['oe','OW'], ['ow','AW'], ['ou','AW'], ['oi','OY'], ['oy','OY'],
        ['au','AO'], ['aw','AO'], ['ie','IY'], ['ue','UW'],
        ['ar','AA R'], ['er','ER'], ['ir','ER'], ['ur','ER'], ['or','AO R']
    ];

    static normalize(text) {
        return String(text ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '')
            .replace(/[\u2018\u2019\u02bc]/g, "'").toLowerCase();
    }

    // Returns {phone, stress}[], preserving CMUdict's 0/1/2 stresses and all 39 phones.
    // Bare vowels (used by the fallback) receive stress 1 on the first vowel, then 0.
    static parse(arpabet) {
        const result = [];
        let vowelCount = 0;
        for (const value of Array.isArray(arpabet) ? arpabet : String(arpabet || '').split(/\s+/)) {
            const match = /^([A-Z]+)([012]?)$/.exec(value);
            if (!match || !this.inventory.has(match[1])) continue;
            const phone = match[1];
            let stress = null;
            if (this.vowels.has(phone)) {
                stress = match[2] ? Number(match[2]) : (vowelCount === 0 ? 1 : 0);
                vowelCount++;
            }
            result.push({phone, stress});
        }
        return result;
    }

    static fallback(word) {
        word = word.replace(/'/g, '');
        const phones = [];
        const consonants = {b:'B',d:'D',f:'F',g:'G',h:'HH',j:'JH',k:'K',l:'L',m:'M',n:'N',
            p:'P',q:'K',r:'R',s:'S',t:'T',v:'V',w:'W',x:'K S',z:'Z'};
        const shortVowels = {a:'AE',e:'EH',i:'IH',o:'AA',u:'AH'};
        const longVowels = {a:'EY',e:'IY',i:'AY',o:'OW',u:'Y UW'};
        let i = /^(kn|gn|pn|ps|wr)/.test(word) ? 1 : 0;
        while (i < word.length) {
            const tail = word.slice(i), letter = word[i];
            // Consonant + final -le has a schwa: flomble -> F L AA M B AH L.
            if (tail === 'le' && i > 0 && !/[aeiouy]/.test(word[i - 1])) {
                phones.push('AH', 'L');
                break;
            }
            if (tail === 'mb') { phones.push('M'); break; }
            const pair = this.spelling.find(([letters]) => tail.startsWith(letters));
            if (pair) {
                phones.push(...pair[1].split(' '));
                i += pair[0].length;
                continue;
            }
            if (letter === 'e' && i === word.length - 1 && /[aeiouy]/.test(word.slice(0, i))) break;
            if (shortVowels[letter]) {
                const long = /^[aeiou][b-df-hj-np-tv-z]e$/.test(tail);
                phones.push(...(long ? longVowels[letter] : shortVowels[letter]).split(' '));
            } else if (letter === 'y') {
                phones.push(i === 0 ? 'Y' : i === word.length - 1 ?
                    (/[aeiou]/.test(word.slice(0, i)) ? 'IY' : 'AY') : 'IH');
            } else if (letter === 'c') {
                phones.push(/^[eiy]/.test(tail.slice(1)) ? 'S' : 'K');
            } else if (letter === 'g' && /^[eiy]/.test(tail.slice(1))) {
                phones.push('JH');
            } else if (consonants[letter]) {
                phones.push(...(letter === 'x' && i === 0 ? 'Z' : consonants[letter]).split(' '));
            }
            // Doubled consonants indicate the preceding short vowel, not two releases.
            i += !/[aeiouy]/.test(letter) && word[i + 1] === letter ? 2 : 1;
        }
        return this.parse(phones);
    }

    static entry(value) {
        const word = this.normalize(value).replace(/^'+|'+$/g, '');
        if (!/^[a-z]+(?:'[a-z]+)*$/.test(word)) return null;
        const pronunciation = ChattrLexicon.lookup(word);
        const phones = pronunciation ? this.parse(pronunciation) : this.fallback(word);
        return phones.length ? {word, phones, approximate:!pronunciation} : null;
    }

    // Single-word convenience API; unsupported words return [], never partial fragments.
    static word(value) {
        const entry = this.entry(value);
        return entry ? entry.phones : [];
    }

    static number(digits) {
        if (digits.length > 6 || (digits.length > 1 && digits[0] === '0')) {
            return Array.from(digits, digit => this.smallNumbers[Number(digit)]);
        }
        const underThousand = value => {
            const words = [];
            if (value >= 100) {
                words.push(this.smallNumbers[Math.floor(value / 100)], 'hundred');
                value %= 100;
            }
            if (value >= 20) {
                words.push(this.tens[Math.floor(value / 10)]);
                value %= 10;
            }
            if (value || !words.length) words.push(this.smallNumbers[value]);
            return words;
        };
        const value = Number(digits);
        if (value < 1000) return underThousand(value);
        return [...underThousand(Math.floor(value / 1000)), 'thousand',
            ...(value % 1000 ? underThousand(value % 1000) : [])];
    }

    // A word token is {word, phones, approximate}; a pause is {punctuation}.
    // Bounded expansion stops at a whole word; the returned array has truncated=true
    // when the 160-character input, 96-word, or 512-phone limit dropped content.
    static tokenize(value) {
        const source = String(value ?? '');
        const text = this.normalize(source.slice(0, 160)).replace(/\u2026/g, '...')
            .replace(/[\u2013\u2014]/g, '-').replace(/["\u201c\u201d()\[\]{}]/g, ' ');
        const tokens = [];
        if (source.length > 160) tokens.truncated = true;
        let wordCount = 0, phoneCount = 0;
        // Keep entire whitespace-delimited chunks for validation: abcЖdef or a🐸b must
        // not turn into several accidental English words after unsupported characters vanish.
        const chunks = text.match(/[^\s.,!?;:\-]+|[.,!?;:\-]+/g) || [];
        for (const chunk of chunks) {
            if (/^[.,!?;:\-]+$/.test(chunk)) {
                const previous = tokens[tokens.length - 1];
                const group = chunk + (previous && previous.punctuation || '');
                const punctuation = ['?','!','.',';',':',',','-'].find(mark => group.includes(mark));
                if (previous && previous.punctuation) previous.punctuation = punctuation;
                else tokens.push({punctuation});
                continue;
            }
            const words = /^\d+$/.test(chunk) ? this.number(chunk) : [chunk];
            for (const word of words) {
                const entry = this.entry(word);
                if (!entry) continue;
                if (wordCount >= 96 || phoneCount + entry.phones.length > 512) {
                    tokens.truncated = true;
                    return tokens;
                }
                tokens.push(entry);
                wordCount++;
                phoneCount += entry.phones.length;
            }
        }
        return tokens;
    }
}
