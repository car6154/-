import React, { useState, useEffect, useRef } from 'react';
import { ExternalLink, RefreshCw, AlertCircle, Car, CheckCircle2 } from 'lucide-react';
import { KcarCarItem, KcarDetailData } from '@/components/BiddingCockpit/types';
import { CarDamageDiagram2D } from '@/components/BiddingCockpit/Sections/CarDamageDiagram2D';
import { getCarColorStyle } from '@/utils/carColor';
import { NewCarCatalogData } from '@/services/biddingOptionCatalog';
import { matchOptionsSingle, BackendMatchedOption, getCachedCarMatchedOptions } from '@/services/optionMatchingService';

export interface SelectedKcarDetailV2SectionProps {
  selectedKcar: KcarCarItem | null;
  targetCatalog?: NewCarCatalogData | null;
}

// 사고 구분 포맷팅 (케이카 기준)
const formatKcarAccident = (rawType?: string) => {
  if (!rawType || rawType === '무사고' || rawType.includes('완전무사고')) {
    return { text: '🟢 완전무사고', style: 'text-emerald-300 bg-emerald-500/20 border-emerald-500/40 font-bold' };
  }
  if (rawType === '사고' || (rawType.includes('사고') && !rawType.includes('무사고'))) {
    return { text: '🔴 프레임사고', style: 'text-rose-300 bg-rose-500/20 border-rose-500/40 font-bold' };
  }
  return { text: '🟡 단순수리', style: 'text-amber-300 bg-amber-500/20 border-amber-500/40 font-bold' };
};

export const SelectedKcarDetailV2Section: React.FC<SelectedKcarDetailV2SectionProps> = ({
  selectedKcar,
  targetCatalog,
}) => {
  const [kcarDetail, setKcarDetail] = useState<KcarDetailData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const kcarDetailCacheRef = useRef<Record<string, KcarDetailData>>({});

  const carCd = selectedKcar?.carCd;

  // 단일 케이카 상세 정보 API 호출 (include3d=true, 7초 타임아웃, 캐시 보존)
  useEffect(() => {
    if (!carCd) {
      setKcarDetail(null);
      setErrorMessage(null);
      return;
    }

    const cached = kcarDetailCacheRef.current[carCd];
    if (cached && cached.has3d) {
      setKcarDetail(cached);
      setErrorMessage(null);
      setIsLoading(false);
      return;
    }
    if (cached) {
      setKcarDetail(cached);
    }

    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, 7000);

    setIsLoading(true);
    setErrorMessage(null);

    fetch('/api/kcar/detail', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ carCd, include3d: true }),
      signal: controller.signal,
    })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(json => {
        if (json.success && json.data) {
          kcarDetailCacheRef.current[carCd] = json.data;
          setKcarDetail(json.data);
          setErrorMessage(null);
        } else {
          if (!cached) setKcarDetail(null);
          setErrorMessage(json.message || '상세 정보를 불러오지 못했습니다.');
        }
      })
      .catch(err => {
        if (err.name === 'AbortError') {
          setErrorMessage('상세 정보 요청 시간이 초과되었습니다.');
        } else {
          setErrorMessage('상세 정보를 불러오지 못했습니다.');
        }
        if (!cached) setKcarDetail(null);
      })
      .finally(() => {
        clearTimeout(timer);
        setIsLoading(false);
      });

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [carCd]);

  // 💡 [Rules of Hooks]: 모든 리액트 훅은 early return(조기 반환) 이전에 컴포넌트 최상단에서 무조건 실행되어야 함
  // 옵션 원문 목록 추출 (kcarDetail options 우선, 없으면 selectedKcar.optnNm 파이프 분리)
  const rawOptionNames: string[] = React.useMemo(() => {
    if (kcarDetail?.options?.items && kcarDetail.options.items.length > 0) {
      return kcarDetail.options.items.map((o) => o.name);
    }
    if (selectedKcar?.optnNm) {
      return selectedKcar.optnNm.split('|').map((s) => s.trim()).filter(Boolean);
    }
    return [];
  }, [kcarDetail, selectedKcar]);

  const catalogOptNames = React.useMemo(() => {
    return targetCatalog?.options ? Object.keys(targetCatalog.options) : [];
  }, [targetCatalog]);

  const hasCatalog = Boolean(targetCatalog && targetCatalog.options && Object.keys(targetCatalog.options).length > 0);

  // 💡 [11-03-11]: 백엔드 단일화 케이카 옵션 매칭 상태
  const [kcarMatchedOpts, setKcarMatchedOpts] = React.useState<BackendMatchedOption[]>([]);

  React.useEffect(() => {
    if (!selectedKcar || rawOptionNames.length === 0) {
      setKcarMatchedOpts([]);
      return;
    }
    const cached = selectedKcar.carCd ? getCachedCarMatchedOptions(selectedKcar.carCd) : null;
    if (cached && cached.length > 0) {
      setKcarMatchedOpts(cached);
      return;
    }
    let isMounted = true;
    matchOptionsSingle({
      id: selectedKcar.carCd,
      carName: selectedKcar.carName || selectedKcar.modelName || '',
      year: selectedKcar.year || '',
      optionsList: rawOptionNames,
    }).then((data) => {
      if (isMounted) setKcarMatchedOpts(data);
    });
    return () => {
      isMounted = false;
    };
  }, [selectedKcar?.carCd, selectedKcar?.carName, selectedKcar?.year, rawOptionNames]);

  const matchedOptionChips = React.useMemo(() => {
    return rawOptionNames.map((rawName, idx) => {
      // 카탈로그가 없거나 백엔드 매칭이 없을 때: 깔때기 폴백으로 원문 그대로·가격 미확인 유지
      if (!hasCatalog && kcarMatchedOpts.length === 0) {
        return {
          rawName,
          displayName: rawName,
          chipStyle: 'bg-[#1a1c26] text-zinc-300 border-[#2d3142]',
          titleText: `[카탈로그 미연동] 원문: ${rawName} (신차 공식 사양 미확인)`,
          isExact: false,
          isFuzzy: false,
          hasCatalog: false,
        };
      }

      const mi = kcarMatchedOpts[idx] || kcarMatchedOpts.find((m) => m.raw_name === rawName);

      if (!mi || mi.match_type === 'none') {
        return {
          rawName,
          displayName: mi?.clean_name || rawName,
          chipStyle: 'bg-[#1a1c26] text-zinc-300 border-[#2d3142]',
          titleText: `[미매칭 옵션] 원문: ${rawName}`,
          isExact: false,
          isFuzzy: false,
          hasCatalog: true,
        };
      }

      const isExact = mi.match_type === 'exact';
      const isFuzzy = mi.match_type === 'fuzzy';
      const srcLabel = mi.source === 'danawa' ? '다나와' : mi.source === 'encar' ? '엔카' : (mi.source || '카탈로그');
      const yearPart = mi.matched_year ? ` · ${mi.matched_year}년` : (targetCatalog?.year ? ` · ${targetCatalog.year}년` : '');
      const stdName = mi.official_name || mi.clean_name || rawName;
      const pricePart = mi.price ? ` (${Math.round(mi.price / 10000)}만)` : '';

      let chipStyle = 'bg-[#1a1c26] text-zinc-300 border-[#2d3142]';
      let titleText = `[미매칭 옵션] 원문: ${rawName}`;

      if (isExact) {
        chipStyle = 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40 font-semibold';
        titleText = `[${srcLabel} 카탈로그 정확 매칭${yearPart}] 표준명: ${stdName}${pricePart}`;
      } else if (isFuzzy) {
        chipStyle = 'bg-amber-500/15 text-amber-300 border-amber-500/40 font-semibold';
        titleText = `[${srcLabel} 카탈로그 퍼지 매칭${yearPart}] 표준명: ${stdName} (원문: ${rawName})`;
      }

      return {
        rawName,
        displayName: stdName,
        chipStyle,
        titleText,
        isExact,
        isFuzzy,
        hasCatalog: true,
      };
    });
  }, [rawOptionNames, kcarMatchedOpts, targetCatalog, hasCatalog]);

  // 1. 미선택 상태 분기
  if (!selectedKcar) {
    return (
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-12 text-center text-zinc-500 shadow-sm space-y-2">
        <Car className="w-8 h-8 text-zinc-600 mx-auto stroke-[1.5]" />
        <p className="text-xs sm:text-sm font-medium text-zinc-400">
          비교 목록에서 케이카 매물을 선택해 주세요
        </p>
        <p className="text-[11px] text-zinc-600">
          선택한 케이카 차량의 상세 스펙과 2D 외판/골격 상태도가 여기에 표시됩니다.
        </p>
      </div>
    );
  }

  // 2. 표시용 데이터 가공 (기존 필드 그대로 바인딩)
  const carName = kcarDetail?.modelName || selectedKcar.modelName || selectedKcar.carName;
  const gradeName = kcarDetail?.gradeFullName || selectedKcar.gradeDetail || selectedKcar.grade || '';
  const detailUrl = kcarDetail?.detailUrl || selectedKcar.detailUrl || `https://www.kcar.com/bc/detail/carInfoDtl?i_sCarCd=${selectedKcar.carCd}`;

  // 색상 칩 스타일
  const rawColor = kcarDetail?.color || selectedKcar.color;
  const colorStyle = getCarColorStyle(rawColor);

  // 점검일자 및 재고일수
  const checkDateText = kcarDetail?.checkDate && kcarDetail.checkDate !== '-'
    ? kcarDetail.checkDate
    : (kcarDetail?.dates?.pfmncDate
      ? kcarDetail.dates.pfmncDate.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
      : (selectedKcar.checkDate && selectedKcar.checkDate !== '-' ? selectedKcar.checkDate : ''));

  const holdingDaysVal = typeof kcarDetail?.holdingDays === 'number' && !isNaN(kcarDetail.holdingDays)
    ? kcarDetail.holdingDays
    : (typeof selectedKcar.holdingDays === 'number' && !isNaN(selectedKcar.holdingDays) ? selectedKcar.holdingDays : null);

  // 사고 구분
  const accType = kcarDetail?.accident?.accidentType || selectedKcar.accident || '';
  const accInfo = formatKcarAccident(accType);

  // 사고 교환/판금 부위
  const repList: string[] = kcarDetail?.accident?.replaceNames || (kcarDetail as any)?.replaceNames || [];
  const fixList: string[] = kcarDetail?.accident?.repairNames || (kcarDetail as any)?.repairNames || [];
  const chgCount = kcarDetail?.accident?.changeCount || 0;
  const mtlCount = kcarDetail?.accident?.metalCount || 0;
  const hasRep = repList.length > 0 || chgCount > 0;
  const hasFix = fixList.length > 0 || mtlCount > 0;

  // 옵션 데이터
  const optionList = kcarDetail?.options?.items || [];
  const optionTotalPrice = kcarDetail?.options?.totalPrice || 0;


  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm space-y-0">
      {/* 1. 상단 바 (차명 원본링크, 등급, 우측 옵션합계 뱃지) */}
      <div className="px-5 py-3.5 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <a
            href={detailUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-base sm:text-lg font-black text-white hover:text-sky-400 transition underline underline-offset-2 flex items-center gap-1.5 truncate group"
            title="케이카 매물 원본 상세페이지 열기"
          >
            <span>{carName}</span>
            <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition shrink-0" />
          </a>
          {gradeName && (
            <span className="text-xs sm:text-sm text-zinc-300 font-semibold truncate">
              {gradeName}
            </span>
          )}
          {isLoading && (
            <span className="text-[11px] text-amber-400 font-mono animate-pulse">
              ⚡ 상세 정보 수신 중...
            </span>
          )}
        </div>

        {/* 우측 영역: JATO 옵션 합계 뱃지 */}
        {optionTotalPrice > 0 && (
          <span
            className="text-xs sm:text-sm font-bold text-amber-300 font-mono shrink-0 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30"
            title="케이카 JATO 추가 선택옵션 합계"
          >
            옵션합계 +{optionTotalPrice.toLocaleString()}만
          </span>
        )}
      </div>

      {/* 2. 에러/타임아웃 안내 배너 (있을 때만) */}
      {errorMessage && !isLoading && (
        <div className="mx-5 mt-3 p-2.5 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 3. 본문 한 박스 (스펙 위 · 2D 아래 세로 쌓기: 절반 너비 100% 활용) */}
      <div className="p-5 space-y-4">
        {/* [상단 스펙 영역: 칩스 바 & 가격 & 옵션] */}
        <div className="space-y-3">
          {/* 3-1) 칩스 바: 연식 / 주행 km / 색상 / 점검일 / 사고 배지 */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {/* 연식 칩 */}
            <span className="px-2.5 py-1 rounded bg-[#1f222e] text-white font-bold font-mono">
              {selectedKcar.fullYear || selectedKcar.year || kcarDetail?.year}년식
            </span>

            {/* 주행거리 칩 */}
            <span className="px-2.5 py-1 rounded bg-[#1f222e] text-emerald-400 font-bold font-mono">
              {(kcarDetail?.mileage || selectedKcar.mileage || 0).toLocaleString()}km
            </span>

            {/* 색상 칩 */}
            <span
              className="px-2.5 py-1 rounded font-medium border text-xs"
              style={{
                backgroundColor: colorStyle.bgColor,
                color: colorStyle.textColor,
                borderColor: colorStyle.borderColor,
              }}
            >
              {colorStyle.dot} {colorStyle.displayName}
            </span>

            {/* 점검일 칩 */}
            {checkDateText ? (
              <span
                className="px-2.5 py-1 rounded bg-blue-500/20 text-blue-300 font-bold font-mono"
                title="법정 성능점검일자"
              >
                📋 점검: {checkDateText}
                {holdingDaysVal !== null && holdingDaysVal >= 0 ? ` (${holdingDaysVal}일 전)` : ''}
              </span>
            ) : null}

            {/* 사고 구분 배지 */}
            <span className={`px-2.5 py-1 rounded border text-xs font-bold ${accInfo.style}`}>
              {accInfo.text}
            </span>
          </div>

          {/* 3-2) 사고 부위 요약 텍스트 */}
          {(hasRep || hasFix) && (
            <div className="pt-1 pb-0.5 text-xs flex flex-col gap-1">
              {hasRep && (
                <div className="text-rose-400 font-medium flex items-start gap-1">
                  <span className="font-bold shrink-0">🔴 교환(X):</span>
                  <span className="font-semibold text-rose-300">
                    {repList.length > 0 ? `${repList.join(', ')} (${repList.length}건)` : `${chgCount}건`}
                  </span>
                </div>
              )}
              {hasFix && (
                <div className="text-amber-400 font-medium flex items-start gap-1">
                  <span className="font-bold shrink-0">🟡 판금/용접(W):</span>
                  <span className="font-semibold text-amber-300">
                    {fixList.length > 0 ? `${fixList.join(', ')} (${fixList.length}건)` : `${mtlCount}건`}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* 3-3) 대형 가격 표시 */}
          <div className="flex items-baseline gap-1.5 pt-1">
            <span className="text-2xl sm:text-3xl font-black text-amber-400 font-mono tracking-tight">
              {(kcarDetail?.price || selectedKcar.price || 0).toLocaleString()}
            </span>
            <span className="text-sm font-bold text-zinc-300">만원</span>
          </div>

          {/* 3-4) 주요 옵션 목록 (엔카 상세와 동일한 매칭 계약) */}
          <div className="p-3 bg-[#0c0e14] rounded-lg border border-[#232634] text-xs space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#8b8e9d] uppercase">
                {matchedOptionChips.length > 0 ? `주요 옵션 (${matchedOptionChips.length}개)` : '주요 옵션'}
              </span>
              <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-medium">
                {hasCatalog ? (
                  <>
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                      정확
                    </span>
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
                      퍼지
                    </span>
                    <span className="flex items-center gap-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-zinc-500 inline-block" />
                      미매칭
                    </span>
                  </>
                ) : (
                  <span className="text-zinc-500 text-[10px]">
                    신차가격표 미연동 (원문 표기)
                  </span>
                )}
              </div>
            </div>
            {matchedOptionChips.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 pt-0.5">
                {matchedOptionChips.slice(0, 8).map((chip, i) => (
                  <span
                    key={i}
                    title={chip.titleText}
                    className={`px-2 py-0.5 rounded text-[11px] border flex items-center gap-1 transition select-none ${chip.chipStyle}`}
                  >
                    <span>{chip.displayName}</span>
                  </span>
                ))}
                {matchedOptionChips.length > 8 && (
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-[#1a1c26] text-zinc-400 border border-[#2d3142]">
                    +{matchedOptionChips.length - 8}개 더보기
                  </span>
                )}
              </div>
            ) : (
              <p className="text-zinc-500 text-xs italic">
                추가옵션 없음 또는 기본 트림 사양
              </p>
            )}
          </div>
        </div>

        {/* [하단 영역: 2D 상태도] */}
        <div className="bg-[#14151b] border border-[#232634] rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-[#232634] pb-2">
            <span className="text-xs font-bold text-white">
              외판 및 주요골격 상태도
            </span>
            {checkDateText && (
              <span className="text-[11px] text-zinc-400 font-mono">
                {checkDateText} 점검
              </span>
            )}
          </div>

          {/* 2D 상태도 컴포넌트 임포트 사용 (기존 부품 무수정 연결) */}
          <div className="pt-1">
            <CarDamageDiagram2D
              selectedEncar={{
                id: selectedKcar.carCd,
                carName,
                accidentType: accType,
                replaces: repList,
                repairs: fixList,
                replaceNames: repList,
                repairNames: fixList,
              } as any}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

