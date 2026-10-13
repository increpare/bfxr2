import json
from pathlib import Path
import tempfile
import unittest

from .enrichment import apply_proposal, duplicate_proposals, load_proposals


class EnrichmentTests(unittest.TestCase):
    taxonomy = {'ANMLDog': {'category': 'ANIMALS', 'subcategory': 'DOG'},
                'ANMLCat': {'category': 'ANIMALS', 'subcategory': 'CAT'}}

    def row(self, **values):
        return dict(id='a', path='a.wav', sha256='abc', pcm_hash='8000:1:abc',
                    category=None, catid=None, extra=None, description='a', reviewed=False) | values

    def proposal(self, **values):
        return dict(description_id='a', path='a.wav', sha256='abc', category='ANIMALS',
                    catid='ANMLDog', method='audio-model', confidence='low', reason='Model suggestion') | values

    def test_changed_bytes_or_path_never_receive_stale_prediction(self):
        for change in [{'sha256': 'changed'}, {'path': 'b.wav'}]:
            row = self.row(**change)
            apply_proposal(row, {'a': self.proposal()}, self.taxonomy)
            self.assertIsNone(row['category'])

    def test_metadata_wins_and_model_is_explicitly_unverified(self):
        row = self.row(category='ANIMALS', catid='ANMLCat')
        apply_proposal(row, {'a': self.proposal()}, self.taxonomy)
        self.assertEqual(row['catid'], 'ANMLCat')
        row = self.row()
        apply_proposal(row, {'a': self.proposal()}, self.taxonomy)
        self.assertEqual(row['classification_status'], 'audio proposal')
        self.assertFalse(row['extra']['training_eligible'])
        self.assertFalse(row['extra']['audio_verified'])

    def test_invalid_proposal_warns_without_breaking_catalogue(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            (root / '_catalogue').mkdir()
            (root / '_catalogue' / 'automated-proposals.jsonl').write_text(json.dumps(self.proposal(catid='INVALID')), encoding='utf8')
            with self.assertWarns(RuntimeWarning):
                self.assertEqual(load_proposals(root, self.taxonomy), {})

    def test_excerpt_match_is_distinct_from_model_and_full_recording_copy(self):
        row = self.row()
        apply_proposal(row, {'a': self.proposal(method='exact-excerpt')}, self.taxonomy)
        self.assertEqual(row['classification_status'], 'excerpt proposal')
        self.assertEqual(row['classification_method'], 'exact-excerpt')
        self.assertFalse(row['extra']['training_eligible'])
        self.assertFalse(row['extra']['audio_verified'])

    def test_duplicate_transfer_requires_agreement_and_single_description(self):
        unknown = self.row()
        donor = self.row(id='b', path='b.wav', category='ANIMALS', catid='ANMLDog')
        self.assertEqual(duplicate_proposals([unknown, donor])[0]['catid'], 'ANMLDog')
        conflict = self.row(id='c', path='c.wav', category='BIRDS', catid='BIRDMisc')
        self.assertEqual(duplicate_proposals([unknown, donor, conflict]), [])
        second_description = donor | {'id': 'b2', 'catid': 'ANMLCat'}
        self.assertEqual(duplicate_proposals([unknown, donor, second_description]), [])

    def test_duplicate_model_predictions_do_not_propagate_as_metadata(self):
        donor = self.row(id='b', path='b.wav', category='ANIMALS', catid='ANMLDog', classification_method='audio-model')
        self.assertEqual(duplicate_proposals([self.row(), donor]), [])

    def test_inconsistent_leaves_only_transfer_agreed_parent(self):
        donors = [self.row(id='b', path='b.wav', category='ANIMALS', catid='ANMLDog'),
                  self.row(id='c', path='c.wav', category='ANIMALS', catid='ANMLCat')]
        proposal = duplicate_proposals([self.row()] + donors)[0]
        self.assertEqual(proposal['category'], 'ANIMALS')
        self.assertIsNone(proposal['catid'])

    def test_raw_asset_group_is_refinable_but_not_a_semantic_donor(self):
        raw = self.row(category='DESIGNED', catid='DSGNSrce', classification_status='source element')
        unknown = self.row(id='c', path='c.wav')
        self.assertEqual(duplicate_proposals([raw, unknown]), [])
        donor = self.row(id='b', path='b.wav', category='ANIMALS', catid='ANMLDog')
        proposals = {x['description_id']: x for x in duplicate_proposals([raw, unknown, donor])}
        self.assertEqual(set(proposals), {'a', 'c'})
        apply_proposal(raw, proposals, self.taxonomy)
        self.assertEqual(raw['catid'], 'ANMLDog')
        self.assertEqual(raw['classification_status'], 'duplicate proposal')

    def test_context_group_yields_to_audio_but_cannot_label_other_recordings(self):
        context = self.row(category='GAMES', catid='GAMEVideo', classification_status='context only')
        self.assertEqual(duplicate_proposals([context, self.row(id='b', path='b.wav')]), [])
        apply_proposal(context, {'a': self.proposal()}, self.taxonomy)
        self.assertEqual(context['catid'], 'ANMLDog')
        self.assertEqual(context['classification_status'], 'audio proposal')

    def test_waveform_traits_require_matching_bytes_and_never_assign_categories(self):
        from .traits import apply_traits
        traits = {('a.wav', 'abc'): {'facets': ['tonal_dominant']}}
        row = self.row()
        apply_traits(row, traits)
        self.assertEqual(row['acoustic_traits'], ['tonal_dominant'])
        self.assertIsNone(row['category'])
        changed = self.row(sha256='changed')
        apply_traits(changed, traits)
        self.assertEqual(changed['acoustic_traits'], [])

    def test_tentative_guess_is_visibly_distinct_and_not_a_duplicate_donor(self):
        row = self.row()
        apply_proposal(row, {'a': self.proposal(decision_strength='tentative')}, self.taxonomy)
        self.assertEqual(row['classification_status'], 'tentative proposal')
        self.assertFalse(row['extra']['training_eligible'])
        self.assertEqual(duplicate_proposals([row, self.row(id='b', path='b.wav')]), [])


if __name__ == '__main__':
    unittest.main()
