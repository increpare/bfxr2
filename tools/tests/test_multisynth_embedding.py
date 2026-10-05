import unittest
from multisynth.embedding import family_groups, validate_wave
import numpy as np

class EmbeddingTests(unittest.TestCase):
    def test_transformed_ancestry_and_pcm_are_connected(self):
        refs = [
            {'pcm':'a','source':{'name':'Sweep','sourceTarget':{'id':'base','parameterHash':'p'}}},
            {'pcm':'b','source':{'name':'Filtered','sourceTarget':{'baseId':'base','sourceTarget':{'parameterHash':'p'}}}},
            {'pcm':'b','source':{'name':'Renamed','sha256':'x'}},
            {'pcm':'c','source':{'name':'elsewhere','sha256':'x'}},
            {'pcm':'d','source':{'name':'other.wav','sha256':'y'}}]
        groups=family_groups(refs)
        self.assertEqual(len(set(groups[:4])),1)
        self.assertNotEqual(groups[0],groups[4])
    def test_related_real_takes_group_conservatively(self):
        refs=[{'pcm':str(i),'source':{'name':n}} for i,n in enumerate(['tag/Cloth03.wav','other/cloth04.ogg','tag/Laser.wav'])]
        g=family_groups(refs)
        self.assertEqual(g[0],g[1]);self.assertNotEqual(g[0],g[2])
    def test_invalid_input_is_not_silently_repaired(self):
        for x in [np.zeros(0),np.array([np.nan]),np.zeros(441001),np.zeros((2,2))]:
            with self.assertRaises(ValueError):validate_wave(x)
        x=np.arange(20,dtype=np.float32)/40
        self.assertTrue(np.array_equal(validate_wave(x),x))

class FittingTests(unittest.TestCase):
    def test_baseline_fit_parity(self):
        from multisynth.embedding import fit_components
        from multisynth.preference import fit,PRIOR
        x=np.random.default_rng(41).normal(size=(12,20))
        y=np.tile([1,-1],6);g=np.repeat(np.arange(6),2)
        w,s=fit_components(x,y,g,PRIOR)
        baseline=fit(x,y,g)
        np.testing.assert_allclose(w,baseline.weights,atol=1e-12)
        np.testing.assert_allclose(s,baseline.scales,atol=1e-12)
