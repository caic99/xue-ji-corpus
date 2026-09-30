"""Render model-reviewed boundaries and verbatim labels for one complete chapter.

All annotations below were read against the complete chapter. Rendering checks
every quoted field and every source character; it does not infer clinical facts.
"""
from audit_corpus import CORPUS, books, parse_metadata, text_digest
import json
import re

BEGIN = '<!-- NKZY_CHAPTER_ONE_CASES_BEGIN -->'
END = '<!-- NKZY_CHAPTER_ONE_CASES_END -->'
CHAPTER = '一、元氣虧損內傷外感等症'

# Paragraph, patient, symptoms, mechanism, treatment, formula, individual outcome.
# Empty fields mean not individually stated, rather than inferred absence.
LABELS = [
 (1,'車駕王用之','卒中昏憒，口眼喎斜，痰氣上湧，咽喉有聲，六脈沉伏','此真氣虛而風邪所乘','以三生飲一兩，加人參一兩，煎服即甦。','三生飲一兩，加人參一兩','煎服即甦'),
 (2,'州判蔣大用','形體魁偉，中滿吐痰，勞則頭暈','中滿者，脾氣虧損也；痰盛者，脾氣不能運也；頭暈者，脾氣不能升也；指麻者，脾氣不能周也','遂以補中益氣加茯苓、半夏以補脾土，用八味地黃以補土母而愈。','補中益氣加茯苓、半夏','以致大便不禁，飲食不進而歿'),
 (3,'一男子','卒中，口眼喎斜，不能言語，遇風寒四肢拘急，脈浮而緊','此手足陽明經虛，風寒所乘','用秦艽升麻湯治之，稍愈，乃以補中益氣加山梔而痊。','秦艽升麻湯','乃以補中益氣加山梔而痊'),
 (4,'一男子','體肥善飲，舌本硬強，語言不清，口眼喎斜，痰氣湧盛，肢體不遂','脾虛濕熱','用六君加煨葛根、山梔、神麯而痊。','六君加煨葛根、山梔、神麯','而痊'),
 (5,'吾師僉憲高如齋','兩腿逸則痿軟而無力，勞則作痛如針刺，脈洪數而有力','此肝腎陰虛火盛，而致痿軟無力，真病之形，作痛如錐，邪火之象也','用壯水益腎之劑而愈。','','用壯水益腎之劑而愈'),
 (6,'大尹劉孟春','素有痰，兩臂作麻，兩目流淚','麻屬氣盛，因前藥而復傷肝，火盛而筋攣耳','遂用六味地黃丸、補中益氣湯，不三月而痊。','六味地黃丸、補中益氣湯','不三月而痊'),
 (7,'一儒者','素勤苦，惡風寒，鼻塞流清涕，寒禁嚏噴','此脾肺氣虛不能實腠理','遂以補中益氣加麥門、五味治之而愈。','補中益氣加麥門、五味','治之而愈'),
 (8,'外舅','年六十餘，素善飲，兩臂作痛','臂麻體軟，脾無用也；痰涎自出，脾不能攝也；口斜語澀，脾氣傷也；頭目暈重，脾氣不能升也；癢起白屑，脾氣不能營也','遂用補中益氣加神麯、半夏、茯苓三十餘劑，諸症悉退，又用參朮煎膏治之而愈。','補中益氣加神麯、半夏、茯苓','諸症悉退，又用參朮煎膏治之而愈'),
 (9,'秀才劉允功','形體魁偉，不慎酒色，因勞怒頭暈仆地，痰涎上湧，手足麻痹，口乾引飲，六脈洪數而虛','腎經虧損，不能納氣歸源而頭暈；不能攝水歸源而為痰；陽氣虛熱而麻痹；虛火上炎而作渴','用補中益氣合六味丸料治之而愈。','補中益氣合六味丸料','其後或勞役或入房，其病即作，用前藥隨愈'),
 (10,'憲幕顧斐齋','飲食起居失宜，左半身並乎不遂，汗出神昏，痰涎上湧','','余朝用補中益氣加黃柏、知母、麥門、五味煎送地黃丸，晚用地黃丸料加黃柏、知母數劑，諸症悉退。','補中益氣加黃柏、知母、麥門、五味煎送地黃丸','但自弛禁，不能痊愈耳'),
 (11,'庠生陳時用','素勤苦，因勞怒口斜痰盛，脈滑數而虛','此勞傷中氣，怒動肝火','用補中益氣加山梔、茯苓、半夏、桔梗，數劑而愈。','補中益氣加山梔、茯苓、半夏、桔梗','數劑而愈'),
 (12,'錦衣楊永興','形體豐厚，筋骨軟痛，痰盛作渴，喜飲冷水','脾腎俱虛','用補中益氣湯、加減八味丸，三月餘而痊。','補中益氣湯、加減八味丸','三月餘而痊。以後連生七子，壽逾七旬'),
 (13,'先母','七十有五，遍身作痛，筋骨尤甚，不能伸屈，口乾目赤，頭暈痰壅，胸膈不利，小便短赤，夜間殊甚，遍身作癢如蟲行','','用六味地黃丸料加山梔、柴胡治之，諸症悉愈。','六味地黃丸料加山梔、柴胡','諸症悉愈'),
 (13,'一男子','時瘡愈後，遍身作痛','風客淫氣','以地黃丸而愈。','地黃丸','而愈'),
 (14,'一老人','兩臂不遂，語言蹇澀','此風藥虧損肝血，益增其病也','余用八珍湯補其氣血，用地黃丸補其腎水，佐以愈風丹而愈。','八珍湯','佐以愈風丹而愈'),
 (15,'一婦人','因怒吐痰，胸滿作痛','鬱怒傷脾肝，氣血復損而然','遂用逍遙散、補中益氣湯、六味地黃丸調治。','逍遙散、補中益氣湯、六味地黃丸','年餘悉愈，形體康健'),
 (16,'一婦人','脾胃虛弱，飲食素少，忽痰湧氣喘，頭搖目札，手揚足擲，難以候脈，視其面色，黃中見青','此肝木乘脾土','用六君加柴胡、升麻治之而蘇，更以補中益氣加半夏調理而痊。','六君加柴胡、升麻','更以補中益氣加半夏調理而痊'),
 (17,'一婦人','懷抱鬱結，筋攣骨痛，喉間似有一核','鬱火傷脾血燥生風所致','用加味歸脾湯二十餘劑，形體漸健，飲食漸加，又服加味逍遙散十餘劑，痰熱少退，喉核少利，更用升陽益胃湯數劑，諸症漸愈，但臂不能伸，此肝經血少，用地黃丸而愈。','加味歸脾湯','此肝經血少，用地黃丸而愈'),
 (18,'一產婦','筋攣臂軟，肌肉掣動','此氣血俱虛而有熱','用十全大補湯而痊。其後因怒而復作，用加味逍遙散而愈。','十全大補湯','其後因怒而復作，用加味逍遙散而愈'),
 (19,'一產婦','兩手麻木','此氣血俱虛','用十全大補加炮姜數劑，諸症悉退，卻去炮姜又數劑而愈。但有內熱，用加味逍遙散數劑而痊。','十全大補加炮姜','用加味逍遙散數劑而痊'),
 (20,'一男子','善飲，舌本強硬，語言不清','此脾虛濕熱','當用補中益氣加神麯、麥芽、乾葛、澤瀉治之。','補中益氣加神麯、麥芽、乾葛、澤瀉',''),
 (21,'一婦人','善怒，舌本強，手臂麻','舌本屬土，被木剋制故耳','當用六君加柴胡、芍藥治之。','六君加柴胡、芍藥',''),
 (22,'一男子','舌下牽強，手大指次指不仁，或大便秘結，或皮膚赤暈','此大腸血虛風熱','當用逍遙散加槐角、秦艽治之。','逍遙散加槐角、秦艽',''),
 (23,'一男子','足痿軟，日晡熱','此足三陰虛','當用六味、滋腎二丸補之。','六味、滋腎二丸',''),
 (24,'一婦人','腿足無力，勞則倦怠','四肢者土也，此屬脾虛','當用補中益氣及還少丹主之。','補中益氣及還少丹',''),
]

# Explicit case/comment boundaries, reviewed from the source paragraph.
TAILS = {1:'若遺尿手撒',2:'愚謂預防之理',3:'若舌喑不能言',
         5:'竊謂前症',12:'《外科精要》云',24:'俱不從余言'}


def yaml(meta):
    return '\n'.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k,v in meta.items())


def main():
    old = CORPUS.read_text()
    original = books(old)
    digest = text_digest(original)
    book = next(b for b in original if b['meta']['work_id']=='XJ-NKZY')
    rows = {int(r['meta']['source_id'].rsplit('P',1)[1]):r
            for r in book['rows'] if r['meta']['volume']=='卷上' and r['meta']['section']==CHAPTER}
    if sorted(rows)!=list(range(1,25)):
        raise ValueError('Full chapter source range must be P001–P024')
    segments = {}
    for n,row in rows.items():
        body=row['body']
        if n==13:
            cut=body.index('一男子時瘡愈後')
            segments[n]=[(0,cut,'case'),(cut,len(body),'case')]
        elif n in TAILS:
            cut=body.index(TAILS[n])
            kind='collective_outcome_note' if n==24 else 'author_commentary'
            segments[n]=[(0,cut,'case'),(cut,len(body),kind)]
        else:
            segments[n]=[(0,len(body),'case')]
    rendered=[BEGIN,'## 《內科摘要》卷上第一篇：全篇醫案結構化（2026-09-28）','',
              '完整覆蓋 `P001–P024` 的 24 段：25 個個別患者敘事、5 個案後評論片段、1 個共同轉歸片段。每個字符都由下列單元覆蓋，原文依現有校訂工作稿照錄。原始來源仍在正文區與當前快照；本節為模型據全文覆核的結構標注，未經人工逐字影像覆核。字段為原文摘引，空值表示原文未個別明載。方藥字段只摘錄一個直接可核的片段，完整病程與全部方藥以原文為準；不把摘引當作完整治療清單。','',
              'P013 明確含先母與一男子兩案。P010 有王竹西與薛己兩位診治者。P020–P024 使用「當用」，不能標作已服該方；P024 段末的「俱」屬共同轉歸，所指案群需核，五案暂列待核並保留個別轉歸空值。P005 的「吾師」照錄，不據此認定醫學師承。','']
    coverage={n:[] for n in rows}
    occurrences={}
    for n,person,symptom,mechanism,treatment,formula,outcome in LABELS:
        occurrences[n]=occurrences.get(n,0)+1
        ordinal=occurrences[n]
        start,end,_=[s for s in segments[n] if s[2]=='case'][ordinal-1]
        body=rows[n]['body'][start:end]
        m=rows[n]['meta'];sid=m['source_id'];cid=f'XJ-NKZY-C-V1-P{n:03d}-{ordinal}'
        for field in (person,symptom,mechanism,treatment,formula,outcome):
            if field and field not in body:
                raise ValueError(f'{cid}: quote does not occur in exact case text: {field}')
        meta={'case_id':cid,'work_ref':'XJ-NKZY','source_ref':sid,
              'source_start_char':start,'source_end_char_exclusive':end,
              'source_location':m['source_location'],'person_quote':person,
              'original_case_author':'薛己（所在自著敘事；親診角色另見原文）',
              'treating_person_refs':'王竹西；余' if n==10 else '余' if '余' in body else '',
              'annotation_author':'未另署；不推定所有原刻小字皆薛己自注',
              'text_layer':'case_from_working_transcription',
              'symptoms_quote':symptom,'mechanism_quote':mechanism,
              'treatment_quote':treatment,'formula_quote':formula,'outcome_quote':outcome,
              'treatment_record_status':'proposed_not_individually_documented_as_administered' if n>=20 else 'narrated_management',
              'boundary_status':'model_reviewed_against_full_chapter',
              'scan_verification_status':m['scan_verification_status'],
              'rights_status':m['rights_status'],'source_url':m['source_url'],
              'retrieval_status':'needs_review' if n>=20 or m.get('retrieval_status')=='needs_review' else 'source_research_with_caveats',
              'annotation_date':'2026-09-28'}
        rendered += [f'### {cid}','', '```yaml',yaml(meta),'```','',body,'']
        coverage[n].append((start,end))
    unit_count=0
    for n,parts in segments.items():
        for start,end,kind in parts:
            if kind=='case':continue
            unit_count+=1
            sid=rows[n]['meta']['source_id']
            meta={'text_unit_id':f'XJ-NKZY-U-V1-P{n:03d}',
                  'source_ref':sid,'source_start_char':start,'source_end_char_exclusive':end,
                  'unit_kind':kind,'author_attribution':'薛己敘事中的評論／引用；被引書另行署名',
                  'review_status':'scope_pending' if n==24 else 'model_boundary_reviewed',
                  'retrieval_status':'needs_review' if n==24 else 'source_research_with_caveats'}
            if n==24:meta['candidate_scope']='P020–P024；共同轉歸指涉需核'
            rendered += [f'### {meta["text_unit_id"]}','', '```yaml',yaml(meta),'```','',rows[n]['body'][start:end],'']
            coverage[n].append((start,end))
    for n,spans in coverage.items():
        cursor=0
        for start,end in sorted(spans):
            if start!=cursor:raise ValueError(f'Coverage gap/overlap in P{n:03d}')
            cursor=end
        if cursor!=len(rows[n]['body']):raise ValueError('Incomplete paragraph coverage')
    rendered += ['### 本篇覆蓋驗收','',
                 '```yaml',yaml({'coverage_id':'XJ-NKZY-V1-CH1','source_prefix':'XJ-NKZY-V1-P','first_source_number':1,'last_source_number':24,'coverage_status':'complete_against_working_transcription'}),'```','',
                 '24 段逐字符覆蓋無缺口、無重疊；25 個 case_id 唯一；所有字段摘引均可在各自原案範圍內精確找到；6 個非個別醫案片段完整保留。這只完成第一篇，整部《內科摘要》其餘 520 條來源記錄仍待結構化。','',END]
    section='\n'.join(rendered)
    if BEGIN in old:
        updated=re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),lambda _:section,old,flags=re.S)
    else:
        at=old.index('\n> 這是目前唯一')
        updated=old[:at]+'\n'+section+'\n\n---\n'+old[at:]
    if text_digest(books(updated))!=digest:
        raise ValueError('Refusing to rewrite source records')
    CORPUS.write_text(updated)
    print(json.dumps({'source_paragraphs':24,'cases':len(LABELS),'other_units':unit_count,
                      'character_coverage':'complete','remaining_nkzy_records':520},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
