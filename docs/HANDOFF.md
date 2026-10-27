# 语料维护说明

## 版本与规模

八部著作当前含5361条来源记录、1532个case_id、3272个非医案单元、1242个方剂归组。记录数量不是独立患者数量。当前权威数据为 `outputs/薛己核心医案_结构化样本.md`，状态见 `state/current_state.json`。

来源、许可和归属见 `NOTICE.md`；字段定义见 `docs/DATA_DICTIONARY.md`；160案研究合同及现状见 `research/CLOSE_READ_SCHEMA_V0_2.md` 和 `research/samples/QA_REPORT_CLOSE_READ_160.md`。整文件版本变化见 `research/SOURCE_BASELINE.md`。

## 证据与编辑约束

- 保留古籍原字、source_id、卷篇及字符范围；更改来源正文须有版本证据、旧读法和逐字迁移记录。
- 现有来源包含历史模型校改，不是未经编辑的原始转录；模型图读不等于独立人工校勘。任一书均未全书逐字核完影像。
- source_id固定不重编。case_id不等于独立患者；多人共叙、跨段续案、候选重出、署名见证和通论须分层。
- 跨物理行采用多个evidence spans，各自保存原字与Unicode码点左闭右开区间；不能将拼接文本伪称单一连续引文。
- `needs_review` 默认隔离；方剂关键药名或剂量未决时，整个方组继承待核。未记载不等于明确否认。
- 原刻小字、版心、后注与正文分层；无证据不认定注文作者。保留版本异文与确定程度，不用文义通顺代替读字证据。
- 比较仅用贯通、发展、张力/差异、明确反对、证据不足；每项思想基线至少两个可定位的不同来源及语境限制。

## 已知解析风险

`audit_corpus.py` 的来源段落终止规则匹配3至5级Markdown标题。把2级说明标题直接插在原始来源段末可能被吞入该来源body，悄悄改变来源文字层摘要。新增结构化区块应放在已有结构化区块末尾，并验证摘要不变。

三条末段来源历史上含书间分隔线：`XJ-NKZY-V2-P368`、`XJ-WKSY-V4-P417`、`XJ-LYJY-V3-P221`。现有覆盖span涵盖分隔线并附说明；不要单独删除正文尾部字符而不迁移范围与基线。

保婴粹要逐行文本须保留U+3000、未解Kanripo字形占位符、`continued_source_ref`及`continued_source_refs`的跨行语义，不把行数当医案数。

`rebuild_book_from_cc0.py` 的BookParser为现行检查依赖，但旧整书重建入口可能覆盖来源元资料。`audit_corpus.py --refresh` 会写主稿，执行前须明确其日期、书目与统计规则。默认检查均只读。

## 检查与后续研究

运行 `python3 work/validate_complete_corpus.py`、`python3 work/audit_corpus.py`、`python3 work/check_retrieval_inheritance.py`、`python3 research/reproduce_sample.py`、`python3 research/build_close_read_160.py` 和 `python3 research/check_sample_snapshots.py`。

来源文字层SHA-256为 `a719e844641d9b610848a923e108f663d0fc1620d4f28c26f1925bfc9d5d27aa`。当前8条结构警告表示全书影像校定未完成，不能忽略为已通过学术验收。

后续优先核查 `research/samples/SOURCE_EVIDENCE_REVIEW_QUEUE.md` 的电子转录差异，完成160案独立专家审校、未载/不明区分、正式事件轴和独立检查维度。71对候选重出尚待裁定；不得据此制造同患者定论或检索盲测增益。
