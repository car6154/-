import React, { useState, useEffect } from 'react';
import { X, RefreshCw, Trash2, ExternalLink, ShieldCheck, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { TrackedCarItem } from '@/types';

interface TrackedCarsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onListChanged?: () => void;
}

export const TrackedCarsModal: React.FC<TrackedCarsModalProps> = ({
  isOpen,
  onClose,
  onListChanged,
}) => {
  const [items, setItems] = useState<TrackedCarItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const fetchTrackedCars = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/tracking/cars');
      const data = await res.json();
      if (data.success && Array.isArray(data.items)) {
        setItems(data.items);
      }
    } catch (e) {
      console.error('[TrackedCarsModal] fetch error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchTrackedCars();
      setRunMessage(null);
    }
  }, [isOpen]);

  const handleRemove = async (carid: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`엔카 ID [${carid}] 차량의 추적을 해제하시겠습니까?`)) return;

    try {
      const res = await fetch(`/api/tracking/cars/${carid}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        setItems(prev => prev.filter(item => item.carid !== carid));
        onListChanged?.();
      } else {
        alert(`추적 해제 실패: ${data.error || '오류 발생'}`);
      }
    } catch (e: any) {
      alert(`추적 해제 요청 실패: ${e.message}`);
    }
  };

  const handleRunNow = async () => {
    if (isRunning) return;
    setIsRunning(true);
    setRunMessage('엔카 페이싱(2초)을 준수하며 재확인 중입니다. 잠시만 기다려주세요...');

    try {
      const res = await fetch('/api/tracking/run?pacing_sec=2.0', { method: 'POST' });
      const data = await res.json();
      if (data.success && data.result) {
        setRunMessage(data.result.message || '재확인이 완료되었습니다.');
        fetchTrackedCars();
        onListChanged?.();
      } else {
        setRunMessage(`재확인 오류: ${data.error || '알 수 없는 오류'}`);
      }
    } catch (e: any) {
      setRunMessage(`재확인 통신 실패: ${e.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  if (!isOpen) return null;

  const activeCount = items.filter(i => i.status === '판매중').length;
  const estimatedSoldCount = items.filter(i => i.status === '판매완료 추정').length;
  const confirmedSoldCount = items.filter(i => i.status === '판매완료').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="bg-[#12141c] border border-[#2b3042] rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#232838] bg-[#161924]">
          <div className="flex items-center gap-3">
            <span className="text-xl">🎯</span>
            <div>
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>관심 매물 실시간 호가 추적기</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30 font-mono">
                  총 {items.length}대 추적 중
                </span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                콕핏·정산에서 지정한 차량이 판매 종료되면 마지막 가격을 <strong>"팔리기 직전 호가"</strong>로 확정 보존합니다.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRunNow}
              disabled={isRunning}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition border ${
                isRunning
                  ? 'bg-blue-600/30 text-blue-300 border-blue-500/40 cursor-wait'
                  : 'bg-blue-600 hover:bg-blue-500 text-white border-blue-500 shadow-sm'
              }`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
              <span>{isRunning ? '재확인 진행 중...' : '지금 전체 재확인'}</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Status KPI Banner */}
        <div className="px-6 py-3 bg-[#0d0f17] border-b border-[#1f2433] flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span>판매중: <strong className="text-emerald-400 font-mono">{activeCount}대</strong></span>
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <span className="w-2 h-2 rounded-full bg-amber-400" />
              <span>판매완료 추정(호가확정): <strong className="text-amber-400 font-mono">{estimatedSoldCount}대</strong></span>
            </span>
            {confirmedSoldCount > 0 && (
              <span className="flex items-center gap-1.5 text-slate-300">
                <span className="w-2 h-2 rounded-full bg-rose-400" />
                <span>판매완료(공식): <strong className="text-rose-400 font-mono">{confirmedSoldCount}대</strong></span>
              </span>
            )}
          </div>
          <div className="text-[11px] text-slate-400">
            ⚡ 엔카 페이싱: 2.0초 간격 | 407 차단 감지 시 즉시 안전 중단
          </div>
        </div>

        {runMessage && (
          <div className="px-6 py-2 bg-blue-500/10 border-b border-blue-500/20 text-xs text-blue-300 flex items-center gap-2">
            <Clock className="w-4 h-4 shrink-0 text-blue-400" />
            <span>{runMessage}</span>
          </div>
        )}

        {/* Content Table */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <div className="text-xs">관심 차량 목록을 불러오는 중...</div>
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <span className="text-3xl mb-2">⭐</span>
              <div className="text-sm font-bold text-slate-200">현재 등록된 관심 추적 차량이 없습니다.</div>
              <div className="text-xs text-slate-400 mt-1 max-w-md">
                콕핏의 엔카 매물 목록(별표 아이콘)이나 정산 탭(추적 버튼)에서 차량을 등록하면,
                하루 2회 자동 재확인 스케줄러가 판매완료 여부와 마지막 호가를 기록합니다.
              </div>
            </div>
          ) : (
            <div className="border border-[#262b3d] rounded-xl overflow-hidden bg-[#0d0f17]">
              <table className="w-full text-left text-xs text-slate-200">
                <thead className="bg-[#181c28] text-[11px] text-slate-300 font-semibold border-b border-[#262b3d]">
                  <tr>
                    <th className="py-2.5 px-3 text-center w-12">상태</th>
                    <th className="py-2.5 px-3">차량정보</th>
                    <th className="py-2.5 px-3 text-right">마지막 가격 (호가)</th>
                    <th className="py-2.5 px-3 text-center">미발견 횟수</th>
                    <th className="py-2.5 px-3 text-center">최근 확인일</th>
                    <th className="py-2.5 px-3 text-center">등록출처</th>
                    <th className="py-2.5 px-3 text-center w-20">관리</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1f2435]">
                  {items.map(item => {
                    const isEstimatedSold = item.status === '판매완료 추정';
                    const isConfirmedSold = item.status === '판매완료';
                    const isActive = item.status === '판매중';
                    const detailUrl = `https://fem.encar.com/cars/detail/${item.carid}`;

                    return (
                      <tr
                        key={item.carid}
                        className={`hover:bg-[#151926] transition ${
                          isEstimatedSold ? 'bg-amber-500/5' : isConfirmedSold ? 'bg-rose-500/5' : ''
                        }`}
                      >
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          {isEstimatedSold ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                              판매완료 추정
                            </span>
                          ) : isConfirmedSold ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/40">
                              판매완료
                            </span>
                          ) : isActive ? (
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                              판매중
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-700 text-slate-300 border border-slate-600">
                              {item.status}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <div className="flex items-center gap-2">
                            <a
                              href={detailUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-bold text-slate-100 hover:text-blue-400 hover:underline flex items-center gap-1"
                              title="엔카 상세페이지 새창 열기"
                            >
                              <span>{item.carName || `엔카 ID: ${item.carid}`}</span>
                              <ExternalLink className="w-3 h-3 text-slate-400" />
                            </a>
                            {item.carNumber && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                                {item.carNumber}
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                            ID: {item.carid}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-right whitespace-nowrap">
                          <div className="font-bold font-mono text-sm text-slate-100">
                            {Number(item.last_asking_price || item.price || 0).toLocaleString()}만원
                          </div>
                          <div className="text-[10px] text-amber-400/90 font-medium">
                            {isEstimatedSold ? '🏷️ 팔리기 직전 호가' : '호가 (등록 기준)'}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          {item.consecutive_misses > 0 ? (
                            <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                              item.consecutive_misses >= 2
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : 'bg-slate-800 text-slate-300'
                            }`}>
                              {item.consecutive_misses}회 미발견
                            </span>
                          ) : (
                            <span className="text-slate-500 text-[11px] font-mono">0</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap font-mono text-[11px] text-slate-400">
                          {item.estimated_sold_date ? (
                            <span className="text-amber-300 font-bold">추정: {item.estimated_sold_date}</span>
                          ) : item.lastCheckedAt ? (
                            item.lastCheckedAt.slice(0, 10)
                          ) : (
                            item.addedAt.slice(0, 10)
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                            {item.source === 'settlement' ? '정산탭' : '콕핏'}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-center whitespace-nowrap">
                          <button
                            type="button"
                            onClick={(e) => handleRemove(item.carid, e)}
                            className="p-1.5 rounded-lg text-rose-400 hover:text-white hover:bg-rose-600/30 transition border border-rose-500/30"
                            title="관심 추적 해제"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#232838] bg-[#161924] flex items-center justify-between text-xs text-slate-400">
          <span>
            💡 관심 목록 차량은 하루 2회(12시간 주기) 백그라운드에서 자동 재확인됩니다.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};
