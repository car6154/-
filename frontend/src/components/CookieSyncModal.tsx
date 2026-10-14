import React, { useState, useEffect } from 'react';
import { 
  X, Key, ShieldCheck, Copy, Check, RefreshCw, 
  Terminal, ChevronDown, ChevronUp, AlertTriangle, 
  CheckCircle2, Download, ExternalLink, Cpu,
  Zap, Settings, Shield
} from 'lucide-react';

interface CookieSyncModalProps {
  isOpen: boolean;
  onClose: () => void;
  cookieStatus: 'active' | 'expired' | 'missing';
  onUpdateCookie: (cookie: string) => Promise<boolean>;
}

type CookieTarget = 'heydealer' | 'autoplus' | 'encar';

export const CookieSyncModal: React.FC<CookieSyncModalProps> = ({
  isOpen,
  onClose,
  cookieStatus,
  onUpdateCookie,
}) => {
  const [activeCookieTab, setActiveCookieTab] = useState<CookieTarget>('heydealer');
  const [manualCookie, setManualCookie] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [saveResult, setSaveResult] = useState<{ success: boolean; text: string } | null>(null);

  // ⚡ 원클릭 자동 로그인 상태
  const [isAutoLoggingIn, setIsAutoLoggingIn] = useState(false);
  const [autoLoginTarget, setAutoLoginTarget] = useState<'heydealer' | 'autoplus' | null>(null);
  const [credentialStatus, setCredentialStatus] = useState<{
    hasAutoplusCredentials?: boolean;
    hasHeydealerCredentials?: boolean;
    autoplusMaskedId?: string;
    heydealerMaskedId?: string;
  }>({});
  const [showCredModal, setShowCredModal] = useState(false);
  const [credIdInput, setCredIdInput] = useState('');
  const [credPwInput, setCredPwInput] = useState('');
  const [isSavingCred, setIsSavingCred] = useState(false);

  // Git 동기화 & 원격 복구 상태
  const [gitStatus, setGitStatus] = useState<string>('조회 중...');
  const [isGitActionRunning, setIsGitActionRunning] = useState(false);
  const [gitActionResult, setGitActionResult] = useState<string | null>(null);

  // 3사 쿠키 상태
  const [cookieInfo, setCookieInfo] = useState<{
    hasHeydealer: boolean;
    hasAutoplus: boolean;
    hasEncar: boolean;
    heydealerLen: number;
    autoplusLen: number;
  }>({
    hasHeydealer: false,
    hasAutoplus: false,
    hasEncar: false,
    heydealerLen: 0,
    autoplusLen: 0,
  });

  // 확장프로그램 가이드 아코디언 접기/펼치기 (기본값: 접힘)
  const [showExtensionGuide, setShowExtensionGuide] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  // 서버 로그
  const [serverLogs, setServerLogs] = useState<string[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);

  // 3대 서버 일괄 재가동 상태
  const [isRestartingServers, setIsRestartingServers] = useState(false);

  const secretToken = 'jpro_sec_9981_live_auth';

  // 모달 열릴 때 상태 조회
  useEffect(() => {
    if (!isOpen) return;
    fetchGitStatus();
    fetchCookieStatus();
    fetchCredentialStatus();
  }, [isOpen]);

  const fetchGitStatus = async () => {
    try {
      const res = await fetch('/api/git/status');
      if (res.ok) {
        const d = await res.json();
        setGitStatus(d.statusBadge || d.lastSyncStatus || '정상');
      } else {
        setGitStatus('백엔드 응답 대기');
      }
    } catch {
      setGitStatus('오프라인 / 연결 대기');
    }
  };

  const fetchCookieStatus = async () => {
    try {
      const res = await fetch('/api/session/cookie');
      if (res.ok) {
        const d = await res.json();
        setCookieInfo({
          hasHeydealer: Boolean(d.hasCookie),
          hasAutoplus: Boolean(d.hasAutoplusCookie),
          hasEncar: true, // 기본 검색 가능
          heydealerLen: d.cookieLength || 0,
          autoplusLen: d.autoplusCookieLength || 0,
        });
      }
    } catch {}
  };

  const fetchCredentialStatus = async () => {
    try {
      const res = await fetch('/api/auth/credentials/status');
      if (res.ok) {
        const d = await res.json();
        setCredentialStatus(d);
      }
    } catch {}
  };

  // ⚡ 원클릭 자동 로그인 실행 (토큰 소모 0개)
  const handleQuickAutoLogin = async (target: 'heydealer' | 'autoplus') => {
    setIsAutoLoggingIn(true);
    setAutoLoginTarget(target);
    setSaveResult(null);

    const targetName = target === 'heydealer' ? '헤이딜러' : '차얼마 (오토플러스)';
    try {
      const res = await fetch('/api/auth/quick_login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
      });
      const data = await res.json();
      if (data.success) {
        setSaveResult({
          success: true,
          text: `⚡ ${data.message || `${targetName} 자동 로그인 및 쿠키 최신화 성공!`}`
        });
        fetchCookieStatus();
      } else {
        setSaveResult({
          success: false,
          text: `❌ ${data.message || `${targetName} 자동 로그인 실패`}`
        });
        if (data.need_credentials) {
          setShowCredModal(true);
        }
      }
    } catch (err: any) {
      setSaveResult({
        success: false,
        text: `❌ 통신 오류: ${err.message}`
      });
    } finally {
      setIsAutoLoggingIn(false);
      setAutoLoginTarget(null);
    }
  };

  // 계정 1회 저장
  const handleSaveCredentials = async () => {
    if (!credIdInput.trim() || !credPwInput.trim()) {
      alert('아이디와 비밀번호를 모두 입력해주세요.');
      return;
    }
    setIsSavingCred(true);
    try {
      const res = await fetch('/api/auth/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform: activeCookieTab,
          userId: credIdInput.trim(),
          userPw: credPwInput.trim(),
        })
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message || '계정 정보가 안전하게 저장되었습니다.');
        setCredIdInput('');
        setCredPwInput('');
        setShowCredModal(false);
        fetchCredentialStatus();
      } else {
        alert(`저장 실패: ${data.message}`);
      }
    } catch (e: any) {
      alert(`오류 발생: ${e.message}`);
    } finally {
      setIsSavingCred(false);
    }
  };

  if (!isOpen) return null;

  // 원격 강제 동기화 (Force Pull - 머지 충돌 0초 강제 해결)
  const handleForcePull = async () => {
    if (!confirm('⚡ 노트북 서버를 GitHub 최신 커밋으로 즉시 강제 동기화(Reset & Pull)하시겠습니까?\n\n이전에 발생한 머지 충돌이 100% 자동 해소됩니다.')) {
      return;
    }
    setIsGitActionRunning(true);
    setGitActionResult(null);
    try {
      const res = await fetch('/api/git/sync?action=force_pull', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setGitActionResult(`✅ 원격 강제 동기화 성공! (${data.message?.slice(0, 50) || '최신 반영됨'})`);
        fetchGitStatus();
      } else {
        setGitActionResult(`❌ 동기화 실패: ${data.message || '오류 발생'}`);
      }
    } catch (e: any) {
      setGitActionResult(`❌ 서버 통신 오류: ${e.message}`);
    } finally {
      setIsGitActionRunning(false);
    }
  };

  // 일반 Git Pull
  const handleNormalPull = async () => {
    setIsGitActionRunning(true);
    setGitActionResult(null);
    try {
      const res = await fetch('/api/git/sync?action=pull', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setGitActionResult(`✅ Git Pull 완료: ${data.message}`);
        fetchGitStatus();
      } else {
        setGitActionResult(`⚠️ Pull 거절됨 (충돌 감지): 옆의 [강제 동기화]를 눌러주세요.`);
      }
    } catch (e: any) {
      setGitActionResult(`❌ 통신 실패: ${e.message}`);
    } finally {
      setIsGitActionRunning(false);
    }
  };

  // 3대 서버 일괄 재가동 (FastAPI 8000, Frontend 3000, Streamlit 8501)
  const handleRestartAllServers = async () => {
    if (!confirm('🔄 J-PRO 3대 서버(FastAPI 8000 / Frontend 3000 / Streamlit 8501)를 일괄 재가동하시겠습니까?\n\n약 5~8초 동안 서버가 완전히 재기동되며, 완료 후 브라우저가 자동 새로고침됩니다.')) {
      return;
    }
    setIsRestartingServers(true);
    setGitActionResult(null);
    try {
      const res = await fetch('/api/server/restart_all', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        setGitActionResult(`🔄 서버 재가동 프로세스 시작됨! 6초 후 화면이 자동 새로고침됩니다.`);
        setTimeout(() => {
          window.location.reload();
        }, 6000);
      } else {
        setGitActionResult(`❌ 재가동 실패: ${data.message || '오류 발생'}`);
      }
    } catch (e: any) {
      setGitActionResult(`❌ 서버 통신 오류: ${e.message}`);
    } finally {
      setTimeout(() => setIsRestartingServers(false), 6000);
    }
  };

  // 클립보드 쿠키 읽어오기
  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && text.trim()) {
        setManualCookie(text.trim());
      }
    } catch {
      alert('클립보드 접근 권한이 필요합니다.');
    }
  };

  // 쿠키 저장
  const handleSaveCookie = async () => {
    if (!manualCookie.trim()) return;
    setIsSaving(true);
    setSaveResult(null);

    try {
      if (activeCookieTab === 'heydealer') {
        const ok = await onUpdateCookie(manualCookie.trim());
        if (ok) {
          setSaveResult({ success: true, text: '✅ 헤이딜러 세션 쿠키가 클라우드 금고에 안전하게 저장되었습니다!' });
          setManualCookie('');
          fetchCookieStatus();
        } else {
          setSaveResult({ success: false, text: '❌ 헤이딜러 쿠키 검증에 실패했습니다. sessionid를 확인해 주세요.' });
        }
      } else {
        // 차얼마(오토플러스) 또는 엔카 쿠키 저장
        const res = await fetch('/api/save_cookie', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            cookie: manualCookie.trim(),
            target: activeCookieTab,
            secretToken
          })
        });
        const d = await res.json();
        if (res.ok && (d.success || d.status === 'ok')) {
          const targetName = activeCookieTab === 'autoplus' ? '차얼마(오토플러스)' : '엔카';
          setSaveResult({ success: true, text: `✅ ${targetName} 쿠키가 정상 저장되었습니다!` });
          setManualCookie('');
          fetchCookieStatus();
        } else {
          setSaveResult({ success: false, text: `❌ 저장 실패: ${d.message || d.error || '오류'}` });
        }
      }
    } catch (err: any) {
      setSaveResult({ success: false, text: `❌ 저장 중 오류: ${err.message}` });
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyToken = () => {
    navigator.clipboard.writeText(secretToken);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2000);
  };

  const fetchServerLogs = async () => {
    setIsLoadingLogs(true);
    try {
      const res = await fetch('/api/logs');
      const d = await res.json();
      setServerLogs(d.logs || []);
    } catch (e: any) {
      setServerLogs([`로그 조회 실패: ${e.message}`]);
    } finally {
      setIsLoadingLogs(false);
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-[#10131B] border border-slate-800 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]"
      >
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/70">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                J-PRO 시스템 & 세션 연동 센터
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-full font-medium border ${
                    cookieStatus === 'active'
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
                  }`}
                >
                  {cookieStatus === 'active' ? '🟢 헤이딜러 활성' : '🔴 세션 만료'}
                </span>
              </h2>
              <p className="text-xs text-slate-400">노트북 원격 복구 · 3사 쿠키 통합 금고 · 통신 모니터링</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-sm">
          
          {/* SECTION 1: 노트북 원격 제어 & Git 비상 복구 */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-sky-400" />
                <h4 className="text-xs font-bold text-slate-200 tracking-wide">
                  노트북 원격 서버 상태 & 비상 복구
                </h4>
              </div>
              <span className="text-[11px] font-mono text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/50">
                {gitStatus}
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              외부에서 코드 갱신이 멈추거나 충돌 발생 시, 아래 버튼 하나로 노트북 서버를 100% 최신 상태로 강제 복구합니다.
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button
                onClick={handleForcePull}
                disabled={isGitActionRunning}
                className="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-sm disabled:opacity-50"
                title="Git 충돌을 강제 취소하고 origin/main 최신 코드로 즉시 복구합니다"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isGitActionRunning ? 'animate-spin' : ''}`} />
                <span>⚡ 원격 강제 동기화 (Force Pull)</span>
              </button>

              <button
                onClick={handleNormalPull}
                disabled={isGitActionRunning}
                className="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs flex items-center gap-1.5 transition border border-slate-700 disabled:opacity-50"
              >
                <span>일반 Pull</span>
              </button>

              <button
                onClick={handleRestartAllServers}
                disabled={isRestartingServers || isGitActionRunning}
                className="px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-sm disabled:opacity-50"
                title="FastAPI(8000), Frontend(3000), Streamlit(8501) 3대 서버를 완전히 껐다 켭니다"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRestartingServers ? 'animate-spin' : ''}`} />
                <span>🔄 3대 서버 일괄 재가동</span>
              </button>

              <button
                onClick={fetchGitStatus}
                className="px-2.5 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition border border-slate-700"
                title="상태 새로고침"
              >
                새로고침
              </button>
            </div>

            {gitActionResult && (
              <div className="p-2.5 rounded-lg bg-black/40 border border-slate-800 text-xs text-slate-200 font-mono">
                {gitActionResult}
              </div>
            )}
          </div>

          {/* SECTION 2: 3대 플랫폼 세션 쿠키 관리 */}
          {/* SECTION 2: 3대 플랫폼 세션 쿠키 관리 & ⚡ 원클릭 자동 갱신 */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-slate-200 tracking-wide flex items-center gap-1.5">
                <Key className="w-4 h-4 text-amber-400" />
                3사 플랫폼 세션 쿠키 관리 &amp; ⚡ 원클릭 자동 갱신
              </h4>
              <button
                onClick={handlePasteClipboard}
                className="text-xs text-amber-400 hover:text-amber-300 font-medium flex items-center gap-1 transition"
              >
                📋 클립보드 붙여넣기
              </button>
            </div>

            {/* Platform Tabs & Quick Action Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setActiveCookieTab('heydealer'); setSaveResult(null); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                    activeCookieTab === 'heydealer'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <span>헤이딜러</span>
                  <span className={`w-2 h-2 rounded-full ${cookieInfo.hasHeydealer ? 'bg-emerald-400' : 'bg-rose-400'}`} />
                </button>

                <button
                  onClick={() => { setActiveCookieTab('autoplus'); setSaveResult(null); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                    activeCookieTab === 'autoplus'
                      ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <span>차얼마 (오토플러스)</span>
                  <span className={`w-2 h-2 rounded-full ${cookieInfo.hasAutoplus ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                </button>

                <button
                  onClick={() => { setActiveCookieTab('encar'); setSaveResult(null); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition ${
                    activeCookieTab === 'encar'
                      ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <span>엔카 (상세스펙)</span>
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                </button>
              </div>

              {/* ⚡ 선택된 플랫폼 원클릭 퀵 버튼 */}
              {activeCookieTab !== 'encar' && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setShowCredModal(!showCredModal)}
                    className="px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-md transition flex items-center gap-1 border border-slate-700/60"
                    title="자동 로그인용 아이디/비밀번호 설정"
                  >
                    <Settings className="w-3 h-3 text-slate-400" />
                    <span>
                      {activeCookieTab === 'heydealer'
                        ? (credentialStatus.hasHeydealerCredentials ? `계정: ${credentialStatus.heydealerMaskedId}` : '계정 등록')
                        : (credentialStatus.hasAutoplusCredentials ? `계정: ${credentialStatus.autoplusMaskedId}` : '계정 등록')}
                    </span>
                  </button>

                  <button
                    onClick={() => handleQuickAutoLogin(activeCookieTab)}
                    disabled={isAutoLoggingIn}
                    className="px-3 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow shadow-emerald-900/40 disabled:opacity-50"
                  >
                    <Zap className={`w-3.5 h-3.5 ${isAutoLoggingIn && autoLoginTarget === activeCookieTab ? 'animate-bounce text-amber-300' : 'text-amber-300'}`} />
                    <span>
                      {isAutoLoggingIn && autoLoginTarget === activeCookieTab
                        ? '로그인 처리 중 (약 3초)...'
                        : `${activeCookieTab === 'heydealer' ? '헤이딜러' : '차얼마'} ⚡ 자동 로그인`}
                    </span>
                  </button>
                </div>
              )}
            </div>

            {/* ⚡ 원클릭 전용 메인 액션 카드 (엔카 제외) */}
            {activeCookieTab !== 'encar' && (
              <div className="p-3 bg-gradient-to-r from-blue-950/30 to-indigo-950/20 rounded-lg border border-blue-500/20 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <div className="text-xs font-bold text-blue-200 flex items-center gap-1.5">
                      <Zap className="w-4 h-4 text-amber-400" />
                      <span>{activeCookieTab === 'heydealer' ? '헤이딜러' : '차얼마'} 원클릭 자동 로그인 &amp; 세션 갱신</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      노트북에서 브라우저가 자동 로그인 후 세션 쿠키를 3초 만에 갱신합니다. (AI 토큰 소모 0개)
                    </p>
                  </div>
                  <button
                    onClick={() => handleQuickAutoLogin(activeCookieTab)}
                    disabled={isAutoLoggingIn}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-lg shadow-emerald-900/40 disabled:opacity-50 whitespace-nowrap"
                  >
                    <Zap className={`w-4 h-4 ${isAutoLoggingIn && autoLoginTarget === activeCookieTab ? 'animate-spin text-amber-300' : 'text-amber-300'}`} />
                    <span>
                      {isAutoLoggingIn && autoLoginTarget === activeCookieTab
                        ? '자동 로그인 중...'
                        : `[${activeCookieTab === 'heydealer' ? '헤이딜러' : '차얼마'}] 지금 갱신하기`}
                    </span>
                  </button>
                </div>

                {/* 계정 등록 폼 (토글) */}
                {showCredModal && (
                  <div className="mt-2 pt-2 border-t border-blue-500/20 space-y-2 bg-black/40 p-2.5 rounded-md">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-amber-300 flex items-center gap-1">
                        <Shield className="w-3 h-3" />
                        {activeCookieTab === 'heydealer' ? '헤이딜러' : '차얼마'} 자동 로그인 계정 등록 (.env 로컬 금고 보관)
                      </span>
                      <button onClick={() => setShowCredModal(false)} className="text-slate-500 hover:text-slate-300 text-[11px]">✕ 닫기</button>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      * 계정 정보는 외부로 유출되지 않고 노트북 로컬(.env)에만 안전하게 1회 보관됩니다.
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <input
                        type="text"
                        placeholder="아이디"
                        value={credIdInput}
                        onChange={(e) => setCredIdInput(e.target.value)}
                        className="px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                      />
                      <input
                        type="password"
                        placeholder="비밀번호"
                        value={credPwInput}
                        onChange={(e) => setCredPwInput(e.target.value)}
                        className="px-2.5 py-1.5 bg-slate-900 border border-slate-700 rounded text-xs text-slate-200 focus:outline-none focus:border-amber-500"
                      />
                    </div>
                    <div className="flex justify-end">
                      <button
                        onClick={handleSaveCredentials}
                        disabled={isSavingCred}
                        className="px-3 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold transition"
                      >
                        {isSavingCred ? '저장 중...' : '계정 정보 1회 안전 저장'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 수동 등록 Form (보조용) */}
            <div className="space-y-2 pt-1">
              <div className="text-[11px] text-slate-400 flex items-center justify-between">
                <span>또는 기존 수동 쿠키 직접 붙여넣기:</span>
                <span className="text-slate-500">
                  {activeCookieTab === 'heydealer' && `현재 등록: ${cookieInfo.heydealerLen}자`}
                  {activeCookieTab === 'autoplus' && `현재 등록: ${cookieInfo.autoplusLen}자`}
                  {activeCookieTab === 'encar' && '실시간 자동 회전 중'}
                </span>
              </div>

              <textarea
                rows={2}
                value={manualCookie}
                onChange={(e) => setManualCookie(e.target.value)}
                placeholder={
                  activeCookieTab === 'heydealer'
                    ? '헤이딜러 로그인 쿠키 문자열 또는 csrftoken을 직접 붙여넣으실 수도 있습니다...'
                    : activeCookieTab === 'autoplus'
                    ? '차얼마/오토플러스 로그인 쿠키를 직접 붙여넣으실 수도 있습니다...'
                    : '엔카 로그인 쿠키 문자열을 붙여넣으세요...'
                }
                className="w-full px-3 py-1.5 rounded-lg bg-black/40 border border-slate-800 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 font-mono"
              />

              <div className="flex items-center justify-end">
                <button
                  onClick={handleSaveCookie}
                  disabled={isSaving || !manualCookie.trim()}
                  className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs flex items-center gap-1.5 transition disabled:opacity-40 border border-slate-700"
                >
                  <RefreshCw className={`w-3 h-3 ${isSaving ? 'animate-spin' : ''}`} />
                  {isSaving ? '저장 중...' : '수동 쿠키 저장'}
                </button>
              </div>

              {saveResult && (
                <div className={`text-xs p-2.5 rounded-lg border ${
                  saveResult.success 
                    ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                    : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                }`}>
                  {saveResult.text}
                </div>
              )}
            </div>
          </div>

          {/* SECTION 3: 크롬 확장프로그램 (컴팩트 접이식) */}
          <div className="rounded-xl bg-slate-900/50 border border-slate-800 overflow-hidden">
            <button
              onClick={() => setShowExtensionGuide(!showExtensionGuide)}
              className="w-full px-4 py-3 flex items-center justify-between text-xs font-semibold text-slate-300 hover:bg-slate-800/40 transition"
            >
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-400" />
                <span>크롬 확장프로그램 자동 연동 (패키지 & 인증 토큰)</span>
              </div>
              {showExtensionGuide ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
            </button>

            {showExtensionGuide && (
              <div className="p-4 pt-1 border-t border-slate-800/80 space-y-3 bg-black/20 text-xs">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <div className="space-y-0.5">
                    <div className="font-bold text-white flex items-center gap-1.5">
                      <span>J-PRO 크롬 확장프로그램 v1.2</span>
                    </div>
                    <div className="text-[11px] text-slate-400">
                      브라우저 클릭 한 번으로 헤이딜러 & 차얼마 쿠키를 자동 갱신합니다.
                    </div>
                  </div>
                  <a
                    href="/jpro_chrome_extension.zip"
                    download="jpro_chrome_extension.zip"
                    className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs flex items-center gap-1 transition shrink-0"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>.zip 다운로드</span>
                  </a>
                </div>

                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">확장프로그램 전용 인증 비밀 토큰</span>
                    <button
                      onClick={handleCopyToken}
                      className="text-[11px] text-blue-400 hover:text-blue-300 flex items-center gap-1"
                    >
                      {copiedToken ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedToken ? '복사됨!' : '토큰 복사'}</span>
                    </button>
                  </div>
                  <div className="p-2 rounded bg-black/60 border border-slate-800 font-mono text-xs text-amber-300 select-all">
                    {secretToken}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* SECTION 4: 실시간 서버 통신 로그 */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-slate-400" />
                <span>실시간 백엔드 통신 로그</span>
                <span className="text-[10px] text-slate-500 font-mono">/api/logs</span>
              </label>
              <button
                type="button"
                onClick={fetchServerLogs}
                disabled={isLoadingLogs}
                className="text-[11px] px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 transition"
              >
                <RefreshCw className={`w-3 h-3 ${isLoadingLogs ? 'animate-spin' : ''}`} />
                <span>새로고침</span>
              </button>
            </div>
            <div className="bg-black/60 border border-slate-800 rounded-lg p-2.5 max-h-36 overflow-y-auto font-mono text-[10px] text-slate-300 space-y-1">
              {serverLogs.length === 0 ? (
                <div className="text-slate-500 py-1">위의 [새로고침]을 누르면 실시간 통신 로그를 확인할 수 있습니다.</div>
              ) : (
                serverLogs.map((log, i) => (
                  <div
                    key={i}
                    className={`leading-relaxed ${
                      log.includes('401')
                        ? 'text-rose-400 font-bold'
                        : log.includes('200')
                        ? 'text-emerald-400'
                        : log.includes('COOKIE_SYNC')
                        ? 'text-amber-300 font-bold'
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
