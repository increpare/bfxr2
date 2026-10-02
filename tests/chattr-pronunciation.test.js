const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
for (const file of ['ChattrLexicon.js', 'Chattr_Pronunciation.js']) {
    const filename = path.join(__dirname, '..', 'js', 'audio', file);
    vm.runInContext(fs.readFileSync(filename, 'utf8'), ctx);
}
function run(code) {
    assert.equal(vm.runInContext('typeof Chattr_Pronunciation', ctx), 'function',
        'The pronunciation layer must expose Chattr_Pronunciation');
    return vm.runInContext(code, ctx);
}
const plain = value => JSON.parse(JSON.stringify(value));
const tokenize = text => plain(run(`Chattr_Pronunciation.tokenize(${JSON.stringify(text)})`));
const phones = word => plain(run(`Chattr_Pronunciation.word(${JSON.stringify(word)})`))
    .map(({phone, stress}) => phone + (stress === null ? '' : stress));

test('dictionary pronunciation retains English distinctions and vowel stress', () => {
    assert.deepEqual(phones('phone'), ['F', 'OW1', 'N']);
    assert.deepEqual(phones('ship'), ['SH', 'IH1', 'P']);
    assert.deepEqual(phones('sheep'), ['SH', 'IY1', 'P']);
    assert.deepEqual(phones('knight'), phones('night'));
    assert.deepEqual(phones('two'), phones('too'));
    assert.deepEqual(phones('hello'), ['HH', 'AH0', 'L', 'OW1']);
    assert.equal(tokenize('Hello')[0].approximate, false);
});

test('all 39 standard phonemes survive parsing with only vowel stress', () => {
    const inventory = 'AA AE AH AO AW AY B CH D DH EH ER EY F G HH IH IY JH K L M N NG OW OY P R S SH T TH UH UW V W Y Z ZH'.split(' ');
    const vowels = new Set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split(' '));
    const source = inventory.map((phone, i) => phone + (vowels.has(phone) ? i % 3 : ''));
    const parsed = plain(run(`Chattr_Pronunciation.parse(${JSON.stringify(source)})`));
    assert.equal(parsed.length, 39);
    assert.deepEqual(parsed, inventory.map((phone, i) => ({phone, stress:vowels.has(phone) ? i % 3 : null})));
    assert.deepEqual(plain(run(`Chattr_Pronunciation.parse('B AH D IY')`)), [
        {phone:'B',stress:null}, {phone:'AH',stress:1}, {phone:'D',stress:null}, {phone:'IY',stress:0}
    ]);
});

test('normalization handles accents and smart apostrophes before dictionary lookup', () => {
    assert.deepEqual(tokenize('Héllo, DON’T!'), tokenize("hello, don't!"));
    assert.equal(tokenize('don’t')[0].approximate, false);
    assert.deepEqual(tokenize("'hello'"), tokenize('hello'));
});

test('unsupported scripts and symbols do not leak fragments of mixed words', () => {
    const result = tokenize('hello 世界 мirbye abcЖdef x🐸y 🐸 héllo');
    assert.deepEqual(result.map(token => token.word), ['hello', 'hello']);
    assert.deepEqual(tokenize('世界 😀 Кириллица'), []);
    assert.deepEqual(phones('abcЖdef'), []);
});

test('punctuation groups collapse to a single bounded pause with question priority', () => {
    const result = tokenize('hello... !!! ?? , ;  sheep----ship');
    assert.deepEqual(result.filter(token => token.punctuation), [{punctuation:'?'}, {punctuation:'-'}]);
    assert.deepEqual(result.filter(token => token.word).map(token => token.word), ['hello', 'sheep', 'ship']);
    assert.deepEqual(tokenize('hello…sheep'), tokenize('hello...sheep'));
    assert.deepEqual(tokenize('hello' + '!'.repeat(150)), [...tokenize('hello'), {punctuation:'!'}]);
});

test('numbers through 999999 expand into ordinary English words', () => {
    for (const [number, expansion] of [
        ['0', 'zero'], ['12', 'twelve'], ['20', 'twenty'], ['42', 'forty two'],
        ['100', 'one hundred'], ['105', 'one hundred five'], ['1000', 'one thousand'],
        ['2048', 'two thousand forty eight'],
        ['999999', 'nine hundred ninety nine thousand nine hundred ninety nine']
    ]) assert.deepEqual(tokenize(number), tokenize(expansion), number);
});

test('large numbers and leading zeroes are read as digits', () => {
    assert.deepEqual(tokenize('007'), tokenize('zero zero seven'));
    assert.deepEqual(tokenize('1000000'), tokenize('one zero zero zero zero zero zero'));
});

test('number expansion has a phone and word budget and reports truncation', () => {
    const result = tokenize('7'.repeat(160));
    assert.ok(result.length > 1 && result.length <= 96);
    assert.ok(result.reduce((sum, token) => sum + (token.phones || []).length, 0) <= 512);
    assert.equal(run(`Chattr_Pronunciation.tokenize('7'.repeat(160)).truncated`), true);
    assert.ok(result.every(token => token.word === 'seven' && token.phones.length > 0));
    assert.equal(Boolean(run(`Chattr_Pronunciation.tokenize('12').truncated`)), false);
});

test('input is bounded to 160 characters without empty word tokens', () => {
    assert.deepEqual(tokenize('hello ' + ' '.repeat(154) + 'sheep'), tokenize('hello'));
    assert.equal(run(`Chattr_Pronunciation.tokenize('hello ' + ' '.repeat(154) + 'sheep').truncated`), true);
    assert.deepEqual(tokenize('  \n\t'), []);
    assert.ok(tokenize("'' hello -- world").every(token => token.punctuation || token.phones.length));
});

test('unfamiliar words use deterministic English spelling rules', () => {
    assert.deepEqual(phones('flomble'), ['F', 'L', 'AA1', 'M', 'B', 'AH0', 'L']);
    assert.deepEqual(tokenize('flomble'), tokenize('flomble'));
    assert.equal(tokenize('flomble')[0].approximate, true);
    assert.deepEqual(phones('phlomble'), phones('flomble'));
    assert.deepEqual(phones('shib'), ['SH', 'IH1', 'B']);
    assert.deepEqual(phones('sheeb'), ['SH', 'IY1', 'B']);
    assert.deepEqual(phones('chake'), ['CH', 'EY1', 'K']);
    assert.deepEqual(phones('knabe'), phones('nabe'));
});

test('fallback never emits invalid phones for unfamiliar words', () => {
    const inventory = new Set('AA AE AH AO AW AY B CH D DH EH ER EY F G HH IH IY JH K L M N NG OW OY P R S SH T TH UH UW V W Y Z ZH'.split(' '));
    const tokens = tokenize('flomble qraxth squozzle wrindle blook splaigh zhoub dhrell zwurx');
    assert.equal(tokens.length, 9);
    for (const token of tokens) {
        assert.ok(token.phones.length > 0, token.word);
        for (const {phone, stress} of token.phones) {
            assert.ok(inventory.has(phone), `${token.word}: ${phone}`);
            assert.ok(stress === null || [0, 1, 2].includes(stress));
        }
    }
});
