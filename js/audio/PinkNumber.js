class PinkNumber {
    constructor() {
        this.max_key = 0x1f; // Five bits set
        this.range = 128;
        this.key = 0;
        this.white_values = new Int32Array(5);
        for (var i = 0; i < 5; i++){
            this.white_values[i] = Math.random() * (this.range / 5)
        }
    }

    //returns number between -1 and 1		
    GetNextValue() {
        var last_key = this.key;

        this.key++;
        if (this.key > this.max_key)
            this.key = 0;
        // Exclusive-Or previous value with current value. This gives
        // a list of bits that have changed.
        var diff = last_key ^ this.key;
        var sum = 0;
        for (var i = 0; i < 5; i++) {
            // If bit changed get new random number for corresponding
            // white_value
            if (diff & (1 << i))
                this.white_values[i] = Math.random() * (this.range / 5);
            sum += this.white_values[i];
        }
        return sum / 64.0 - 1.0;
    }
}; 