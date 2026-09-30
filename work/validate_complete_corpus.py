"""Validate the single-file full-text corpus of Xue Ji's direct works."""

from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys
from audit_corpus import parse_metadata


CORPUS = Path("outputs/薛己核心医案_结构化样本.md")

ADDED_OUT_OF_ORDER = {"XJ-NKZY-V1": [177, 178], "XJ-LYJY-V3": [222, 223]}

EXPECTED = {
    "XJ-NKZY": {
        "title": "內科摘要",
        "count": 546,
        "headings": ["卷上", "卷下"],
    },
    "XJ-NKCZ": {
        "title": "女科撮要",
        "count": 593,
        "headings": ["前序", "卷上", "卷下"],
    },
    "XJ-ZTLY": {
        "title": "正體類要",
        "count": 329,
        "headings": ["序", "上卷", "下卷"],
    },
    "XJ-KCLY": {
        "title": "口齒類要",
        "count": 322,
        "headings": [
            "繭唇一",
            "口瘡二",
            "齒痛三",
            "舌症四",
            "喉痹諸症五",
            "喉痛六",
            "諸骨稻穀發鯁七",
            "治諸鯁咒法八",
            "誤吞水蛭九",
            "諸蟲入耳十",
            "蛇入七竅及蟲咬傷十一",
            "男女體氣十二",
            "附方並注",
        ],
    },
    "XJ-LZWKFH": {
        "title": "立齋外科發揮",
        "count": 1170,
        "headings": ["敘", "卷一", "卷二", "卷三", "卷四", "卷五", "卷六", "卷七", "卷八"],
    },
    "XJ-WKSY": {
        "title": "外科樞要",
        "count": 853,
        "headings": ["序", "卷一", "卷二", "卷三", "卷四"],
    },
    "XJ-LYJY": {
        "title": "癘瘍機要",
        "count": 409,
        "headings": ["序", "上卷", "中卷", "下卷"],
    },
    "XJ-BYCY": {
        "title": "保嬰粹要",
        "count": 1139,
        "headings": ["卷五（保嬰粹要）"],
    },
}


def parse_simple_yaml(block: str) -> dict[str, str]:
    return parse_metadata(block)[0]


def main() -> None:
    text = CORPUS.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    report: dict[str, object] = {"corpus": str(CORPUS), "works": {}}

    starts = list(re.finditer(r"^# 《([^》]+)》[^\n]*$", text, re.M))
    sections = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        sections.append((match.group(1), text[match.start():end]))

    section_by_work = {}
    all_ids: list[str] = []
    record_index: dict[str, tuple[dict[str, str], str]] = {}
    for heading_title, section in sections:
        yaml_match = re.search(r"```yaml\n([\s\S]*?)\n```", section)
        if not yaml_match:
            errors.append(f"《{heading_title}》缺少书级 YAML")
            continue
        metadata = parse_simple_yaml(yaml_match.group(1))
        work_id = metadata.get("work_id")
        if work_id in EXPECTED:
            section_by_work[work_id] = (heading_title, metadata, section)

    if set(section_by_work) != set(EXPECTED):
        missing = sorted(set(EXPECTED) - set(section_by_work))
        extra = sorted(set(section_by_work) - set(EXPECTED))
        if missing:
            errors.append("缺少作品：" + "、".join(missing))
        if extra:
            errors.append("意外作品：" + "、".join(extra))

    for work_id, expected in EXPECTED.items():
        if work_id not in section_by_work:
            continue
        heading_title, metadata, section = section_by_work[work_id]
        work_errors = []
        work_warnings = []
        if metadata.get("work_title") != expected["title"]:
            work_errors.append(
                f"书名不符：{metadata.get('work_title')} != {expected['title']}"
            )
        for field in (
            "author",
            "source_url",
            "rights_status",
            "full_text_transcription_status",
            "scan_verification_status",
        ):
            if not metadata.get(field):
                work_errors.append(f"缺少书级字段 {field}")
        if metadata.get("author") != "薛己":
            work_errors.append("作者不是薛己")
        if not metadata.get("source_url", "").startswith("https://"):
            work_errors.append("书级来源 URL 无效")

        body_start = section.find("## 全文")
        if body_start < 0:
            work_errors.append("缺少“全文”区")
            body = ""
        else:
            body = section[body_start:]

        level3 = re.findall(r"^### (.+)$", body, re.M)
        if level3 != expected["headings"]:
            work_errors.append(
                f"卷篇标题不符：实际 {level3}；预期 {expected['headings']}"
            )

        record_re = re.compile(
            r"^##### ([^\n]+)\n\n```yaml\n([\s\S]*?)\n```\n\n"
            r"([\s\S]*?)(?=\n##### |\Z)",
            re.M,
        )
        records = list(record_re.finditer(body))
        if len(records) != expected["count"]:
            work_errors.append(
                f"记录数不符：实际 {len(records)}；预期 {expected['count']}"
            )
        declared = metadata.get("paragraph_count") or metadata.get("source_line_count")
        if declared is None or int(declared) != len(records):
            work_errors.append(f"书级声明数 {declared} 与实际 {len(records)} 不一致")

        prefix_numbers: dict[str, list[int]] = defaultdict(list)
        folios = []
        for match in records:
            heading_id = match.group(1).strip()
            record_meta = parse_simple_yaml(match.group(2))
            record_text = match.group(3).strip()
            source_id = record_meta.get("source_id", "")
            all_ids.append(source_id)
            record_index[source_id] = (record_meta, record_text)
            if heading_id != source_id:
                work_errors.append(f"标题 ID 与 YAML 不符：{heading_id} / {source_id}")
            if record_meta.get("work_id") != work_id:
                work_errors.append(f"{source_id}: work_id 不符")
            if record_meta.get("text_layer") != "original_text":
                work_errors.append(f"{source_id}: text_layer 不符")
            if record_meta.get("record_kind") not in {"source_paragraph", "source_line"}:
                work_errors.append(f"{source_id}: record_kind 不受支持")
            if not record_meta.get("source_location"):
                work_errors.append(f"{source_id}: 缺少定位")
            if not record_meta.get("source_url", "").startswith("https://"):
                work_errors.append(f"{source_id}: 来源 URL 无效")
            if not record_meta.get("rights_status"):
                work_errors.append(f"{source_id}: 缺少权利状态")
            if record_meta.get("scan_verification_status") not in {
                "not_started",
                "sampled_pending",
                "sampled_verified",
                "sampled_variants_found",
            }:
                work_errors.append(f"{source_id}: 影像状态非法")
            if not record_text:
                work_errors.append(f"{source_id}: 原文为空")

            id_match = re.match(r"^(.+)-(?:P|L)(\d+)$", source_id)
            if not id_match:
                work_errors.append(f"{source_id}: ID 格式非法")
            else:
                prefix_numbers[id_match.group(1)].append(int(id_match.group(2)))
            if work_id == "XJ-BYCY":
                folios.append(record_meta.get("folio", ""))

        for prefix, numbers in prefix_numbers.items():
            # Records added after the first release keep new numbers but sit at their print position (see print_position_note).
            added = ADDED_OUT_OF_ORDER.get(prefix, [])
            in_order = [n for n in numbers if n not in added]
            expected_numbers = list(range(1, len(numbers) + 1))
            if sorted(numbers) != expected_numbers or in_order != sorted(in_order):
                work_errors.append(
                    f"{prefix}: 序号不连续或顺序错误；前后为 {numbers[:3]}…{numbers[-3:]}"
                )

        if work_id == "XJ-BYCY":
            if metadata.get("physical_line_count") != "1302":
                work_errors.append("物理行数声明不是 1302")
            if metadata.get("folio_marker_count") != "144":
                work_errors.append("叶面标记数声明不是 144")
            if metadata.get("first_folio") != "KR3e0070_WYG_005-1a":
                work_errors.append("首叶标记不符")
            if metadata.get("last_folio") != "KR3e0070_WYG_005-72b":
                work_errors.append("末叶标记不符")
            wanted_folios = [
                f"KR3e0070_WYG_005-{number}{side}"
                for number in range(1, 73)
                for side in ("a", "b")
            ]
            present_folios = list(dict.fromkeys(folios))
            if present_folios != wanted_folios:
                work_errors.append("1a—72b 叶面序列不连续")
            if not body.rstrip().endswith("薛氏醫案卷五"):
                work_errors.append("卷尾闭合文字缺失")

        if metadata.get("scan_verification_status") != "fully_verified":
            work_warnings.append("尚未完成全书馆藏影像逐字校定（现有状态仅代表抽样）")

        errors.extend(f"{work_id}: {item}" for item in work_errors)
        warnings.extend(f"{work_id}: {item}" for item in work_warnings)
        report["works"][work_id] = {
            "title": expected["title"],
            "records": len(records),
            "headings": level3,
            "id_series": {
                prefix: {"count": len(numbers), "first": numbers[0], "last": numbers[-1]}
                for prefix, numbers in prefix_numbers.items()
            },
            "errors": work_errors,
            "warnings": work_warnings,
        }

    duplicates = [item for item, count in Counter(all_ids).items() if item and count > 1]
    if duplicates:
        errors.append("全库 source_id 重复：" + "、".join(duplicates[:20]))
    if any(not item for item in all_ids):
        errors.append("存在空 source_id")

    # High-risk collation regressions: corrected readings must not silently revert.
    collation_expectations = {
        "XJ-NKZY-V1-P001": {
            "required_text": ["加人參一兩", "煎服即甦", "駕馭其邪", "否則不惟無益", "芪附"],
            "forbidden_text": ["煎服即蘇", "駕驅其邪", "否則無益", "耆附"],
            "required_fields": [
                "parallel_source_url",
                "scan_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "early_edition_variant",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-NKZY-V1-P071": {
            "required_text": ["尺脈漸復"],
            "forbidden_text": ["足脈漸復"],
            "required_fields": [
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-NKZY-V1-P174": {
            "required_text": ["右各另為末"],
            "forbidden_text": ["上各另為末"],
            "required_fields": [
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-NKZY-V2-P001": {
            "required_text": ["誠開後學之矇瞶", "腎氣丸即六味丸也"],
            "forbidden_text": ["誠開後學之蒙瞶"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "parallel_edition_variant",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-NKZY-V2-P040": {
            "required_text": ["加柴胡、當歸"],
            "forbidden_text": ["加白朮、當歸"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "preferred_reading",
                "parallel_edition_variant",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-NKZY-V2-P366": {
            "required_text": [
                "肉蓯蓉（酒浸焙）　石斛　附子（炮）　五味子　白茯苓",
                "石菖蒲　遠志（去心）　麥門冬（去心）　官桂（各等分）",
            ],
            "forbidden_text": ["石菖蒲遠志"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-NKZY-V2-P367": {
            "required_text": ["右每服三錢"],
            "forbidden_text": ["上每服三錢"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P018": {
            "required_text": ["各二錢五分", "右為末"],
            "forbidden_text": ["各五錢五分", "上為末"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "parallel_edition_variant",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P020": {
            "required_text": ["右水酒各半煎服"],
            "forbidden_text": ["上水酒各半煎服"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P022": {
            "required_text": ["右水煎服"],
            "forbidden_text": ["上水煎服"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P215": {
            "required_text": ["右為末"],
            "forbidden_text": ["上為末"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P217": {
            "required_text": ["右為末"],
            "forbidden_text": ["上為末"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P219": {
            "required_text": ["右各另為末"],
            "forbidden_text": ["上各另為末"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
        "XJ-LYJY-V3-P221": {
            "required_text": ["如用熟附子，不應", "然後量症治之"],
            "forbidden_text": ["如用熱附子，不應"],
            "required_fields": [
                "scan_source_url",
                "parallel_source_url",
                "collation_status",
                "original_public_transcription",
                "preferred_reading",
                "difference_grade",
                "retrieval_warning",
            ],
        },
    }
    for source_id, expectation in collation_expectations.items():
        if source_id not in record_index:
            errors.append(f"校勘记录缺失：{source_id}")
            continue
        record_meta, record_text = record_index[source_id]
        for fragment in expectation["required_text"]:
            if fragment not in record_text:
                errors.append(f"{source_id}: 校订正文缺少“{fragment}”")
        for fragment in expectation["forbidden_text"]:
            if fragment in record_text:
                errors.append(f"{source_id}: 校订正文回退为“{fragment}”")
        for field in expectation["required_fields"]:
            if not record_meta.get(field):
                errors.append(f"{source_id}: 缺少校勘字段 {field}")

    new_scan_corrections = {
        "XJ-NKCZ-V2-P164": (["右每服四錢"], ["上每服四錢"]),
        "XJ-NKCZ-V2-P168": (["右薑蔥水煎服"], ["上薑蔥水煎服"]),
        "XJ-NKCZ-V2-P172": (
            ["右二味，以水五升，煮取二升，分三服"],
            ["以水服一錢", "上二味"],
        ),
        "XJ-NKCZ-V2-P175": (["右每服四錢"], ["上每服四錢"]),
        "XJ-NKCZ-V2-P177": (
            ["枳殼（炒）　黃芩（炙。各半兩）　白朮（一兩）"],
            ["黃芩（炙，半兩）"],
        ),
        "XJ-NKCZ-V2-P178": (["右為末"], ["上為末"]),
        "XJ-NKCZ-V2-P181": (["右為末"], ["上為末"]),
        "XJ-ZTLY-V2-P107": (["神效太乙膏　治癰疽發背杖瘡"], []),
        "XJ-ZTLY-V2-P110": (["乳香定痛散　治杖瘡、金瘡"], []),
        "XJ-ZTLY-V2-P112": (["右為末"], ["上為末"]),
        "XJ-ZTLY-V2-P113": (["豬蹄湯　治一切癰疽杖瘡潰爛"], []),
        "XJ-ZTLY-V2-P115": (["右用豬蹄一隻"], []),
        "XJ-KCLY-H13-P114": (["右為末，水調神麯糊丸"], ["上為末"]),
        "XJ-KCLY-H13-P117": (
            ["川芎（各二錢）　右水煎服"],
            ["川藥", "上水煎服"],
        ),
        "XJ-KCLY-H13-P120": (["右水煎服"], ["上水煎服"]),
        "XJ-KCLY-H13-P123": (["右水煎服"], ["上水煎服"]),
        "XJ-KCLY-H13-P126": (["右水煎熟"], ["上水煎熟"]),
        "XJ-KCLY-H13-P129": (["右水煎服"], ["上水煎服"]),
        "XJ-KCLY-H13-P132": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P160": (["薄荷　白芷（各五錢）"], ["蒲荷"]),
        "XJ-WKSY-V4-P161": (
            ["右每服五錢，薑水煎，日二三服"],
            ["上每服五錢", "姜水煎"],
        ),
        "XJ-WKSY-V4-P164": (["右每服五七錢，水煎服"], ["上每服五七錢"]),
        "XJ-WKSY-V4-P167": (
            ["右每服五七錢，水煎服。臟腑和而自汗者"],
            ["上每服五七錢"],
        ),
        "XJ-WKSY-V4-P168": (
            ["六味丸（一名地黃丸）"],
            ["六味丸（一名六味地黃丸）"],
        ),
        "XJ-WKSY-V4-P171": (
            ["右地黃杵膏，餘為末"],
            ["上地黃杵膏", "余為末"],
        ),
        "XJ-WKSY-V4-P178": (
            ["右薑棗水煎，空心午前服"],
            ["上薑、棗水煎，空心午前服"],
        ),
        "XJ-WKSY-V4-P179": (["面色萎黃"], ["面色痿黃"]),
        "XJ-WKSY-V4-P181": (
            ["右水煎服。如不應，倍之"],
            ["上水煎服。如不應，倍之"],
        ),
        "XJ-WKSY-V4-P182": (["面色萎黃"], ["面色痿黃"]),
        "XJ-WKSY-V4-P184": (["右薑棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P187": (["右薑棗水煎服"], ["上薑棗水煎服"]),
        "XJ-WKSY-V4-P191": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P194": (["右薑棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P197": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P200": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P201": (["怔忡頰赤"], ["怔仲頰赤"]),
        "XJ-WKSY-V4-P203": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P206": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P209": (["右為末，水丸桐子大"], ["上為末，水丸桐子大"]),
        "XJ-WKSY-V4-P211": (
            ["澤瀉　豬苓　白朮　赤茯苓　肉桂（各等分）"],
            ["澤瀉　豬苓　肉桂　白朮　赤茯苓"],
        ),
        "XJ-WKSY-V4-P212": (["右為細末，每服一二錢"], ["上為細末，每服一二錢"]),
        "XJ-WKSY-V4-P213": (["犀角地黃湯"], ["犀角地黃丸"]),
        "XJ-WKSY-V4-P215": (["右水煎熟，入犀角末服"], ["上水煎熟", "入犀末服"]),
        "XJ-WKSY-V4-P216": (["用四物加炮薑"], ["用四物加炮姜"]),
        "XJ-WKSY-V4-P219": (["右水煎服。痛未止"], ["上水煎服。痛未止"]),
        "XJ-WKSY-V4-P222": (["右各另研為末"], ["上各另研為末"]),
        "XJ-WKSY-V4-P225": (
            ["右為末，水二碗，生薑八兩、紅棗一百枚"],
            ["上為末，水二碗", "水二碗，姜八兩"],
        ),
        "XJ-WKSY-V4-P228": (
            ["右為末，用大紅棗四十九枚", "生薑四兩切碎，同棗用水煮熟"],
            ["上為末，用大紅棗", "大紅棗四十枚", "生薑四兩，水煮熟"],
        ),
        "XJ-WKSY-V4-P231": (["右為末，水調麴櫱麵糊丸"], ["上為末，水調麴櫱麵糊丸"]),
        "XJ-WKSY-V4-P237": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P240": (["右為末，入地黃膏"], ["上為末，入地黃膏"]),
        "XJ-WKSY-V4-P244": (["及腋下"], ["及脅下"]),
        "XJ-WKSY-V4-P246": (["右先用琥珀、丁香、桂心、硃砂、木香為末"], ["上先用琥珀"]),
        "XJ-WKSY-V4-P243": (
            ["右將熟地黃搗碎，酒拌濕杵膏"],
            ["上將熟地黃掏碎", "熟地黃掏碎"],
        ),
        "XJ-WKSY-V4-P245": (
            ["丁香　木香（各三錢）"],
            ["丁香　木香（各二錢）"],
        ),
        "XJ-WKSY-V4-P249": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P252": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P255": (["右入糯米一撮，水煎服"], ["上入糯米一撮"]),
        "XJ-WKSY-V4-P258": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P261": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P264": (["右水煎服"], ["上水煎服"]),
        "XJ-LZWKFH-V5-P183": (["四劑少愈"], ["四劑稍愈"]),
        "XJ-LZWKFH-V5-P184": (
            ["以內疏黃連湯，一劑少愈"],
            ["以內疏黃連湯，二劑愈"],
        ),
        "XJ-LZWKFH-V5-P185": (
            ["以托裡溫中湯，二劑頓愈"],
            ["以托裡理中湯，二劑頓愈"],
        ),
        "XJ-LZWKFH-V5-P205": (
            ["右為末，用大紅棗四十九枚"],
            ["上為末，用大紅棗四十九枚"],
        ),
        "XJ-WKSY-V4-P267": (["右水煎稠湯化服之"], ["上水煎稠湯化服之"]),
        "XJ-WKSY-V4-P270": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P272": (
            ["肉豆蔻　川烏"],
            ["肉豆蔻川烏"],
        ),
        "XJ-WKSY-V4-P273": (
            ["右為末，用羊腰子兩對", "丸，如梧桐子大"],
            ["上為末，用羊腰子兩對", "丸，如梧桐子。"],
        ),
        "XJ-WKSY-V4-P276": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P279": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P282": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P284": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P286": (
            ["半夏（各一錢）", "炮薑", "右薑棗水煎服"],
            ["半夏（各一兩）", "炮姜", "上薑、棗水煎服"],
        ),
        "XJ-WKSY-V4-P289": (["右薑、棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P292": (["右作二劑，水煎服"], ["上作二劑，水煎服"]),
        "XJ-WKSY-V4-P295": (
            ["右每服五七錢水煎服，加減仝上"],
            ["上每五七錢水煎服", "加減同上"],
        ),
        "XJ-WKSY-V4-P298": (["右為細末，研極細"], ["上為細末，研極細"]),
        "XJ-WKSY-V4-P301": (
            ["右先將豬蹄一隻"],
            ["上先將豬蹄", "豬蹄彎一隻"],
        ),
        "XJ-WKSY-V4-P304": (["右用水酒煎服"], ["上用水酒煎服"]),
        "XJ-WKSY-V4-P306": (
            ["牡丹皮（八分）", "右水煎服"],
            ["牡丹皮（八錢）", "上水煎服"],
        ),
        "XJ-WKSY-V4-P309": (["右薑水煎服"], ["上姜水煎服"]),
        "XJ-WKSY-V4-P312": (["右為末，每服一錢酒調下"], ["上為末，每服一錢酒調下"]),
        "XJ-WKSY-V4-P315": (
            ["右為末，每服一錢", "冷酒調下，徐徐嚥之", "重者一料全愈", "忌鹹酸、油膩、澀氣等物。修合用除日效"],
            ["上為末，每服一錢", "冷酒調搽", "徐徐嚥下", "一料痊愈", "修合用除日效，忌鹹酸"],
        ),
        "XJ-WKSY-V4-P317": (
            ["海藻　昆布（各二兩）", "龍膽草（二兩）　小麥（四兩，醋煮炒乾）"],
            ["海藻　昆布（各一兩）", "小麥（四兩，醋煮炒乾）　龍膽草（二兩）"],
        ),
        "XJ-WKSY-V4-P318": (
            ["右為末，煉蜜丸", "臨臥白湯送下", "並噙化嚥之"],
            ["上為末，煉蜜丸", "臨臥白湯下", "並噙化咽之"],
        ),
        "XJ-WKSY-V4-P319": (["普濟消毒飲"], ["普濟消毒散"]),
        "XJ-WKSY-V4-P320": (
            ["牛蒡子　馬勃", "右水煎服"],
            ["牛蒡子馬勃", "上水煎服"],
        ),
        "XJ-WKSY-V4-P323": (["右為末，用紙捻蘸少許"], ["上為末，用紙捻蘸少許"]),
        "XJ-WKSY-V4-P329": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P332": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P336": (
            ["升麻　川芎　當歸（各一錢半）"],
            ["升麻　川芎　當歸（各錢半）"],
        ),
        "XJ-WKSY-V4-P337": (["右水煎服。焮連太陽加羌活"], ["上水煎服。焮連太陽加羌活"]),
        "XJ-WKSY-V4-P340": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P343": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P348": (["右為末，蒸餅糊丸"], ["上為末，蒸餅糊丸"]),
        "XJ-WKSY-V4-P351": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P354": (["右水酒煎服"], ["上水酒煎服"]),
        "XJ-WKSY-V4-P357": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P358": (["加味龍膽瀉肝湯"], ["加味龍膽湯　"]),
        "XJ-WKSY-V4-P360": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P361": (["清心蓮心飲"], ["清心蓮心丸"]),
        "XJ-WKSY-V4-P363": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P366": (
            ["右用燈心三十根煎服"],
            ["上用燈心三十根", "燈心三十根，水煎服"],
        ),
        "XJ-WKSY-V4-P369": (["右為細末，每服五錢，水煎服"], ["上為細末"]),
        "XJ-WKSY-V4-P373": (["右為末，用紅棗肉同蜜為丸"], ["上為末，用紅棗肉同蜜為丸"]),
        "XJ-WKSY-V4-P376": (["右薑棗水煎服"], ["上薑、棗水煎服"]),
        "XJ-WKSY-V4-P379": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P382": (["右為末，每服二錢"], ["上為末，每服二錢"]),
        "XJ-WKSY-V4-P385": (["右為末，每服三錢"], ["上為末，每服三錢"]),
        "XJ-WKSY-V4-P386": (["升麻和氣飲"], ["升麻和氣湯"]),
        "XJ-WKSY-V4-P388": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P391": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P394": (["右水煎服，衣覆之，取微汗"], ["上水煎服，衣覆之"]),
        "XJ-WKSY-V4-P398": (["右水煎服"], ["上水煎服"]),
        "XJ-WKSY-V4-P401": (["右各別為末，酒糊丸"], ["上各別為末，酒糊丸"]),
        "XJ-WKSY-V4-P404": (
            ["右用麻油二斤", "煎至黑濾去查"],
            ["上用麻油二斤", "濾去粗"],
        ),
        "XJ-WKSY-V4-P409": (
            ["右鎔蠟和礬末", "治毒蛇咬，鎔滴傷處"],
            ["上熔蠟和礬末", "治毒蛇咬，熔滴傷處"],
        ),
        "XJ-WKSY-V4-P412": (
            ["右先用當歸、地黃", "入油煎黑去查"],
            ["上先用當歸、地黃", "煎黑去粗"],
        ),
        "XJ-WKSY-V4-P415": (["右水煎服"], ["上水煎服"]),
    }
    for source_id, (required_text, forbidden_text) in new_scan_corrections.items():
        if source_id not in record_index:
            errors.append(f"新增影像校勘记录缺失：{source_id}")
            continue
        record_meta, record_text = record_index[source_id]
        for fragment in required_text:
            if fragment not in record_text:
                errors.append(f"{source_id}: 新增校订正文缺少“{fragment}”")
        for fragment in forbidden_text:
            if fragment in record_text:
                errors.append(f"{source_id}: 新增校订正文回退为“{fragment}”")
        if not (record_meta.get("scan_source_url") or record_meta.get("secondary_scan_source_url")):
            errors.append(f"{source_id}: 缺少新增校勘影像頁連結")
        for field in (
            "collation_status",
            "original_public_transcription",
            "preferred_reading",
            "difference_grade",
        ):
            if not record_meta.get(field):
                errors.append(f"{source_id}: 缺少新增校勘字段 {field}")
        if record_meta.get("scan_verification_status") != "sampled_variants_found":
            errors.append(f"{source_id}: 新增校勘状态不符")

    for source_id in (
        "XJ-NKCZ-V2-P172",
        "XJ-NKCZ-V2-P177",
        "XJ-KCLY-H13-P117",
        "XJ-WKSY-V4-P160",
        "XJ-WKSY-V4-P168",
        "XJ-WKSY-V4-P213",
        "XJ-WKSY-V4-P215",
        "XJ-WKSY-V4-P201",
        "XJ-WKSY-V4-P225",
        "XJ-WKSY-V4-P228",
        "XJ-WKSY-V4-P244",
        "XJ-WKSY-V4-P243",
        "XJ-WKSY-V4-P245",
        "XJ-LZWKFH-V5-P184",
        "XJ-LZWKFH-V5-P185",
        "XJ-WKSY-V4-P272",
        "XJ-WKSY-V4-P273",
        "XJ-WKSY-V4-P286",
        "XJ-WKSY-V4-P295",
        "XJ-WKSY-V4-P301",
        "XJ-WKSY-V4-P306",
        "XJ-WKSY-V4-P317",
        "XJ-WKSY-V4-P319",
        "XJ-WKSY-V4-P320",
        "XJ-WKSY-V4-P336",
        "XJ-WKSY-V4-P358",
        "XJ-WKSY-V4-P361",
        "XJ-WKSY-V4-P366",
        "XJ-WKSY-V4-P386",
        "XJ-WKSY-V4-P404",
        "XJ-WKSY-V4-P412",
    ):
        record_meta, _ = record_index.get(source_id, ({}, ""))
        if not record_meta.get("retrieval_warning"):
            errors.append(f"{source_id}: B 级方药／服法校勘缺少检索警示")

    for source_id, public_reading, scan_reading in (
        ("XJ-WKSY-V4-P302", "神效栝蔞散", "神效瓜蔞散"),
        ("XJ-WKSY-V4-P303", "黃栝蔞", "黃瓜蔞"),
    ):
        record_meta, record_text = record_index.get(source_id, ({}, ""))
        if public_reading not in record_text:
            errors.append(f"{source_id}: 同藥異寫記錄未保留公開轉錄讀法")
        if record_meta.get("public_transcription_reading") != public_reading:
            errors.append(f"{source_id}: 同藥異寫缺少公開轉錄讀法字段")
        if record_meta.get("scan_reading") != scan_reading:
            errors.append(f"{source_id}: 同藥異寫缺少影像讀法字段")
        if record_meta.get("scan_verification_status") != "sampled_variants_found":
            errors.append(f"{source_id}: 同藥異寫影像狀態不符")
        for field in ("scan_source_url", "collation_status", "difference_grade", "retrieval_note"):
            if not record_meta.get(field):
                errors.append(f"{source_id}: 同藥異寫缺少字段 {field}")

    p320_meta, _ = record_index.get("XJ-WKSY-V4-P320", ({}, ""))
    if p320_meta.get("scan_glyph_variant") != "白殭蠶／白僵蠶":
        errors.append("XJ-WKSY-V4-P320: 未保留白殭蠶／白僵蠶同藥字形異文")

    p409_meta, _ = record_index.get("XJ-WKSY-V4-P409", ({}, ""))
    if p409_meta.get("scan_glyph_variant") != "熔／鎔":
        errors.append("XJ-WKSY-V4-P409: 未保留熔／鎔字形異文")
    if not p409_meta.get("retrieval_note"):
        errors.append("XJ-WKSY-V4-P409: 熔／鎔字形異文缺少檢索說明")

    p341_meta, p341_text = record_index.get("XJ-WKSY-V4-P341", ({}, ""))
    if "以致腫痛" not in p341_text:
        errors.append("XJ-WKSY-V4-P341: 未保留已由第二影像確認的『以致腫痛』")
    if p341_meta.get("scan_verification_status") != "sampled_variants_found":
        errors.append("XJ-WKSY-V4-P341: 第二影像定讀後影像狀態不符")
    if p341_meta.get("difference_grade") != "C_glyph_normalization_no_textual_correction":
        errors.append("XJ-WKSY-V4-P341: 瘇／腫字形差異未標為 C 級")
    for field in (
        "scan_source_url",
        "secondary_scan_source_url",
        "parallel_source_url",
        "parallel_repetition_url",
        "collation_status",
        "public_transcription_reading",
        "scan_initial_uncertain_reading",
        "resolved_reading",
        "retrieval_note",
    ):
        if not p341_meta.get(field):
            errors.append(f"XJ-WKSY-V4-P341: 第二影像定讀缺少字段 {field}")

    p314_meta, p314_text = record_index.get("XJ-WKSY-V4-P314", ({}, ""))
    p314_required_text = (
        "豬厭肉子（生於豚豬項下者，一枚如棗大，取四十九）",
        "珍珠（四十九粒，砂鍋內泥封口煨過）",
    )
    for required_text in p314_required_text:
        if required_text not in p314_text:
            errors.append(f"XJ-WKSY-V4-P314: 第二影像定讀缺少正文 {required_text}")
    if "取四十丸" in p314_text or "過絲" in p314_text:
        errors.append("XJ-WKSY-V4-P314: 已確認的公開轉錄訛文仍殘留在正文")
    if p314_meta.get("scan_verification_status") != "sampled_variants_found":
        errors.append("XJ-WKSY-V4-P314: 第二影像校正後影像狀態不符")
    if not p314_meta.get("difference_grade", "").startswith("B_"):
        errors.append("XJ-WKSY-V4-P314: 注文歸屬與數量錯誤未標為 B 級")
    for field in (
        "scan_source_url",
        "scan_source_url_continued",
        "secondary_scan_source_url",
        "parallel_source_url",
        "parallel_formula_source_url",
        "collation_status",
        "original_public_transcription",
        "preferred_reading",
        "collation_note",
        "retrieval_warning",
    ):
        if not p314_meta.get(field):
            errors.append(f"XJ-WKSY-V4-P314: 第二影像校正缺少字段 {field}")

    wksy_v4_records = [
        meta
        for source_id, (meta, _) in record_index.items()
        if source_id.startswith("XJ-WKSY-V4-P")
    ]
    wksy_v4_scan_counts = Counter(
        meta.get("scan_verification_status") for meta in wksy_v4_records
    )
    expected_wksy_v4_scan_counts = {
        "sampled_verified": 137,
        "sampled_variants_found": 101,
        "sampled_pending": 0,
    }
    for status, expected_count in expected_wksy_v4_scan_counts.items():
        actual_count = wksy_v4_scan_counts.get(status, 0)
        if actual_count != expected_count:
            errors.append(
                f"XJ-WKSY-V4: {status} 数量应为 {expected_count}，实际为 {actual_count}"
            )

    # “上／右” is a formula-instruction marker variant, not a medical-content error.
    # Keep both readings for textual fidelity, but enforce separate C0 reporting.
    wksy_instruction_marker_ids = []
    for source_id, (meta, _) in record_index.items():
        if not source_id.startswith("XJ-WKSY-V4-P"):
            continue
        public_reading = meta.get("original_public_transcription", "")
        scan_reading = meta.get("preferred_reading", "")
        if "上" in public_reading and "右" in scan_reading:
            wksy_instruction_marker_ids.append(source_id)
            if meta.get("scan_verification_status") != "sampled_variants_found":
                errors.append(f"{source_id}: 方后指令标记异文状态不符")
            if not meta.get("collation_status") or not meta.get("difference_grade"):
                errors.append(f"{source_id}: 方后指令标记异文缺少校勘字段")
    if len(wksy_instruction_marker_ids) != 80:
        errors.append(
            "XJ-WKSY-V4: C0 上／右方后指令标记异文应为 80 条，"
            f"实际为 {len(wksy_instruction_marker_ids)} 条"
        )
    for required_policy_text in (
        "C0 方後指令標記異文",
        "不計入藥名、劑量、治法或醫義錯誤",
        "結構層等義歸一",
    ):
        if required_policy_text not in text:
            errors.append(f"方后指令标记政策缺少：{required_policy_text}")
    if "上／右”誤轉" in text:
        errors.append("报告仍将上／右方后指令标记写作误转")
    if any(meta.get("difference_grade", "").startswith("D_") for meta in wksy_v4_records):
        errors.append("XJ-WKSY-V4: 第二影像覆核后仍残留 D 级记录")

    # Sampled matches must retain page-level evidence and must not be promoted to full verification.
    for source_id in (
        "XJ-NKZY-V2-P113",
        "XJ-NKZY-V2-P116",
        "XJ-NKZY-V2-P119",
        "XJ-LYJY-V1-P001",
        "XJ-LYJY-V1-P002",
        "XJ-LYJY-V2-P026",
        "XJ-LYJY-V2-P027",
        "XJ-LYJY-V2-P028",
        "XJ-ZTLY-V2-P109",
        "XJ-LZWKFH-V5-P179",
        "XJ-LZWKFH-V5-P180",
        "XJ-LZWKFH-V5-P181",
        "XJ-LZWKFH-V5-P182",
        "XJ-LZWKFH-V5-P186",
        "XJ-LZWKFH-V5-P187",
        "XJ-LZWKFH-V5-P188",
        "XJ-LZWKFH-V5-P189",
        "XJ-LZWKFH-V5-P190",
        "XJ-LZWKFH-V5-P191",
        "XJ-LZWKFH-V5-P192",
        "XJ-LZWKFH-V5-P193",
        "XJ-LZWKFH-V5-P194",
        "XJ-LZWKFH-V5-P195",
        "XJ-LZWKFH-V5-P196",
        "XJ-LZWKFH-V5-P197",
        "XJ-LZWKFH-V5-P198",
        "XJ-LZWKFH-V5-P199",
        "XJ-LZWKFH-V5-P200",
        "XJ-LZWKFH-V5-P201",
        "XJ-LZWKFH-V5-P202",
        "XJ-LZWKFH-V5-P203",
        "XJ-LZWKFH-V5-P204",
        "XJ-WKSY-V4-P162",
        "XJ-WKSY-V4-P163",
        "XJ-WKSY-V4-P165",
        "XJ-WKSY-V4-P166",
        "XJ-WKSY-V4-P169",
        "XJ-WKSY-V4-P170",
        "XJ-WKSY-V4-P172",
        "XJ-WKSY-V4-P173",
        "XJ-WKSY-V4-P174",
        "XJ-WKSY-V4-P175",
        "XJ-WKSY-V4-P176",
        "XJ-WKSY-V4-P177",
        "XJ-WKSY-V4-P180",
        "XJ-WKSY-V4-P183",
        "XJ-WKSY-V4-P185",
        "XJ-WKSY-V4-P186",
        "XJ-WKSY-V4-P188",
        "XJ-WKSY-V4-P189",
        "XJ-WKSY-V4-P190",
        "XJ-WKSY-V4-P192",
        "XJ-WKSY-V4-P193",
        "XJ-WKSY-V4-P195",
        "XJ-WKSY-V4-P196",
        "XJ-WKSY-V4-P198",
        "XJ-WKSY-V4-P199",
        "XJ-WKSY-V4-P202",
        "XJ-WKSY-V4-P204",
        "XJ-WKSY-V4-P205",
        "XJ-WKSY-V4-P207",
        "XJ-WKSY-V4-P208",
        "XJ-WKSY-V4-P210",
        "XJ-WKSY-V4-P214",
        "XJ-WKSY-V4-P217",
        "XJ-WKSY-V4-P218",
        "XJ-WKSY-V4-P220",
        "XJ-WKSY-V4-P221",
        "XJ-WKSY-V4-P223",
        "XJ-WKSY-V4-P224",
        "XJ-WKSY-V4-P226",
        "XJ-WKSY-V4-P227",
        "XJ-WKSY-V4-P229",
        "XJ-WKSY-V4-P230",
        "XJ-WKSY-V4-P235",
        "XJ-WKSY-V4-P236",
        "XJ-WKSY-V4-P238",
        "XJ-WKSY-V4-P239",
        "XJ-WKSY-V4-P241",
        "XJ-WKSY-V4-P242",
        "XJ-WKSY-V4-P265",
        "XJ-WKSY-V4-P266",
        "XJ-WKSY-V4-P268",
        "XJ-WKSY-V4-P269",
        "XJ-WKSY-V4-P271",
        "XJ-WKSY-V4-P274",
        "XJ-WKSY-V4-P275",
        "XJ-WKSY-V4-P277",
        "XJ-WKSY-V4-P278",
        "XJ-WKSY-V4-P280",
        "XJ-WKSY-V4-P281",
        "XJ-WKSY-V4-P283",
        "XJ-WKSY-V4-P285",
        "XJ-WKSY-V4-P287",
        "XJ-WKSY-V4-P288",
        "XJ-WKSY-V4-P290",
        "XJ-WKSY-V4-P291",
        "XJ-WKSY-V4-P293",
        "XJ-WKSY-V4-P294",
        "XJ-WKSY-V4-P296",
        "XJ-WKSY-V4-P297",
        "XJ-WKSY-V4-P299",
        "XJ-WKSY-V4-P300",
        "XJ-WKSY-V4-P305",
        "XJ-WKSY-V4-P307",
        "XJ-WKSY-V4-P308",
        "XJ-WKSY-V4-P310",
        "XJ-WKSY-V4-P311",
        "XJ-WKSY-V4-P313",
        "XJ-WKSY-V4-P316",
        "XJ-WKSY-V4-P321",
        "XJ-WKSY-V4-P322",
        "XJ-WKSY-V4-P324",
        "XJ-WKSY-V4-P327",
        "XJ-WKSY-V4-P328",
        "XJ-WKSY-V4-P330",
        "XJ-WKSY-V4-P331",
        "XJ-WKSY-V4-P333",
        "XJ-WKSY-V4-P335",
        "XJ-WKSY-V4-P338",
        "XJ-WKSY-V4-P339",
        "XJ-WKSY-V4-P342",
        "XJ-WKSY-V4-P346",
        "XJ-WKSY-V4-P347",
        "XJ-WKSY-V4-P349",
        "XJ-WKSY-V4-P350",
        "XJ-WKSY-V4-P352",
        "XJ-WKSY-V4-P353",
        "XJ-WKSY-V4-P355",
        "XJ-WKSY-V4-P356",
        "XJ-WKSY-V4-P359",
        "XJ-WKSY-V4-P362",
        "XJ-WKSY-V4-P364",
        "XJ-WKSY-V4-P365",
        "XJ-WKSY-V4-P367",
        "XJ-WKSY-V4-P368",
        "XJ-WKSY-V4-P370",
        "XJ-WKSY-V4-P371",
        "XJ-WKSY-V4-P372",
        "XJ-WKSY-V4-P374",
        "XJ-WKSY-V4-P375",
        "XJ-WKSY-V4-P377",
        "XJ-WKSY-V4-P378",
        "XJ-WKSY-V4-P380",
        "XJ-WKSY-V4-P381",
        "XJ-WKSY-V4-P383",
        "XJ-WKSY-V4-P384",
        "XJ-WKSY-V4-P387",
        "XJ-WKSY-V4-P389",
        "XJ-WKSY-V4-P390",
        "XJ-WKSY-V4-P392",
        "XJ-WKSY-V4-P393",
        "XJ-WKSY-V4-P395",
        "XJ-WKSY-V4-P396",
        "XJ-WKSY-V4-P397",
        "XJ-WKSY-V4-P399",
        "XJ-WKSY-V4-P400",
        "XJ-WKSY-V4-P402",
        "XJ-WKSY-V4-P403",
        "XJ-WKSY-V4-P405",
        "XJ-WKSY-V4-P406",
        "XJ-WKSY-V4-P407",
        "XJ-WKSY-V4-P408",
        "XJ-WKSY-V4-P410",
        "XJ-WKSY-V4-P411",
        "XJ-WKSY-V4-P413",
        "XJ-WKSY-V4-P414",
    ):
        if source_id not in record_index:
            errors.append(f"影像抽樣記錄缺失：{source_id}")
            continue
        record_meta, _ = record_index[source_id]
        if record_meta.get("scan_verification_status") != "sampled_verified":
            errors.append(f"{source_id}: 抽樣相合狀態不符")
        if not (record_meta.get("scan_source_url") or record_meta.get("secondary_scan_source_url")):
            errors.append(f"{source_id}: 缺少館藏影像頁連結")

    # BYCY risk-directed samples: three cases and two formula groups must retain
    # page-level evidence, while the endpoint differences remain explicit variants.
    bycy_verified_ids = [
        *(f"XJ-BYCY-V5-L{number:04d}" for number in range(521, 530)),
        *(f"XJ-BYCY-V5-L{number:04d}" for number in range(1121, 1133)),
    ]
    for source_id in bycy_verified_ids:
        if source_id not in record_index:
            errors.append(f"《保嬰粹要》影像抽樣記錄缺失：{source_id}")
            continue
        record_meta, _ = record_index[source_id]
        if record_meta.get("scan_verification_status") != "sampled_verified":
            errors.append(f"{source_id}: 《保嬰粹要》抽樣相合狀態不符")
        for field in ("scan_source_url", "parallel_edition_status"):
            if not record_meta.get(field):
                errors.append(f"{source_id}: 缺少《保嬰粹要》抽樣字段 {field}")

    for source_id in (f"XJ-BYCY-V5-L{number:04d}" for number in range(1133, 1140)):
        if source_id not in record_index:
            errors.append(f"《保嬰粹要》卷末校勘記錄缺失：{source_id}")
            continue
        record_meta, _ = record_index[source_id]
        if record_meta.get("scan_verification_status") != "sampled_variants_found":
            errors.append(f"{source_id}: 《保嬰粹要》卷末異文狀態不符")
        for field in ("scan_source_url", "early_edition_variant", "difference_grade"):
            if not record_meta.get(field):
                errors.append(f"{source_id}: 缺少《保嬰粹要》卷末異文字段 {field}")

    lyjy_p018_meta, _ = record_index.get("XJ-LYJY-V3-P018", ({}, ""))
    if "not_confirmed_as_edition_variant" not in lyjy_p018_meta.get("collation_status", ""):
        errors.append("XJ-LYJY-V3-P018: 未保留“影像未核、非版本定論”的校勘狀態")
    if not lyjy_p018_meta.get("difference_grade", "").startswith("D_WYG_image_unavailable"):
        errors.append("XJ-LYJY-V3-P018: 四庫卷十九影像缺失未標為 D 級")
    if "轉錄疑點" not in lyjy_p018_meta.get("retrieval_warning", ""):
        errors.append("XJ-LYJY-V3-P018: 檢索警示未明示為轉錄疑點")

    # 2026-09-30: the two paragraphs once judged cross-work contamination are the 當歸川芎散 formula that the 承應 print
    # places between 柴胡清肝散 and 小柴胡湯; they are restored as added records P222/P223.
    for source_id in ("XJ-LYJY-V3-P222", "XJ-LYJY-V3-P223"):
        if source_id not in record_index:
            errors.append(f"{source_id}: 當歸川芎散補入記錄缺失")
        elif not record_index[source_id][0].get("record_added_status"):
            errors.append(f"{source_id}: 缺少 record_added_status")
    for audit_fragment in (
        "跨書誤收審計記錄",
        "四庫《薛氏醫案》卷四十八公開文本",
        "原網頁誤接段一：當歸川芎散",
    ):
        if audit_fragment not in text:
            errors.append(f"《癘瘍機要》跨書誤收缺少審計證據：{audit_fragment}")

    for source_id in ("XJ-WKSY-V4-P416", "XJ-WKSY-V4-P417"):
        if source_id not in record_index:
            errors.append(f"卷末补文缺失：{source_id}")
            continue
        record_meta, _ = record_index[source_id]
        if record_meta.get("omission_status") != "confirmed_web_transcription_omission_restored":
            errors.append(f"{source_id}: 卷末漏文修复状态不符")
        if not record_meta.get("difference_grade", "").startswith("A_"):
            errors.append(f"{source_id}: 卷末漏文未标为 A 级")

    report["summary"] = {
        "works": len(section_by_work),
        "records": len(all_ids),
        "duplicate_source_ids": len(duplicates),
        "errors": len(errors),
        "warnings": len(warnings),
    }
    report["errors"] = errors
    report["warnings"] = warnings
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
