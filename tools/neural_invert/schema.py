"""Global control codecs, including categorical and transition controls."""
from copy import deepcopy
import numpy as np


class ControlSchema:
    def __init__(self, spec):
        self.spec = deepcopy(spec)
        self.continuous, self.categorical, self.fixed_text = [], [], []
        self.fixed_randomness = []
        for p in spec['params']:
            name, kind = p['name'], p['type']
            if name == 'masterVolume':
                continue
            if name in ('seed', 'instrumentSeed'):
                self.fixed_randomness.append(name)
                continue
            if kind == 'TEXT':
                self.fixed_text.append(name)
            elif kind == 'BUTTONSELECT':
                self.categorical.append({'name': name, 'path': [name], 'values': p['values']})
            elif kind == 'KNOB_TRANSITION':
                for end in ('start', 'end'):
                    self.continuous.append({'name': name+'.'+end, 'path': [name, end], 'min': p['min'], 'max': p['max']})
                self.categorical.append({'name': name+'.curve', 'path': [name, 'curve'], 'values': p['values']})
            elif kind == 'RANGE':
                self.continuous.append({'name': name, 'path': [name], 'min': p['min'], 'max': p['max']})
            else:
                raise ValueError('Unsupported control type: '+kind)

    @staticmethod
    def _read(params, path):
        value = params
        for part in path:
            value = value[part]
        return value

    @staticmethod
    def _write(params, path, value):
        node = params
        for part in path[:-1]:
            node = node.setdefault(part, {})
        node[path[-1]] = value

    def encode(self, params):
        merged = deepcopy(self.spec['defaults']); merged.update(deepcopy(params))
        numeric = [(self._read(merged, c['path'])-c['min'])/max(c['max']-c['min'], 1e-12) for c in self.continuous]
        categorical = [c['values'].index(self._read(merged, c['path'])) for c in self.categorical]
        return np.clip(numeric, 0, 1).astype(np.float32), np.array(categorical, dtype=np.int64)

    def decode(self, unit, categorical, anchor=None):
        if len(unit) != len(self.continuous) or len(categorical) != len(self.categorical):
            raise ValueError('Control vector dimensions do not match schema')
        if not np.isfinite(unit).all():
            raise ValueError('Nonfinite continuous predictions')
        params = deepcopy(self.spec['defaults'])
        if anchor is not None:
            params.update(deepcopy(anchor))
        for c, value in zip(self.continuous, unit):
            self._write(params, c['path'], float(c['min'] + np.clip(value, 0, 1)*(c['max']-c['min'])))
        for c, label in zip(self.categorical, categorical):
            label = int(label)
            if not 0 <= label < len(c['values']):
                raise ValueError('Categorical prediction outside schema')
            self._write(params, c['path'], c['values'][label])
        params['masterVolume'] = .5
        return params

    def mutate(self, params, rng, mode):
        """Fresh global draws; sparse mutations preserve most original controls."""
        unit, cat = self.encode(params)
        if mode == 'sparse':
            changed = rng.choice(len(unit), size=max(1, len(unit)//6), replace=False)
        elif mode == 'broad':
            changed = rng.choice(len(unit), size=max(1, len(unit)//2), replace=False)
        else:
            return deepcopy(params)
        unit[changed] = rng.uniform(0, 1, len(changed))
        for i, control in enumerate(self.categorical):
            if rng.random() < (.15 if mode == 'sparse' else .5):
                cat[i] = rng.integers(len(control['values']))
        return self.decode(unit, cat, params)
