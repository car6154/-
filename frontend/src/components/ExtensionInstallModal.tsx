import React, { useState } from 'react';
import { X, Puzzle, Download, Copy, Check, Laptop, ShieldCheck } from 'lucide-react';

interface ExtensionInstallModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExtensionInstallModal: React.FC<ExtensionInstallModalProps> = ({ isOpen, onClose }) => {
  const [copiedPath, setCopiedPath] = useState(false);
  const [copiedToken, setCopiedToken] = useState(false);

  if (!isOpen) return null;

  const notebookExtensionPath = 'C:\\jpro\\chrome_extension';
  const secretToken = 'jpro_sec_9981_live_auth';

  const handleCopyPath = () => {
    navigator.clipboard.writeText(notebookExtensionPath);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const handleCopyToken = () => {
    navigator.clipboard.writeText(secretToken);
    setCopiedToken(true);
    setTimeout(() => setCopiedToken(false), 2000);
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="bg-[#10131B] border border-slate-800 rounded-2xl w-full max-w-xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]"
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
              <Puzzle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                크롬 확장프로그램 설치 &amp; 가이드
                <span className="text-[11px] px-2 py-0.5 rounded-full font-bold bg-sky-500/20 text-sky-300 border border-sky-500/40">
                  v1.2 최신
                </span>
              </h2>
              <p className="text-xs text-slate-400">헤이딜러 &amp; 차얼마 쿠키 자동 전송 지원</p>
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
        <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-300">
          
          {/* SECTION 1: 노트북 환경 (초고속 10초 설치) */}
          <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/40 space-y-3">
            <div className="flex items-center gap-2">
              <Laptop className="w-4 h-4 text-emerald-400" />
              <h4 className="text-xs font-bold text-emerald-300 tracking-wide">
                💻 노트북(jpro) 크롬 10초 설치법 (다운로드 불필요!)
              </h4>
            </div>

            <p className="text-[11.5px] text-slate-300 leading-relaxed">
              노트북 머신에는 이미 최신 확장 파일이 저장되어 있으므로 <strong className="text-emerald-400">다운로드나 압축 풀기 없이</strong> 바로 크롬에 등록하시면 됩니다:
            </p>

            <ol className="space-y-2 pl-1 font-sans">
              <li className="flex items-start gap-2">
                <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px]">1</span>
                <span>노트북 크롬 주소창에 <code className="px-1.5 py-0.5 bg-black/60 rounded text-amber-300 font-mono">chrome://extensions</code> 입력 후 엔터</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px]">2</span>
                <span>우측 상단 <strong className="text-white">[개발자 모드]</strong> 스위치 켜기</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px]">3</span>
                <span>좌측 상단 <strong className="text-white">[압축해제된 확장 프로그램을 로드합니다]</strong> 클릭</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px]">4</span>
                <span className="flex-1">
                  폴더 선택 창에 아래 경로를 그대로 선택:
                  <div className="mt-1 flex items-center justify-between p-2 rounded bg-black/60 border border-slate-800 font-mono text-emerald-300">
                    <span>{notebookExtensionPath}</span>
                    <button
                      onClick={handleCopyPath}
                      className="px-2 py-0.5 rounded bg-emerald-600/40 hover:bg-emerald-600/60 text-emerald-200 text-[10px] flex items-center gap-1 transition"
                    >
                      {copiedPath ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedPath ? '복사됨!' : '경로 복사'}</span>
                    </button>
                  </div>
                </span>
              </li>
            </ol>
          </div>

          {/* SECTION 2: 타 PC 또는 ZIP 수동 다운로드 */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-sky-400" />
                <h4 className="text-xs font-bold text-slate-200 tracking-wide">
                  📥 다른 PC 설치 (.ZIP 다운로드)
                </h4>
              </div>
              <a
                href="/jpro_chrome_extension.zip"
                download="jpro_chrome_extension.zip"
                className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow-sm"
              >
                <Download className="w-3.5 h-3.5" />
                <span>최신 ZIP 다운로드 (11.5KB)</span>
              </a>
            </div>

            <p className="text-[11.5px] text-slate-400 leading-relaxed">
              다른 PC에서 사용 시 위 버튼으로 압축파일을 내려받아 압축 해제 후, 크롬 <code className="text-amber-300 font-mono">chrome://extensions</code>에서 해제된 폴더를 선택하시면 됩니다.
            </p>
          </div>

          {/* SECTION 3: 전용 인증 토큰 */}
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-amber-400" />
                <h4 className="text-xs font-bold text-slate-200 tracking-wide">
                  🔑 확장프로그램 전용 인증 비밀 토큰
                </h4>
              </div>
              <button
                onClick={handleCopyToken}
                className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1 transition"
              >
                {copiedToken ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedToken ? '토큰 복사됨!' : '토큰 복사'}</span>
              </button>
            </div>

            <p className="text-[11px] text-slate-400">
              확장 팝업 우측 상단 ⚙️ 설정에서 인증 토큰을 요청하면 아래 값을 1회 입력하시면 됩니다.
            </p>

            <div className="p-2.5 rounded-lg bg-black/60 border border-slate-800 font-mono text-xs text-amber-300 flex items-center justify-between">
              <span>{secretToken}</span>
              <span className="text-[10px] text-slate-500 font-sans">고유 보안키</span>
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-900/60 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
};
