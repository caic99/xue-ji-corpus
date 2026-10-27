# 五领域逐案模型复读合同 V0.2

这是 V0.1 特征 schema 的**研究标注层扩展**，不是已验收的标准化临床特征库。本层 `close_read_160_v1.jsonl` 取代旧16案 pilot 作为当前模型复读成果；旧自动候选、16案文件及其原报告保留为历史，不覆盖。每案全文窗口已读，记录精选证据，未穷尽每个症状、所有治疗和每个脉象。

## 数据和复现

- `review_inputs/{8书代号}.tsv` 是模型复读后的显式选择：20行/书，七列依次为案例ID后缀、症状、诱发/缓解关联、病程、干预前史/后续插入干预、病机解释、复读意见。空格和原字有意义，不做简繁转换。`¦` 只用作多个观察的分隔符。
- 输入不是正则抽取结果，也不是专家审稿。所有输出 `human_adjudication=pending`，本轮原刻影像核查为0。
- `@post:` 标记首次明确叙述者评议/治疗决定之后的事件；`@prior_response:` 标记既往药后反应；`@theory:` 标记理论引文；`@absent:` 标记原文明确否认的表现。`phase_overrides.json` 保存角色和时间不能用默认规则的个案判断。
- `python3 research/build_close_read_160.py` 默认只读，验证固定源文、160案资格、五域完整和输出可复现；`--write` 仅重建新模型复读输出，不碰源文、旧候选和pilot。
- `python3 research/check_sample_snapshots.py` 检查选定证据在**缓存电子转录**中是否存在；有差异保留双方原文及已存在的改正线索。不把差异自动定为误字或真实版本差异。

## 时间坐标：为何不用简单的治疗前/后

本层的 `time_phase` 有三个值：`initial_narrator_window`、`later_narrator_window`、`unknown`。坐标锚为**案文中首次明确叙述者的医疗评议或处置决定**，包括未执行的建议。首次窗口可含已发生的他医药后症状，不能当作患者最初发病时原始表现。later 也可能只是拒绝建议后自行服药，并不证明已经接受叙述者首次治疗。本轴不能直接转成 V0.1 的现代临床 `pre_intervention`/`post_intervention`；正式事件轴仍须专家判断。

`prior_treatment` 域保留首次评议前史，以及在后续复诊/结局之前插入的外部干预；后一种明确 later，不能当作首次前史。未明治疗者记 uncertain，不把所有“服/用”认成他医或薛己。

## 证据、缺失及角色

每个观察保留 `reading_joined_source_segments` 和 `evidence[]`。每个 evidence 都有 source_ref、Unicode码点 `[start,end)`、真正的单片段 raw_quote。跨物理行仅拼接显示读文；不添加标点，不把带有换行省略的拼接伪称单片段逐字引文。程序拒绝同案中多处同文且位置不明的短引文。

有选定证据记 `model_selected_evidence`。空域记 `not_identified_in_model_case_read` + `unrecorded_or_unresolved_in_this_case_window`：模型无法可靠区分原案未载与语义/角色无法确定时，保留合并未决状态，而非制造确定“未载”或阴性。此状态不同于旧正则的 not_identified_by_rule。专家阶段须将未载和无法断定逐项拆开裁决。

观察 polarity 的 present 指所选文字描述的观察被记载，并不把字面“不食”等解释成正常食欲；明确没有痛、没有脓水另列 explicitly_absent。未做统一的现代医学概念编码。

病机默认为 case_narrator 的 physician_interpretation；患者自释、署名见证中转述医者、引用他人理论分别标明。背景习惯不强制进入 trigger，病机解释不能转为客观症状。`initial_query_eligible=false` 对所有观察生效，直至专家完成角色、阶段和来源验收；这与3案 needs_review 来源隔离是两道不同门槛。

## 验证能证明什么

脚本可证明固定源文、清单、偏移、原字和生成物一致；9个负例回归测试覆盖越界、篡改引文、丢失待核隔离、虚构人工审校、错误查询导出、跨行/空格和重复短引文。不能证明模型语义正确，不能统计为双人一致率，不保证底本印字和案文切分无误。14个跨来源观察只覆盖本轮选定证据，不是全库跨行总数。

后续专家宜重点审查：少量案文依赖“患前症”、案尾通论/集体转归、平素背景与诱发事件、药前药后时间轴、三处旧版本决议及快照不一致片段。舌/脉、体形、习惯等独立维度尚未为160案全量精细标注。
