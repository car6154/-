import React, { useState, useRef, useEffect } from 'react';
import { Search, Car, Cloud, Key, ChevronDown, Check } from 'lucide-react';

export type AppTab = 'cockpit' | 'ledger' | 'settlement' | 'soldout' | 'performance' | 'inventory';

interface HeaderProps {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  totalCarsCount: number;
  totalBuyAmount: number;
  avgMargin: number;
  onOpenAddModal?: () => void;
  onOpenDriveModal: () => void;
  onOpenCookieModal: () => void;
  onPasteClipboardCookie?: () => void;
  cookieStatus: 'active' | 'expired' | 'missing';
  isPrivateUnlocked?: boolean;
  setIsPrivateUnlocked?: (unlocked: boolean | ((prev: boolean) => boolean)) => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
  totalCarsCount,
  onOpenDriveModal,
  onOpenCookieModal,
  onPasteClipboardCookie,
  cookieStatus,
}) => {
  const [copiedLink, setCopiedLink] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleCopyLink = () => {
    navigator.clipboard.writeText('https://tinyurl.com/jpro-live');
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2500);
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

        {/* Right: Search & Action Tools */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Search Box */}
          <div className="relative w-36 sm:w-48">
            <Search className="w-3.5 h-3.5 text-[#9194a1] absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="차량/모델 검색..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-7 pr-2.5 py-1 text-xs bg-[#121317] border border-[#1c1d22] rounded-lg text-white placeholder-[#5e616e] focus:outline-none focus:border-[#cc9166] transition"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-[#9194a1] hover:text-white"
              >
                ✕
              </button>
            )}
          </div>

          <button
            onClick={handleCopyLink}
            className={`px-2 py-1 rounded-lg text-xs font-medium flex items-center gap-1 transition shrink-0 ${
              copiedLink
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                : 'bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30'
            }`}
            title="대표님 전용 단축 주소 복사"
          >
            <span>{copiedLink ? '✓' : '🔗'}</span>
            <span className="hidden md:inline font-mono">
              {copiedLink ? '복사됨!' : '주소'}
            </span>
          </button>

          <button
            onClick={onOpenDriveModal}
            className="px-2 py-1 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 text-xs font-medium flex items-center gap-1 transition shrink-0"
            title="Google Drive"
          >
            <Cloud className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Drive</span>
          </button>

          {onPasteClipboardCookie && (
            <button
              onClick={onPasteClipboardCookie}
              className="px-2 py-1 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold flex items-center gap-1 transition shadow-sm shrink-0"
              title="클립보드에 복사된 헤이딜러/차얼마 쿠키를 즉시 연동합니다"
            >
              <span>📋</span>
              <span className="hidden md:inline">쿠키</span>
            </button>
          )}

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
