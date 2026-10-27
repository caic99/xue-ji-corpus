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


class ExtendedAndScanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_extended_kcly as extended
        import check_scan_spots as scan
        import json
        cls.extended=extended
        cls.rows,cls.cases,cls.index=extended.build()
        cls.scan=scan
        cls.scan_record=json.loads(scan.PATH.read_text())

    def test_empty_tongue_slot_is_not_explicit_absence(self):
        rows=copy.deepcopy(self.rows)
        row=next(r for r in rows if not r['fields']['tongue_features']['observations'])
        row['fields']['tongue_features']['missingness']='explicitly_absent'
        with self.assertRaisesRegex(ValueError,'unresolved, not absent'):
            self.extended.validate(rows,self.cases,self.index)

    def test_extended_observation_cannot_enable_query_export(self):
        rows=copy.deepcopy(self.rows)
        row=next(r for r in rows if r['fields']['pulse']['observations'])
        row['fields']['pulse']['observations'][0]['initial_query_eligible']=True
        with self.assertRaisesRegex(ValueError,'query or phase'):
            self.extended.validate(rows,self.cases,self.index)

    def test_recurrent_case_pulse_stages_remain_separate(self):
        row=next(r for r in self.rows if r['case_id']=='XJ-KCLY-C-H2-P004-1')
        obs=row['fields']['pulse']['observations']
        self.assertEqual([o['reading_joined_source_segments'] for o in obs],['脈數而有力','脈數而無力'])
        self.assertEqual([o['time_phase'] for o in obs],['initial_narrator_window','later_narrator_window'])

    def test_tongue_swelling_cannot_be_promoted_to_formal_exam(self):
        rows=copy.deepcopy(self.rows)
        row=next(r for r in rows if r['fields']['tongue_features']['observations'])
        row['fields']['tongue_features']['observations'][0]['interpretation_type']='formal_tongue_exam'
        with self.assertRaisesRegex(ValueError,'formal tongue-exam'):
            self.extended.validate(rows,self.cases,self.index)

    def test_scan_spot_cannot_claim_full_case_collation(self):
        rec=copy.deepcopy(self.scan_record)
        rec['full_case_print_collations']=3
        with self.assertRaisesRegex(ValueError,'adjudication claim'):
            self.scan.validate(rec,self.index)

    def test_scan_page_must_be_in_downloaded_pdf(self):
        rec=copy.deepcopy(self.scan_record)
        rec['spots'][0]['pdf_page']=49
        with self.assertRaisesRegex(ValueError,'page out of range'):
            self.scan.validate(rec,self.index)

    def test_scan_artifact_hash_rejects_unrelated_pdf(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'unrelated.pdf';path.write_bytes(b'%PDF-not-the-recorded-artifact')
            with self.assertRaisesRegex(ValueError,'differs from recorded'):
                self.scan.validate(self.scan_record,self.index,path)

    def test_scan_reference_does_not_leak_to_other_case_in_same_paragraph(self):
        spot=self.scan_record['spots'][0]
        ev=spot['working_evidence']
        other_case={'segments':[{'source_ref':spot['source_ref'],
                                 'start':0,'end':ev['source_start_char']}]}
        self.assertEqual(review.case_scan_refs(other_case,[spot]),[])
        own_case={'segments':[{'source_ref':spot['source_ref'],
                               'start':ev['source_start_char'],'end':ev['source_end_char_exclusive']}]}
        self.assertEqual(review.case_scan_refs(own_case,[spot]),[spot['spot_id']])

    def test_case_cannot_invent_targeted_scan_reference(self):
        rows,sample,index=review.build()
        row=next(r for r in rows if not r['targeted_print_spot_refs'])
        row['targeted_print_spot_refs']=['unviewed-page']
        with self.assertRaisesRegex(ValueError,'verification claim'):
            review.validate_records(rows,sample,index)


class ZtlyEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import build_event_pilot as events
        cls.events=events
        cls.record,cls.case,cls.index=events.build()

    def test_patient_explanation_is_not_physician_endorsement(self):
        records,_,_=review.build()
        row=next(r for r in records if r['case_id']=='XJ-ZTLY-C-V1-P102-1')
        obs=row['fields']['mechanism']['observations']
        self.assertEqual([o['assertion_type'] for o in obs],
                         ['patient_interpretation','physician_interpretation'])
        self.assertEqual(obs[0]['speaker_role'],'patient_or_family')

    def test_role_override_cannot_rewrite_evidence(self):
        case={'case_id':'synthetic','parts':['甲'],
              'segments':[{'source_ref':'A','start':0,'end':1}]}
        overrides={'synthetic':{'mechanism':{'甲':{'evidence':[]}}}}
        with self.assertRaisesRegex(ValueError,'may not alter evidence'):
            review.make_observation(case,'mechanism','甲',{'A':'甲'},{},overrides)

    def test_general_theory_scan_does_not_attach_to_case(self):
        _,sample,_=review.build()
        case=next(c for c in sample if c['case_id']=='XJ-ZTLY-C-V1-P054-1')
        refs=review.case_scan_refs(case,review.scan_spots())
        self.assertIn('ZTLY-24-P054-CASE',refs)
        self.assertNotIn('ZTLY-24-P054-THEORY',refs)

    def test_medicinal_wine_does_not_generate_drinking_habit(self):
        import build_extended_kcly as extended
        rows,_,_=extended.build('ZTLY')
        row=next(r for r in rows if r['case_id']=='XJ-ZTLY-C-V1-P057-1')
        self.assertEqual(row['fields']['habits']['observations'],[])
        self.assertEqual(row['fields']['habits']['missingness'],
                         'unrecorded_or_unresolved_not_explicit_absence')

    def test_full_event_window_cannot_drop_outcome(self):
        row=copy.deepcopy(self.record);row['events'].pop();row['relations'].pop()
        with self.assertRaisesRegex(ValueError,'cover entire case window'):
            self.events.validate(row,self.case,self.index)

    def test_advice_is_not_performed_treatment(self):
        row=copy.deepcopy(self.record)
        row['events'][2]['intervention_status']='narrated_as_performed'
        with self.assertRaisesRegex(ValueError,'Recommendation cannot be promoted'):
            self.events.validate(row,self.case,self.index)

    def test_narrative_adjacency_is_not_causality(self):
        row=copy.deepcopy(self.record);row['relations'][0]['relation']='causes'
        with self.assertRaisesRegex(ValueError,'must not invent causality'):
            self.events.validate(row,self.case,self.index)

    def test_relative_day_cannot_invent_calendar_date(self):
        row=copy.deepcopy(self.record);row['events'][5]['calendar_date']='1528-01-02'
        with self.assertRaisesRegex(ValueError,'Unsupported event calendar date'):
            self.events.validate(row,self.case,self.index)

    def test_refusal_after_advice_is_not_initial_window(self):
        row=copy.deepcopy(self.record);row['events'][3]['time_phase']='initial_narrator_window'
        with self.assertRaisesRegex(ValueError,'phase crosses care-advice anchor'):
            self.events.validate(row,self.case,self.index)


if __name__ == '__main__':
    unittest.main()
