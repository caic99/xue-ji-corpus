"""Source-preserving NKZY V2 structure, with explicitly reviewed boundaries.

No efficacy, modern disease, author lineage, or scan verification is inferred.
Empty quotation fields are unindexed, not assertions of absence.
"""
from audit_corpus import CORPUS, books, text_digest, validate_structured_units
from structure_nkzy_chapter import yaml
import json
import re

BEGIN = '<!-- NKZY_VOLUME_TWO_CASES_BEGIN -->'
END = '<!-- NKZY_VOLUME_TWO_CASES_END -->'
PATIENTS = {
1:'閣老梁厚齋',2:'都憲孟有涯',3:'孫都憲',5:'昌平守王天成',6:'大尹祝支山',
7:'桐石',8:'一男子',9:'先兄',10:'儒者楊澤之',11:'一男子',12:'一男子',
13:'舉人江節夫',14:'大尹劉天錫',15:'州守王用之',16:'州同劉禹功',
17:'一富商',18:'一儒者',19:'一男子',20:'一男子',21:'一男子',22:'山妻趙氏',
25:'大司徒李蒲汀',26:'應天王治中',27:'太守朱陽山弟',28:'一儒者',29:'一儒者',
30:'一男子',31:'一男子',32:'給事張禹功',34:'少宰李蒲汀',35:'少司馬黎仰之',
36:'尚寶劉毅齋',37:'一儒者',38:'一男子',39:'一儒者',40:'一男子',41:'一儒者',
42:'一男子',43:'一男子',45:'大司徒許函谷',47:'司徒邊華泉',48:'司馬李梧山',
49:'考功楊村庵',50:'司空何燕泉',51:'商主客',52:'一儒者',53:'儒者楊文魁',
54:'余',55:'大尹顧榮甫',56:'顧同崖',57:'庶吉士黃伯鄰',58:'少司空何瀟用',
59:'一儒者',60:'儒者劉允功',61:'一男子',62:'余甥居宏',63:'余甥凌雲漢',
64:'其弟雲霄',65:'少宰汪涵齋',66:'南銀臺許函谷',67:'司廳陳石鏡',68:'光祿柴黼庵',
69:'司廳張襝齋',70:'朱工部',71:'一男子',72:'一男子',73:'一男子',74:'一男子',
75:'儒者楊啟元',76:'一儒者',77:'一男子',78:'一童子',79:'一男子',80:'星士張東谷',
81:'通府黃廷用',82:'儒者章立之',83:'鍾之英',84:'一男子',86:'一儒者',87:'一老儒',
88:'一婦人',89:'一男子',90:'一儒者',91:'一男子',92:'職坊陳莪齋',
}
# One directly stated management excerpt per source; repeated courses remain in full text.
TREATMENTS = {
1:'用四物送六味丸',2:'用八味丸料',3:'用補中益氣加麥門、五味及加減八味丸',
5:'用補中益氣湯',6:'用八珍加柴胡、山梔、牡丹皮',7:'或用清氣化痰愈甚',
8:'與法制清氣化痰丸',9:'服八味丸及補中益氣加附子錢許',10:'余用補中益氣及六味地黃',
11:'用六味地黃，補中益氣',14:'更以補中益氣加麥門、五味、兼服',15:'用金匱腎氣丸',
16:'先用金匱加減腎氣丸料，肉桂、附各一錢五分',17:'用金匱腎氣丸、補中益氣湯',
18:'朝用補中益氣加薑、附，夕用金匱腎氣加骨脂、肉果',
19:'朝用金匱加減腎氣丸，夕用補中益氣湯煎送前丸',20:'余為壯火補土',
22:'又用補中益氣加木香、黃連、吳茱、五味',25:'以茵陳五苓散加芩、連、山梔',
26:'用桃仁承氣湯一劑',27:'用抵當湯',28:'更用六味丸',
29:'用八味丸以補土母，補中益氣以接中氣',30:'余用附子理中湯',
31:'又用補中益氣加炮姜',32:'卻用補中益氣加前藥',34:'五更服六味地黃丸，食前服補中益氣湯',
35:'用小柴胡合四物加山梔、茯神、陳皮',36:'更用六味丸以生腎水',37:'用補中益氣倍加參、耆',
38:'用補中益氣、六味地黃',39:'服十全大補',40:'用六味地黃丸料加柴胡、當歸',
41:'亦用前藥',42:'用補中益氣加麥門、山梔',43:'余與六味地黃料加麥門、五味',
45:'午前用補中益氣加山藥、黃柏、知母，午後服地黃丸',47:'用六味、滋腎二丸',
48:'用補中益氣、六味地黃',49:'再用補中益氣、六味地黃以補肺腎',
50:'用補中益氣、六味丸加五味',51:'用滋腎、六味二丸',52:'用六味丸加五味子及補中益氣',
53:'用補中益氣湯加附子',54:'仍服前湯加木通、茯苓、膽草、澤瀉及地黃丸',
57:'就以地黃丸料煎與',58:'用十全大補加麥門、五味、山藥、山茱',
59:'用當歸補血湯',60:'余用六味地黃、補中益氣',61:'當滋化源',
62:'用六味丸及大補湯加麥門、五味',63:'亦服地黃丸數斤，煎藥三百餘劑',
64:'及加減八味丸',65:'用八味丸',66:'午前用補中益氣加山藥、山茱，午後服地黃丸',
67:'再用六味地黃丸兼服',68:'用濟生歸脾、十全大補二湯',
69:'用小柴胡加山梔、膽草、茱萸、芎、歸',70:'更以十全大補加麥門、五味',
71:'用補中益氣加芍藥、玄參，並加減八味丸',72:'又兼六味地黃丸',
74:'服十全大補加麥門、五味、山茱、山藥',75:'再用歸脾湯',
76:'用補中益氣加麥門、五味，及六味地黃丸加五味',77:'用六味地黃丸',
78:'遂用補中益氣及地黃丸',79:'用補中益氣、六味地黃',
80:'與補中益氣加麥門、五味、山藥、熟地、茯神、遠志',81:'滋其化源',
82:'用補中益氣、六味地黃',83:'用加味六味丸',84:'用補中益氣加芍藥、玄參及六味丸',
86:'余與補中益氣、六味地黃湯',87:'用豬膽潤',88:'用十全大補調理',
89:'今滋其化源',90:'用八珍湯加蓯蓉、麥門、五味',91:'辭不治',
}
OUTCOMES = {
1:'不月而康',2:'三劑而愈',3:'而愈',5:'而痊',6:'二十餘劑而愈',7:'治者不悟而歿',
8:'而愈',9:'停藥月餘，諸症仍作',10:'年餘元氣漸復而腫消',11:'而愈',13:'必不起，後果然',
14:'兼服而愈',15:'不月而康',16:'辭不治，果歿',17:'而愈',18:'半載而康',
19:'服前藥即愈',20:'後果歿',21:'後果然',22:'數劑而愈',25:'二劑而愈',
26:'下瘀血而愈',27:'而愈',28:'更用六味丸而痊',29:'而愈',30:'而愈',
31:'二劑痊愈',32:'而痊',34:'頓愈',35:'而瘥',36:'後不再發',37:'數劑痊愈',
38:'而愈',39:'而痊',40:'一劑而安',41:'頓安',42:'而愈',43:'一劑頓明',
45:'月餘諸症悉退',47:'而愈',48:'而愈',49:'而安',50:'而安',51:'滋補腎水而愈',
52:'喜其謹守得愈',53:'仍服前藥頓愈',54:'而愈',55:'後果歿',56:'而歿',
57:'服前藥即愈',58:'而愈',59:'而安',60:'而愈',61:'不信，服黃柏、知母之類而歿',
62:'而痊',63:'煎藥三百餘劑而愈',64:'元氣漸復而愈',65:'全愈',66:'月餘諸症悉退',
67:'諸症悉愈',68:'間服而愈',69:'而愈',70:'而痊',71:'而愈',72:'而痊',
74:'而愈',75:'再用歸脾湯而血止',76:'眉發頓生如故',77:'兩月復舊',78:'而瘥',
79:'而痊愈',80:'吐血頓止，神思如故',81:'半載得瘥',82:'年許而痊',83:'數日而愈',
84:'而愈',86:'年許而安',87:'通利如常',88:'若間前藥，飲食不進，諸症復作',
89:'如法果驗',90:'大便自潤',91:'辭不治，後果然',92:'後果然',
}
TAILS = {1:'仲景先生云',3:'若人少有老態',8:'彼為有驗',11:'亦有胸脅',
34:'此症若',49:'若汗多',52:'若肢體',77:'吳江史萬湖云',
80:'後率其子',83:'此等症候',86:'若脾肺'}
FULL_UNITS = {4:'general_claim',23:'signed_testimony_colophon',24:'chapter_scope_note',
33:'quoted_author_claim',44:'cross_work_reference',46:'conditional_treatment_rules',85:'cross_work_reference',368:'cross_volume_reference'}
RANGES = [(1,9),(10,13),(14,23),(24,31),(32,44),(45,56),(57,64),(65,80),(81,85),(86,92),(93,368)]
# Formula starts, reviewed consecutively against all P093-P368 paragraphs.
FORMULA_STARTS = [93,96,97,100,103,106,109,112,115,118,121,124,127,132,
135,138,141,144,147,150,153,156,159,162,165,168,171,174,177,180,183,186,
189,192,195,198,201,204,207,210,213,216,219,222,225,228,231,234,237,240,
243,246,249,252,255,258,261,264,265,268,271,274,277,280,283,286,289,292,
295,298,301,304,307,310,313,316,319,322,325,328,331,334,337,338,341,344,
347,350,353,356,359,362,365]
CONTEXTS = {20:19,38:37,41:40,64:63,91:90}
REPEATS = {37:'XJ-NKZY-V1-P036',38:'XJ-NKZY-V1-P037',45:'XJ-NKZY-V2-P066',
60:'XJ-NKZY-V1-P009',66:'XJ-NKZY-V2-P045',68:'XJ-NKZY-V1-P083'}


def main():
    old = CORPUS.read_text()
    original = books(old)
    digest = text_digest(original)
    book = next(b for b in original if b['meta']['work_id'] == 'XJ-NKZY')
    rows = {int(r['meta']['source_id'].rsplit('P',1)[1]):r
            for r in book['rows'] if r['meta']['volume'] == '卷下'}
    if sorted(rows) != list(range(1,369)):
        raise ValueError('Missing volume-two source record')
    segments = {}
    for n, r in rows.items():
        body = r['body']
        if n in FULL_UNITS:
            segments[n] = [(0,len(body),FULL_UNITS[n])]
        elif n >= 93:
            segments[n] = [(0,len(body),'formula_text')]
        elif n == 7:
            cut = body.index('後余應杭人之請')
            segments[n] = [(0,cut,'comparative_case_context'),(cut,len(body),'case')]
        elif n == 12:
            cut = body.index('一男子眉間'); shared = body.index('悉用')
            segments[n] = [(0,cut,'case'),(cut,shared,'case'),(shared,len(body),'shared_management_and_outcome')]
        elif n == 30:
            cut = body.index('有同患此者')
            segments[n] = [(0,cut,'case'),(cut,len(body),'case')]
        elif n == 73:
            second = body.index('一男子尿血'); third = body.index('一男子發熱'); shared = body.index('俱屬')
            segments[n] = [(0,second,'case'),(second,third,'case'),(third,shared,'case'),(shared,len(body),'shared_management_and_outcome')]
        elif n in TAILS:
            cut = body.index(TAILS[n])
            kind = 'reported_anecdote' if n == 77 else 'relationship_wording_not_lineage_determination' if n == 80 else 'author_commentary'
            segments[n] = [(0,cut,'case'),(cut,len(body),kind)]
        else:
            if n not in PATIENTS: raise ValueError(f'Unreviewed case boundary {n}')
            segments[n] = [(0,len(body),'case')]
    lines = [BEGIN,'## 《內科摘要》卷下十一篇：全文結構化（2026-09-28）','',
        '完整組織卷下 P001–P368，並保留每個來源字符。病例字段是可核對的選定原句，並非完整方藥索引；完整病程、歷次處置與劑量以正文為準，空字段表示尚未單獨索引。原文位置按工作轉錄固定字符序號計，不冒充影像行碼。','',
        'P012 兩人、P073 三人的共用病機／治法／轉歸獨立記錄，通過 shared_management_ref 引用，不杜撰個人的分別療效。P007 的孟有涯、陳東谷比較敘述不另算兩個獨立案例；顧桐石自己的病程單獨成案。P057 的郭主政及妻孥是黃伯鄰案的背景，郭的死亡不屬黃的轉歸。P077 後段是史萬湖轉述的男女軼事，不假造姓名或病例數。P080「師余」原詞保留，不據此自動認定醫學師承。','',
        '署名來書 P022 的原案敘述者為沈大方，P023 另存跋語。P013、P021、P091、P092 的「後果然」保留原詞，不以模型補寫死亡。相似重見的病例只加待比對引用，既不合併也不宣稱獨立患者數。附方完整保留，未見具體患者的方論不算醫案。','',
        '新登記疑字：P083「府癢」、P178「草果茯苓」分隔及 P308「各一錢」仍待影像確認。P179 已查看承應本 PDF 第86頁，圖讀「右姜七片烏梅一箇水煎服」；與電子原文「上姜七斤」有指令標記及用量單位差異。模型圖讀尚待人工審定，電子原字不改，相關條目及整方隔離為 needs_review。其餘疑字只是核查提示，不是已證實的錯誤。','']
    case_count = unit_count = 0
    for n, parts in segments.items():
        for ordinal, (start,end,kind) in enumerate([p for p in parts if p[2]=='case'],1):
            case_count += 1
            m = rows[n]['meta']; body = rows[n]['body'][start:end]
            patient = '同患此者' if n == 30 and ordinal == 2 else PATIENTS[n]
            after = body.index(patient)+len(patient)
            stop = body.find('。',after)
            symptoms = body[after:stop if stop >= 0 else len(body)].lstrip('，')
            treatment = TREATMENTS.get(n,'')
            outcome = OUTCOMES.get(n,'')
            if n in {12,73}: treatment = outcome = ''
            if n == 30 and ordinal == 2:
                treatment, outcome = '別用二陳、芩、連之類','而死'
            cid = f'XJ-NKZY-C-V2-P{n:03d}-{ordinal}'
            meta = {'case_id':cid,'work_ref':'XJ-NKZY','source_ref':m['source_id'],
                'source_start_char':start,'source_end_char_exclusive':end,
                'source_location':m['source_location'],'person_quote':patient,
                'original_case_author':'沈大方（妻子趙氏治驗來書；P023 署名）' if n==22 else '薛己（自著敘事）',
                'treating_person_refs':'先生（上下文指薛己）' if n==22 else '敘事涉及余及其他治者；具體處置以原句為準',
                'text_layer':'case_from_working_transcription','symptoms_quote':symptoms,
                'mechanism_quote':'','treatment_quote':treatment,'formula_quote':'','outcome_quote':outcome,
                'tag_index_status':'selected_literal_excerpts_full_course_in_body',
                'treatment_record_status':'proposed_not_documented_as_administered' if n==61 else 'shared_unit_only' if n in {12,73} else 'narrated_course_not_efficacy_inference',
                'boundary_status':'model_reviewed_against_full_volume',
                'scan_verification_status':m['scan_verification_status'],'rights_status':m['rights_status'],
                'source_url':m['source_url'],'retrieval_status':'needs_review' if n==83 else m.get('retrieval_status','source_research_with_caveats'),
                'annotation_date':'2026-09-28'}
            if n in {12,73}: meta['shared_management_ref']=f'XJ-NKZY-U-V2-P{n:03d}-1'
            if n in CONTEXTS: meta['narrative_context_ref']=f'XJ-NKZY-V2-P{CONTEXTS[n]:03d}'
            if n==30 and ordinal==2:meta['symptom_context_ref']='XJ-NKZY-C-V2-P030-1'
            if n==7:meta['person_context_ref']=m['source_id'];meta['intro_context_ref']='XJ-NKZY-U-V2-P007-1'
            if n==57:meta['embedded_people_note']='郭主政與妻孥是背景敘述，郭的死亡不得歸到黃伯鄰'
            if n==78:meta['quoted_author_refs']='丹溪；褚氏遺書精血篇（引用，不是本案治者）'
            if n==89:meta['quoted_author_refs']='東垣（引用，不是本案治者）'
            if n in REPEATS:meta['possible_repeat_source_ref']=REPEATS[n];meta['repeat_status']='candidate_not_merged'
            if n==83:meta['pending_reason']='府癢：官稱用字可疑，影像未核，不更改原字'
            for key,val in meta.items():
                if key.endswith('_quote') and val and val not in body:raise ValueError(f'{cid} {key} mismatch: {val}')
            lines += [f'### {cid}','','```yaml',yaml(meta),'```','',body,'']
    formulas = {}
    for i, first in enumerate(FORMULA_STARTS):
        last = FORMULA_STARTS[i+1]-1 if i+1<len(FORMULA_STARTS) else 367
        name = rows[first]['body'].split('　',1)[0]
        for n in range(first,last+1):formulas[n]=(first,last,name)
    for n, parts in segments.items():
        for ordinal,(start,end,kind) in enumerate([p for p in parts if p[2]!='case'],1):
            unit_count += 1
            uid=f'XJ-NKZY-U-V2-P{n:03d}-{ordinal}'
            meta={'text_unit_id':uid,'source_ref':rows[n]['meta']['source_id'],
                  'source_location':rows[n]['meta']['source_location'],
                  'source_url':rows[n]['meta']['source_url'],
                  'rights_status':rows[n]['meta']['rights_status'],
                  'scan_verification_status':rows[n]['meta']['scan_verification_status'],
                  'source_start_char':start,'source_end_char_exclusive':end,'unit_kind':kind,
                  'author_attribution':'沈大方' if n==23 else '史萬湖（薛己轉述）' if n==77 else '東垣（薛己引述）' if n==33 else '薛己自著中的文字；引用者及原方作者不等同薛己創方',
                  'review_status':'model_boundary_reviewed',
                  'retrieval_status':'needs_review' if n in {177,178,179,307,308,309} else rows[n]['meta'].get('retrieval_status','source_research_with_caveats')}
            if n in formulas:
                first,last,name=formulas[n]
                meta.update({'formula_id':f'XJ-NKZY-F-V2-P{first:03d}','formula_name':name,
                    'formula_first_source':f'XJ-NKZY-V2-P{first:03d}','formula_last_source':f'XJ-NKZY-V2-P{last:03d}'})
            if n in {12,73}:meta['shared_case_refs']='; '.join(f'XJ-NKZY-C-V2-P{n:03d}-{i}' for i in range(1,3 if n==12 else 4))
            if n==23:meta['case_ref']='XJ-NKZY-C-V2-P022-1'
            if n==44:meta['target_work']='女科撮要；精確目標案待定位'
            if n==85:meta['target_work']='外科樞要；精確目標案待定位'
            if n==368:meta['target_volume']='內科摘要卷上';meta['editorial_separator_note']='本來源記錄尾隨 Markdown 分隔線是舊稿格式，不屬古籍正文；保持來源層校驗值不變'
            if n in {178,179,308}:meta['pending_reason']={178:'草果茯苓：藥名分隔待核',179:'電子原文上姜七斤；承應本第86頁圖讀右姜七片。單位差異已登記，待人工審定，不改原文',308:'各一錢：多味方劑用量待影像核對，不能依常用方擅改'}[n]
            if n==179:
                meta['current_scan_source_url']='https://commons.wikimedia.org/wiki/File:NCL-06248-0008_%E5%85%A7%E7%A7%91%E6%91%98%E8%A6%81.pdf?page=86'
                meta['current_scan_raw_reading']='右姜七片烏梅一箇水煎服'
                meta['current_scan_evidence_status']='model_visual_reading_of_target_line_not_human_adjudicated'
            if n in {177,178,179,307,308,309}:
                meta['formula_group_status']='needs_review_due_to_unverified_ingredient_or_dose'
                if n not in {178,179,308}:meta['pending_reason']='同方藥名／用量疑點未核，整方暫不作默認檢索條目'
            lines += [f'### {uid}','','```yaml',yaml(meta),'```','',rows[n]['body'][start:end],'']
    lines += ['### 卷下十一篇覆蓋驗收','']
    for chapter,(first,last) in enumerate(RANGES,1):
        lines += ['```yaml',yaml({'coverage_id':f'XJ-NKZY-V2-CH{chapter}','source_prefix':'XJ-NKZY-V2-P',
            'first_source_number':first,'last_source_number':last,'coverage_status':'complete_against_working_transcription'}),'```','']
    lines += [f'卷下 {case_count} 案、{unit_count} 個非個別醫案單元、{len(FORMULA_STARTS)} 個方劑歸組。368 條来源記錄完整逐字符覆蓋；連同卷上，全書 544 段、23 篇的全文組織完成。這是工作轉錄結構化完整，不是全書影像校勘完成，也不是獨立患者或療效統計。','',END]
    section='\n'.join(lines)
    if BEGIN in old:updated=re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),lambda _:section,old,flags=re.S)
    else:
        at=old.index('\n> 這是目前唯一');updated=old[:at]+'\n'+section+'\n\n---\n'+old[at:]
    final=books(updated)
    if text_digest(final)!=digest:raise ValueError('Source body changed')
    totals=validate_structured_units(updated,final)
    CORPUS.write_text(updated)
    print(json.dumps({'new_cases':case_count,'new_units':unit_count,'formula_groups':len(FORMULA_STARTS),'totals':totals,'source_text_sha256':digest},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
