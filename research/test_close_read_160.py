"""Negative regression checks for provenance, boundary and verification claims."""
import copy
import unittest
import build_close_read_160 as review


class ReviewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.sample, cls.index = review.build()

    def test_all_rows_are_five_domain_model_drafts(self):
        review.validate_records(self.records, self.sample, self.index)
        self.assertEqual(sum(r['default_retrieval_excluded'] for r in self.records), 3)
        self.assertEqual(sum(len(o['evidence']) > 1 for r in self.records
                             for f in r['fields'].values() for o in f['observations']), 14)

    def test_tampered_literal_rejected(self):
        rows = copy.deepcopy(self.records)
        rows[0]['fields']['symptoms']['observations'][0]['evidence'][0]['raw_quote'] += '偽'
        with self.assertRaisesRegex(ValueError, 'Literal evidence'):
            review.validate_records(rows, self.sample, self.index)

    def test_outside_case_span_rejected(self):
        rows = copy.deepcopy(self.records)
        e = rows[0]['fields']['symptoms']['observations'][0]['evidence'][0]
        e['source_end_char_exclusive'] = len(self.index[e['source_ref']]) + 1
        with self.assertRaisesRegex(ValueError, 'outside case'):
            review.validate_records(rows, self.sample, self.index)

    def test_unchecked_query_export_rejected(self):
        rows = copy.deepcopy(self.records)
        rows[0]['fields']['mechanism']['observations'][0]['initial_query_eligible'] = True
        with self.assertRaisesRegex(ValueError, 'query export'):
            review.validate_records(rows, self.sample, self.index)

    def test_invented_human_review_rejected(self):
        rows = copy.deepcopy(self.records)
        rows[0]['human_adjudication'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'verification claim'):
            review.validate_records(rows, self.sample, self.index)

    def test_pending_source_exclusion_cannot_be_dropped(self):
        rows = copy.deepcopy(self.records)
        r = next(r for r in rows if r['default_retrieval_excluded'])
        r['default_retrieval_excluded'] = False
        with self.assertRaisesRegex(ValueError, 'exclusion lost'):
            review.validate_records(rows, self.sample, self.index)

    def test_join_retains_unicode_and_punctuation(self):
        case = {'case_id': 'synthetic', 'parts': ['甲\u3000乙', '丙，丁'],
                'segments': [{'source_ref':'A','start':1,'end':4},
                             {'source_ref':'B','start':0,'end':3}]}
        index = {'A':'前甲\u3000乙後','B':'丙，丁尾'}
        ev = review.evidence_for(case, '乙丙，', index)
        self.assertEqual([e['raw_quote'] for e in ev], ['乙','丙，'])
        with self.assertRaisesRegex(ValueError, 'not found'):
            review.evidence_for(case, '甲乙', index)

    def test_repeated_quote_requires_disambiguation(self):
        case = {'case_id':'synthetic','parts':['甲甲'],
                'segments':[{'source_ref':'A','start':0,'end':2}]}
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            review.evidence_for(case, '甲', {'A':'甲甲'})

    def test_wrong_source_blob_rejected(self):
        rows = copy.deepcopy(self.records)
        rows[0]['source_git_blob'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'provenance drift'):
            review.validate_records(rows, self.sample, self.index)

    def test_duplicate_domain_observation_rejected(self):
        rows = copy.deepcopy(self.records)
        obs = rows[0]['fields']['symptoms']['observations']
        obs.append(copy.deepcopy(obs[0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate observation'):
            review.validate_records(rows, self.sample, self.index)

    def test_snapshot_search_includes_overlapping_occurrences(self):
        from check_sample_snapshots import literal_locations
        self.assertEqual(literal_locations('甲甲甲', '甲甲'),
                         [{'start_char': 0, 'end_char_exclusive': 2},
                          {'start_char': 1, 'end_char_exclusive': 3}])
        with self.assertRaisesRegex(ValueError, 'Empty evidence'):
            literal_locations('甲', '')

    def test_snapshot_alignment_preserves_second_occurrence(self):
        from check_sample_snapshots import quote_alignment
        ev = {'raw_quote': '甲', 'source_start_char': 2, 'source_end_char_exclusive': 3}
        aligned = quote_alignment('甲乙甲', '甲乙甲', ev)
        self.assertEqual(aligned['snapshot_start_char'], 2)
        self.assertEqual(aligned['snapshot_occurrence_count'], 2)
        ambiguous = quote_alignment('甲丙甲', '甲乙甲', ev)
        self.assertNotIn('snapshot_start_char', ambiguous)
        self.assertEqual(len(ambiguous['snapshot_candidate_spans']), 2)
        self.assertIsNone(quote_alignment('乙', '甲乙甲', ev))
        with self.assertRaisesRegex(ValueError, 'lost evidence offset'):
            quote_alignment('甲乙甲', '甲乙甲', dict(ev, source_start_char=1))

    def test_second_pass_preserves_later_episode(self):
        by_id = {r['case_id']: r for r in self.records}
        row = by_id['XJ-BYCY-C-V5-L0521']
        for field in ('symptoms', 'mechanism'):
            self.assertEqual(row['fields'][field]['observations'][-1]['time_phase'],
                             'later_narrator_window')
        course = by_id['XJ-BYCY-C-V5-L0052']['fields']['course']['observations'][0]
        self.assertEqual(course['narrative_role'],
                         'after_earlier_treatment_before_narrator_assessment')

    def test_time_and_speaker_regressions(self):
        by_id = {r['case_id']:r for r in self.records}
        patient = by_id['XJ-NKZY-C-V2-P007-1']['fields']['mechanism']['observations'][0]
        self.assertEqual(patient['assertion_type'], 'patient_interpretation')
        post = by_id['XJ-LZWKFH-C-V2-P015-1']['fields']['mechanism']['observations']
        self.assertTrue(all(o['time_phase'] == 'later_narrator_window' for o in post))
        prior = by_id['XJ-KCLY-C-H3-P014-1']['fields']['prior_treatment']['observations']
        self.assertEqual(prior, [])


if __name__ == '__main__':
    unittest.main()
