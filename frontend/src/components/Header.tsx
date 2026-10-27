import React, { useState, useRef, useEffect } from 'react';
import { Car, Cloud, Key, ChevronDown, Check } from 'lucide-react';

export type AppTab = 'cockpit' | 'ledger' | 'settlement' | 'soldout' | 'performance' | 'inventory' | 'ocr';

interface HeaderProps {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
  searchQuery?: string;
  setSearchQuery?: (q: string) => void;
  totalCarsCount: number;
  totalBuyAmount: number;
  avgMargin: number;
  onOpenAddModal?: () => void;
  onOpenDriveModal: () => void;
  onOpenCookieModal: () => void;
  onOpenExtensionModal?: () => void;
  cookieStatus: 'active' | 'expired' | 'missing';
  isPrivateUnlocked?: boolean;
  setIsPrivateUnlocked?: (unlocked: boolean | ((prev: boolean) => boolean)) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  totalCarsCount,
  onOpenDriveModal,
  onOpenCookieModal,
  onOpenExtensionModal,
  cookieStatus,
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 상단 줄 실시간 동기화 상태 및 핸들러
  const [isBuySyncing, setIsBuySyncing] = useState(false);
  const [isStockSyncing, setIsStockSyncing] = useState(false);

  const handleSyncBuy = async () => {
    if (isBuySyncing) return;
    setIsBuySyncing(true);
    try {
      const res = await fetch('/api/settlement/sync_highplus_buy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const syncData = await res.json();
      const st = (syncData && syncData.data) || {};
      const timeStr = st.last_sync_time || new Date().toLocaleTimeString('ko-KR');
      const total = st.total_synced_cars || 0;
      const added = st.new_inventory_added || 0;
      const updated = st.inventory_updated || 0;

      if (syncData.success !== false) {
        alert(
          `[high A+ 매입 모바일 API 연동 결과]\n\n` +
          `• 연동 시간: ${timeStr}\n` +
          `• 감지된 매입차량: ${total}대\n` +
          `• 신규 재고 등록: ${added}대\n` +
          `• 기존 재고 갱신: ${updated}대\n\n` +
          `✅ 모바일 API를 통해 실시간 매입 데이터가 정상 연동되었습니다.`
        );
      } else {
        alert(
          `[high A+ 매입 연동 알림]\n\n` +
          `• 상태: ${syncData.message || '세션 만료 또는 데이터 없음'}\n` +
          `• 이전 성공 시점: ${st.last_sync_time || '없음'}\n\n` +
          `💡 조치 방법:\n` +
          `1. high.autoplus.co.kr 모바일 사이트에 로그인하여 high_cookie.txt를 갱신해 주세요.\n` +
          `2. admin.autoplus.co.kr 이나 data.autoplus.co.kr 사이트와는 도메인이 달라 쿠키가 공유되지 않습니다.`
        );
      }
    } catch (e: any) {
      alert(`매입연동 오류: ${e.message}`);
    } finally {
      setIsBuySyncing(false);
    }
  };

  const handleSyncStock = async () => {
    if (isStockSyncing) return;
    setIsStockSyncing(true);
    try {
      const res = await fetch('/api/autoplus/sync_now', { method: 'POST' });
      const data = await res.json();
      if (data.status === 'SUCCESS') {
        alert(
          `[오토플러스.Data 전사 최신화 성공]\n\n` +
          `• 최신화 시간: ${new Date(data.last_sync_time).toLocaleTimeString('ko-KR')}\n` +
          `• 판매중 매물: ${Number(data.inventory_count || 0).toLocaleString()}대\n` +
          `• 판매완료 매물: ${Number(data.sold_count || 0).toLocaleString()}대\n` +
          `• 정산 장부 갱신: ${Number(data.settlement_updated_count || 0).toLocaleString()}건\n\n` +
          `✅ 전사 보유 재고 및 판매완료 데이터가 정상 갱신되었습니다.`
        );
      } else if (data.status === 'COOKIE_EXPIRED' || data.status === 'NO_SESSION' || data.status === 'EXPIRED') {
        alert(
          `[오토플러스.Data 세션 쿠키 필요]\n\n` +
          `• 사유: ${data.message}\n\n` +
          `💡 조치 방법:\n` +
          `1. 브라우저에서 https://data.autoplus.co.kr 에 접속하여 로그인합니다.\n` +
          `2. 크롬 확장 프로그램 팝업에서 [📊 오토플러스.Data 쿠키 전송] 버튼을 클릭해 주세요.`
        );
      } else {
        alert(`[전사 동기화 알림]\n\n• 상태: ${data.status}\n• 메시지: ${data.message || '알 수 없는 오류'}`);
      }
    } catch (e: any) {
      alert(`동기화 통신 오류: ${e.message}`);
    } finally {
      setIsStockSyncing(false);
    }
  };

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const tabOptions: { id: AppTab; label: string; icon: string; count?: number }[] = [
    { id: 'cockpit', label: '시세 분석 (비딩 콕핏)', icon: '⚡' },
    { id: 'ledger', label: '매입 장부', icon: '📒', count: totalCarsCount },
    { id: 'settlement', label: '재고 및 정산', icon: '📦' },
    { id: 'soldout', label: '판매완료 정산', icon: '🏁' },
    { id: 'performance', label: '판매실적 DB', icon: '📈' },
    { id: 'inventory', label: '보유재고', icon: '🏢' },
    { id: 'ocr', label: '거래처 OCR', icon: '📄' },
  ];

  const currentTabInfo = tabOptions.find((t) => t.id === activeTab) || tabOptions[0];

  return (
    // 고정(sticky) 제거 -> 스크롤 시 화면을 가리지 않고 자연스럽게 스크롤됨
    <header className="border-b border-[#1c1d22] bg-[#07080B] text-zinc-300">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 py-2 flex flex-wrap items-center justify-between gap-2.5">
        
        {/* Left: Logo & Dropdown Navigation */}
        <div className="flex items-center gap-3">
          {/* Logo */}
          <div 
            onClick={() => setActiveTab('cockpit')}
            className="flex items-center gap-2 cursor-pointer hover:opacity-90 transition"
          >
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#cc9166] to-[#9e6840] flex items-center justify-center shadow-md shadow-[#cc9166]/10">
              <Car className="w-4 h-4 text-black stroke-[2.5]" />
            </div>
            <span className="text-base font-bold font-serif-display tracking-wide text-white">
              J-PRO
            </span>
          </div>

          <div className="h-4 w-px bg-[#1c1d22] hidden sm:block" />

          {/* Discreet Dropdown Navigation (사람들 눈에 띄지 않게 드롭다운으로 배치) */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#121317] hover:bg-[#1a1c23] border border-[#262832] text-white shadow-sm transition"
              title="메뉴 전환 (시세분석, 매입장부, 재고, 정산 등)"
            >
              <span>{currentTabInfo.icon}</span>
              <span>
                {currentTabInfo.label}
                {currentTabInfo.count !== undefined ? ` (${currentTabInfo.count})` : ''}
              </span>
              <ChevronDown className={`w-3.5 h-3.5 text-[#9194a1] transition-transform duration-150 ${isDropdownOpen ? 'rotate-180 text-[#cc9166]' : ''}`} />
            </button>

            {/* Dropdown Menu Items */}
            {isDropdownOpen && (
              <div className="absolute left-0 top-full mt-1.5 w-52 bg-[#0e0f13] border border-[#2a2c38] rounded-xl shadow-2xl py-1.5 z-50 backdrop-blur-xl animate-in fade-in slide-in-from-top-1 duration-150">
                <div className="px-3 py-1 text-[10px] font-semibold text-[#6e7180] uppercase tracking-wider">
                  메뉴 바로가기
                </div>
                {tabOptions.map((option) => {
                  const isSelected = activeTab === option.id;
                  return (
                    <button
                      key={option.id}
                      onClick={() => {
                        setActiveTab(option.id);
                        setIsDropdownOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-3 py-2 text-xs text-left transition ${
                        isSelected
                          ? 'bg-[#cc9166]/15 text-[#f5ba8a] font-semibold'
                          : 'text-[#a1a4b2] hover:bg-[#161820] hover:text-white'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span>{option.icon}</span>
                        <span>{option.label}</span>
                        {option.count !== undefined && (
                          <span className="text-[10px] px-1.5 py-0.2 bg-[#20222c] text-zinc-400 rounded-full font-mono">
                            {option.count}
                          </span>
                        )}
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-[#cc9166]" />}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Action Tools */}
        <div className="flex items-center gap-2 ml-auto">

          <button
            onClick={onOpenDriveModal}
            className="px-2 py-1 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-medium flex items-center gap-1 transition shrink-0"
            title="Google Drive"
          >
            <Cloud className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Drive</span>
          </button>

          {onOpenExtensionModal && (
            <button
              onClick={onOpenExtensionModal}
              className="px-2 py-1 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/30 text-xs font-semibold flex items-center gap-1 transition shadow-sm shrink-0"
              title="크롬 확장프로그램 10초 설치 및 다운로드 가이드"
            >
              <span>🧩</span>
              <span className="hidden md:inline">확장</span>
            </button>
          )}


          <button
            onClick={handleSyncBuy}
            disabled={isBuySyncing}
            className="px-2 py-1 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-semibold flex items-center gap-1 transition shadow-sm shrink-0 disabled:opacity-50"
            title="high A+ 모바일 매입연동 실시간 동기화 (/api/settlement/sync_highplus_buy)"
          >
            <span>📦</span>
            <span className="hidden md:inline">{isBuySyncing ? '동기화 중...' : '매입연동'}</span>
          </button>

          <button
            onClick={handleSyncStock}
            disabled={isStockSyncing}
            className="px-2 py-1 rounded-lg bg-violet-500/10 hover:bg-violet-500/20 text-violet-300 border border-violet-500/30 text-xs font-semibold flex items-center gap-1 transition shadow-sm shrink-0 disabled:opacity-50"
            title="오토플러스.Data 전사 보유재고 및 판매완료 실시간 최신화 (/api/autoplus/sync_now)"
          >
            <span>🏢</span>
            <span className="hidden md:inline">{isStockSyncing ? '최신화 중...' : '보유재고'}</span>
          </button>

          <button
            onClick={onOpenCookieModal}
            className={`px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1 border transition shrink-0 ${
              cookieStatus === 'active'
                ? 'bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-semibold'
                : 'bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border-amber-500/30 animate-pulse'
            }`}
          >
            <Key className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">{cookieStatus === 'active' ? '🟢 활성' : '🔑 연동'}</span>
          </button>
        </div>

      </div>
    </header>
  );
};
