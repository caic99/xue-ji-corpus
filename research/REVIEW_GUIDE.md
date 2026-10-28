# PR研究审阅入口

## 审阅范围

本PR提交可复现160案样本、五领域模型精选观察、逐字证据回链和验证程序。它是可审阅的研究资料，不是专家已审的金标准、原刻定本或临床系统。

- 160案，八书各20，800领域槽。
- 788项模型精选观察，801个逐字证据片段，13项观察跨来源。
- 与缓存电子来源对账：783片段可逐字找到；18片段保留不同读文，含尚未新核的立斋少/稍。
- 3案来源needs_review继续隔离；初诊查询导出全部禁用。
- 古籍来源文字摘要、ID、样本名单和字符跨度保持不变；来源文件两处非原典书目说明及其版本校验已更新，见SOURCE_BASELINE.md。

八书160案第二遍模型阅读全部完成；独立维度160案111条（115片段），事件试点7案87段80关系。专家审核及全案影像校定0；当前影像仅13页15个目标。最新自审见 `samples/SELF_REVIEW_ASSESSMENT_BOUNDARY_2026-10-28.md`，历史报告保留各自阶段数字。

## 复验

保婴母子人物与语气试点另选7处关键片段，见 `samples/ROLE_PILOT_BYCY_V1.md`，不重复计入完整事件轴。

保婴跨年案26段完整来源覆盖。阶段比较覆盖44条核心观察；模型复审将机制引文余作胎毒治之收窄为余作胎毒，施治及结局保持事件E03，当前阶段候选0。旧候选和修订理由见最新自审及 `review_inputs/BYCY_anchor_review_2026-10-28.json`。原图和专家尚未新核，零候选不代表语义无误。

在PR检出目录中运行完整检验（26项命令，保存真实日志）：

```sh
python3 research/run_research_checks.py --report-date 2026-10-28 --label verification
```

以下为核心单项入口，独立维度和事件试点由完整检验覆盖：

```sh
python3 work/validate_complete_corpus.py
python3 work/audit_corpus.py
python3 work/check_retrieval_inheritance.py
python3 research/reproduce_sample.py
python3 research/build_close_read_160.py
python3 research/check_sample_snapshots.py
python3 research/check_publication.py
python3 -m unittest discover -s research -p 'test_close_read_160.py' -v
```

预期：5361条来源、1532案、0结构错误；8条全书影像校定未完成警告保留；待核继承缺口0；94项回归测试通过。缓存文本的18片段差异是保留的研究项，不是将快照差异强改为一致。

## 人工及Claude Code审阅重点

1. 对比当前PR diff，检查来源文字层摘要与引用偏移是否保持、版本固定是否同步。
2. 核查症状/诱因/病程/前史/病机的时点和归属；特别是先用、拒绝建议后的用药、患者自释及理论引文。
3. 核查跨物理行证据是否逐片段存字；未载/不明是否被错误转成阴性。
4. 核查3案待核隔离和禁用查询导出；不能把模型或程序检查升级为人类文献学审定。
5. 检查复现代码、检查日志与报告数字一致性。记录可重现的问题、案例ID及证据位置，不直接修改古籍源文来消除测试差异。
6. 版本影像和专业语义仍需独立专家复核。详见samples/QA_REPORT_CLOSE_READ_160.md及samples/SOURCE_EVIDENCE_REVIEW_QUEUE.md。

本指南可供维护者或Claude Code开展只读审查。是否安装或启用自动审核服务，由仓库维护者管理；本PR不新增外部服务、凭据、付费调用或自动合并。

## 提交前自审

每次创建PR之前须完成 `REVIEW_POLICY.md`。2026-10-27增量及明确未决事项见 `samples/SELF_REVIEW_2026-10-27.md`；初读阶段历史报告不代表最新观察数量。

口齿增量、独立维度及影像点核：见 `samples/SELF_REVIEW_KCLY_2026-10-27.md`。追加执行 `python3 research/build_extended_kcly.py` 和 `python3 research/check_scan_spots.py`；后者不自动确认视觉读字。

正体增量、逐观察角色及事件分段见 `samples/SELF_REVIEW_ZTLY_2026-10-27.md`。追加执行 `python3 research/build_extended_kcly.py --work ZTLY`、`python3 research/build_event_pilot.py`；影像检查默认汇总多文件，但不自动裁定读字。

女科增量、先前解释者不明及处置意向见 `samples/SELF_REVIEW_NKCZ_2026-10-27.md`。追加执行 `python3 research/build_extended_kcly.py --work NKCZ`、`python3 research/build_event_pilot.py --work NKCZ`；意向和建议均不作为已实施治疗。

内科增量、用药声称与待核继承见 `samples/SELF_REVIEW_NKZY_2026-10-27.md`。追加执行 `python3 research/build_extended_kcly.py --work NKZY`、`python3 research/build_event_pilot.py --work NKZY`。独立维度中的needs_review不得解除，声称用药不得变成已实施。

外科增量、句界、未实现预期和可反驳影像记录见 `samples/SELF_REVIEW_WKSY_2026-10-28.md`。追加 `python3 research/build_extended_kcly.py --work WKSY`、`python3 research/build_event_pilot.py --work WKSY`；影像记录检查不得要求见证必须支持工作稿。

疠疡背景及缺失诊治锚点见 `samples/SELF_REVIEW_LYJY_2026-10-28.md`；立斋阶段性否定、条件计划及当前未决原刻目标见 `samples/SELF_REVIEW_LZWKFH_2026-10-28.md`。全部第二遍模型阅读完成不能表述为专家金标准或全量原典校勘完成。

独立维度全部160案已有首轮模型记录。最新横向核查与未决候选见 `samples/SELF_REVIEW_CROSS_DIMENSIONS_2026-10-28.md`；23项完整检查现包含8书独立维度、5案事件、跨文件联接及有限提示筛查，不能代替原刻与专家审定。
