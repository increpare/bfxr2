import unittest
import numpy as np
import torch
from neural_invert.event_timing import features, targets, decode, TimingNet, match_events

class TimingTests(unittest.TestCase):
    def test_features_gain_and_late_evidence(self):
        w=np.zeros(44100);t=np.arange(4410)/44100;w[30000:34410]=np.sin(2*np.pi*700*t)
        a=features(w);b=features(w*.1)
        self.assertEqual(a.shape,(25,256));np.testing.assert_allclose(a,b,atol=1e-5)
        self.assertGreater(float(a[-1,115:140].max()),float(a[-1,:90].max()))
        for bad in ([],[[1]],[np.nan],np.zeros(70000)):
            with self.assertRaises(ValueError):features(bad)

    def test_labels_decode_and_matching(self):
        y=targets([0,.2,.5]);p=np.zeros(256)
        p[round(.2*44100/256)]=.9;p[round(.5*44100/256)]=.8
        cuts=decode(p,44100)
        self.assertEqual(len(cuts),4)
        self.assertEqual(cuts[0],0);self.assertEqual(cuts[-1],44100)
        self.assertLess(abs(cuts[1]/44100-.2),.006)
        self.assertEqual(match_events([.2,.5],[.21,.51]),{'tp':2,'fp':0,'fn':0})
        self.assertEqual(match_events([.2],[.19,.21]),{'tp':1,'fp':1,'fn':0})
        self.assertEqual(match_events([],[]),{'tp':0,'fp':0,'fn':0})
        self.assertEqual(float(y[0]),0)
        position=.2*44100/256
        self.assertAlmostEqual(float(y[round(position)]),float(np.exp(-.5*(round(position)-position)**2)),places=6)
        self.assertEqual(decode(np.zeros(256),1000),[0,1000])

    def test_finite_gradients_and_reload(self):
        torch.manual_seed(7);model=TimingNet();x=torch.randn(2,25,256)
        y=model(x);self.assertEqual(tuple(y.shape),(2,256))
        y.square().mean().backward();self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters()))
        other=TimingNet();other.load_state_dict(model.state_dict());torch.testing.assert_close(y,other(x))

if __name__=='__main__':unittest.main()
