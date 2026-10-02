class Glitchr extends PresetSynth {
    name="Glitchr";
    tooltip="Damaged buffers, broken data and digital disintegration.";
    static DSP=Glitchr_DSP;
    param_info=[...PresetSynth.common_params,
        ["Duration", "Seconds.", "duration", 0.7, 0.08, 4],
        ["Pitch", "Pitch.", "pitch", 0.5, 0, 1],
        ["Fragment", "Fragment.", "fragment", 0.3, 0, 1],
        ["Repeat", "Repeat.", "repeat", 0.4, 0, 1],
        ["Chaos", "Chaos.", "chaos", 0.5, 0, 1],
        ["Dropout", "Dropout.", "dropout", 0.2, 0, 1],
        ["Crush", "Crush.", "crush", 0.3, 0, 1],
        ["Sample Hold", "Sample Hold.", "rate", 0.3, 0, 1]];
    recipes=[
    {
        "name": "Save Corruption",
        "id": "save_corruption",
        "tip": "Generate another save corruption.",
        "values": {
            "duration": [
                0.25,
                0.65
            ],
            "pitch": [
                0.51,
                0.69
            ],
            "fragment": [
                0.06,
                0.24
            ],
            "repeat": [
                0.7100000000000001,
                0.89
            ],
            "chaos": [
                0.31000000000000005,
                0.49
            ],
            "dropout": [
                0.06,
                0.24
            ],
            "crush": [
                0.41000000000000003,
                0.59
            ],
            "rate": [
                0.11000000000000001,
                0.29000000000000004
            ]
        }
    },
    {
        "name": "Teleport Error",
        "id": "teleport_error",
        "tip": "Generate another teleport error.",
        "values": {
            "duration": [
                0.4,
                1.1
            ],
            "pitch": [
                0.31000000000000005,
                0.49
            ],
            "fragment": [
                0.16,
                0.33999999999999997
            ],
            "repeat": [
                0.41000000000000003,
                0.59
            ],
            "chaos": [
                0.7100000000000001,
                0.89
            ],
            "dropout": [
                0.21,
                0.39
            ],
            "crush": [
                0.26,
                0.43999999999999995
            ],
            "rate": [
                0.06,
                0.24
            ]
        }
    },
    {
        "name": "Bit Rot",
        "id": "bit_rot",
        "tip": "Generate another bit rot.",
        "values": {
            "duration": [
                0.7,
                1.6
            ],
            "pitch": [
                0.21,
                0.39
            ],
            "fragment": [
                0.36,
                0.54
            ],
            "repeat": [
                0.31000000000000005,
                0.49
            ],
            "chaos": [
                0.21,
                0.39
            ],
            "dropout": [
                0.4600000000000001,
                0.64
            ],
            "crush": [
                0.76,
                0.94
            ],
            "rate": [
                0.7100000000000001,
                0.89
            ]
        }
    },
    {
        "name": "Buffer Skip",
        "id": "buffer_skip",
        "tip": "Generate another buffer skip.",
        "values": {
            "duration": [
                0.3,
                0.8
            ],
            "pitch": [
                0.56,
                0.74
            ],
            "fragment": [
                0.06,
                0.24
            ],
            "repeat": [
                0.81,
                0.99
            ],
            "chaos": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "dropout": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "crush": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "rate": [
                0.16,
                0.33999999999999997
            ]
        }
    },
    {
        "name": "Corrupt Pickup",
        "id": "corrupt_pickup",
        "tip": "Generate another corrupt pickup.",
        "values": {
            "duration": [
                0.12,
                0.4
            ],
            "pitch": [
                0.7100000000000001,
                0.89
            ],
            "fragment": [
                0.010000000000000009,
                0.19
            ],
            "repeat": [
                0.31000000000000005,
                0.49
            ],
            "chaos": [
                0.7100000000000001,
                0.89
            ],
            "dropout": [
                0.010000000000000009,
                0.19
            ],
            "crush": [
                0.51,
                0.69
            ],
            "rate": [
                0.21,
                0.39
            ]
        }
    },
    {
        "name": "Broken Terminal",
        "id": "broken_terminal",
        "tip": "Generate another broken terminal.",
        "values": {
            "duration": [
                0.6,
                1.8
            ],
            "pitch": [
                0.36,
                0.54
            ],
            "fragment": [
                0.26,
                0.43999999999999995
            ],
            "repeat": [
                0.61,
                0.7899999999999999
            ],
            "chaos": [
                0.51,
                0.69
            ],
            "dropout": [
                0.41000000000000003,
                0.59
            ],
            "crush": [
                0.56,
                0.74
            ],
            "rate": [
                0.51,
                0.69
            ]
        }
    },
    {
        "name": "Rewind Burst",
        "id": "rewind_burst",
        "tip": "Generate another rewind burst.",
        "values": {
            "duration": [
                0.3,
                0.85
            ],
            "pitch": [
                0.4600000000000001,
                0.64
            ],
            "fragment": [
                0,
                0.16999999999999998
            ],
            "repeat": [
                0.56,
                0.74
            ],
            "chaos": [
                0.81,
                0.99
            ],
            "dropout": [
                0.010000000000000009,
                0.19
            ],
            "crush": [
                0.26,
                0.43999999999999995
            ],
            "rate": [
                0.26,
                0.43999999999999995
            ]
        }
    },
    {
        "name": "Digital Death",
        "id": "digital_death",
        "tip": "Generate another digital death.",
        "values": {
            "duration": [
                0.7,
                1.5
            ],
            "pitch": [
                0.16,
                0.33999999999999997
            ],
            "fragment": [
                0.4600000000000001,
                0.64
            ],
            "repeat": [
                0.21,
                0.39
            ],
            "chaos": [
                0.91,
                1
            ],
            "dropout": [
                0.4600000000000001,
                0.64
            ],
            "crush": [
                0.76,
                0.94
            ],
            "rate": [
                0.76,
                0.94
            ]
        }
    }
];
    constructor(){super();this.initialize_presets();}
}
