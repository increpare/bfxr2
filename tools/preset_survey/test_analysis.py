import unittest
import numpy as np
from analyze import extract_features, cluster, normalize, silhouette, diverse_representatives
from measure_curated import wobble
from runtime_provenance import runtime_fingerprint,require_current_runtime

class AudioFeaturesTest(unittest.TestCase):
    def test_features_measure_brightness_pitch_direction_and_duration(self):
        rate=44100
        t=np.arange(rate)/rate
        low=np.sin(2*np.pi*150*t)*np.minimum(1,t/0.01)*np.minimum(1,(1-t)/0.05)
        high=np.sin(2*np.pi*2200*t)*np.minimum(1,t/0.01)*np.minimum(1,(1-t)/0.05)
        rise=np.sin(2*np.pi*(150*t+800*t*t/2))
        a=extract_features(low,rate);b=extract_features(high,rate);c=extract_features(rise,rate)
        self.assertGreater(b['pitch_hz'],a['pitch_hz']*8)
        self.assertGreater(b['centroid_hz'],a['centroid_hz']*8)
        self.assertGreater(c['pitch_slope_octaves'],1)
        self.assertTrue(all(np.isfinite(v) for v in a.values()))
    def test_noise_has_less_tonal_concentration_than_a_whistle(self):
        t=np.arange(22050)/44100
        sine=extract_features(np.sin(2*np.pi*600*t),44100)
        noise=extract_features(np.random.default_rng(1).normal(size=len(t)),44100)
        self.assertGreater(sine['tonal_concentration'],noise['tonal_concentration']*4)
    def test_clustering_is_repeatable_and_recovers_separated_groups(self):
        random=np.random.default_rng(1)
        x=np.r_[random.normal(-3,.2,(20,3)),random.normal(3,.2,(20,3))]
        a,c=cluster(x,2,seed=9);b,d=cluster(x,2,seed=9)
        np.testing.assert_array_equal(a,b)
        self.assertEqual(len(set(a[:20])),1);self.assertEqual(len(set(a[20:])),1)
        self.assertNotEqual(a[0],a[-1]);self.assertGreater(silhouette(x,a),.8)
    def test_representative_selection_fills_its_limit_without_duplicates(self):
        x=np.random.default_rng(8).normal(size=(40,5))
        selected=diverse_representatives(x,np.arange(40),x.mean(axis=0),limit=24)
        self.assertEqual(len(selected),24)
        self.assertEqual(len(set(selected)),24)
    def test_wobble_measurement_detects_sustained_vibrato(self):
        rate=44100;t=np.arange(rate)/rate
        frequency=400*2**(.11*np.sin(2*np.pi*8*t))
        pcm=np.sin(2*np.pi*np.cumsum(frequency)/rate)
        result=wobble(pcm,rate)
        self.assertAlmostEqual(result['wobble_hz'],8,delta=1)
        self.assertGreater(result['wobble_rms_octaves'],.035)
        plain=wobble(np.sin(2*np.pi*400*t),rate)
        self.assertLess(plain['wobble_rms_octaves'],.005)
    def test_stale_sampler_renderer_or_bank_invalidates_validation(self):
        current=runtime_fingerprint()
        require_current_runtime({'runtime_sha256':current})
        for source in ['js/synths/PresetFamily.js','js/audio/Transfxr_DSP.js','js/synths/TransfxrPresets.js']:
            stale={**current,source:'outdated'}
            with self.assertRaisesRegex(ValueError,'sources have changed'):
                require_current_runtime({'runtime_sha256':stale})
        with self.assertRaises(ValueError):require_current_runtime({})

if __name__=='__main__':unittest.main()
