import React from 'react';
import { Calculator, FileText, Clock, CheckCircle2, TrendingUp, Warehouse } from 'lucide-react';
import type { AppTab } from './Header';

interface MobileNavProps {
  activeTab: AppTab;
  setActiveTab: (tab: AppTab) => void;
}

export const MobileNav: React.FC<MobileNavProps> = ({ activeTab, setActiveTab }) => {
  return (
    <div className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-[#07080B]/95 backdrop-blur-lg border-t border-[#1c1d22] px-1 py-1.5 flex items-center justify-around safe-area-pb">
      <button
        onClick={() => setActiveTab('cockpit')}
        className={`flex flex-col items-center py-1 px-2 rounded-lg transition ${
          activeTab === 'cockpit' ? 'text-[#cc9166]' : 'text-[#9194a1] hover:text-white'
        }`}
      >
        <Calculator className="w-4 h-4 mb-0.5" />
        <span className="text-[9px] font-medium">시세</span>
      </button>

      <button
        onClick={() => setActiveTab('ledger')}
        className={`flex flex-col items-center py-1 px-2 rounded-lg transition ${
          activeTab === 'ledger' ? 'text-[#cc9166]' : 'text-[#9194a1] hover:text-white'
        }`}
      >
        <FileText className="w-4 h-4 mb-0.5" />
        <span className="text-[9px] font-medium">장부</span>
      </button>

      <button
        onClick={() => setActiveTab('settlement')}
        className={`flex flex-col items-center py-1 px-2 rounded-lg transition ${
          activeTab === 'settlement' ? 'text-[#cc9166]' : 'text-[#9194a1] hover:text-white'
        }`}
      >
        <Clock className="w-4 h-4 mb-0.5" />
        <span className="text-[9px] font-medium">정산</span>
      </button>

      <button
        onClick={() => setActiveTab('soldout')}
        className={`flex flex-col items-center py-1 px-2 rounded-lg transition ${
          activeTab === 'soldout' ? 'text-[#cc9166]' : 'text-[#9194a1] hover:text-white'
        }`}
      >
        <CheckCircle2 className="w-4 h-4 mb-0.5" />
        <span className="text-[9px] font-medium">완판</span>
      </button>

      <button
        onClick={() => setActiveTab('performance')}
        className={`flex flex-col items-center py-1 px-2 rounded-lg transition ${
          activeTab === 'performance' ? 'text-[#cc9166]' : 'text-[#9194a1] hover:text-white'
        }`}
      >
        <TrendingUp className="w-4 h-4 mb-0.5" />
        <span className="text-[9px] font-medium">실적DB</span>
      </button>

      <button
        onClick={() => setActiveTab('inventory')}
        className={`flex flex-col items-center py-1 px-2 rounded-lg transition ${
          activeTab === 'inventory' ? 'text-[#cc9166]' : 'text-[#9194a1] hover:text-white'
        }`}
      >
        <Warehouse className="w-4 h-4 mb-0.5" />
        <span className="text-[9px] font-medium">재고</span>
      </button>
    </div>
  );
};
