import React from 'react';
import { Eye, ExternalLink } from 'lucide-react';
import { HeydealerBidItem } from '@/components/BiddingCockpit/Sections/HeydealerBidsSection';
import { CarDamageDiagram2D } from '@/components/BiddingCockpit/Sections/CarDamageDiagram2D';
import { HD_PART_MAP } from '@/services/biddingOptionCatalog';

export interface SelectedHeydealerBidDetailV2SectionProps {
  selectedHeydealerBid: HeydealerBidItem | null;
}

/**
 * 헤이딜러 수리 부위명 -> CarDamageDiagram2D 표준 부위 키워드로 변환
 * - 운전석 -> 좌, 조수석 -> 우 기본 치환
 * - 다이어그램에 앞/뒤 구분이 없는 부위(인사이드패널 등)는 위치어 정리
 * - 다이어그램 배제어 충돌(예: 휠하우스의 '우') 방지를 위해 필요 시 표준 부위 코드 반환
 * - 다이어그램 미지원 부위(범퍼, 뒤 휠하우스 등)는 null 반환
 */
export const mapHeydealerPartToDiagram = (rawPart: string): string | null => {
  if (!rawPart || typeof rawPart !== 'string') return null;
  const raw = rawPart.trim();
  if (!raw) return null;

  // 영문 코드일 경우 HD_PART_MAP으로 한글 변환
  const s = HD_PART_MAP[raw] || raw;

  // 1. 범퍼: 다이어그램 미지원 부위
  if (s.includes('범퍼')) {
    return null;
  }

  // 2. 휠하우스: 다이어그램에는 앞 휠하우스만 존재
  if (s.includes('휠하우스')) {
    if (s.includes('뒤') || s.toLowerCase().includes('rear')) {
      return null; // 뒤 휠하우스는 다이어그램 미지원
    }
    // 프론트 휠하우스: 한글 '휠하우스(좌)'는 '휠하우스'의 '우'가 exclude: ['우']에 걸리므로 표준 코드로 매핑
    if (s.includes('운전석') || s.includes('좌')) {
      return 'FRONT_WHEEL_HOUSE_L';
    }
    if (s.includes('조수석') || s.includes('우')) {
      return 'FRONT_WHEEL_HOUSE_R';
    }
    return 'FRONT_WHEEL_HOUSE_L';
  }

  // 3. 인사이드패널: 다이어그램에 앞/뒤 구분이 없으므로 위치어(앞/, 뒤/) 제거하고 좌/우 통일
  if (s.includes('인사이드')) {
    if (s.includes('운전석') || s.includes('좌')) {
      return '인사이드패널(좌)';
    }
    if (s.includes('조수석') || s.includes('우')) {
      return '인사이드패널(우)';
    }
    return 'INSIDE_PANEL_L';
  }

  // 4. 사이드멤버: 다이어그램에 앞/뒤 구분이 명확히 있음
  if (s.includes('사이드멤버')) {
    const isRear = s.includes('뒤') || s.includes('리어') || s.toLowerCase().includes('rear');
    if (s.includes('운전석') || s.includes('좌')) {
      return isRear ? '리어사이드멤버(좌)' : '앞사이드멤버(좌)';
    }
    if (s.includes('조수석') || s.includes('우')) {
      return isRear ? '리어사이드멤버(우)' : '앞사이드멤버(우)';
    }
    return '앞사이드멤버(좌)';
  }

  // 5. 사이드실 패널
  if (s.includes('사이드실')) {
    if (s.includes('운전석') || s.includes('좌')) {
      return '사이드실(좌)';
    }
    if (s.includes('조수석') || s.includes('우')) {
      return '사이드실(우)';
    }
    return '사이드실(좌)';
  }

  // 6. 후드(보닛)
  if (s.includes('후드') || s.includes('보닛') || s.includes('본넷')) {
    return '후드';
  }

  // 7. 기본 방향 치환 (운전석 -> 좌, 조수석 -> 우)
  const mapped = s.replace(/운전석/g, '좌').replace(/조수석/g, '우');
  return mapped;
};

export const SelectedHeydealerBidDetailV2Section: React.FC<SelectedHeydealerBidDetailV2SectionProps> = ({
  selectedHeydealerBid,
}) => {
  if (!selectedHeydealerBid) {
    return (
      <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl p-6 text-center text-xs text-zinc-500">
        선택된 헤이딜러 매물이 없습니다.
      </div>
    );
  }

  // 주요옵션 텍스트 정리 (빈 문자열 또는 '-'는 무옵션으로 처리)
  const fallbackOptionsText =
    selectedHeydealerBid.options && selectedHeydealerBid.options !== '-'
      ? selectedHeydealerBid.options.trim()
      : '';

  // 2D 상태도용 수리 부위 매핑 (교환: replaces, 판금/용접: repairs)
  const diagramEncar = React.useMemo(() => {
    if (!selectedHeydealerBid?.repairs || selectedHeydealerBid.repairs.length === 0) {
      return { replaces: [], repairs: [] };
    }

    const replaces: string[] = [];
    const repairs: string[] = [];

    for (const r of selectedHeydealerBid.repairs) {
      const mappedPart = mapHeydealerPartToDiagram(r.part);
      if (!mappedPart) continue;

      const isReplace = r.repair === '교환' || r.repair === 'exchange' || r.repair === 'replace';
      if (isReplace) {
        replaces.push(mappedPart);
      } else {
        repairs.push(mappedPart);
      }
    }

    return { replaces, repairs };
  }, [selectedHeydealerBid?.repairs]);

  return (
    <div className="bg-[#0f1015] border border-[#1e2029] rounded-xl overflow-hidden shadow-sm space-y-0">
      {/* 1. 상단 바 (헤더 및 내수/수출 뱃지) */}
      <div className="px-5 py-3.5 border-b border-[#1e2029] flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 text-xs font-bold text-white">
          <Eye className="w-3.5 h-3.5 text-sky-400" />
          <span>상세설명 및 옵션 (헤이딜러)</span>
        </div>
        <div className="flex items-center gap-2">
          {selectedHeydealerBid.isExport ? (
            <span className="px-2.5 py-0.5 rounded bg-blue-500/20 border border-blue-500/30 text-blue-300 font-bold text-xs">
              🚢 수출딜러 낙찰
            </span>
          ) : (
            <span className="px-2.5 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 font-bold text-xs">
              🚙 내수딜러 낙찰
            </span>
          )}
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* 2. 차명 (원본보기 링크 지원) 및 기본 스펙 줄 */}
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            {selectedHeydealerBid.link ? (
              <a
                href={selectedHeydealerBid.link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-base sm:text-lg font-black text-white hover:text-sky-400 transition underline underline-offset-2 flex items-center gap-1.5 truncate group"
                title="헤이딜러 매물 원본 상세페이지 열기"
              >
                <span>{selectedHeydealerBid.model}</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-60 group-hover:opacity-100 transition shrink-0" />
              </a>
            ) : (
              <span className="text-base sm:text-lg font-black text-white tracking-tight">
                {selectedHeydealerBid.model}
              </span>
            )}
          </div>
          <div className="text-xs text-zinc-400 font-mono">
            {selectedHeydealerBid.year} · {selectedHeydealerBid.mileage.toLocaleString()}km
          </div>
        </div>

        {/* 3. 뱃지 모음 (낙찰가, 낙찰일) */}
        <div className="flex flex-wrap items-center gap-2 pt-0.5">
          <span className="px-2.5 py-1 rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 font-extrabold text-xs font-mono">
            {selectedHeydealerBid.isExport ? `🚢 수출 ${selectedHeydealerBid.bidPrice}만원` : `${selectedHeydealerBid.bidPrice.toLocaleString()}만원`}
          </span>
          <span className="px-2.5 py-1 rounded bg-[#1a1c26] border border-[#2d3142] text-zinc-400 font-medium text-xs font-mono">
            ⏱️ {selectedHeydealerBid.bidDate}
          </span>
        </div>

        {/* 4. 사고유무 / 교환 및 수리 부위 / 주요옵션 */}
        <div className="pt-3 border-t border-[#1e2029] space-y-3.5">
          {/* 사고유무 */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-zinc-400 font-medium">사고유무:</span>
            <span className={`px-2 py-0.5 rounded font-bold text-[11px] border ${
              selectedHeydealerBid.accidentType === '완전무사고'
                ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                : selectedHeydealerBid.accidentType === '유사고'
                ? 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                : 'bg-amber-500/20 border-amber-500/40 text-amber-300'
            }`}>
              {selectedHeydealerBid.accident}
            </span>
          </div>

          {/* 교환 및 수리 부위 */}
          <div>
            <div className="text-xs text-white font-bold mb-1.5 flex items-center gap-1">
              <span>🛠️</span> 교환 및 수리 부위
            </div>
            <div className="flex flex-wrap gap-1.5">
              {selectedHeydealerBid.repairs && selectedHeydealerBid.repairs.length > 0 ? (
                selectedHeydealerBid.repairs.map((r, pIdx) => (
                  <span
                    key={pIdx}
                    className="px-2.5 py-1 rounded bg-amber-500/15 text-amber-200 border border-amber-500/30 text-xs font-medium"
                  >
                    {r.desc}
                  </span>
                ))
              ) : (
                <span className="text-xs text-zinc-500">수리 이력 없음 (완전무사고)</span>
              )}
            </div>
          </div>

          {/* 주요옵션 */}
          <div>
            <div className="text-xs text-white font-bold mb-1.5">주요옵션</div>
            <div className="flex flex-wrap gap-1.5">
              {selectedHeydealerBid.keyOptions && selectedHeydealerBid.keyOptions.length > 0 ? (
                selectedHeydealerBid.keyOptions.map((opt, oIdx) => (
                  <span
                    key={oIdx}
                    className="px-2.5 py-1 rounded bg-blue-500/15 text-blue-300 border border-blue-500/25 text-xs font-medium"
                  >
                    {opt}
                  </span>
                ))
              ) : fallbackOptionsText ? (
                <div className="text-xs text-zinc-400">{fallbackOptionsText}</div>
              ) : (
                <div className="text-xs text-zinc-500">등록된 옵션 없음</div>
              )}
            </div>
          </div>
        </div>

        {/* 5. 외판 및 주요골격 2D 상태도 */}
        <CarDamageDiagram2D selectedEncar={diagramEncar} />
      </div>
    </div>
  );
};

