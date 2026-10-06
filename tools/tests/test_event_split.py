import unittest
import numpy as np
from multisynth.event_split import split_events

class EventSplitTests(unittest.TestCase):
    def test_pulses_and_gain(self):
        rate=44100
        t=np.arange(rate//2)/rate
        wave=np.sin(2*np.pi*600*t)*((t<.12)|((t>.27)&(t<.4)))
        a=split_events(wave); b=split_events(wave*.03)
        self.assertEqual(a,b)
        self.assertTrue(any(abs(i/rate-.27)<.035 for i in a[1:-1]),a)
        self.assertEqual(a[0],0);self.assertEqual(a[-1],len(wave))
        self.assertLessEqual(len(a),4)

    def test_note_change_not_stationary_tone(self):
        rate=44100;t=np.arange(rate//2)/rate
        tone=np.sin(2*np.pi*600*t)
        self.assertEqual(split_events(tone),[0,len(tone)])
        phase=2*np.pi*np.cumsum(np.where(t<.25,600,1100))/rate
        cuts=split_events(np.sin(phase))
        self.assertTrue(any(abs(i/rate-.25)<.035 for i in cuts[1:-1]),cuts)

    def test_short_silent_and_invalid(self):
        self.assertEqual(split_events(np.zeros(10)),[0,10])
        self.assertEqual(split_events(np.ones(1000)),[0,1000])
        for x in ([],[[1]], [np.nan]):
            with self.assertRaises(ValueError):split_events(x)

if __name__=='__main__':unittest.main()
