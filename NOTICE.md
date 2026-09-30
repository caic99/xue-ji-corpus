# NOTICE — provenance, attribution and licensing

This repository combines material with different origins. Read this before reusing any part.

## 1. Underlying works

The eight books are Ming-dynasty classical texts by 薛己 and are in the public domain. What follows concerns the *electronic transcriptions and scans* used.

| Component | Where used | Source | Terms |
|---|---|---|---|
| Text of 內科摘要, 女科撮要, 正體類要, 口齒類要, 立齋外科發揮, 外科樞要, 癘瘍機要 | source records of the corpus; `work/source-snapshots/*.html` | 中醫笈成 (jicheng.tw), transcribing the Japanese 承應三年 (1654) print held by the National Central Library, Taiwan | CC0 per the site's copyright statement (https://jicheng.tw/tcm/copyright.html) |
| Text of 保嬰粹要 | source records; `work/source-snapshots/bycy-kr3e0070_005-*.txt` | Kanseki Repository (漢籍リポジトリ), KR3e0070_005, 文淵閣四庫全書 edition | Labelled CC BY-SA by the repository; the version is not stated upstream. Attribution: *Kanseki Repository, https://www.kanripo.org/ (KR3e0070)*. Share-alike applies to this repository's derivatives |
| Wikisource 《薛氏醫案（四庫全書本）》 vols 1–19 | `work/source-snapshots/wikisource-skqs/` | https://zh.wikisource.org/wiki/薛氏醫案_(四庫全書本) via the MediaWiki API, fetched 2026-09-30 | CC BY-SA 4.0 (text contributed by Wikisource contributors); attribution required |
| Page scans (NCL 承應三年 prints; Waseda University Library copy) | **not included**; referenced by URL and page number in the data | National Central Library via Wikimedia Commons; Waseda University Library | Governed by those hosts; not redistributed here |

Some source records include a legacy reading history; see `docs/DATA_DICTIONARY.md`.

## 2. What this repository adds

Case/unit/formula structuring, evidence and status fields, candidate repeat-case flags, baseline cards, comparisons, edition-difference classifications, image spot-check readings, validators and scripts.

* **Data and annotations: CC BY-SA 4.0** (`LICENSE-DATA`), chosen because the Kanripo text is share-alike and the structured file interleaves it with the other sources. The CC0 transcriptions remain CC0 in their own right when taken from their original sites.
* **Code: MIT** (`LICENSE-CODE`).

## 3. AI-generated content

Structuring, annotation, classification and image readings were produced by AI agents (Anthropic Claude models) under human direction. They have not been human-reviewed. Fields recording this: `review_status` (e.g. `model_boundary_reviewed`, `model_drafted_not_human_reviewed`), `*_status`, `edition_image_check_status`, `skqs_variant_status`. Treat them as candidates.

## 4. No medical use

This is a historical-text research resource. Doses, drug names and formulas are transcribed historical data with recorded doubts. Nothing here is medical advice, and no individual clinical use is intended or supported.

## 5. Not included on purpose

* A library scan of 內科摘要 卷上 that was supplied to the project as an input (no redistribution right was established);
* superseded genealogy/lineage drafts and derived images from earlier project stages;
* the downloaded page-scan PDFs used for image spot-checks.
