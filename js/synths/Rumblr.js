class Rumblr extends PresetSynth {
    name="Rumblr";
    tooltip="Structural pressure, giant spaces and approaching trouble.";
    static DSP=Rumblr_DSP;
    param_info=[...PresetSynth.common_params,
        ["Duration", "Seconds.", "duration", 2, 0.2, 5],
        ["Size", "Size.", "size", 0.6, 0, 1],
        ["Weight", "Weight.", "weight", 0.6, 0, 1],
        ["Roughness", "Roughness.", "roughness", 0.4, 0, 1],
        ["Tremor", "Tremor.", "tremor", 0.3, 0, 1],
        ["Dust", "Dust.", "dust", 0.15, 0, 1],
        ["Attack", "Attack.", "attack", 0.3, 0, 1],
        ["Sweep", "Sweep.", "sweep", 0, -1, 1]];
    recipes=[
    {
        "name": "Earthquake",
        "id": "earthquake",
        "tip": "Generate another earthquake.",
        "values": {
            "duration": [
                1.5,
                3.5
            ],
            "size": [
                0.7100000000000001,
                0.89
            ],
            "weight": [
                0.76,
                0.94
            ],
            "roughness": [
                0.61,
                0.7899999999999999
            ],
            "tremor": [
                0.56,
                0.74
            ],
            "dust": [
                0.51,
                0.69
            ],
            "attack": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "sweep": [
                -0.039999999999999994,
                0.14
            ]
        }
    },
    {
        "name": "Boss Approach",
        "id": "boss_approach",
        "tip": "Generate another boss approach.",
        "values": {
            "duration": [
                2,
                4
            ],
            "size": [
                0.76,
                0.94
            ],
            "weight": [
                0.81,
                0.99
            ],
            "roughness": [
                0.26,
                0.43999999999999995
            ],
            "tremor": [
                0.31000000000000005,
                0.49
            ],
            "dust": [
                0.010000000000000009,
                0.19
            ],
            "attack": [
                0.66,
                0.84
            ],
            "sweep": [
                0.06,
                0.24
            ]
        }
    },
    {
        "name": "Stone Door",
        "id": "stone_door",
        "tip": "Generate another stone door.",
        "values": {
            "duration": [
                0.8,
                2
            ],
            "size": [
                0.4600000000000001,
                0.64
            ],
            "weight": [
                0.66,
                0.84
            ],
            "roughness": [
                0.61,
                0.7899999999999999
            ],
            "tremor": [
                0.4600000000000001,
                0.64
            ],
            "dust": [
                0.7100000000000001,
                0.89
            ],
            "attack": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "sweep": [
                -0.29000000000000004,
                -0.11000000000000001
            ]
        }
    },
    {
        "name": "Engine Room",
        "id": "engine_room",
        "tip": "Generate another engine room.",
        "values": {
            "duration": [
                1.5,
                3.5
            ],
            "size": [
                0.36,
                0.54
            ],
            "weight": [
                0.56,
                0.74
            ],
            "roughness": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "tremor": [
                0.7100000000000001,
                0.89
            ],
            "dust": [
                0,
                0.14
            ],
            "attack": [
                0.31000000000000005,
                0.49
            ],
            "sweep": [
                -0.06999999999999999,
                0.11
            ]
        }
    },
    {
        "name": "Space Hull",
        "id": "space_hull",
        "tip": "Generate another space hull.",
        "values": {
            "duration": [
                1.6,
                3.6
            ],
            "size": [
                0.81,
                0.99
            ],
            "weight": [
                0.7100000000000001,
                0.89
            ],
            "roughness": [
                0.21,
                0.39
            ],
            "tremor": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "dust": [
                0.11000000000000001,
                0.29000000000000004
            ],
            "attack": [
                0.36,
                0.54
            ],
            "sweep": [
                -0.33999999999999997,
                -0.16
            ]
        }
    },
    {
        "name": "Landslide",
        "id": "landslide",
        "tip": "Generate another landslide.",
        "values": {
            "duration": [
                1.2,
                3
            ],
            "size": [
                0.56,
                0.74
            ],
            "weight": [
                0.76,
                0.94
            ],
            "roughness": [
                0.81,
                0.99
            ],
            "tremor": [
                0.36,
                0.54
            ],
            "dust": [
                0.81,
                0.99
            ],
            "attack": [
                0.21,
                0.39
            ],
            "sweep": [
                0.16,
                0.33999999999999997
            ]
        }
    },
    {
        "name": "Deep Pressure",
        "id": "deep_pressure",
        "tip": "Generate another deep pressure.",
        "values": {
            "duration": [
                2,
                4.5
            ],
            "size": [
                0.86,
                1
            ],
            "weight": [
                0.76,
                0.94
            ],
            "roughness": [
                0.06,
                0.24
            ],
            "tremor": [
                0.010000000000000009,
                0.19
            ],
            "dust": [
                0,
                0.12
            ],
            "attack": [
                0.76,
                0.94
            ],
            "sweep": [
                -0.24,
                -0.06
            ]
        }
    },
    {
        "name": "Volcano",
        "id": "volcano",
        "tip": "Generate another volcano.",
        "values": {
            "duration": [
                1.5,
                3.5
            ],
            "size": [
                0.7100000000000001,
                0.89
            ],
            "weight": [
                0.86,
                1
            ],
            "roughness": [
                0.76,
                0.94
            ],
            "tremor": [
                0.61,
                0.7899999999999999
            ],
            "dust": [
                0.56,
                0.74
            ],
            "attack": [
                0.31000000000000005,
                0.49
            ],
            "sweep": [
                0.010000000000000009,
                0.19
            ]
        }
    }
];
    constructor(){super();this.initialize_presets();}
}
