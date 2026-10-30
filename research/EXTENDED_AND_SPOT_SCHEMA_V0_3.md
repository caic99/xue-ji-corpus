# V0.3：独立维度、分书复审及指定字句影像记录

2026-10-27。在V0.2五领域结构上增加旁系资料，保留冻结样本和Unicode左闭右开定位，不改正文。

## 分书第二遍复审

`review_inputs/*_second_pass.json` 每份恰覆盖固定样本中某书20案，记录 `work_ref`、日期、案文摘要和逐案意见。构建程序拒绝书目不符、遗漏、重复或摘要漂移。模型复审不增加人类审校数量；`human_adjudication` 保持 `pending`。本轮为保婴及口齿两书，共40案。

## 四个独立维度

`review_inputs/KCLY_extended.tsv` 的无表头五列依次为案尾号、pulse、tongue_features、habitus、habits。使用既有逐字选证及前药反应/后续阶段标记，生成 `samples/extended_kcly_20_v1.jsonl` 和可读版。它们单独统计，不计入五领域观察总数。

- pulse：保留原文脉位、脉形及出现阶段，不改写成现代检测值。
- tongue_features：本批仅一案舌肿的明载形态变化，非正式舌诊；口舌生疮和舌痛不自动生成舌苔或舌色。
- habitus：当时的骨立、瘦倦描述；不能据此确定发病前体质。
- habits：分开记录善怒的平素性情、善饮、膏粱之人的叙述者类别词。未量化酒量或饮食，未把性情直接当作本次诱因。

空槽保留 `unrecorded_or_unresolved_not_explicit_absence`。全部查询导出继续禁用；人工审校待办。

## 影像点核

`scan_reviews/KCLY_target_spots_2026-10-27.json` 记录实际下载PDF的URL、字节数、SHA256、总页数，逐处登记1起算PDF页码、半叶、定位语句、模型图读、目标异字、原文片段及渲染图校验值。未发布扫描件或渲染图。可按记录的下载地址与渲染参数复取；不同Poppler版本的PNG字节可能不同，PDF摘要与页码才是影像身份的主要依据。

当前3个指定字句支持工作转录中的“虛”“痛”“腫”。这不裁定同书所有字句，也不据此裁定四库本。16条缓存差异保留，其中5条引用涉及这3个本轮点核字，不能称16条差异全部解决。

五领域记录新增 `targeted_print_spot_refs`。仅在点核片段完全落入该案某个来源区间时关联；相同段落中的其他案例不能继承该点核。状态可为 `not_performed` 或 `targeted_spots_only_not_full_case`。汇总中的 `print_images_checked_this_pass=3` 指3个PDF页，`full_case_print_collations_this_pass=0`，人类审定仍为0。

`check_scan_spots.py` 默认离线检查记录与原文的关联。`--pdf FILE` 另校验实际扫描文件的字节数和摘要；此程序不会自动验证模型的视觉读字结论。缓存对账程序仍只核电子转录，其影像检查计数为0，两种检查不可相加混称完整校勘。
