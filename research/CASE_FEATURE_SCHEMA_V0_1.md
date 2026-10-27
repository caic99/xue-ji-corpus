# 薛己医案检索特征 schema V0.1（研究草案）

此规范基于八书全量医案结构与定点原文抽查提出；**尚未得到代表性人工标注样本验证**，勿视为现成的 1532 案临床标注。设计重心是避免把医家解释、医治后的反应和患者初诊描述混用。

## 1. 单条特征的数据合同

每个 feature 独立保存：
```json
{
  "case_id": "XJ-NKZY-C-V1-P002-1",
  "source_ref": "XJ-NKZY-V1-P002",
  "feature_type": "trigger_exertion",
  "raw_quote": "勞則頭暈",
  "source_start_char": null,
  "source_end_char_exclusive": null,
  "value_original": "劳则头晕",
  "value_normalized": "劳累后头晕",
  "polarity": "present",
  "time_phase": "pre_intervention",
  "speaker_role": "case_narrator",
  "assertion_type": "narrated_observation",
  "certainty": "explicit",
  "verification": "manual_review_pending"
}
```
以上 `null` 字符偏移量仅示范**尚未做局部源文定位的记录**；不允许用空值作为已校验特征入库。正式记录必须根据原始 `source_ref` 全文定位原文逐字跨度，且 `source[start:end] == raw_quote`；多段原文使用多个 evidence span，禁止拼接跨越治疗的两段原文并伪称同一逐字引用。

- `polarity`: `present`, `explicitly_absent`, `unrecorded`, `uncertain`。
- `time_phase`: `pre_intervention`, `during_intervention`, `post_intervention`, `unknown`；如同一案例多轮治疗，建议额外 `episode_order` 和 `observation_order`。
- `speaker_role`: `patient_or_family`, `case_narrator`, `xue_ji`, `other_physician`, `later_editor`, `uncertain`；并用原文证据而非人称词臆断。
- `assertion_type`: `narrated_observation`, `physician_interpretation`, `treatment_given`, `treatment_proposed`, `observed_outcome`, `quoted_theory`, `uncertain`。
- `certainty`: `explicit`, `derived_literal`, `requires_review`；推导项必须提供标准化规则，不让模型自由补病历。
- `verification`: `auto_extracted`, `sample_reviewed`, `human_adjudicated`, `manual_review_pending`。

## 2. 特征层次和检索窗口

| 层 | 特征字段 | 使用规则 |
|---|---|---|
| 患者背景 | `age`、`sex`、`life_stage`、`body_habitus`、`baseline_constitution`、`usual_diet`、`social_or_occupational_context` | 性别年龄不详不推断；官职≠确定生理性别 |
| 主诉与伴随 | `symptom`、`site`、`quality`、`severity`、`co_symptom`、`functional_impairment` | 症状标准化和原文严格分离 |
| 时间与变化 | `onset`、`duration`、`course`、`recurrence`、`daytime_pattern`、`season` | 记录症状相对时间，不凭章节推 |
| 诱发与缓解 | `exertion`、`rest`、`emotion_anger`、`worry`、`diet`、`alcohol`、`temperature`、`sexual_activity`、`injury`、`pregnancy`、`postpartum` | 保留“观察到的关联”与“薛己认为的病因”差别 |
| 全身状态 | `appetite`、`thirst`、`cold_heat`、`sweat`、`sleep`、`stool`、`urine`、`energy` | 未述≠正常；先提取明确表达 |
| 分科特色 | `menstrual_cycle`、`bleeding`、`pediatric_feeding`、`skin_lesion`、`ulceration`、`pus`、`swelling`、`oral_throat_function` | 由医案相关表现触发追问，非一律必填 |
| 检查记录 | `pulse_original`、`tongue_original`、`inspection`、`palpation` | 脉诊、舌诊都为可选；舌痛/舌疮不是“舌象” |
| 治疗前史 | `prior_treatment`、`prior_response`、`mistreatment_narrative` | 对本次薛己干预前的已发生治疗，按初诊可知信息存 |
| 医家解释（另层） | `mechanism_quote`、`reasoning_context`、`diagnosis_label_original` | 不倒填患者症状，也不当作初诊检索输入的已知答案 |
| 本次干预及结局（另层） | `treatment`、`formula`、`response`、`outcome` | **严格排除在初诊检索特征之外**；用于展示与回顾性分析 |

## 3. 检索与相似性

1. 初始召回先用原文/异体同义词 BM25 或其他全文检索 + 语义向量；随后依据证据支持的初诊特征重排。**目前未实施向量索引，也没有实际检索效果数据。**
2. 分开计算“明确吻合”“明确矛盾”“双方均未记录”“系统不确定”；不得对 unrecorded 做否定惩罚。
3. 特征权重应在盲测/专家审查中学习、验证，不能仅凭主观判断确定“薛己最重视”的字段。
4. 对 `needs_review` 原文，常规检索不呈现；研究者显式选择“包含待核文献”后，才允许呈现并显著标记来源状态。
5. 相似度分数为检索相关性，而非现代临床诊断概率或疗效预测。
6. 71 对候选重出要作为评测分组，避免同一叙事重文在训练集与测试集之间造成泄漏。

## 4. 开发硬门槛

- 所有具体特征值必须逐字可定位于版本明确的来源，文本变动须更新偏移量或标记 `stale_span`。
- 原文未载的检查结果设 `unrecorded`，而不是构造「舌淡」「脉细」等现代证型预期信息。
- 基线抽查必须包含误治、反复诊治与多人共同转归等复杂案例。
- 需独立检查 `symptoms_quote` 的缺省情形；既有字段没有完成全面的细粒度分段，更不能简单视为症状空白。
