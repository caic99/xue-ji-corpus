"""Reviewed case boundaries and source-preserving formula units for NKZY V1."""
from audit_corpus import CORPUS, books, text_digest, validate_structured_units
from structure_nkzy_chapter import yaml
import json
import re

BEGIN='<!-- NKZY_VOLUME_ONE_REST_CASES_BEGIN -->'
END='<!-- NKZY_VOLUME_ONE_REST_CASES_END -->'
# Number, patient, directly stated mechanism, management quotation, outcome quotation.
LABELS=[
(70,'大司馬王浚川','','用參附湯一劑頓愈。','一劑頓愈'),
(71,'趙吏部文卿','此食鬱上','宜吐，不須用藥，乃候。','勿藥自安'),
(72,'一儒者','此脾胃虛寒','用六君加炮薑、木香漸愈，兼用四神丸而元氣復。','兼用四神丸而元氣復'),
(73,'一上舍','','余用補中益氣加茯苓、半夏，治之而愈。','治之而愈'),
(74,'儒者胡濟之','悉屬虛寒','乃以八味丸痊愈。','乃以八味丸痊愈'),
(75,'一上舍','嘔吐痰涎，胃氣虛寒；發熱作渴，胃不生津；胸膈痞滿，脾氣虛弱','須用參、耆、歸、術之類，溫補脾胃，生髮陽氣，諸病自退。','當殞於晝。果然'),
(76,'余母太宜人','此胃中濕熱鬱火','以黃連一味煎湯，冷飲少許','調理得痊'),
(77,'一婦人','此脾胃虧損，末傳寒中','又以補中益氣加炮薑、木香、茯苓、半夏，兼服痊愈。','兼服痊愈'),
(78,'一婦人','此脾虛痞滿','後以六君、芎、歸、貝母、桔梗、炮姜而愈。','而愈'),
(79,'家母','此寒涼損真之故，內真寒而外假熱也','遂與補中益氣加半夏、茯苓、吳茱、木香，一服而效。','諸症釋然'),
(80,'一婦人','脾氣鬱結','用歸脾加吳茱，不數劑而飲食如常。','飲食如常'),
(81,'一婦人','','仍服六君之類而安。','而安'),
(82,'進士劉華甫','乃肝木克脾土','用六君加木香治之而愈。','治之而愈'),
(83,'光祿柴黼庵','此脾胃之氣虛','再用補中益氣加茯苓、半夏，瀉、脹亦愈。','瀉、脹亦愈'),
(84,'舊僚錢可久','此腸胃濕痰壅滯','此後日以黃連三錢泡湯飲之而安。','而安'),
(85,'一儒者','症屬脾腎虛寒','更用八味丸，胃強脾健而愈。','胃強脾健而愈'),
(86,'一男子','此是脾氣虛弱','用六君送四神丸而愈。','而愈'),
(87,'一羽士','此脾腎泄也','當用六君加薑、桂送四神丸。','終踐余言而愈'),
(88,'紹','爾病脾腎兩虛，內真寒而外虛熱','遂以參、術為君，山藥、黃耆、肉果、薑、附為臣，茱萸、骨脂、五味、歸、苓為佐','盡劑而血止，諸疾遄已'),
(89,'崔司空','此濕熱壅滯','用補中益氣送香連丸而愈。','而愈'),
(89,'羅給事','此脾腎氣虛而下陷也','用補中益氣送八味丸，二劑而愈。','二劑而愈'),
(90,'少宗伯顧東江','','余以六君加薑、桂各二錢，吳茱、五味各一錢','再劑全退'),
(91,'太常邊華泉','','又用補中益氣加炮姜，二劑而愈。','二劑而愈'),
(92,'廷評曲汝為','','又用八味丸料加五味、吳茱、骨脂、肉蔻，二劑痊愈。','二劑痊愈'),
(93,'判官汪天錫','','仍用前藥，大黃減半，數劑而愈。','數劑而愈'),
(94,'通府薛允頫','此脾氣下陷','余用補中益氣加炮姜，一劑而愈。','一劑而愈'),
(95,'一上舍','脾胃虧損','用六君加木香、炮姜，二劑而愈。','二劑而愈'),
(96,'一老人','','遂以茶茗為丸，時用清茶送三、五十丸，不數服而瘥。','不數服而瘥'),
(97,'一老婦','屬脾氣下陷','與六味地黃丸，二劑頓愈。','二劑頓愈'),
(98,'先母','真氣虛而邪氣實也','急用人參五錢，白朮、茯苓各三錢，陳皮、升麻、附子、炙甘草各一錢','再劑而安'),
(98,'石閣老太夫人','','彼乃專治其痢','遂致不起'),
(99,'橫金陳梓園','此乃脾腎虧損，不能生剋制化','當滋化源','果患痢而歿'),
(101,'冬官朱省庵','食後脹痛，乃脾虛不能克化也','治以補中益氣加吳茱、炮薑、木香、肉桂','不數劑而痊'),
(104,'大尹曹時用','此陽氣虛寒','加炮薑、附子各一錢','數劑而元氣復'),
(105,'一儒者','','更以調中益氣加半夏、茯苓、炮姜','服前藥即愈'),
(107,'一上舍','','又服還少丹半載','形體充實'),
(108,'一婦人','','乃用補中益氣加茯苓、半夏，十餘劑而愈。','十餘劑而愈'),
(110,'東洞庭馬志卿','','用補中益氣，內參、耆、歸、術各加三錢，甘草一錢五分，炮姜二錢','數劑而元氣復'),
(111,'一婦人','','余用調中益氣加茯苓、半夏、炮姜各一錢','二劑而痊'),
(112,'一婦人','','又以前藥，炮姜用一錢','元氣復而痊愈'),
(114,'大參李北泉','此腎水泛而為痰','卻用六味丸','月餘諸症悉愈'),
(115,'鴻臚蘇龍溪','腹脹不食，脾胃虛也；小便短少，肺腎虛也','再用補中益氣加炮薑、五味','數劑痊愈'),
(116,'地官李北川','此誤汗亡津液而變痙矣','仍以前湯加附子一錢','四劑而痊'),
(118,'待御譚希曾','脾肺虛寒','用補中益氣加炮姜而愈。','而愈'),
(119,'職坊王用之','脾肺有熱','用二陳加芩、連、山梔、桔梗、麥門而愈。','而愈'),
(120,'僉憲阮君聘','此脾肺虛而兼外邪','又用六君、芎、歸之類而安。','而安'),
(121,'司廳陳國華','此脾肺虛也','夕用八味丸，補命門火以生脾土','諸症漸愈'),
(123,'中書鮑希伏','脾土既不能生肺金，陰火又從而克之','夕用六味地黃加五味子','喜其慎疾得愈'),
(124,'武選汪用之','水泛為痰之症','佐以六味丸治之而痊。','治之而痊'),
(125,'錦衣李大用','此化源既絕，五臟已敗','當滋化源','已而果然'),
(126,'絲客姚荃者','乃肝木克脾土，而脾土不能生肺金也','用滋化源之藥，四劑，諸症頓退。','果吐穢膿而歿'),
(127,'學士吳北川','脾虛濕熱','余作脾虛濕熱治之而愈。','治之而愈'),
(128,'上舍史瞻之','此是腎經陰火,刑剋肺金','遂以六味丸料加麥門、五味、炒梔及補中益氣湯而愈。','而愈'),
(129,'儒者張克明','侵晨吐痰，脾虛不能消化飲食','更用八味丸，以補土母而愈。','以補土母而愈'),
(130,'一男子','火乘肺金','日用生脈散而痊。','而痊'),
(131,'一婦人','皆屬肝火血虛，陰挺痿痹','用前散及地黃丸','月餘而瘥'),
(132,'表弟婦','此命門火衰，脾土虛寒','用八味丸及附子理中湯加減治之而愈。','治之而愈'),
(133,'一婦人','此脾肺俱傷，痰鬱於中','後以六君加芎、歸、桔梗','間服而愈'),
(134,'一婦人','早間痰，乃脾虛飲食所化，夜間喘急，乃肺虛陰火上衝','遂用補中益氣加麥門、五味而愈。','而愈'),
(135,'一婦人','此屬肝脾二經血虛','再用十全大補而安。','而安'),
(136,'上舍陳道復長子','虧損腎經','乃以參、耆、熟地、山茱為丸','卒致不起'),
]
FULL_UNITS={100:'cross_work_reference',102:'author_commentary',103:'author_commentary',
106:'author_commentary',109:'formula_use_commentary',113:'cross_work_reference',
117:'author_commentary',122:'author_commentary',137:'cross_work_reference',176:'cross_volume_reference'}
TAILS={71:'後撫陝右',72:'此症若',73:'若腿足',79:'先生之見',80:'若人脾腎',81:'婦人患此',
82:'若食已消',83:'此症若',84:'但如此',86:'若脾氣',87:'蓋化氣',88:'嗚呼!',
90:'此假熱',93:'此等元氣',130:'若咳而',132:'詳見婦人',135:'此症若'}
RANGES=[(70,81),(82,88),(89,100),(101,113),(114,137),(138,176)]
FORMULAS=[(138,140,'四物湯'),(141,141,'加味四物湯'),(142,144,'四君子湯'),
(145,145,'異功散'),(146,146,'六君子湯'),(147,147,'香砂六君子湯'),
(148,150,'人參理中湯'),(151,151,'附子理中湯'),(152,152,'八珍湯'),
(153,153,'十全大補湯'),(154,156,'人參養榮湯'),(157,159,'當歸補血湯'),
(160,162,'當歸六黃湯'),(163,165,'獨參湯'),(166,168,'歸脾湯'),
(169,169,'加味歸脾湯'),(170,170,'加減八味丸'),(171,174,'六味丸'),(175,175,'八味丸')]


def main():
 old=CORPUS.read_text();original=books(old);digest=text_digest(original)
 book=next(b for b in original if b['meta']['work_id']=='XJ-NKZY')
 rows={int(r['meta']['source_id'].rsplit('P',1)[1]):r for r in book['rows'] if r['meta']['volume']=='卷上' and int(r['meta']['source_id'].rsplit('P',1)[1])>=70}
 if sorted(rows)!=list(range(70,177)):raise ValueError('Full V1 remainder missing')
 segments={}
 for n,r in rows.items():
  body=r['body']
  if n in FULL_UNITS:segments[n]=[(0,len(body),FULL_UNITS[n])]
  elif n>=138:segments[n]=[(0,len(body),'formula_text')]
  elif n==89:
   a=body.index('羅給事');b=body.index('此等症候')
   segments[n]=[(0,a,'case'),(a,b,'case'),(b,len(body),'author_commentary')]
  elif n==98:
   a=body.index('此取症');b=body.index('時石閣')
   segments[n]=[(0,a,'case'),(a,b,'author_commentary'),(b,len(body),'case')]
  elif n in TAILS:
   a=body.index(TAILS[n]);kind='cross_work_reference' if n in {81,132} else 'signed_testimony_commentary' if n in {79,88} else 'author_commentary'
   segments[n]=[(0,a,'case'),(a,len(body),kind)]
  else:segments[n]=[(0,len(body),'case')]
 lines=[BEGIN,'## 《內科摘要》卷上第七至十二篇：全篇結構化（2026-09-28）','',
 '完整覆蓋 P070–P176。P089、P098 各含兩案，P079、P088 是陸伷、朱紹的署名治驗；其署名評論保留為獨立單元。P071 勿藥自安照錄，方藥留空。P125「已而果然」、P136「不起」保持原詞，不增寫未明載的轉歸。各症方藥全部保留並以方劑 ID 歸組；不列作患者醫案。','',
 '症狀字段是病程開頭的原文敘述，可能同時含背景或既往處置；病機與治法字段是選定的原句摘引。完整的症狀、歷次用藥、劑量與轉歸以每案全文為準。這一版本尚未完成所有方藥名稱的逐項索引。','']
 occurrences={}
 for n,patient,mechanism,treatment,outcome in LABELS:
  occurrences[n]=occurrences.get(n,0)+1;ordinal=occurrences[n]
  start,end,_=[s for s in segments[n] if s[2]=='case'][ordinal-1]
  m=rows[n]['meta'];body=rows[n]['body'][start:end];cid=f'XJ-NKZY-C-V1-P{n:03d}-{ordinal}'
  for q in (patient,mechanism,treatment,outcome):
   if q and q not in body:raise ValueError(f'{cid}: missing quotation: {q}')
  author='陸伷（母親治驗來書；同段末署名）' if n==79 else '朱紹（自述治驗；同段末署名）' if n==88 else '薛己（自著敘事）'
  after=body.index(patient)+len(patient);first_stop=body.find('。',after)
  symptoms=body[after:first_stop if first_stop>=0 else len(body)].lstrip('，')
  meta={'case_id':cid,'work_ref':'XJ-NKZY','source_ref':m['source_id'],'source_start_char':start,'source_end_char_exclusive':end,
  'source_location':m['source_location'],'person_quote':patient,'original_case_author':author,
  'treating_person_refs':'立齋先生；朱存默氏' if n==79 else '立齋先生' if n==88 else '余' if '余' in body else '予' if '予曰' in body else '',
  'text_layer':'case_from_working_transcription','symptoms_quote':symptoms,'mechanism_quote':mechanism,
  'treatment_quote':treatment,'formula_quote':'' if n==71 else treatment,'outcome_quote':outcome,
  'treatment_record_status':'observation_without_medicine' if n==71 else 'proposed_not_documented_as_administered' if n in {75,99,125} else 'narrated_management',
  'boundary_status':'model_reviewed_against_full_chapter','scan_verification_status':m['scan_verification_status'],
  'rights_status':m['rights_status'],'source_url':m['source_url'],'retrieval_status':m.get('retrieval_status','source_research_with_caveats'),'annotation_date':'2026-09-28'}
  lines +=[f'### {cid}','','```yaml',yaml(meta),'```','',body,'']
 units=0
 for n,parts in segments.items():
  for start,end,kind in parts:
   if kind=='case':continue
   units+=1;uid=f'XJ-NKZY-U-V1-P{n:03d}'
   meta={'text_unit_id':uid,'source_ref':rows[n]['meta']['source_id'],'source_start_char':start,'source_end_char_exclusive':end,'unit_kind':kind,
         'author_attribution':'陸伷' if n==79 else '朱紹' if n==88 else '薛己所在自著；原刻小字作者未另詳',
         'review_status':'model_boundary_reviewed','retrieval_status':rows[n]['meta'].get('retrieval_status','source_research_with_caveats')}
   for first,last,name in FORMULAS:
    if first<=n<=last:
     meta.update({'formula_id':f'XJ-NKZY-F-V1-P{first:03d}','formula_name':name,'formula_first_source':f'XJ-NKZY-V1-P{first:03d}','formula_last_source':f'XJ-NKZY-V1-P{last:03d}'})
   if n in {79,88}:meta['case_ref']=f'XJ-NKZY-C-V1-P{n:03d}-1'
   if n in {100,113,137}:meta['target_work']='女科撮要；精確目標案待定位'
   if n==176:meta['target_volume']='內科摘要卷下'
   lines +=[f'### {uid}','','```yaml',yaml(meta),'```','',rows[n]['body'][start:end],'']
 lines+=['### 第七至十二篇覆蓋驗收','']
 for i,(first,last) in enumerate(RANGES,7):
  lines+=['```yaml',yaml({'coverage_id':f'XJ-NKZY-V1-CH{i}','source_prefix':'XJ-NKZY-V1-P','first_source_number':first,'last_source_number':last,'coverage_status':'complete_against_working_transcription'}),'```','']
 lines +=[f'本組 {len(LABELS)} 案、{units} 個非個別醫案文字單元、19 個方劑歸組；107 段逐字符覆蓋無缺口、無重疊。卷上全部 176 條來源記錄均已組織，卷下 368 條待續。','',END]
 section='\n'.join(lines)
 if BEGIN in old:updated=re.sub(re.escape(BEGIN)+r'.*?'+re.escape(END),lambda _:section,old,flags=re.S)
 else:
  at=old.index('\n> 這是目前唯一');updated=old[:at]+'\n'+section+'\n\n---\n'+old[at:]
 final=books(updated)
 if text_digest(final)!=digest:raise ValueError('Source text changed')
 totals=validate_structured_units(updated,final);CORPUS.write_text(updated)
 print(json.dumps({'new_cases':len(LABELS),'new_units':units,'completed_volume':'卷上','totals':totals},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
