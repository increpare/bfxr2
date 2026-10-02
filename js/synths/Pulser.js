class Pulser extends PresetSynth {
    name="Pulser";
    tooltip="Heartbeats, living machines and uneasy rhythms.";
    static DSP=Pulser_DSP;
    param_info=[...PresetSynth.common_params,
        ["Duration", "Seconds.", "duration", 1.5, 0.2, 5],
        ["Beats", "Beats.", "beats", 3, 1, 12],
        ["Pitch", "Pitch.", "pitch", 0.35, 0, 1],
        ["Size", "Size.", "size", 0.5, 0, 1],
        ["Second Beat", "Second Beat.", "secondary", 0.6, 0, 1],
        ["Separation", "Separation.", "separation", 0.35, 0, 1],
        ["Murmur", "Murmur.", "murmur", 0.1, 0, 1],
        ["Tension", "Tension.", "tension", 0.2, 0, 1],
        ["Irregularity", "Irregularity.", "irregular", 0.05, 0, 1]];
    recipes=[
    {
        "name": "Heartbeat",
        "id": "heartbeat",
        "tip": "Generate another heartbeat.",
        "values": {
            "duration": [
                1.2,
                2.4
            ],
            "beats": [
                2,
                4
            ],
            "pitch": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "size": [
                0.41000000000000003,
                0.59
            ],
            "secondary": [
                0.56,
                0.74
            ],
            "separation": [
                0.26,
                0.43999999999999995
            ],
            "murmur": [
                0.03,
                0.21
            ],
            "tension": [
                0.010000000000000009,
                0.19
            ],
            "irregular": [
                0,
                0.13
            ]
        }
    },
    {
        "name": "Panic",
        "id": "panic",
        "tip": "Generate another panic.",
        "values": {
            "duration": [
                0.8,
                1.5
            ],
            "beats": [
                4,
                7
            ],
            "pitch": [
                0.36,
                0.54
            ],
            "size": [
                0.21,
                0.39
            ],
            "secondary": [
                0.7100000000000001,
                0.89
            ],
            "separation": [
                0.06,
                0.24
            ],
            "murmur": [
                0.16,
                0.33999999999999997
            ],
            "tension": [
                0.51,
                0.69
            ],
            "irregular": [
                0.11000000000000001,
                0.29000000000000004
            ]
        }
    },
    {
        "name": "Giant Heart",
        "id": "giant_heart",
        "tip": "Generate another giant heart.",
        "values": {
            "duration": [
                2,
                4
            ],
            "beats": [
                2,
                4
            ],
            "pitch": [
                0,
                0.14
            ],
            "size": [
                0.81,
                0.99
            ],
            "secondary": [
                0.61,
                0.7899999999999999
            ],
            "separation": [
                0.4600000000000001,
                0.64
            ],
            "murmur": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "tension": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "irregular": [
                0,
                0.14
            ]
        }
    },
    {
        "name": "Android Core",
        "id": "android_core",
        "tip": "Generate another android core.",
        "values": {
            "duration": [
                0.7,
                1.6
            ],
            "beats": [
                3,
                6
            ],
            "pitch": [
                0.66,
                0.84
            ],
            "size": [
                0.16,
                0.33999999999999997
            ],
            "secondary": [
                0.41000000000000003,
                0.59
            ],
            "separation": [
                0.06,
                0.24
            ],
            "murmur": [
                0,
                0.12
            ],
            "tension": [
                0.7100000000000001,
                0.89
            ],
            "irregular": [
                0,
                0.11
            ]
        }
    },
    {
        "name": "Poison",
        "id": "poison",
        "tip": "Generate another poison.",
        "values": {
            "duration": [
                1,
                2.4
            ],
            "beats": [
                3,
                6
            ],
            "pitch": [
                0.21,
                0.39
            ],
            "size": [
                0.51,
                0.69
            ],
            "secondary": [
                0.31000000000000005,
                0.49
            ],
            "separation": [
                0.41000000000000003,
                0.59
            ],
            "murmur": [
                0.56,
                0.74
            ],
            "tension": [
                0.41000000000000003,
                0.59
            ],
            "irregular": [
                0.66,
                0.84
            ]
        }
    },
    {
        "name": "Underwater",
        "id": "underwater",
        "tip": "Generate another underwater.",
        "values": {
            "duration": [
                1.8,
                3.2
            ],
            "beats": [
                2,
                4
            ],
            "pitch": [
                0.010000000000000009,
                0.19
            ],
            "size": [
                0.66,
                0.84
            ],
            "secondary": [
                0.56,
                0.74
            ],
            "separation": [
                0.56,
                0.74
            ],
            "murmur": [
                0.36,
                0.54
            ],
            "tension": [
                0,
                0.16999999999999998
            ],
            "irregular": [
                0.03,
                0.21
            ]
        }
    },
    {
        "name": "Energy Core",
        "id": "energy_core",
        "tip": "Generate another energy core.",
        "values": {
            "duration": [
                0.8,
                2
            ],
            "beats": [
                3,
                6
            ],
            "pitch": [
                0.51,
                0.69
            ],
            "size": [
                0.4600000000000001,
                0.64
            ],
            "secondary": [
                0.76,
                0.94
            ],
            "separation": [
                0.26,
                0.43999999999999995
            ],
            "murmur": [
                0.06,
                0.24
            ],
            "tension": [
                0.76,
                0.94
            ],
            "irregular": [
                0,
                0.14
            ]
        }
    },
    {
        "name": "Last Life",
        "id": "last_life",
        "tip": "Generate another last life.",
        "values": {
            "duration": [
                1.5,
                3.1
            ],
            "beats": [
                2,
                4
            ],
            "pitch": [
                0.06,
                0.24
            ],
            "size": [
                0.7100000000000001,
                0.89
            ],
            "secondary": [
                0.21,
                0.39
            ],
            "separation": [
                0.56,
                0.74
            ],
            "murmur": [
                0.26,
                0.43999999999999995
            ],
            "tension": [
                0.26,
                0.43999999999999995
            ],
            "irregular": [
                0.76,
                0.94
            ]
        }
    }
];
    constructor(){super();this.initialize_presets();}
    set_param(name,value,checkLocked=false){super.set_param(name,value,checkLocked);if(name==='beats'&&!(checkLocked&&this.locked_param(name)))this.params.beats=Math.round(this.params.beats);}
}
