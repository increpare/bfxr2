// Sample buffers and mutation definitions have separate bounded LRU budgets.
class LibraryLRU {
    constructor(budget, limit = Infinity) {
        this.budget = budget;
        this.limit = limit;
        this.bytes = 0;
        this.entries = new Map();
    }

    get(key) {
        const entry = this.entries.get(key);
        if (!entry) return undefined;
        this.entries.delete(key);
        this.entries.set(key, entry);
        return entry.value;
    }

    set(key, value, bytes) {
        const previous = this.entries.get(key);
        if (previous) { this.bytes -= previous.bytes; this.entries.delete(key); }
        if (bytes > this.budget) return value;
        while (this.bytes + bytes > this.budget || this.entries.size >= this.limit) {
            const oldest = this.entries.keys().next().value;
            this.bytes -= this.entries.get(oldest).bytes;
            this.entries.delete(oldest);
        }
        this.entries.set(key, {value, bytes});
        this.bytes += bytes;
        return value;
    }

    clear() { this.entries.clear(); this.bytes = 0; }
}

const LibraryCache = {
    samples: new LibraryLRU(32 * 1024 * 1024),
    pools: new LibraryLRU(4 * 1024 * 1024, 256),
    generation: 0,

    stable(value) {
        if (!value || typeof value !== 'object') return JSON.stringify(value);
        if (Array.isArray(value)) return '[' + value.map(v => this.stable(v)).join(',') + ']';
        return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + this.stable(value[key])).join(',') + '}';
    },

    key(sound) {
        return this.stable({synth: sound.synth_type, params: sound.params, renderSeed: sound.renderSeed});
    },

    remember(key, entry) {
        // AudioBuffer and PCM each own a sample allocation; account for both.
        return this.samples.set(key, entry, entry.pcm.byteLength * (entry.buffer ? 2 : 1) + key.length * 2);
    },

    sound(sound) {
        const key = this.key(sound);
        return this.samples.get(key) || this.remember(key, {pcm: LibrarySounds.render(sound), buffer: null});
    },

    pool(sound, amount, count) {
        if (!Number.isFinite(amount) || amount < 0 || amount > 1) {
            throw new RangeError('Mutation amount must be between 0 and 1');
        }
        if (!Number.isInteger(count) || count < 1 || count > 256) {
            throw new RangeError('Mutation count must be an integer between 1 and 256');
        }
        const key = this.key(sound) + ':' + amount + ':' + count;
        let pool = this.pools.get(key);
        if (!pool) {
            pool = {key, original: sound, amount, count, sounds: [], next: 0};
            this.rememberPool(pool);
        }
        return pool;
    },

    rememberPool(pool) {
        const bytes = (pool.key.length + JSON.stringify(pool.original).length +
            JSON.stringify(pool.sounds).length) * 2;
        this.pools.set(pool.key, pool, bytes);
    },

    variation(pool, index) {
        if (!pool.sounds[index]) {
            pool.sounds[index] = LibrarySounds.mutate(pool.original, pool.amount,
                LibrarySounds.seed(pool.key + ':' + index));
            this.rememberPool(pool);
        }
        return pool.sounds[index];
    },

    mutated(sound, amount, count) {
        const pool = this.pool(sound, amount, count);
        const index = pool.next < count ? pool.next++ : Math.floor(global.Math.random() * count);
        return this.variation(pool, index);
    },

    yield() { return new Promise(resolve => global.setTimeout(resolve, 0)); },

    async warm(sound) {
        const generation = this.generation;
        await this.yield();
        if (generation === this.generation) this.sound(sound);
    },

    async warmMutations(sound, amount, count) {
        const pool = this.pool(sound, amount, count), generation = this.generation;
        for (let index = 0; index < count; index++) {
            await this.yield();
            if (generation !== this.generation) return;
            this.sound(this.variation(pool, index));
        }
        pool.next = count;
    },

    clear() { this.generation++; this.samples.clear(); this.pools.clear(); }
};
