import React from 'react';

export interface QuickPasteModalProps {
  isOpen: boolean;
  quickPasteText: string;
  setQuickPasteText: (text: string) => void;
  onClose: () => void;
  onParse: () => void;
}

export const QuickPasteModal: React.FC<QuickPasteModalProps> = ({
  isOpen,
  quickPasteText,
  setQuickPasteText,
  onClose,
  onParse,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-[#121317] border border-[#262833] rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl animate-in fade-in zoom-in duration-150">
        <div className="p-4 border-b border-[#22242c] flex items-center justify-between bg-[#16171d]">
          <div className="flex items-center gap-2">
            <span className="text-emerald-400 font-bold text-sm">📋 1초 텍스트/스펙 즉시 자동 분석</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#8b8e9d] hover:text-white p-1 rounded-lg hover:bg-[#22242c] transition"
          >
            ✕
          </button>
        </div>

        <div className="p-4 space-y-3">
          <p className="text-xs text-[#8b8e9d]">
            헤이딜러, 카카오톡, 메모장, 문자 등에서 복사한 차량 정보 텍스트를 그대로 붙여넣으세요.
            차량번호, 차종, 연식, 주행거리, 시세, 사고유무를 즉시 자동 추출합니다.
          </p>

          <textarea
            rows={5}
            value={quickPasteText}
            onChange={(e) => setQuickPasteText(e.target.value)}
            placeholder="예시: 240어8733 올뉴모닝(JA) 럭셔리 20년식 24,500km 815만원 완전무사고 스마트키"
            className="w-full bg-[#0d0e11] border border-[#22242c] rounded-xl p-3 text-xs text-white placeholder-[#515360] focus:outline-none focus:border-emerald-500 font-mono resize-none"
          />

          <div className="flex justify-between items-center gap-2 pt-2">
            <div className="flex items-center gap-1.5 overflow-x-auto text-[11px]">
              <span className="text-[#515360]">빠른 예시:</span>
              <button
                type="button"
                onClick={() => setQuickPasteText('더 뉴 그랜저 IG 2.5 가솔린 르블랑 21년 42000km 2550만원 무사고')}
                className="px-2 py-0.5 rounded bg-[#1f2029] text-[#8b8e9d] hover:text-white border border-[#2b2d3a] shrink-0"
              >
                그랜저 르블랑
              </button>
              <button
                type="button"
                onClick={() => setQuickPasteText('37다1840 올 뉴 카니발 디젤 9인승 18년식 98000km 980만원')}
                className="px-2 py-0.5 rounded bg-[#1f2029] text-[#8b8e9d] hover:text-white border border-[#2b2d3a] shrink-0"
              >
                카니발
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded-lg bg-[#1f2029] hover:bg-[#2b2d3a] text-xs text-[#8b8e9d] hover:text-white transition"
              >
                취소
              </button>
              <button
                type="button"
                onClick={onParse}
                className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white transition shadow-sm"
              >
                1초 자동 파싱 & 적용
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
