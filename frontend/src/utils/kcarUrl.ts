// K-Car 제조사 및 모델 코드 매핑 테이블 (https://market-api.kcar.com/api/v1/ds/getModelListCount 실측 기준)

export const KCAR_MNUFTR_MAP: Record<string, string> = {
  '현대': '001',
  '기아': '002',
  '쉐보레': '003',
  '쉐보레(GM대우)': '003',
  '쉐보레(대우)': '003',
  'GM대우': '003',
  'KGM': '004',
  'KG모빌리티': '004',
  'KG모빌리티(쌍용)': '004',
  '쌍용': '004',
  '르노코리아': '005',
  '르노코리아(삼성)': '005',
  '르노삼성': '005',
  '제네시스': '007',
  '아우디': '011',
  'BMW': '012',
  '벤츠': '013',
  '볼보': '017',
  '렉서스': '035',
  '테슬라': '087',
};

export interface KcarModelGroupEntry {
  mnuftrCd: string;
  modelGrpCd: string;
  models: Record<string, string>;
}

export const KCAR_MODEL_GROUPS: KcarModelGroupEntry[] = [
  // 기아 (002)
  {
    mnuftrCd: '002',
    modelGrpCd: '036', // 카니발
    models: {
      '그랜드 카니발': '074',
      '뉴카니발': '075',
      '카니발 R': '090',
      '올 뉴 카니발': '113',
      '더 뉴 카니발': '137',
      '카니발 (4세대)': '166',
      '카니발 4세대': '166',
      '신형 카니발': '166',
      '더 뉴 카니발 4세대': '190',
      '더 뉴 카니발 하이브리드 4세대': '191',
      '더 뉴 카니발 4세대 하이브리드': '191',
      '카니발 하이브리드 4세대': '191',
      '하이브리드 4세대': '191',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '027', // 쏘렌토
    models: {
      '쏘렌토 R': '087',
      '뉴 쏘렌토 R': '102',
      '올 뉴 쏘렌토': '114',
      '더 뉴 쏘렌토': '133',
      '쏘렌토 4세대': '163',
      '신형 쏘렌토 (MQ4)': '163',
      '쏘렌토 4세대 하이브리드': '164',
      '더 뉴 쏘렌토 4세대': '185',
      '더 뉴 쏘렌토 4세대 하이브리드': '186',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '025', // 스포티지
    models: {
      '스포티지 R': '091',
      '더 뉴 스포티지 R': '107',
      '스포티지 4세대': '119',
      '스포티지 더 볼드': '141',
      '디 올 뉴 스포티지': '175',
      '스포티지 5세대': '175',
      '디 올 뉴 스포티지 하이브리드': '176',
      '스포티지 5세대 하이브리드': '176',
      '더 뉴 스포티지': '198',
      '더 뉴 스포티지 하이브리드': '199',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '065', // 셀토스
    models: {
      '셀토스': '155',
      '더 뉴 셀토스': '181',
      '디 올 뉴 셀토스': '204',
      '디 올 뉴 셀토스 하이브리드': '205',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '061', // 니로
    models: {
      '니로': '126',
      '니로 EV': '140',
      '니로 플러그인 하이브리드': '149',
      '더 뉴 니로': '150',
      '디 올 뉴 니로': '177',
      '디 올 뉴 니로 EV': '179',
      '니로 플러스': '180',
      '더 뉴 니로 (SG2)': '206',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '058', // 레이
    models: {
      '레이': '099',
      '더 뉴 레이': '134',
      '레이 EV': '153',
      '더 뉴 기아 레이': '182',
      '더 뉴 기아 레이 EV': '187',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '013', // 모닝
    models: {
      '뉴모닝': '083',
      '올 뉴 모닝': '095',
      '더 뉴 모닝': '116',
      '올 뉴 모닝 (JA)': '130',
      '모닝 어반': '165',
      '더 뉴 모닝 (JA)': '184',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '015', // 모하비
    models: {
      '모하비': '080',
      '더 뉴 모하비': '123',
      '모하비 더 마스터': '156',
    },
  },
  { mnuftrCd: '002', modelGrpCd: '063', models: { '스토닉': '132' } },
  { mnuftrCd: '002', modelGrpCd: '037', models: { '뉴카렌스': '076', '올 뉴 카렌스': '105', '더 뉴 카렌스': '127' } },
  {
    mnuftrCd: '002',
    modelGrpCd: '060', // K3
    models: {
      'K3': '103',
      '더 뉴 K3': '120',
      '올 뉴 K3': '136',
      'K3 GT': '142',
      '더 뉴 K3 2세대': '171',
      '더 뉴 K3 GT 2세대': '172',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '001', // K5
    models: {
      'K5': '092',
      'K5 하이브리드': '097',
      '더 뉴 K5': '106',
      'K5 2세대': '118',
      'K5 하이브리드 2세대': '121',
      '더 뉴 K5 2세대': '135',
      '더 뉴 K5 하이브리드 2세대': '139',
      'K5 3세대': '157',
      '신형 K5': '157',
      'K5 3세대 하이브리드': '162',
      '더 뉴 K5 3세대': '188',
      '더 뉴 K5 3세대 하이브리드': '189',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '002', // K7
    models: {
      'K7': '089',
      '더 프레스티지 K7': '096',
      '더 뉴 K7': '104',
      'K7 하이브리드': '111',
      '올 뉴 K7': '122',
      '올 뉴 K7 하이브리드': '129',
      'K7 프리미어': '152',
      'K7 프리미어 하이브리드': '154',
    },
  },
  {
    mnuftrCd: '002',
    modelGrpCd: '066', // K8
    models: {
      'K8': '169',
      'K8 하이브리드': '173',
      '더 뉴 K8': '196',
      '더 뉴 K8 하이브리드': '197',
    },
  },
  { mnuftrCd: '002', modelGrpCd: '059', models: { 'K9': '101', '더 뉴 K9': '117', '더 K9': '138', '더 뉴 K9 2세대': '174' } },
  { mnuftrCd: '002', modelGrpCd: '062', models: { '스팅어': '131', '스팅어 마이스터': '167' } },
  { mnuftrCd: '002', modelGrpCd: '067', models: { 'EV6': '170', '더 뉴 EV6': '195' } },
  { mnuftrCd: '002', modelGrpCd: '068', models: { 'EV9': '183' } },
  { mnuftrCd: '002', modelGrpCd: '069', models: { 'EV3': '194' } },
  { mnuftrCd: '002', modelGrpCd: '071', models: { 'EV4': '201' } },
  { mnuftrCd: '002', modelGrpCd: '073', models: { 'EV5': '203' } },

  // 현대 (001)
  {
    mnuftrCd: '001',
    modelGrpCd: '004', // 그랜저
    models: {
      '그랜저 TG': '040',
      '더 럭셔리 그랜저': '101',
      '그랜저 뉴 럭셔리': '103',
      '그랜저 HG': '106',
      '그랜저 HG 하이브리드': '125',
      '그랜저 IG': '141',
      '그랜저 IG 하이브리드': '143',
      '더 뉴 그랜저': '171',
      '더 뉴 그랜저 IG': '171',
      '더 뉴 그랜저 하이브리드': '174',
      '더 뉴 그랜저 IG 하이브리드': '174',
      '그랜저 (GN7)': '199',
      '그랜저 하이브리드 (GN7)': '200',
      '그랜저 (GN7) 하이브리드': '200',
      '더 뉴 그랜저 (GN7)': '230',
      '더 뉴 그랜저 하이브리드 (GN7)': '231',
    },
  },
  {
    mnuftrCd: '001',
    modelGrpCd: '019', // 아반떼
    models: {
      '아반떼 HD': '081',
      '아반떼 하이브리드': '095',
      '아반떼 MD': '104',
      '아반떼 쿠페': '121',
      '더 뉴 아반떼': '123',
      '아반떼 AD': '136',
      '더 뉴 아반떼 AD': '154',
      '아반떼 (CN7)': '176',
      '아반떼 하이브리드 (CN7)': '181',
      '아반떼 (CN7) 하이브리드': '181',
      '아반떼 N': '195',
      '더 뉴 아반떼 (CN7)': '206',
      '더 뉴 아반떼 하이브리드 (CN7)': '207',
      '더 뉴 아반떼 N': '211',
      '디 올 뉴 아반떼 (CN8)': '232',
      '디 올 뉴 아반떼 하이브리드 (CN8)': '233',
    },
  },
  {
    mnuftrCd: '001',
    modelGrpCd: '018', // 쏘나타
    models: {
      'NF 쏘나타': '039',
      'NF 쏘나타 트랜스폼': '092',
      'YF 쏘나타': '098',
      '쏘나타 하이브리드': '108',
      '쏘나타 더 브릴리언트': '115',
      'LF 쏘나타': '126',
      'LF 쏘나타 하이브리드': '128',
      '쏘나타 뉴 라이즈': '142',
      '쏘나타 뉴 라이즈 하이브리드': '144',
      '쏘나타 DN8': '163',
      '쏘나타 (DN8)': '163',
      '쏘나타 DN8 하이브리드': '169',
      '쏘나타 디 엣지': '203',
      '쏘나타 디 엣지 하이브리드': '204',
    },
  },
  {
    mnuftrCd: '001',
    modelGrpCd: '017', // 싼타페
    models: {
      '싼타페 CM': '080',
      '싼타페 DM': '111',
      '싼타페 더 프라임': '134',
      '싼타페 TM': '150',
      '더 뉴 싼타페': '177',
      '더 뉴 싼타페 하이브리드': '191',
      '디 올 뉴 싼타페': '208',
      '디 올 뉴 싼타페 하이브리드': '209',
    },
  },
  {
    mnuftrCd: '001',
    modelGrpCd: '032', // 투싼
    models: {
      '투싼 ix': '096',
      '뉴 투싼 ix': '122',
      '올 뉴 투싼': '133',
      '더 올뉴투싼': '133',
      '올 뉴 투싼 TL': '155',
      '투싼 (4세대)': '179',
      '투싼 4세대': '179',
      '투싼 (NX4)': '179',
      '투싼 하이브리드 (4세대)': '183',
      '투싼 (NX4) 하이브리드': '183',
      '더 뉴 투싼': '213',
      '더 뉴 투싼 하이브리드': '214',
    },
  },
  {
    mnuftrCd: '001',
    modelGrpCd: '058', // 팰리세이드
    models: {
      '팰리세이드': '157',
      '더 뉴 팰리세이드': '197',
      '디 올 뉴 팰리세이드': '221',
      '디 올 뉴 팰리세이드 하이브리드': '222',
    },
  },
  {
    mnuftrCd: '001',
    modelGrpCd: '055', // 코나
    models: {
      '코나': '146',
      '코나 일렉트릭': '152',
      '코나 하이브리드': '173',
      '더 뉴 코나': '180',
      '더 뉴 코나 하이브리드': '182',
      '코나 N': '194',
      '코나 (SX2)': '201',
      '코나 하이브리드 (SX2)': '202',
      '코나 일렉트릭 (SX2)': '205',
    },
  },
  { mnuftrCd: '001', modelGrpCd: '067', models: { '캐스퍼': '196', '캐스퍼 일렉트릭': '219', '더 뉴 캐스퍼': '220' } },
  {
    mnuftrCd: '001',
    modelGrpCd: '053', // 아이오닉
    models: {
      '아이오닉 하이브리드': '138',
      '아이오닉 일렉트릭': '139',
      '더 뉴 아이오닉 하이브리드': '161',
      '더 뉴 아이오닉 일렉트릭': '172',
      '아이오닉 5': '186',
      '아이오닉 6': '198',
      '아이오닉 5 N': '210',
      '더 뉴 아이오닉 5': '216',
      '아이오닉 9': '223',
      '더 뉴 아이오닉 6': '225',
    },
  },
  { mnuftrCd: '001', modelGrpCd: '063', models: { '스타리아': '185', '스타리아 하이브리드': '217', '더 뉴 스타리아': '227', '더 뉴 스타리아 하이브리드': '228' } },
  { mnuftrCd: '001', modelGrpCd: '015', models: { '그랜드 스타렉스': '083', '더 뉴 그랜드 스타렉스': '148' } },
  { mnuftrCd: '001', modelGrpCd: '059', models: { '베뉴': '167' } },
  { mnuftrCd: '001', modelGrpCd: '056', models: { '넥쏘': '151', '디 올 뉴 넥쏘': '224' } },
  { mnuftrCd: '001', modelGrpCd: '001', models: { 'i30': '084', 'i30(신형)': '117', '더 뉴 i30': '130', 'i30 (PD)': '140' } },
  { mnuftrCd: '001', modelGrpCd: '049', models: { 'i40': '109', 'i40 살룬': '110', '더 뉴 i40': '131', '더 뉴 i40 살룬': '132' } },
  { mnuftrCd: '001', modelGrpCd: '048', models: { '벨로스터': '107', '더 뉴 벨로스터': '129', '벨로스터 (JS)': '149', '벨로스터-N': '156' } },
  { mnuftrCd: '001', modelGrpCd: '050', models: { '맥스크루즈': '118', '더 뉴 맥스크루즈': '135' } },
  { mnuftrCd: '001', modelGrpCd: '025', models: { '제네시스 DH': '124' } },

  // 쉐보레 (003)
  { mnuftrCd: '003', modelGrpCd: '043', models: { '스파크': '075', '스파크 EV': '083', '더 넥스트 스파크': '086', '더 뉴 스파크': '096' } },
  { mnuftrCd: '003', modelGrpCd: '046', models: { '말리부': '079', '올 뉴 말리부': '088', '더 뉴 말리부': '098' } },
  { mnuftrCd: '003', modelGrpCd: '048', models: { '트랙스': '082', '더 뉴 트랙스': '092', '트랙스 크로스오버': '108' } },
  { mnuftrCd: '003', modelGrpCd: '055', models: { '트레일블레이저': '102', '더 뉴 트레일블레이저': '109' } },
  { mnuftrCd: '003', modelGrpCd: '041', models: { '크루즈': '073', '크루즈5': '078', '어메이징 뉴 크루즈': '084', '올 뉴 크루즈': '093' } },
  { mnuftrCd: '003', modelGrpCd: '040', models: { '올란도': '072' } },
  { mnuftrCd: '003', modelGrpCd: '052', models: { '이쿼녹스': '097', '더 넥스트 이쿼녹스': '107' } },
  { mnuftrCd: '003', modelGrpCd: '054', models: { '트래버스': '101', '더 뉴 트래버스': '111' } },
  { mnuftrCd: '003', modelGrpCd: '053', models: { '콜로라도': '100', '리얼 뉴 콜로라도': '103', '올 뉴 콜로라도': '110' } },
  { mnuftrCd: '003', modelGrpCd: '051', models: { '볼트 EV': '095', '뉴 볼트 EV': '104' } },
  { mnuftrCd: '003', modelGrpCd: '056', models: { '볼트 EUV': '105' } },

  // KGM (004)
  { mnuftrCd: '004', modelGrpCd: '013', models: { '토레스': '121', '토레스 EVX': '123', '더 뉴 토레스': '128', '더 뉴 토레스 하이브리드': '134', '뉴 토레스': '137', '뉴 토레스 하이브리드': '138' } },
  { mnuftrCd: '004', modelGrpCd: '012', models: { '티볼리': '107', '티볼리 에어': '108', '티볼리 아머': '112', '베리 뉴 티볼리': '116', '더 뉴 티볼리': '124', '더 뉴 티볼리 에어': '125' } },
  {
    mnuftrCd: '004',
    modelGrpCd: '003',
    models: {
      '렉스턴 W': '103',
      'G4 렉스턴': '111',
      '렉스턴 스포츠': '113',
      '렉스턴 스포츠 칸': '114',
      '올 뉴 렉스턴': '117',
      '더 뉴 렉스턴 스포츠': '118',
      '더 뉴 렉스턴 스포츠 칸': '119',
      '렉스턴 뉴 아레나': '122',
      '더 뉴 렉스턴 스포츠 쿨멘': '126',
      '더 뉴 렉스턴 스포츠 칸 쿨멘': '127',
    },
  },
  {
    mnuftrCd: '004',
    modelGrpCd: '011',
    models: {
      '코란도 C': '099',
      '코란도 스포츠': '102',
      '코란도 투리스모': '105',
      '뉴코란도 C': '106',
      '더 뉴 코란도 스포츠': '109',
      '뉴 스타일 코란도 C': '110',
      '뷰티풀 코란도': '115',
      '코란도 이모션': '120',
      '코란도 EV': '129',
    },
  },
  { mnuftrCd: '004', modelGrpCd: '006', models: { '액티언 (J120)': '130', '액티언 하이브리드 (J120)': '135' } },

  // 르노코리아 (005)
  { mnuftrCd: '005', modelGrpCd: '011', models: { 'QM6': '066', '더 뉴 QM6': '071', '뉴 QM6': '077', '더 뉴 QM6 F/L': '079' } },
  { mnuftrCd: '005', modelGrpCd: '010', models: { 'SM6': '065', '더 뉴 SM6': '074' } },
  { mnuftrCd: '005', modelGrpCd: '015', models: { 'XM3': '072', 'XM3 하이브리드': '078' } },
  { mnuftrCd: '005', modelGrpCd: '019', models: { '그랑 콜레오스': '082', '그랑 콜레오스 하이브리드': '083' } },
  { mnuftrCd: '005', modelGrpCd: '018', models: { '아르카나 하이브리드': '080', '아르카나': '081' } },
  { mnuftrCd: '005', modelGrpCd: '009', models: { 'QM3': '059', '뉴QM3': '067' } },
  { mnuftrCd: '005', modelGrpCd: '001', models: { 'SM3': '002', '뉴SM3': '054', 'SM3 네오': '062' } },
  { mnuftrCd: '005', modelGrpCd: '002', models: { '뉴SM5(신형)': '055', '뉴SM5 플래티넘': '058', 'SM5 노바': '064' } },
  { mnuftrCd: '005', modelGrpCd: '003', models: { 'All New SM7': '057', 'SM7 노바': '063' } },
  { mnuftrCd: '005', modelGrpCd: '014', models: { '마스터': '070', '뉴 마스터': '075' } },

  // 제네시스 (007)
  { mnuftrCd: '007', modelGrpCd: '001', models: { 'EQ900': '001' } },
  { mnuftrCd: '007', modelGrpCd: '003', models: { 'G70': '003', '더 뉴 G70': '008' } },
  {
    mnuftrCd: '007',
    modelGrpCd: '002',
    models: {
      'G80': '002',
      'G80 (RG3)': '007',
      'G80 (RG3) 일렉트리파이드': '010',
      'G80 (RG3 F/L)': '015',
      'G80 (RG3 F/L) 일렉트리파이드': '018',
    },
  },
  { mnuftrCd: '007', modelGrpCd: '004', models: { 'G90': '005', 'G90 (RS4)': '012' } },
  { mnuftrCd: '007', modelGrpCd: '007', models: { 'GV60': '011', '더 뉴 GV60': '020' } },
  { mnuftrCd: '007', modelGrpCd: '006', models: { 'GV70': '009', 'eGV70': '013', 'GV70 (F/L)': '017', 'eGV70 (F/L)': '019' } },
  { mnuftrCd: '007', modelGrpCd: '005', models: { 'GV80': '006', 'GV80 쿠페': '014', 'GV80 (F/L)': '016', 'GV80 하이브리드': '022' } },

  // 아우디 (011)
  { mnuftrCd: '011', modelGrpCd: '001', models: { 'A3 (8Y)': '063', '뉴 A3': '024' } },
  { mnuftrCd: '011', modelGrpCd: '002', models: { 'A4 (B9)': '041', '뉴 A4 (B8)': '011' } },
  { mnuftrCd: '011', modelGrpCd: '021', models: { 'A5 (B10)': '078', 'A5 (F5)': '047' } },
  { mnuftrCd: '011', modelGrpCd: '004', models: { 'A6 (C9)': '083', 'A6 (C8)': '048', '뉴 A6 (C7)': '004' } },
  { mnuftrCd: '011', modelGrpCd: '025', models: { 'A7 (4K)': '051', 'A7': '030' } },
  { mnuftrCd: '011', modelGrpCd: '003', models: { 'A8 (D5)': '052', '뉴 A8 (D4)': '013' } },
  { mnuftrCd: '011', modelGrpCd: '026', models: { 'Q3 (F3)': '049', 'Q3': '031' } },
  { mnuftrCd: '011', modelGrpCd: '039', models: { 'Q4 e-트론': '067' } },
  { mnuftrCd: '011', modelGrpCd: '020', models: { 'Q5 (FY)': '053', 'Q5': '025' } },
  { mnuftrCd: '011', modelGrpCd: '013', models: { 'Q7 (4M)': '040', 'Q7': '016' } },
  { mnuftrCd: '011', modelGrpCd: '034', models: { 'Q8 (4M)': '050' } },
  { mnuftrCd: '011', modelGrpCd: '036', models: { 'e-트론': '058' } },

  // BMW (012)
  { mnuftrCd: '012', modelGrpCd: '001', models: { '1시리즈 (F70)': '103', '1시리즈 (F40)': '076', '1시리즈 (F20)': '020' } },
  { mnuftrCd: '012', modelGrpCd: '018', models: { '2시리즈 그란쿠페 (F44)': '072', '2시리즈 액티브 투어러 (U06)': '090' } },
  { mnuftrCd: '012', modelGrpCd: '002', models: { '3시리즈 (G20)': '069', '3시리즈 (F30)': '038', '3시리즈 (E90)': '001' } },
  { mnuftrCd: '012', modelGrpCd: '017', models: { '4시리즈 (G22)': '082', '4시리즈 (F32)': '012' } },
  { mnuftrCd: '012', modelGrpCd: '003', models: { '5시리즈 (G60)': '095', '5시리즈 (G30)': '060', '5시리즈 (F10)': '039' } },
  { mnuftrCd: '012', modelGrpCd: '004', models: { '6시리즈 (F12)': '018' } },
  { mnuftrCd: '012', modelGrpCd: '015', models: { '6시리즈 GT (G32)': '061', '3시리즈 GT (F34)': '029', '5시리즈 GT (F07)': '026' } },
  { mnuftrCd: '012', modelGrpCd: '005', models: { '7시리즈 (G70)': '091', '7시리즈 (G11 F/L)': '066', '7시리즈 (G11)': '036', '7시리즈 (F01)': '003' } },
  { mnuftrCd: '012', modelGrpCd: '006', models: { '8시리즈 (G15)': '077' } },
  { mnuftrCd: '012', modelGrpCd: '014', models: { 'X1 (U11)': '094', 'X1 (F48)': '037' } },
  { mnuftrCd: '012', modelGrpCd: '007', models: { 'X3 (G45)': '100', 'X3 (G01)': '062', 'X3 (F25)': '028' } },
  { mnuftrCd: '012', modelGrpCd: '020', models: { 'X4 (G02)': '068', 'X4 (F26)': '033' } },
  { mnuftrCd: '012', modelGrpCd: '008', models: { 'X5 (G05)': '065', 'X5 (F15)': '030', 'X5 (E70)': '022' } },
  { mnuftrCd: '012', modelGrpCd: '011', models: { 'X6 (G06)': '078', 'X6 (F16)': '023' } },
  { mnuftrCd: '012', modelGrpCd: '032', models: { 'X7 (G07)': '071' } },
  { mnuftrCd: '012', modelGrpCd: '038', models: { 'i4 (G26)': '087' } },
  { mnuftrCd: '012', modelGrpCd: '042', models: { 'i5 (G60)': '097' } },
  { mnuftrCd: '012', modelGrpCd: '036', models: { 'iX3 (G08)': '085' } },

  // 벤츠 (013)
  { mnuftrCd: '013', modelGrpCd: '029', models: { 'A-클래스 W177': '087', 'A-클래스 W176': '064' } },
  { mnuftrCd: '013', modelGrpCd: '001', models: { 'C-클래스 W206': '096', 'C-클래스 W205': '067', 'C-클래스 W204': '012' } },
  { mnuftrCd: '013', modelGrpCd: '031', models: { 'CLA-클래스 C118': '088', 'CLA-클래스 C117': '066' } },
  { mnuftrCd: '013', modelGrpCd: '003', models: { 'CLS-클래스 C257': '083', 'CLS-클래스 W218': '062' } },
  { mnuftrCd: '013', modelGrpCd: '004', models: { 'E-클래스 W214': '104', 'E-클래스 W213': '072', 'E-클래스 W212': '001' } },
  { mnuftrCd: '013', modelGrpCd: '005', models: { 'S-클래스 W223': '092', 'S-클래스 W222': '065', 'S-클래스 W221': '002' } },
  { mnuftrCd: '013', modelGrpCd: '032', models: { 'GLA-클래스 H247': '091', 'GLA-클래스 X156': '068' } },
  { mnuftrCd: '013', modelGrpCd: '038', models: { 'GLB-클래스 X247': '089' } },
  { mnuftrCd: '013', modelGrpCd: '034', models: { 'GLC-클래스 X254': '101', 'GLC-클래스 X253': '071' } },
  { mnuftrCd: '013', modelGrpCd: '035', models: { 'GLE-클래스 W167': '086', 'GLE-클래스 W166': '070' } },
  { mnuftrCd: '013', modelGrpCd: '037', models: { 'GLS-클래스 X167': '093', 'GLS-클래스 X166': '074' } },
  { mnuftrCd: '013', modelGrpCd: '013', models: { 'G-클래스 W465': '106', 'G-클래스 W463b': '085', 'G-클래스 W463': '010' } },
  { mnuftrCd: '013', modelGrpCd: '040', models: { 'EQA H243': '094' } },
  { mnuftrCd: '013', modelGrpCd: '042', models: { 'EQB X243': '097' } },
  { mnuftrCd: '013', modelGrpCd: '044', models: { 'EQE V295': '098', 'EQE SUV X294': '102' } },
  { mnuftrCd: '013', modelGrpCd: '041', models: { 'EQS V297': '095', 'EQS SUV X296': '099' } },

  // 볼보 (017)
  { mnuftrCd: '017', modelGrpCd: '009', models: { 'S60 3세대': '028', 'S60': '008' } },
  { mnuftrCd: '017', modelGrpCd: '015', models: { 'S90': '016' } },
  { mnuftrCd: '017', modelGrpCd: '017', models: { 'V60 크로스컨트리 2세대': '029', 'V60 크로스컨트리': '022' } },
  { mnuftrCd: '017', modelGrpCd: '022', models: { 'V90 크로스컨트리': '025' } },
  { mnuftrCd: '017', modelGrpCd: '023', models: { 'XC40 리차지': '031', 'XC40': '027' } },
  { mnuftrCd: '017', modelGrpCd: '016', models: { 'XC60 2세대': '026', 'XC60': '017' } },
  { mnuftrCd: '017', modelGrpCd: '010', models: { 'XC90 2세대': '024', 'XC90': '010' } },

  // 렉서스 (035)
  { mnuftrCd: '035', modelGrpCd: '001', models: { '올 뉴 ES': '066', 'ES300h 7세대': '053', '뉴 ES300h': '037', '뉴 ES350': '036' } },
  { mnuftrCd: '035', modelGrpCd: '013', models: { 'NX350h': '058', 'NX450h+': '059', 'NX300h': '034', 'NX300': '048' } },
  { mnuftrCd: '035', modelGrpCd: '005', models: { 'RX 5세대': '060', 'RX450hL 4세대': '055', 'RX450h 4세대': '044', 'RX350 4세대': '043', 'RX450h': '028' } },
  { mnuftrCd: '035', modelGrpCd: '016', models: { 'UX300h': '063', 'UX250h': '054' } },

  // 테슬라 (087)
  { mnuftrCd: '087', modelGrpCd: '003', models: { '모델 3 하이랜드': '005', '모델 3': '003' } },
  { mnuftrCd: '087', modelGrpCd: '004', models: { '모델 Y 주니퍼': '006', '모델 Y': '004' } },
  { mnuftrCd: '087', modelGrpCd: '001', models: { '모델 S': '001' } },
  { mnuftrCd: '087', modelGrpCd: '002', models: { '모델 X': '002' } },
  { mnuftrCd: '087', modelGrpCd: '005', models: { '사이버트럭': '007' } },
];

import { KCAR_GRADE_TREE } from './kcarGradeData';

const normalizeModelKey = (s: string): string => s.replace(/[\s()\-_/]+/g, '').toUpperCase();

export function resolveKcarGradeCodes(
  mnuftrCd: string,
  modelGrpCd: string,
  modelCd: string,
  subModel: string = '',
  rawCarName: string = ''
): { grdCd?: string; grdDtlCd?: string } {
  if (!subModel || !subModel.trim() || subModel.trim() === '전체' || subModel.trim() === '-') {
    return {};
  }

  const mKey = `${mnuftrCd},${modelGrpCd},${modelCd}`;
  const grdMap = KCAR_GRADE_TREE[mKey];
  if (!grdMap) return {};

  const subStr = subModel.trim();
  const combinedSrc = `${rawCarName} ${subStr}`.trim();
  const combNorm = normalizeModelKey(combinedSrc);

  const hasTurbo = combNorm.includes('터보') || /\d\.\d\s*T(?![A-Z])/i.test(combinedSrc);
  const hasVan = combNorm.includes('밴') || combNorm.includes('카고');
  const hasLpg = combNorm.includes('LPG') || combNorm.includes('LPI') || combNorm.includes('LPE');
  const hasDiesel =
    combNorm.includes('디젤') ||
    combNorm.includes('VGT') ||
    combNorm.includes('TDI') ||
    combNorm.includes('CDI') ||
    /\d\.\d\s*D(?![A-Z])/i.test(combinedSrc);
  const hasGasoline =
    combNorm.includes('가솔린') ||
    combNorm.includes('GDI') ||
    combNorm.includes('GDE') ||
    combNorm.includes('GTE') ||
    combNorm.includes('MPI') ||
    combNorm.includes('휘발유');

  const has4wd =
    combNorm.includes('4WD') ||
    combNorm.includes('AWD') ||
    combNorm.includes('4MATIC') ||
    combNorm.includes('XDRIVE') ||
    combNorm.includes('QUATTRO');
  const has2wd = combNorm.includes('2WD') || combNorm.includes('FF');

  const seatM = combinedSrc.match(/(\d+)\s*인승/);
  const targetSeat = seatM ? `${seatM[1]}인승` : '';

  let dispMatches = combinedSrc.match(/(\d\.\d)/g) || [];
  if (dispMatches.length === 0) {
    const mHg = combNorm.match(/(?:HG|TG|IG|K7|K5|SM[3567])\s*(\d)(\d)0/);
    if (mHg) dispMatches = [`${mHg[1]}.${mHg[2]}`];
  }
  const targetDisp = dispMatches[0] || '';

  const specialKeywords = [
    '하이리무진', '아웃도어', '캠핑', '특장', '택시', '장애인',
    '렌터카', '수출', '운전교습', '어린이', '킨더', '구급', '휠체어',
    'N라인', 'NLINE', 'GT',
  ];

  const allGrdKeys = Object.keys(grdMap);
  const nonVanGrds = allGrdKeys.filter(k => {
    const nk = normalizeModelKey(k);
    return !nk.includes('밴') && !nk.includes('카고');
  });
  const baseGrds = nonVanGrds.length > 0 ? nonVanGrds : allGrdKeys;
  const turboFlags = baseGrds.map(
    k => normalizeModelKey(k).includes('터보') || /\d\.\d\s*T(?![A-Z])/i.test(k)
  );
  const hasBothTurboAndNa = turboFlags.some(Boolean) && !turboFlags.every(Boolean);

  const specIgnore = new Set([
    '가솔린', '디젤', '전기', 'EV', '하이브리드', 'HEV', 'LPG', 'LPI', 'LPE',
    '2WD', '4WD', 'AWD', 'FF', 'FR', '터보', '일반인판매용', '일반판매용', '일반인',
    '롱레인지', '스탠다드',
  ]);
  const extraSuffixes = [
    '스페셜', '플러스', 'PLUS', '스포츠', '베이직', '라이트',
    '초이스', '어드밴스', '프리미어', '익스트림', 'TUIX', '살롱',
  ];

  let bestGrdCd = '';
  let bestDtlCd = '';
  let bestScore = -999;

  for (const [grdNm, gObj] of Object.entries(grdMap)) {
    const grdCd = gObj.cd;
    const dtlMap = gObj.dtl || {};
    const gNorm = normalizeModelKey(grdNm);

    // (A) 밴/카고 분리
    const gIsVan = gNorm.includes('밴') || gNorm.includes('카고');
    if (hasVan !== gIsVan) continue;

    // (B) 터보 분리
    const gIsTurbo = gNorm.includes('터보') || /\d\.\d\s*T(?![A-Z])/i.test(grdNm);
    if (hasBothTurboAndNa && hasTurbo !== gIsTurbo) continue;

    // (C) 인승 분리
    const gSeatM = grdNm.match(/(\d+)\s*인승/);
    const gSeat = gSeatM ? `${gSeatM[1]}인승` : '';
    if (targetSeat && gSeat && targetSeat !== gSeat) continue;

    // (D) 배기량 분리
    const gDispM = grdNm.match(/(\d\.\d)/);
    const gDisp = gDispM ? gDispM[1] : '';
    if (targetDisp && gDisp && targetDisp !== gDisp) continue;

    // (E) 유종 분리
    const gIsLpg = gNorm.includes('LPG') || gNorm.includes('LPI') || gNorm.includes('LPE');
    const gIsDiesel = gNorm.includes('디젤') || gNorm.includes('VGT') || gNorm.includes('TDI');
    const gIsGas =
      gNorm.includes('가솔린') ||
      gNorm.includes('GDI') ||
      gNorm.includes('GDE') ||
      gNorm.includes('GTE') ||
      gNorm.includes('MPI') ||
      gNorm.includes('VVT');

    if (hasLpg && !gIsLpg && (gIsDiesel || gIsGas)) continue;
    if (!hasLpg && gIsLpg) continue;
    if (hasDiesel && gIsGas) continue;
    if (hasGasoline && gIsDiesel) continue;
    if (!hasGasoline && gIsGas && allGrdKeys.some(k => !normalizeModelKey(k).includes('가솔린'))) {
      if (hasDiesel || allGrdKeys.some(k => k.includes('9인승') || k.includes('11인승'))) {
        continue;
      }
    }

    // (F) 구동계 분리
    const gIs4wd = gNorm.includes('4WD') || gNorm.includes('AWD');
    const gIs2wd = gNorm.includes('2WD');
    if (has4wd && gIs2wd) continue;
    if (has2wd && gIs4wd) continue;
    if (!has4wd && !has2wd && (gIs4wd || gIs2wd)) continue;

    // (G) 특수 파생 키워드 검증
    let skipSpecial = false;
    for (const sp of specialKeywords) {
      const spN = normalizeModelKey(sp);
      if (gNorm.includes(spN) && !combNorm.includes(spN)) {
        skipSpecial = true;
        break;
      }
    }
    if (skipSpecial) continue;
    if (gNorm.includes('리무진') && !gNorm.includes('하이리무진') && !combNorm.includes('리무진')) {
      continue;
    }

    let score = 0;
    if (allGrdKeys.length === 1) score += 5;
    if (targetDisp && gDisp === targetDisp) score += 10;
    if (targetSeat && gSeat === targetSeat) score += 10;
    if (hasTurbo && gIsTurbo) score += 8;
    if (has2wd && gIs2wd) score += 6;
    if (has4wd && gIs4wd) score += 6;
    if (hasDiesel && gIsDiesel) score += 5;
    if (hasGasoline && gIsGas) score += 5;
    if (hasLpg && gIsLpg) score += 5;
    if (gNorm.includes('일반')) score += 2;

    const grdTokens = grdNm
      .split(/[\s()/\-]+/)
      .map(t => normalizeModelKey(t))
      .filter(t => t && !specIgnore.has(t));
    const nonSpecTokens = grdTokens.filter(
      t => !/^(\d+\.\d+T?|\d+인승|GDI|GDE|GTE|VGT|EVGT|VVT|MPI|LPE|TDI)$/.test(t)
    );

    if (nonSpecTokens.length > 0) {
      if (nonSpecTokens.every(t => combNorm.includes(t))) {
        let badSuffix = false;
        for (const ex of extraSuffixes) {
          if (gNorm.includes(ex) && !combNorm.includes(ex)) {
            badSuffix = true;
            break;
          }
        }
        if (badSuffix) continue;
        score += 20 + nonSpecTokens.reduce((acc, t) => acc + t.length, 0);
      } else {
        continue;
      }
    }

    let matchedDtlCd = '';
    let dtlBestLen = 0;
    for (const [dNm, dCd] of Object.entries(dtlMap)) {
      const dNorm = normalizeModelKey(dNm);
      if (!dNorm) continue;
      if (combNorm.includes(dNorm)) {
        if (dNorm.length > dtlBestLen) {
          dtlBestLen = dNorm.length;
          matchedDtlCd = dCd;
        }
      }
    }

    const totalScore = score + (matchedDtlCd ? 15 + dtlBestLen : 0);
    if (totalScore > bestScore) {
      bestScore = totalScore;
      bestGrdCd = grdCd;
      bestDtlCd = matchedDtlCd;
    }
  }

  if (bestScore <= 0 && !bestDtlCd) return {};
  return {
    grdCd: bestGrdCd || undefined,
    grdDtlCd: bestDtlCd || undefined,
  };
}

export function resolveKcarModelCodes(
  rawBaseName: string,
  brandHint: string = '',
  subModel: string = ''
): { mnuftrCd: string; modelGrpCd: string; modelCd: string; grdCd?: string; grdDtlCd?: string } | null {
  if (!rawBaseName || !rawBaseName.trim()) return null;

  let text = rawBaseName.trim();
  let detectedMnuftrCd = '';

  const sortedBrands = Object.keys(KCAR_MNUFTR_MAP).sort((a, b) => b.length - a.length);
  for (const bName of sortedBrands) {
    if (text.startsWith(bName)) {
      detectedMnuftrCd = KCAR_MNUFTR_MAP[bName];
      text = text.slice(bName.length).trim();
      break;
    }
  }

  if (!detectedMnuftrCd && brandHint && brandHint.trim() && brandHint.trim() !== '전체') {
    const bHint = brandHint.trim();
    for (const bName of sortedBrands) {
      if (bName.includes(bHint) || bHint.includes(bName)) {
        detectedMnuftrCd = KCAR_MNUFTR_MAP[bName];
        break;
      }
    }
  }

  const normText = normalizeModelKey(text);
  if (!normText) return null;

  const subNorm = normalizeModelKey(subModel || '');
  const isHevSub =
    (subNorm.includes('HEV') || subNorm.includes('하이브리드')) && !normText.includes('하이브리드');

  const candidates: Array<{ len: number; mnuftrCd: string; modelGrpCd: string; modelCd: string }> = [];
  for (const grp of KCAR_MODEL_GROUPS) {
    if (detectedMnuftrCd && grp.mnuftrCd !== detectedMnuftrCd) continue;
    for (const [mName, modCd] of Object.entries(grp.models)) {
      if (mName === '하이브리드 4세대' && !rawBaseName.includes('카니발')) continue;
      const nm = normalizeModelKey(mName);
      if (nm && (normText === nm || normText.startsWith(nm))) {
        candidates.push({
          len: nm.length,
          mnuftrCd: grp.mnuftrCd,
          modelGrpCd: grp.modelGrpCd,
          modelCd: modCd,
        });
      } else if (isHevSub && nm.includes('하이브리드')) {
        const nmNoHev = nm.replace('하이브리드', '');
        if (nmNoHev && (normText === nmNoHev || normText.startsWith(nmNoHev))) {
          candidates.push({
            len: nm.length + 10,
            mnuftrCd: grp.mnuftrCd,
            modelGrpCd: grp.modelGrpCd,
            modelCd: modCd,
          });
        }
      }
    }
  }

  if (candidates.length > 0) {
    candidates.sort((a, b) => b.len - a.len);
    const best = candidates[0];
    const grdRes = resolveKcarGradeCodes(best.mnuftrCd, best.modelGrpCd, best.modelCd, subModel, rawBaseName);
    return {
      mnuftrCd: best.mnuftrCd,
      modelGrpCd: best.modelGrpCd,
      modelCd: best.modelCd,
      ...grdRes,
    };
  }

  return null;
}

export function buildKcarSearchUrl(params: {
  carName: string;
  detailModel?: string;
  manufacturer?: string;
  yearModel?: number | string;
  mileageKm?: number | string;
}): string {
  const cond: Record<string, any> = {};
  const searchText = (params.carName || '').trim();
  const subText = (params.detailModel || '').trim();
  const codes = searchText ? resolveKcarModelCodes(searchText, params.manufacturer || '', subText) : null;

  if (codes) {
    cond.wr_eq_mnuftr_cd = codes.mnuftrCd;
    cond.wr_eq_model_grp_cd = codes.modelGrpCd;
    cond.wr_eq_model_cd = codes.modelCd;
    if (codes.grdCd) {
      cond.wr_eq_grd_cd = codes.grdCd;
      if (codes.grdDtlCd) {
        cond.wr_eq_grd_dtl_cd = codes.grdDtlCd;
      }
    }
  } else if (searchText) {
    cond.wr_txt_idx = searchText;
    cond.wr_in_model_nm = searchText;
  }

  if (params.yearModel && Number(params.yearModel) > 0) {
    const yVal = Number(params.yearModel);
    const kcarYear = yVal < 100 ? 2000 + yVal : yVal;
    cond.wr_gt_mfg_dt = `${kcarYear - 1}01`;
    cond.wr_lt_mfg_dt = `${kcarYear + 1}12`;
  }

  if (params.mileageKm && Number(params.mileageKm) > 0) {
    const milVal = Number(params.mileageKm);
    const roundedMil = Math.round(milVal / 10000) * 10000;
    cond.wr_gt_milg = Math.max(0, roundedMil - 30000);
    cond.wr_lt_milg = roundedMil + 30000;
  }

  if (Object.keys(cond).length > 0) {
    return `https://www.kcar.com/bc/search?searchCond=${encodeURIComponent(JSON.stringify(cond))}`;
  }
  return 'https://www.kcar.com/bc/search';
}
