# J-PRO 현재 동작 코드 감사 (Code Audit) 소스

> **제미나이(NotebookLM / Gemini Web) 지시문**:
> 이 문서는 대한민국 중고차 딜러용 입찰/시세 산출 시스템(J-PRO)의 **현재 실제 운영 중인 소스코드**와 **실제 발생한 2가지 치명적 버그 사례**입니다.
> 
> 당신의 임무는 아래 원본 코드를 정밀 분석하여:
> 1. 왜 이 코드 구조에서 옵션 텍스트가 5조각으로 파편화되는지 시스템적 원인 규명
> 2. 왜 헤이딜러 조회 시 등급 기본사양이 유료 추가옵션으로 둔갑하여 7개로 불어나는지 데이터 흐름상 원인 규명
> 3. 특정 차종 전용 if문 땜질이 아닌, 모든 차종에 공통 적용 가능한 근본적 아키텍처 해결책 제시
> 를 수행하는 것입니다.

---

## 1. 실제 발생한 2대 버그 현장 실측 데이터

### [사례 A] 신차 옵션 1개가 5개 칩으로 쪼개지는 버그 (쏘나타 디엣지 26년식)
- **신차 카탈로그 원본 (정상 1개 옵션)**:
  ```text
  ▶ 빌트인 캠 2, 증강현실 내비게이션 450,000
  ※ 내비게이션 선택 시 가능
  ※ 주행/주차 중 녹화 지원
  ```
- **현재 콕핏 UI 렌더링 결과 (5개 칩으로 파편화)**:
  - 칩 1: `빌트인 캠 2`
  - 칩 2: `증강현실 내비게이션`
  - 칩 3: `※ 내비게이션 선택 시 가능`
  - 칩 4: `※ 주행`
  - 칩 5: `주차 중 녹화 지원(45만)`
- **증상**: 쉼표(`,`)와 슬래시(`/`), 개행(`\n`)이 옵션 내부 글자인데도 무차별 구분자로 오인되어 1개 패키지가 5개 칩으로 박살 남.

### [사례 B] 등급 기본 사양 48개가 유료 추가옵션으로 둔갑하는 버그 (동일 차량 비교)
- **엔카 상세 "이 차만의 옵션" (실제 유료 출고옵션 2개)**:
  1. `세레니티 화이트 펄(W6H) 외장 컬러` (8만원)
  2. `빌트인 캠 2, 증강현실 내비게이션` (45만원)
- **차얼마 원천 데이터 (실제 유료 출고옵션 1개)**:
  1. `빌트인 캠 2` (450,000원)
- **현재 콕핏 사이드바 헤이딜러 조회 결과 (엉뚱한 7개 노출)**:
  - `빌트인 캠 2 + 증강현실 내비게이션(45만)`
  - `파노라마 선루프(119만)` ➔ **해당 트림 기본장착 사양인데 유료옵션으로 오인!**
  - `세레니티 화이트 펄`
  - `나파가죽 시트` ➔ **해당 트림 기본장착 사양인데 유료옵션으로 오인!**
  - `BOSE 프리미엄 사운드(64만)` ➔ **해당 트림 기본장착 사양인데 유료옵션으로 오인!**
  - `※ 내비게이션 선택 시 가능`
  - `★ 주행`

---

## 2. [문제의 원본 코드 1] 옵션을 무차별 분해하는 프론트 파서
**파일 경로**: `frontend/src/services/biddingOptionCatalog.ts` (L622 ~ L665)

```typescript
/**
 * 괄호 안의 쉼표나 상세 설명을 보존하면서 개별 옵션 단위로 안전하게 분리하는 스마트 파서
 * - 타이어 규격(245/45R20, 275/40R20 등)의 슬래시(/) 및 쉼표(,) 쪼개짐 방지 보존
 */
export const splitOptionString = (optStr: string): string[] => {
  if (!optStr) return [];
  // [옵션총액: 354만], [순정옵션총액: ...] 등 메타 태그 사전 분리/제거
  let cleanedStr = String(optStr)
    .replace(/\[(?:순정)?옵션총액[^\]]*\]/gi, '')
    .trim();
  if (!cleanedStr || ['없음', '-', '없음(구버전점검)', '⚠️조회실패', '코드매칭실패', '기본'].includes(cleanedStr)) {
    return [];
  }

  // 🚗 [타이어 규격 보존 전처리]
  cleanedStr = cleanedStr.replace(/(?<=\b|\D)(\d{3})\/(\d{2}(?:\s*[-a-zA-Z]{1,2}\s*\d{2})?)(?=\b|\D)/g, '$1__SLASH__$2');
  cleanedStr = cleanedStr.replace(/(\([앞전뒤후]\))\s*,\s*(\d{3}__SLASH__)/g, '$1__COMMA__$2');

  const results: string[] = [];
  let current = '';
  let depth = 0;

  for (let i = 0; i < cleanedStr.length; i++) {
    const ch = cleanedStr[i];
    if (ch === '(' || ch === '[' || ch === '{') {
      depth++;
      current += ch;
    } else if (ch === ')' || ch === ']' || ch === '}') {
      depth = Math.max(0, depth - 1);
      current += ch;
    } else if (depth === 0 && (ch === '/' || ch === '·' || ch === '\n' || ch === ',')) {
      // ⚠️ 치명적 결함 지점:
      // depth가 0(괄호 바깥)이면 '/', '·', '\n', ','를 무조건 옵션 간 구분자로 판정하여 분리함!
      // "빌트인 캠 2, 증강현실 내비게이션"의 쉼표(,)와
      // "주행/주차 중 녹화 지원"의 슬래시(/)가 모조리 여기서 찢어짐!
      const trimmed = current.trim();
      if (trimmed) results.push(trimmed);
      current = '';
    } else {
      current += ch;
    }
  }

  const lastTrimmed = current.trim();
  if (lastTrimmed) results.push(lastTrimmed);

  return results
    .map(o => o.replace(/__SLASH__/g, '/').replace(/__COMMA__/g, ', ').replace(/\[(?:순정)?옵션총액[^\]]*\]/gi, '').trim())
    .filter(o => o.length > 0 && !['없음', '-', '기본'].includes(o));
};
```

---

## 3. [문제의 원본 코드 2] 기본사양 48개를 유료옵션으로 밀어 넣는 백엔드
**파일 경로**: `services/heydealer_service.py` (L86 ~ L121)

```python
def enrich_heydealer_options(car_dict: dict) -> dict:
    # ... (생략) ...
    def _process_single(target_d: dict) -> tuple:
        if not isinstance(target_d, dict):
            return [], "", []
        d = target_d.get('detail') if isinstance(target_d.get('detail'), dict) else target_d
        
        # 1. car_spec.description 우선 파싱 (실차주가 적은 신차 추가옵션)
        s_desc = ""
        if isinstance(d.get('car_spec'), dict):
            s_desc = d.get('car_spec', {}).get('description') or ""
        if not s_desc and isinstance(target_d.get('car_spec'), dict):
            s_desc = target_d.get('car_spec', {}).get('description') or ""
        if not s_desc:
            s_desc = str(d.get('spec_description') or target_d.get('spec_description') or "")

        parsed_spec = parse_heydealer_options(s_desc)

        # 2. advanced_options(loaded) 폴백
        adv_list = d.get('advanced_options') or target_d.get('advanced_options') or []
        adv_opts = []
        if isinstance(adv_list, list):
            for o in adv_list:
                # ⚠️ 치명적 결함 지점:
                # 헤이딜러의 advanced_options 중 choice == 'loaded'는 유료옵션이 아니라
                # "차량에 장착된 48개 주요 기본/선택 사양 전체"를 뜻함!
                if isinstance(o, dict) and o.get('choice') == 'loaded':
                    name = o.get('name') or (o.get('content', {}).get('option_name') if isinstance(o.get('content'), dict) else None)
                    if name and str(name).strip():
                        adv_opts.append(str(name).strip())

        # ⚠️ 치명적 결함 지점 (L112):
        # parsed_spec(실차주 입력)이 비어있으면, 48개 전체 장착사양(선루프, 가죽시트, 스마트키 등 기본품목 포함)을
        # 그대로 final_opts(유료 추가옵션)로 삼아버림!
        final_opts = parsed_spec if parsed_spec else adv_opts
        final_opts = [str(x).strip() for x in final_opts if str(x).strip()]
        opt_text = " · ".join(final_opts) if final_opts else ""

        return final_opts, opt_text, opt_items
```

---

## 4. [문제의 원본 코드 3] 콕핏 프론트엔드의 옵션 출처 불일치
**파일 경로**: `frontend/src/components/BiddingCockpit/hooks/useBiddingCockpit.ts`

### 1) 헤이딜러 URL 조회 시 (L1250 ~ L1254)
```typescript
// ⚠️ 백엔드 heydealer_service의 오염된 options_text를 그대로 꽂음
const optionsResult = detail.options_text || carData.options_text || resJson.data?.options_text ||
  (Array.isArray(detail.parsed_options) ? detail.parsed_options.join(' · ') : '') ||
  (Array.isArray(carData.parsed_options) ? carData.parsed_options.join(' · ') : '');

// targetOptions(정밀 OptionItem 배열)는 세팅하지 않고, optionsTag(문자열)만 세팅함!
setOptionsTag(optionsResult);
```

### 2) 차량번호 조회 시 (L873 ~ L885)
```typescript
// ✅ 차얼마 API에서 유료 추가옵션만 정제되어 넘어옴
if (res.options && res.options.length > 0) {
  setTargetOptions(res.options); // [{name: '빌트인 캠 2', price: 450000}, ...]
  const optStr = res.options.map(o => `${o.name}(${o.price_man || Math.round(o.price / 10000)}만)`).join(' · ');
  const totalOptMan = res.total_option_price ? Math.round(res.total_option_price / 10000) : ...;
  calculatedOptionsTag = `${optStr} [옵션총액: ${totalOptMan}만]`;
  setOptionsTag(calculatedOptionsTag);
}
```

---

## 5. [신차 카탈로그 정규화 기준 DB 구조]
**파일 경로**: `data/encar_newcar_catalog.json` (백엔드 크롤링 데이터 샘플)

```json
{
  "현대_쏘나타디엣지(dn8)_2026": {
    "grades": ["1.6 터보 가솔린 프리미엄", "1.6 터보 가솔린 익스클루시브", "1.6 터보 가솔린 인스퍼레이션"],
    "options": {
      "파노라마 선루프": { "price": 1190000 },
      "빌트인 캠 2, 증강현실 내비게이션": { 
        "price": 450000, 
        "desc": "※ 내비게이션 선택 시 가능 ※ 주행/주차 중 녹화 지원" 
      },
      "BOSE 프리미엄 사운드": { "price": 640000 }
    },
    "packages": {
      "빌트인 캠 2, 증강현실 내비게이션": "빌트인 캠 2, 증강현실 내비게이션, 보조배터리"
    }
  }
}
```

---

## 6. 제미나이에게 요구하는 질문 (Prompt to Gemini)

아래 질문을 복사하여 제미나이에게 전달하세요:

> 1. `splitOptionString` 함수에서 타이어 규격(`245/45R20`)은 정규식으로 보호하면서, 왜 `빌트인 캠 2, 증강현실 내비게이션` 같은 복합 옵션명은 쪼개질 수밖에 없는지 구조적 한계를 분석해줘.
> 2. `encar_newcar_catalog.json`의 공식 옵션명 목록을 사전 지식(Dictionary)으로 활용하여, split 분해 전에 복합 옵션명을 보호하거나, 분해 후에 카탈로그 기준으로 재결합하는 가장 우아한 TypeScript 정규화 알고리즘을 제안해줘.
> 3. `heydealer_service.py`에서 `parsed_spec`이 없을 때 `advanced_options(loaded)` 48개를 폴백으로 넣는 로직이 왜 중고차 시세 산출에서 치명적인 독(Poison)이 되는지 설명하고, 차얼마 API를 단일 진실 공급원(SSOT)으로 삼는 올바른 백엔드 수정 방안을 제시해줘.
