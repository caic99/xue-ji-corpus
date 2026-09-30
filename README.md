# xue-ji-corpus — 薛己直接著作：结构化语料与版本对照 / Structured corpus of Xue Ji's eight books, with edition comparison

**English** · [中文](#中文说明)

A single, machine-checkable Markdown corpus of the eight medical books directly authored by **Xue Ji (薛己, 16th-century Ming physician)**, built for historical **case retrieval, edition tracing and syndrome-differentiation comparison**. Every structured record points back to an exact character span of an immutable source-text layer, and every quotation is verified by script.

> **Status: research draft. Not medical advice.** Almost all annotation was produced by AI agents (Anthropic Claude) under human direction and has **not been human-reviewed**. Doses and drug names are *transcription data with known doubts*, not clinical guidance. Nothing here has been verified against the whole of any scan, and the corrected passages rest on model readings of page images. See [Limitations](#limitations).

## What is in the repository

| Path | Content |
|---|---|
| `outputs/薛己核心医案_结构化样本.md` | **The corpus** (one ~9 MB file). Source text of 8 books (5,361 records) + structured overlay: 1,532 cases, 3,272 non-case text units, 1,242 formula groups, 46 baseline cards, 83 comparisons |
| `docs/DATA_DICTIONARY.md` | Record types, fields, status values, how to parse |
| `docs/HANDOFF.md` | Maintainer notes (Chinese): decisions, known risks, tool pitfalls |
| `work/edition-compare/` | Machine alignment of 7 books against Wikisource's 四庫全書 text; 3,159 classified differences; 325 image checks (README explains method and findings) |
| `work/source-snapshots/` | Dated snapshots of the electronic sources used (see [NOTICE.md](NOTICE.md)) |
| `work/*.py` | Parser, validators, reconciliation and comparison scripts (Python ≥ 3.9, standard library only) |
| `state/` | Machine-readable status, counts, checksums, open tasks |

The eight books: 內科摘要, 女科撮要, 正體類要, 口齒類要, 立齋外科發揮, 外科樞要, 癘瘍機要, 保嬰粹要.

## Quick start

```sh
git clone https://github.com/caic99/xue-ji-corpus && cd xue-ji-corpus
python3 work/validate_complete_corpus.py   # expects: works 8, records 5361, errors 0
python3 work/audit_corpus.py               # source-text digest must stay fd06d94f…e2df
python3 work/check_retrieval_inheritance.py
```

```python
import sys; sys.path.insert(0, 'work')
from audit_corpus import books, CORPUS
for book in books(CORPUS.read_text(encoding='utf-8')):
    print(book['meta']['work_title'], len(book['rows']))        # source records
    first = book['rows'][0]; print(first['meta']['source_id'], first['body'][:30])
```

## Design in one paragraph

Source text and interpretation are separate layers. **Source records** (`source_id` such as `XJ-NKZY-V2-P083`) are never renumbered. **Structured records** (`case_id`, `text_unit_id`, `formula_id`, `baseline_id`, `comparison_id`) cite a source record plus `source_start_char`/`source_end_char_exclusive`; the validator rejects any record whose printed text is not exactly that span, any coverage gap or overlap, dangling references, unknown comparison categories, and records that depend on a pending (`needs_review`) source but are not themselves pending. Comparisons use only five conclusions — 貫通, 發展, 張力／差異, 明確反對, 證據不足 — and never infer lineage from similar wording.

## Findings you can reuse

* **The public transcription (jicheng.tw) has real errors relative to the 承應 print.** In 325 page-image checks covering essentially all machine-flagged high-importance differences, the 承應 print agreed with the 四庫 reading 214 times, with the working text 97 times, and with neither 14 times. This covers only the flagged high-importance subset (medium/low-importance differences are not yet image-checked), it is not an overall error rate, and it varies by book. On 2026-09-30, 153 of 187 confident proposals were applied to the source text (136 records changed; every change is logged in `work/edition-compare/applied_corrections.json` with a per-record `text_correction_applied` note and is reversible); 32 were deliberately not applied and 2 reverted (`correction_outcomes.json`). The source-text digest changed on purpose (history in `state/current_state.json`). Examples: 內科摘要 P308 ‘各一兩’ (working text: 各一錢), P178 蒼朮 ‘一錢’ (working: 三分), P083 ‘府庠’ (working: 府癢).
* **The working text is not a pure 承應 transcription.** Page-image checks show that some passages present in it (the 陸師道 preface of 正體類要; the preface and two later passages of 女科撮要) do not appear in the 承應 scan at all, and one 409-character passage of 女科撮要 appears in the 承應 print but not in the 四庫 text (`work/edition-compare/README.md`).
* **71 candidate repeated cases** across books (`possible_repeat_case_refs`), flagged mechanically, not confirmed.
* **保嬰粹要 source lines contain 7 unresolved Kanripo glyph placeholders** (`&KR1792;` …), annotated but not replaced.

## Limitations

1. AI-drafted, not human-reviewed: case boundaries, patient counts, formula names, baseline cards, comparison categories, difference classes.
2. Image checks are model readings of single spots; small numerals are error-prone. No book has a complete image proofreading.
3. The working text comes from jicheng.tw (which names the Japanese 承應 print as its base, plus a 嘉靖 print for some books) for seven books, and from the 四庫 text (via Kanripo) for 保嬰粹要. It is *not* identical to the 承應 scan (see Findings), and the two editions differ from each other.
4. 立齋外科發揮 has no 四庫 parallel and was not edition-compared.
5. Source records ≠ cases ≠ patients; repeats and multi-patient paragraphs are handled as evidence, not merged.
6. No database, vector index or Q&A interface is built; that was deliberately deferred until evidence review.

## Licenses and provenance

Mixed. Code: MIT (`LICENSE-CODE`). Data and annotations: CC BY-SA 4.0 (`LICENSE-DATA`) because one source (Kanripo) is share-alike. Underlying classical texts are public domain; transcriptions carry their own terms. Full attribution in [NOTICE.md](NOTICE.md). Page scans are **not** included; links only.

## Contributing

Corrections are welcome, especially: image-based verification of the differences listed in `work/edition-compare/edition_diffs_all.json`; review of baseline cards and comparisons; identification of the Kanripo glyph placeholders. Keep the validators passing and never edit a source-text record without a migration note (see `docs/HANDOFF.md`).

---

## 中文说明

本仓库是薛己（16 世纪明代医家）**八部直接著作**的结构化 Markdown 语料，服务于历史医案检索、版本溯源和辨证比较。每条结构化记录都指向不可变来源文字层中的精确字符跨度，所有引文由脚本逐字校验。

> **状态：研究草稿，非医疗建议。** 绝大多数标注由 AI（Anthropic Claude）在人类指示下生成，**尚未经人工复核**。方药剂量与药名是带有已知疑点的转录数据，不是诊疗依据。任何一本书都未做完整影像逐字校对。

### 内容
* `outputs/薛己核心医案_结构化样本.md`：语料主文件。八书 5361 条来源记录；1532 案、3272 个非医案文字单元、1242 个方剂归组、46 张思想基线候选卡、83 条比较记录。
* `work/edition-compare/`：与 Wikisource 四库全书本的逐字对照（七书），3159 条已分类差异，逐处承应本影像抽核（现 325 处，见 edition-compare/README）。
* `docs/DATA_DICTIONARY.md`：字段与状态说明；`docs/HANDOFF.md`：维护说明（含已知风险与工具陷阱）。
* 校验：`python3 work/validate_complete_corpus.py`、`python3 work/audit_corpus.py`。仅需 Python 标准库。

### 主要发现
* **工作稿（公开转录）相对承应本存在实质误读**：对机械筛出的“高重要差异”共核影像 325 处，承应本与四库读法一致 214 处、与工作稿一致 97 处、两者皆不同 14 处（仅覆盖高重要差异，各书不均，不是整体错误率）；2026-09-30 已依影像对 187 条高确定度提案中的 153 条改正文字（136 条记录，逐处有日志、可还原），32 条有意未应用、2 条撤回，见 `work/edition-compare/correction_outcomes.json`；来源文字层校验值随之有意更新。
* **工作稿不是纯承应本**：影像核查发现《正体类要》陆师道序、《女科撮要》序文等处在承应影像中并不存在（来源待考）；《女科撮要》卷下一段409字承应本有而四库本无。
* 机械筛出 71 对跨书候选重出案例（未确认）。
* 《保婴粹要》有 7 处 Kanripo 缺字占位符，已标注未替换。

### 许可
代码 MIT；数据与标注 CC BY-SA 4.0（因 Kanripo 来源为相同方式共享）；古籍原文属公有领域，各转录本保留其自身条款；不含影像文件。详见 [NOTICE.md](NOTICE.md)。
