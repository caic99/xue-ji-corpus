"""Render reviewed full-chapter annotations for NKZY volume one chapters 2–6."""
from audit_corpus import CORPUS, books, text_digest, validate_structured_units
from structure_nkzy_chapter import yaml
import json
import re

BEGIN = '<!-- NKZY_CHAPTERS_TWO_TO_SIX_CASES_BEGIN -->'
END = '<!-- NKZY_CHAPTERS_TWO_TO_SIX_CASES_END -->'

# Each quotation is checked inside the exact individual case span.
# n, patient, symptom excerpt, mechanism excerpt, treatment excerpt, outcome excerpt.
LABELS = [
 (25,'進士王汝和','因勞役失於調養，忽然昏憒','此元氣虛火妄動，挾痰而作','又以十全大補湯加五味、麥門治之而安。','治之而安'),
 (26,'光祿高署丞','脾胃素虛，因飲食勞倦，腹痛胸痞','此因胃虛五臟虧損，虛症發見','用六君子加炮姜四劑而安。','服補胃之劑，諸症悉退'),
 (27,'大尹徐克明','因飲食失宜，日晡發熱，口乾體倦，小便赤澀，兩腿痠痛','','又用八珍湯調補而愈。','又用八珍湯調補而愈'),
 (30,'一男子','每遇勞役，食少胸痞，發熱頭痛，吐痰作渴，脈浮大','此脾胃血虛病也，脾屬土，為至陰而生血，故曰陰虛','余先用六君加炮姜，痛嘔漸愈；又用補中益氣痊愈。','又用補中益氣痊愈'),
 (31,'秀才劉貫卿','勞役失宜，飲食失節，肢體倦怠，發熱作渴，頭痛惡寒','','余用補中益氣加薑、桂、麥門、五味，補之而愈。','補之而愈'),
 (32,'黃武選','飲食勞倦，發熱惡寒','','余欲用補中益氣之劑，不從而歿。','不從而歿'),
 (33,'一儒者','素勤苦，因飲食失節，大便下血，或赤或黯','此思傷心脾，不能攝血歸源','乃午前用歸脾加麥門、五味以補心脾之血，收耗散之液，不兩月而諸症悉愈。','不兩月而諸症悉愈'),
 (34,'馬生','發熱煩渴，時或頭痛','此勞傷元氣，誤汗所致','遂與十全大補加附子一錢，服之熟睡','再劑而痊'),
 (36,'一儒者','日晡兩目緊澀不能瞻視','此元氣下陷','用補中益氣倍加參、耆數劑痊愈。','數劑痊愈'),
 (37,'一男子','患症同前','此脾氣虛不能統血，肝氣虛不能藏血','用補中益氣、六味地黃以補肝脾生腎水，諸症漸愈。','諸症漸愈'),
 (38,'一男子','飲食勞倦，而發寒熱，右手麻木','此脾胃之氣虛也','遂用補中益氣及溫和之藥煎漬湯手而愈。','而愈'),
 (39,'一儒者','足重墜微腫痛','此是脾氣虛弱下陷','用十全大補湯而愈。','而愈'),
 (40,'余','久則倦怠','此勞傷元氣，陰火乘虛下注','必服補中益氣加麥門、五味、酒炒黑黃柏少許','每至午前諸齒並肢體方得稍健，午後仍脹'),
 (42,'唐儀部','胸內作痛，月餘腹亦痛，左關弦長，右關弦緊','此脾虛肝邪所乘','以補中益氣加半夏、木香二劑而愈，又用六君子湯二劑而安。','又用六君子湯二劑而安'),
 (43,'儀部李北川','肚腹作痛，胸脅作脹，嘔吐不食，肝脈弦緊','此脾氣虛弱，肝火所乘','仍用前湯吞左金丸，一服而愈。','一服而愈'),
 (44,'太守朱陽山','因怒腹痛作瀉','此肝木乘脾土','用小柴胡加山梔、炮薑、茯苓、陳皮、制黃連，一劑而愈。','一劑而愈'),
 (45,'陽山之內','素善怒，胸膈不利，吐痰甚多，吞酸噯腐，飲食少思，手足發熱','此屬肝火血燥，木乘土位','余用六君加薑桂一鍾即睡，覺而諸症如失，又數劑而康。','又數劑而康'),
 (46,'儒者沈尼文','內停飲食，外感風寒，頭痛發熱，噁心腹痛','此客寒乘虛而作也','乃以香砂六君加木香、炮姜','又加黃耆、當歸，少佐升麻而愈'),
 (47,'府庠徐道夫母','胃脘當心痛劇，右寸關俱無，左雖有，微而似絕，手足厥冷','此脾虛肝木所勝','用參、朮、茯苓、陳皮、甘草補其中氣','諸病悉愈'),
 (48,'一婦人','懷抱鬱結，不時心腹作痛，年餘不愈，諸藥不應','','余用歸脾加炒山梔而愈。','而愈'),
 (49,'譚侍御','但頭痛即吐清水，不拘冬夏，吃薑便止，已三年矣','中氣虛寒','用六君加當歸、黃耆、木香、炮姜而瘥。','而瘥'),
 (50,'一儒者','四時喜極熱飲食，或吞酸噯腐，或大便不實，足指縫濕癢','此脾氣虛寒下陷','用前藥加附子錢許，數劑不再發。','數劑不再發'),
 (51,'一男子','形體倦怠，飲食適可，足指縫濕癢，行坐久則重墜','此脾胃氣虛而下陷','用補中益氣加茯苓、半夏而愈。','而愈'),
 (52,'一男子','食少胸滿，手足逆冷，飲食畏寒，發熱吐痰，時欲作嘔','此脾胃虛寒無火之症','遂用八味丸補火以生土，用補中益氣加薑、桂培養中宮，生髮陽氣尋愈。','尋愈'),
 (53,'一男子','每勞肢體時痛','此陽氣虛寒','用補中益氣加附子一錢、人參五錢，腫痛悉愈，又以十全大補百餘劑而康。','又以十全大補百餘劑而康'),
 (54,'家母','年四十有二','此脾虛不能約制，故涎自出也','後投以參、術等藥溫補脾胃，五十餘劑而愈。','五十餘劑而愈'),
 (56,'廷評張汝翰','胸膈作痞，飲食難化','脾胃虛寒','遂用八味丸補命門火，不月而飲食進，三月而形體充。','三月而形體充'),
 (57,'一儒者','雖盛暑喜燃火，四肢常欲沸湯漬之，面赤吐痰','食入反出，乃脾胃虛寒','用八味丸及十全大補加炮姜漸愈，不月平復。','不月平復'),
 (58,'一婦人','飲食無過碗許，非大便不實，必吞酸噯腐','此脾胃虛弱，末傳寒中','用益氣湯八味丸兩月，諸症悉愈。','諸症悉愈'),
 (58,'佐','坐立久則左足麻木，雖夏月足寒如冰','乃命門火衰不能生土，土虛寒使之然也','可服八味丸則愈。予亦敬服，果驗。','予亦敬服，果驗'),
 (59,'光祿鄺子涇','面白神勞，食少難化','此脾土虛寒之症','法當補土之母','以致不起'),
 (60,'羅工部','仲夏腹惡寒而外惡熱，鼻吸氣而腹覺冷，體畏風而惡寒','熱之不熱，是無火也','當用八味丸壯火之源，以消陰翳。','彼反服四物、玄參之類而歿'),
 (61,'工部陳禪亭','發熱有痰','此命門火衰，不能生土而脾病','當補火以生土，或可愈也。','辭不治'),
 (62,'林二守','不時昏憒','此陽虛之症也','當用參附湯治之','神思如故，其脈頓斂'),
 (63,'大尹沈用之','不時發熱，日飲冰水數碗','','法當補腎，用加減八味丸，不月而愈。','不月而愈'),
 (64,'通安橋顧大有父','年七十有九','此腎經虛火遊行於外','投以十全大補加山茱、澤瀉、丹皮、山藥、麥門、五味、附子。','後畏冷物而痊'),
 (65,'下堡顧仁成','年六十有一，痢後入房，精滑自遺','此屬無火虛熱','急與十全大補加山藥、山茱、丹皮、附子。','一劑諸症頓愈而痊'),
 (66,'一儒者','口乾，發熱，小便頻濁，大便秘結，盜汗，夢遺','','用十全大補湯及前丸兼服，月餘悉愈。','月餘悉愈'),
 (67,'州同韓用之','年四十有六，時仲夏，色欲過度，煩熱作渴','此腎陰虛，陽無所附而發於外，非火也','急用十全大補湯數劑方應。','急用十全大補湯數劑方應'),
 (68,'舉人陳履賢','色欲過度，丁酉孟冬發熱無時，飲水不絕，遺精不止，小便淋瀝','','余朝用四君為主，佐以熟地、當歸，夕用加減八味丸','乃服四物、黃柏、知母而歿'),
 (69,'吳江晚生沈察','僕年二十有六，所稟虛弱，兼之勞心','此症乃腎經虧損，火不歸經','遂用補中益氣及六味地黃而愈。','果歿於京'),
]

TAILS={25:'凡人元氣素弱',41:'觀此，可知',44:'（制黃連',
       56:'此症若不用前丸',61:'經云：',62:'竊觀仲景',65:'此等元氣'}
FULL_UNITS={28:'author_commentary',29:'author_commentary',35:'author_commentary',55:'signed_testimony_colophon'}
CHAPTER_RANGES=[(25,41),(42,48),(49,55),(56,62),(63,69)]


def main():
    old=CORPUS.read_text()
    original=books(old)
    digest=text_digest(original)
    book=next(b for b in original if b['meta']['work_id']=='XJ-NKZY')
    rows={int(r['meta']['source_id'].rsplit('P',1)[1]):r for r in book['rows']
          if r['meta']['volume']=='卷上' and 25<=int(r['meta']['source_id'].rsplit('P',1)[1])<=69}
    if sorted(rows)!=list(range(25,70)):raise ValueError('Full chapter range missing')
    segments={}
    for n,r in rows.items():
        body=r['body']
        if n in FULL_UNITS:segments[n]=[(0,len(body),FULL_UNITS[n])]
        elif n in TAILS:
            cut=body.index(TAILS[n]);kind='formula_preparation_note' if n==44 else 'author_commentary'
            segments[n]=[(0,cut,'case'),(cut,len(body),kind)]
        elif n==48:
            cut=body.index('一婦人');segments[n]=[(0,cut,'author_commentary'),(cut,len(body),'case')]
        elif n==58:
            cut=body.index('佐云：');end=body.index('蓋八味丸有附子')
            segments[n]=[(0,cut,'case'),(cut,end,'case'),(end,len(body),'signed_testimony_commentary')]
        else:segments[n]=[(0,len(body),'case')]
    lines=[BEGIN,'## 《內科摘要》卷上第二至六篇：全篇醫案結構化（2026-09-28）','',
           '覆蓋 P025–P069 共 45 段。P040–P041 為薛己連續自述，合為一案；P058 明確分為婦人與朱佐來書兩案。P054 的病程由沈大雅敘述，P055 保留其署名。P069 含沈察來書與薛己答治，作者角色並列。全文、案後評論及原刻方藥注文均按來源位置保留；影像狀態沿用原記錄，字段為可回指原案的摘引。','',
           'P037「患症同前」保留原句並指向 P036，不直接把前案全部症狀複製進該案。P059「不起」保持原詞，P061「辭不治」只標為拒絕續治；案後「不死何俟」不填作已死亡。P063 的王太僕是被引理論作者，並非已證實的該案診治者。','']
    counts={}
    for n,patient,symptom,mechanism,treatment,outcome in LABELS:
        counts[n]=counts.get(n,0)+1;ordinal=counts[n]
        start,end,_=[s for s in segments[n] if s[2]=='case'][ordinal-1]
        r=rows[n];m=r['meta'];body=r['body'][start:end]
        continuation=None
        if n==40:
            _,continued_end,_=segments[41][0]
            continuation=(rows[41]['meta']['source_id'],0,continued_end)
            body+='\n\n'+rows[41]['body'][:continued_end]
        cid=f'XJ-NKZY-C-V1-P{n:03d}-{ordinal}'
        for q in (patient,symptom,mechanism,treatment,outcome):
            if q and q not in body:raise ValueError(f'{cid}: excerpt not in case: {q}')
        author='薛己（自著敘事）'
        if n==54:author='沈大雅（母親治驗來書；P055 署名）'
        if n==58 and ordinal==2:author='朱佐（自述治驗來書；同段末署名）'
        if n==69:author='沈察（來書）；薛己（答治與後續敘事）'
        proposed=n in {32,59,60,61}
        meta={'case_id':cid,'work_ref':'XJ-NKZY','source_ref':m['source_id'],
              'source_start_char':start,'source_end_char_exclusive':end,
              'source_location':m['source_location'],'person_quote':patient,
              'original_case_author':author,
              'treating_person_refs':'立齋先生' if n==58 and ordinal==2 else '先生（本段未明姓名）' if n==54 else '余；原醫者' if n==62 else '余' if '余' in body else '',
              'text_layer':'case_from_working_transcription',
              'symptoms_quote':symptom,'mechanism_quote':mechanism,
              'treatment_quote':treatment,'formula_quote':treatment,'outcome_quote':outcome,
              'treatment_record_status':'proposed_not_documented_as_administered' if proposed else 'narrated_management',
              'boundary_status':'model_reviewed_against_full_chapter',
              'scan_verification_status':m['scan_verification_status'],
              'rights_status':m['rights_status'],'source_url':m['source_url'],
              'retrieval_status':m.get('retrieval_status','source_research_with_caveats'),
              'annotation_date':'2026-09-28'}
        if continuation:
            meta.update({'continued_source_ref':continuation[0],
                         'continued_start_char':continuation[1],
                         'continued_end_char_exclusive':continuation[2],
                         'person_role':'author_self_case'})
        if n==37:meta['symptom_context_ref']='XJ-NKZY-V1-P036'
        if n==54:meta['signature_source_ref']='XJ-NKZY-V1-P055'
        if n==58 and ordinal==2:meta['signature_quote']='杉墩介庵朱佐頓首拜書'
        if n==63:meta['quoted_author_refs']='王太僕（理論引文，非診治歸屬）'
        if n==58 and ordinal==2:
            # The signature belongs to the preserved commentary, not the case span.
            meta['signature_evidence_text']='杉墩介庵朱佐頓首拜書'
            del meta['signature_quote']
        lines += [f'### {cid}','','```yaml',yaml(meta),'```','',body,'']
    unit_count=0
    for n,parts in segments.items():
        for start,end,kind in parts:
            if kind=='case':continue
            unit_count+=1
            uid=f'XJ-NKZY-U-V1-P{n:03d}'
            meta={'text_unit_id':uid,'source_ref':rows[n]['meta']['source_id'],
                  'source_start_char':start,'source_end_char_exclusive':end,
                  'unit_kind':kind,'review_status':'model_boundary_reviewed',
                  'author_attribution':'沈大雅' if n==55 else '朱佐' if n==58 else '原刻注文作者未詳' if n==44 else '薛己敘事中的評論／引用',
                  'retrieval_status':'source_research_with_caveats'}
            if n==55:meta['case_ref']='XJ-NKZY-C-V1-P054-1'
            if n==58:meta['case_ref']='XJ-NKZY-C-V1-P058-2'
            lines += [f'### {uid}','','```yaml',yaml(meta),'```','',rows[n]['body'][start:end],'']
    lines += ['### 第二至六篇覆蓋驗收','']
    for i,(first,last) in enumerate(CHAPTER_RANGES,2):
        lines += ['```yaml',yaml({'coverage_id':f'XJ-NKZY-V1-CH{i}',
                   'source_prefix':'XJ-NKZY-V1-P','first_source_number':first,
                   'last_source_number':last,'coverage_status':'complete_against_working_transcription'}),'```','']
    lines += [f'本組共 {len(LABELS)} 個個別醫案、{unit_count} 個非個別医案文字單元；45 段所有字符均有覆蓋，無缺口、無重疊。全書現已覆蓋卷上前六篇的 69 段，其餘 475 條來源記錄待結構化。','',END]
    section='\n'.join(lines)
    if BEGIN in old:updated=re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),lambda _:section,old,flags=re.S)
    else:
        at=old.index('\n> 這是目前唯一');updated=old[:at]+'\n'+section+'\n\n---\n'+old[at:]
    final=books(updated)
    if text_digest(final)!=digest:raise ValueError('Source text changed')
    totals=validate_structured_units(updated,final)
    CORPUS.write_text(updated)
    print(json.dumps({'new_cases':len(LABELS),'new_non_case_units':unit_count,
                      'new_complete_chapters':5,'structured_totals':totals},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
