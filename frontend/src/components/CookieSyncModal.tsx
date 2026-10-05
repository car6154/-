import React, { useState } from 'react';
import { X, Key, ShieldCheck, Laptop, Smartphone, Copy, Check, Server, RefreshCw } from 'lucide-react';

interface CookieSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  cookieStatus: 'active' | 'expired' | 'missing';
  onUpdateCookie: (cookie: string) => Promise<boolean>;
}

export const CookieSyncModal: React.FC<CookieSyncModalProps> = ({
  isOpen,
  onClose,
  cookieStatus,
  onUpdateCookie,
}) => {
  const [copied, setCopied] = useState(false);
  const [manualCookie, setManualCookie] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<string | null>(null);
  const [serverLogs, setServerLogs] = useState<string[]>([]);

  if (!isOpen) return null;

  const secretToken = 'jpro_sec_9981_live_auth';

  const handleCopyToken = () => {
    navigator.clipboard.writeText(secretToken);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveCookie = async () => {
    if (!manualCookie.trim()) return;
    setIsSaving(true);
    setSaveResult(null);
    try {
      const ok = await onUpdateCookie(manualCookie.trim());
      if (ok) {
        setSaveResult('✅ 헤이딜러 세션 쿠키가 클라우드 금고에 안전하게 저장되었습니다!');
        setManualCookie('');
      } else {
        setSaveResult('❌ 세션 쿠키 검증에 실패했습니다. 유효한 쿠키인지 확인해 주세요.');
      }
    } catch {
      setSaveResult('❌ 저장 중 오류가 발생했습니다.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#12161F] border border-slate-700/80 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                헤이딜러 세션 & 기기 연동 센터
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-full font-medium border ${
                    cookieStatus === 'active'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}
                >
                  {cookieStatus === 'active' ? '🟢 세션 활성 (24H 준비)' : '🔴 세션 만료됨'}
                </span>
              </h2>
              <p className="text-xs text-slate-400">PC·노트북 자동 동기화 & 모바일 공용 금고</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-sm">
          {/* Architecture Card */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              크롬 확장프로그램 & 세션 연동 시스템
            </h4>
            
            {/* Download Extension Banner */}
            <div className="p-3.5 rounded-xl bg-gradient-to-r from-blue-950/60 to-slate-900 border border-blue-500/30 flex flex-col sm:flex-row items-center justify-between gap-3">
              <div className="space-y-0.5 text-center sm:text-left">
                <div className="text-xs font-bold text-white flex items-center gap-1.5 justify-center sm:justify-start">
                  <span>📦 J-PRO 크롬 확장프로그램 패키지</span>
                  <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 py-0.5 rounded border border-blue-500/30">v1.2</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  헤이딜러 & 차얼마 쿠키를 클릭 한 번으로 자동 동기화합니다.
                </div>
              </div>
              <a
                href="/jpro_chrome_extension.zip"
                download="jpro_chrome_extension.zip"
                className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition flex items-center gap-1.5 shadow-md shadow-blue-600/30 whitespace-nowrap"
              >
                📥 확장프로그램 다운로드 (.zip)
              </a>
            </div>

            {/* Quick 3-Step Guide */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs pt-1">
              <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50 space-y-1">
                <div className="font-bold text-amber-300">1. 압축 해제</div>
                <div className="text-[11px] text-slate-400">다운로드받은 zip 파일의 압축을 바탕화면이나 폴더에 풉니다.</div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50 space-y-1">
                <div className="font-bold text-amber-300">2. 크롬에 등록</div>
                <div className="text-[11px] text-slate-400">
                  <code className="text-sky-300">chrome://extensions</code> 접속 ➔ [개발자 모드 ON] ➔ [압축해제된 로드]
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/50 space-y-1">
                <div className="font-bold text-emerald-300">3. 원클릭 전송</div>
                <div className="text-[11px] text-slate-400">헤이딜러 로그인 후 확장프로그램에서 [쿠키 전송] 클릭!</div>
              </div>
            </div>
          </div>

          {/* Extension Secret Token */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300">
                내 크롬 확장프로그램 인증 비밀 토큰 (<code className="text-amber-300">X-JPRO-Token</code>)
              </label>
              <button
                onClick={handleCopyToken}
                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? '복사됨!' : '토큰 복사'}
              </button>
            </div>
            <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800 font-mono text-xs text-amber-400 flex items-center justify-between select-all">
              <span>{secretToken}</span>
              <span className="text-[10px] text-slate-500 font-sans">외부 해킹 방지용</span>
            </div>
            <p className="text-[11px] text-slate-400">
              PC의 크롬 확장프로그램 설정 창에서 이 토큰을 등록해 두면, 인증 없는 외부 사이트의 접근이 100% 차단됩니다.
            </p>
          </div>

          {/* Manual Cookie Paste Fallback */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>수동 세션 쿠키 등록 (비상용)</span>
              <span className="text-[11px] text-slate-400">PC 없이 즉시 갱신할 때 사용</span>
            </label>
            <textarea
              rows={3}
              value={manualCookie}
              onChange={(e) => setManualCookie(e.target.value)}
              placeholder="헤이딜러 로그인 쿠키 문자열 또는 csrftoken을 붙여넣으세요..."
              className="w-full px-3 py-2 rounded-lg bg-black/40 border border-slate-800 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 font-mono"
            />
            <div className="flex items-center justify-between">
              <button
                onClick={handleSaveCookie}
                disabled={isSaving || !manualCookie.trim()}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium text-xs flex items-center gap-1.5 transition disabled:opacity-40"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isSaving ? 'animate-spin' : ''}`} />
                {isSaving ? '검증 및 저장 중...' : '클라우드 금고에 저장'}
              </button>
            </div>
            {saveResult && (
              <div className="text-xs p-2.5 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-200">
                {saveResult}
              </div>
            )}
          </div>

          {/* Live Server Logs Viewer */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <span>🖥️ 실시간 서버 통신 로그</span>
                <span className="text-[10px] text-slate-500 font-mono">/api/logs</span>
              </label>
              <button
                type="button"
                onClick={async () => {
                  try {
                    const res = await fetch('/api/logs');
                    const d = await res.json();
                    setServerLogs(d.logs || []);
                  } catch (e: any) {
                    setServerLogs([`로그 조회 실패: ${e.message}`]);
                  }
                }}
                className="text-[11px] px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 transition cursor-pointer"
              >
                <RefreshCw className="w-3 h-3" />
                <span>새로고침</span>
              </button>
            </div>
            <div className="bg-black/60 border border-slate-800 rounded-lg p-2.5 max-h-40 overflow-y-auto font-mono text-[10px] text-slate-300 space-y-1">
              {serverLogs.length === 0 ? (
                <div className="text-slate-500 py-1">위의 [새로고침]을 누르면 실시간 백엔드 및 헤이딜러 통신 로그를 확인할 수 있습니다.</div>
              ) : (
                serverLogs.map((log, i) => (
                  <div
                    key={i}
                    className={`leading-relaxed ${
                      log.includes('HEYDEALER_IN] Response status 401')
                        ? 'text-rose-400 font-bold'
                        : log.includes('HEYDEALER_IN] Response status 200')
                        ? 'text-emerald-400 font-bold'
                        : log.includes('HEYDEALER_OUT')
                        ? 'text-amber-300'
                        : 'text-slate-400'
                    }`}
                  >
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
