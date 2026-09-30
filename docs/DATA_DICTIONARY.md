# Data dictionary

The corpus is one Markdown file, `outputs/薛己核心医案_结构化样本.md` (UTF-8). Every metadata block is a fenced ```yaml block of flat `key: "value"` lines (values are JSON strings or bare numbers; a few legacy values contain unescaped inner quotes — parse with `work/audit_corpus.py:parse_metadata`, not a YAML library).

## File layout

```
# 《書名》：…全文原始層          one heading per book (8); its first yaml block is the book metadata (work_id, title, source, snapshot, alignment notes…)
##### XJ-NKZY-V2-P083          source record: yaml block, blank line, the source text (the *immutable* layer)
## 《書名》「章節」…             structured section (prose header), between  <!-- ..._BEGIN -->  and  <!-- ..._END -->  comments
### XJ-NKZY-C-V2-P083-1        structured record: yaml block, blank line, printed text = the exact cited span(s)
```yaml coverage_id: …           coverage manifest: declares that source records first..last are covered with no gap/overlap
```

Use `work/audit_corpus.py:books(text)` to get every book and its source rows (`{"meta", "body"}`) and `validate_structured_units` for the checks.

## Source records (5,357)

| Field | Meaning |
|---|---|
| `source_id` | Fixed ID: `XJ-<BOOK>-<vol>-P<nnn>` for paragraphs, `XJ-BYCY-V5-L<nnnn>` for physical print lines (保嬰粹要 is unpunctuated 四庫 text, one record per printed line) |
| `record_kind` | `source_paragraph` (4,218) or `source_line` (1,139) |
| `text_layer` | `original_text` — historical field name; the text is a *working transcription with legacy edits*, not a pristine original |
| `volume`, `section`, `source_location` | Position in the book |
| `source_url`, `rights_status` | Where the transcription comes from and its terms (`CC0_public_transcription`, `CC_BY_SA_version_unspecified`) |
| `scan_verification_status` | `not_started`, `sampled_verified`, `sampled_variants_found` (sampled = a few spots checked, never a whole page or book) |
| `retrieval_status` | `source_research_with_caveats` (default) or `needs_review` (excluded from default retrieval) |
| correction fields | `text_correction_applied` (what was changed and on which page evidence), `pre_correction_body_sha256` (digest of the body before the correction; the full change log with offsets is `work/edition-compare/applied_corrections.json`), `text_correction_note` (a proposed change that was reverted or withheld and why) |
| optional evidence fields | `original_public_transcription` / `preferred_reading` (legacy reading pair), `difference_grade` (old mixed A–D grade), `current_scan_*` (single-spot image readings), `skqs_variant_note`/`skqs_variant_counts` (Wikisource 四庫 comparison), `skqs_cross_check_note`, `edition_image_check` (image spot-check verdicts), `source_gaiji_note`, `pending_reason` |

**Never renumber source IDs; never edit a source body without a migration note.** (`skqs_variant_note` and `edition_image_check` describe the difference *at the time of comparison*; where `text_correction_applied` is present the body was later corrected to the print reading.) The source-text digest printed by `audit_corpus.py` (`text_sha256`, currently `df8fbd10ebbd097995485a55fcef34741c9f54d90dc0624db797f0fa10a347a7`; it was `20077b83…1abe9` before the 2026-09-30 image-based corrections, see `state/current_state.json` → `source_text_sha256_history`) covers every `(source_id, body)` pair and must not change.

Known quirks: the last record of three books (`XJ-NKZY-V2-P368`, `XJ-WKSY-V4-P417`, `XJ-LYJY-V3-P221`) carries a trailing `---` separator in its parsed body; structured units covering them include it in their span with an `editorial_separator_note`. Seven `保嬰粹要` lines contain unresolved Kanripo glyph codes (`&KRnnnn;`).

## Cases (`case_id`, 1,532)

`case_id` (e.g. `XJ-NKZY-C-V2-P083-1`), `source_ref` + `source_start_char` / `source_end_char_exclusive` (Python zero-based character offsets, end exclusive), optional `continued_source_ref` (+ `continued_start_char`, `continued_end_char_exclusive`) for one continuation, or `continued_source_refs: "sid:start:end; sid:start:end"` for any number of continuation spans (spans are joined with a blank line in the printed text). Descriptive fields: `person_description`, `original_case_author` (who narrates; signed testimony by disciples is recorded here), `treating_person_refs`, `treatment_record_status`.

`*_quote` fields (`person_quote`, `symptoms_quote`, `mechanism_quote`, `treatment_quote`, `formula_quote`, `outcome_quote`) must be contiguous substrings of the case text; empty means *not selected*, not *absent in the source*. `treatment_record_status`: `narrated_management`, `narrated_course_not_efficacy_inference`, `proposed_not_documented_as_administered`, `shared_unit_only`, `observation_without_medicine`, `deceased_outcome_recorded`, …. No efficacy or modern diagnosis is inferred anywhere. `shared_case_refs`, `shared_management_ref`, `possible_repeat_source_ref` and `possible_repeat_case_refs` (candidate repeats with metrics, status `candidate_not_confirmed_same_patient`) link related records.

Cases are neither patients nor source records: one paragraph may hold several patients, and one patient may recur across books.

## Text units (`text_unit_id`, 3,268) and formula groups (`formula_id`, 1,240)

Everything that is not an individual case: `unit_kind` ∈ `formula_text` (2,495), `general_claim`, `section_label`, `chapter_scope_note`, `author_commentary`, `conditional_treatment_rules`, `quoted_author_claim`, `formula_use_commentary`, `signed_testimony_colophon`, `cross_work_reference`, `collective_outcome_note`, and a few others. Units of one formula share `formula_id`/`formula_name`; a formula group inherits `needs_review` as a whole if any member is pending. Formula names for unnamed source formulas are model-assigned by ingredient matching or description and are labelled as such in the section prose.

## Baseline cards (`baseline_id`, 46) and comparisons (`comparison_id`, 83)

* Baseline: `theme`, `claim_label` (wording restricted to what the quotes support), `supporting_passage_count` and `p{k}_source_ref/_start_char/_end_char_exclusive/_quote` (≥ 2, starting in ≥ 2 different source records), `counterexample_count` with `c{k}_*` or `counterexample_search_note`, `context_note`. A quote may run over consecutive 保嬰粹要 lines through `p{k}_continued_source_refs` (spans concatenated with no separator).
* Comparison: `comparison_category` ∈ {貫通, 發展, 張力／差異, 明確反對, 證據不足}; sides `a_*` and `b_*` (source_ref, offsets, quote, label); `basis_note`. No lineage or influence is ever inferred from similar wording.
* Both are `review_status: model_drafted_not_human_reviewed`.

## Statuses in one place

`retrieval_status`: `source_research_with_caveats` | `needs_review` (a unit/group/baseline depending on any `needs_review` source must itself be `needs_review`; check with `work/check_retrieval_inheritance.py`). `review_status`: `model_boundary_reviewed`, `model_drafted_not_human_reviewed`. Nothing in this repository is human-adjudicated.

## Validation

`work/validate_complete_corpus.py` (fixed book list, counts, unique IDs, metadata parse) and `work/audit_corpus.py` (exact span equality, coverage manifests, dangling references, baseline/comparison rules, source-text digest). When adding a new structured section, append it after the latest `<!-- …_END -->` marker: the parser bounds a source body only at a line starting with 3–5 `#`, so a `## ` header placed right after raw source text would be absorbed into the previous source record and silently change the digest.
