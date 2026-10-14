import React from 'react';

export interface CarDamageDiagram2DProps {
  selectedEncar: any;
}

interface DamagePart {
  code: string;
  kw: string[];
  exclude?: string[];
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  full: string;
}

export const CarDamageDiagram2D: React.FC<CarDamageDiagram2DProps> = ({ selectedEncar }) => {
  if (!selectedEncar) return null;

  const matchesPart = (part: DamagePart, itemStr: string) => {
    const normItem = String(itemStr || '').toLowerCase().replace(/[\s_\-()]/g, '');
    if (!normItem) return false;

    // 배제 키워드 검사 (배제어가 하나라도 포함되면 절대 매칭 불가)
    if (part.exclude && part.exclude.some(ex => normItem.includes(ex.toLowerCase().replace(/[\s_\-()]/g, '')))) {
      return false;
    }

    // 1. 표준 부위 코드 정확 일치
    const normCode = (part.code || '').toLowerCase().replace(/[\s_\-()]/g, '');
    if (normCode && normItem === normCode) {
      return true;
    }

    // 2. 키워드 매칭 (완전 일치 또는 타겟 명칭이 키워드를 포함할 때만! 역방향 k.includes(normItem)은 전면 금지)
    for (const k of part.kw) {
      const normK = k.toLowerCase().replace(/[\s_\-()]/g, '');
      if (normItem === normK || normItem.includes(normK)) {
        return true;
      }
    }

    return false;
  };

  const checkStatus = (part: DamagePart) => {
    const dData = selectedEncar?.damageData || {};
    const rep = (selectedEncar?.replaces || []) as string[];
    const fix = (selectedEncar?.repairs || []) as string[];
    const repNames = (selectedEncar?.replaceNames || []) as string[];
    const fixNames = (selectedEncar?.repairNames || []) as string[];

    // 1. 교환 부위 대조
    for (const r of [...rep, ...repNames]) {
      if (matchesPart(part, r)) return '#ef4444';
    }

    // 2. 판금/수리 부위 대조
    for (const f of [...fix, ...fixNames]) {
      if (matchesPart(part, f)) return '#f59e0b';
    }

    // 3. damageData 객체 검사
    for (const [pName, st] of Object.entries(dData)) {
      if (matchesPart(part, pName)) {
        if (st === '교환') return '#ef4444';
        if (st === '판금' || st === '용접') return '#f59e0b';
      }
    }

    return '#1e293b';
  };

  // 외판 부위 (사이드실 패널을 차체 바닥 양측면에 맞추어 완벽히 정렬)
  const outerParts: DamagePart[] = [
    { code: 'HOOD', kw: ['후드', '보닛', '본넷', 'hood', 'p010'], exclude: [], x: 55, y: 20, w: 110, h: 55, label: '후드', full: '후드(보닛)' },
    { code: 'F_FENDER_L', kw: ['앞휀더(좌)', '앞휀더좌', '프론트휀더(좌)', 'front_fender_left', 'front_fender_l', 'f_fender_l', 'p021'], exclude: ['뒤', '리어', 'rear', '우', 'right'], x: 18, y: 25, w: 33, h: 65, label: 'F휀', full: '프론트 휀더(좌)' },
    { code: 'F_FENDER_R', kw: ['앞휀더(우)', '앞휀더우', '프론트휀더(우)', 'front_fender_right', 'front_fender_r', 'f_fender_r', 'p022'], exclude: ['뒤', '리어', 'rear', '좌', 'left'], x: 169, y: 25, w: 33, h: 65, label: 'F휀', full: '프론트 휀더(우)' },
    { code: 'SIDE_SILL_L', kw: ['사이드실(좌)', '사이드실좌', '사이드실패널(좌)', 'side_sill_left', 'side_sill_l', 'p081'], exclude: ['우', 'right'], x: 18, y: 95, w: 12, h: 130, label: '실', full: '사이드실 패널(좌)' },
    { code: 'FRONT_DOOR_L', kw: ['앞문(좌)', '앞문좌', '앞도어(좌)', '앞도어좌', '프론트도어(좌)', 'front_door_left', 'front_door_l', 'p031'], exclude: ['뒤', '뒷', '리어', 'rear', '우', 'right'], x: 33, y: 98, w: 34, h: 60, label: 'F도', full: '프론트 도어(좌)' },
    { code: 'FRONT_DOOR_R', kw: ['앞문(우)', '앞문우', '앞도어(우)', '앞도어우', '프론트도어(우)', 'front_door_right', 'front_door_r', 'p032'], exclude: ['뒤', '뒷', '리어', 'rear', '좌', 'left'], x: 153, y: 98, w: 34, h: 60, label: 'F도', full: '프론트 도어(우)' },
    { code: 'SIDE_SILL_R', kw: ['사이드실(우)', '사이드실우', '사이드실패널(우)', 'side_sill_right', 'side_sill_r', 'p082'], exclude: ['좌', 'left'], x: 190, y: 95, w: 12, h: 130, label: '실', full: '사이드실 패널(우)' },
    { code: 'REAR_DOOR_L', kw: ['뒤문(좌)', '뒷문(좌)', '뒤문좌', '뒷문좌', '뒤도어(좌)', '뒤도어좌', '리어도어(좌)', 'rear_door_left', 'rear_door_l', 'p033'], exclude: ['앞', '프론트', 'front', '우', 'right'], x: 33, y: 163, w: 34, h: 60, label: 'R도', full: '리어 도어(좌)' },
    { code: 'REAR_DOOR_R', kw: ['뒤문(우)', '뒷문(우)', '뒤문우', '뒷문우', '뒤도어(우)', '뒤도어우', '리어도어(우)', 'rear_door_right', 'rear_door_r', 'p034'], exclude: ['앞', '프론트', 'front', '좌', 'left'], x: 153, y: 163, w: 34, h: 60, label: 'R도', full: '리어 도어(우)' },
    { code: 'QUARTER_L', kw: ['쿼터(좌)', '쿼터좌', '뒤휀더(좌)', '뒤휀더좌', '리어휀더(좌)', '쿼터패널(좌)', 'quarter_panel_left', 'quarter_panel_l', 'quarter_l', 'p061'], exclude: ['앞', '프론트', 'front', '우', 'right'], x: 18, y: 230, w: 48, h: 60, label: '쿼터', full: '쿼터 패널(좌)' },
    { code: 'QUARTER_R', kw: ['쿼터(우)', '쿼터우', '뒤휀더(우)', '뒤휀더우', '리어휀더(우)', '쿼터패널(우)', 'quarter_panel_right', 'quarter_panel_r', 'quarter_r', 'p062'], exclude: ['앞', '프론트', 'front', '좌', 'left'], x: 154, y: 230, w: 48, h: 60, label: '쿼터', full: '쿼터 패널(우)' },
    { code: 'ROOF', kw: ['루프', '루프패널', 'roof', 'p070'], exclude: [], x: 70, y: 80, w: 80, h: 145, label: '루프', full: '루프 패널' },
    { code: 'TRUNK', kw: ['트렁크리드', '트렁크 리드', '트렁크', 'trunk_lid', 'trunk', 'p040', 'p041'], exclude: ['플로어', '바닥', 'floor'], x: 70, y: 230, w: 80, h: 60, label: 'TR', full: '트렁크리드' }
  ];

  // 주요골격 부위 (엔카 및 국토부 성능점검 전체 골격 부위 포괄)
  const innerParts: DamagePart[] = [
    { code: 'FRONT_PANEL', kw: ['프론트패널', '프론트 패널', '앞패널', 'front_panel'], exclude: ['리어', '뒤', '대쉬', '대시', '플로어', 'floor'], x: 55, y: 16, w: 110, h: 14, label: '프론트패널', full: '프론트 패널' },
    { code: 'RADIATOR_SUPPORT', kw: ['라디에이터', '라디에이터서포트', 'radiator_support', 'radiator'], exclude: [], x: 55, y: 33, w: 110, h: 22, label: 'R.S', full: '라디에이터 서포트' },
    { code: 'SIDE_MEMBER_FRONT_L', kw: ['사이드멤버(좌)', '프론트사이드멤버(좌)', '앞사이드멤버(좌)', 'side_member_front_left', 'side_member_front_l', 'front_side_member_l', 'p101'], exclude: ['리어', '뒤', 'rear', '우', 'right'], x: 18, y: 25, w: 33, h: 50, label: 'F멤', full: '프론트 사이드멤버(좌)' },
    { code: 'SIDE_MEMBER_FRONT_R', kw: ['사이드멤버(우)', '프론트사이드멤버(우)', '앞사이드멤버(우)', 'side_member_front_right', 'side_member_front_r', 'front_side_member_r', 'p102'], exclude: ['리어', '뒤', 'rear', '좌', 'left'], x: 169, y: 25, w: 33, h: 50, label: 'F멤', full: '프론트 사이드멤버(우)' },
    { code: 'FRONT_WHEEL_HOUSE_L', kw: ['휠하우스(좌)', '프론트휠하우스(좌)', 'front_wheel_house_l', 'wheel_house_l', 'p111'], exclude: ['우', 'right'], x: 18, y: 78, w: 33, h: 32, label: 'F하우스', full: '프론트 휠하우스(좌)' },
    { code: 'FRONT_WHEEL_HOUSE_R', kw: ['휠하우스(우)', '프론트휠하우스(우)', 'front_wheel_house_r', 'wheel_house_r', 'p112'], exclude: ['좌', 'left'], x: 169, y: 78, w: 33, h: 32, label: 'F하우스', full: '프론트 휠하우스(우)' },
    { code: 'CROSS_MEMBER', kw: ['크로스멤버', 'cross_member', 'p120'], exclude: [], x: 55, y: 60, w: 110, h: 22, label: '크로스멤버', full: '크로스멤버' },
    { code: 'INSIDE_PANEL_L', kw: ['인사이드(좌)', '인사이드패널(좌)', 'inside_panel_left', 'inside_panel_l', 'p131'], exclude: ['우', 'right'], x: 18, y: 113, w: 33, h: 34, label: 'I패', full: '인사이드 패널(좌)' },
    { code: 'INSIDE_PANEL_R', kw: ['인사이드(우)', '인사이드패널(우)', 'inside_panel_right', 'inside_panel_r', 'p132'], exclude: ['좌', 'left'], x: 169, y: 113, w: 33, h: 34, label: 'I패', full: '인사이드 패널(우)' },
    { code: 'DASH_PANEL', kw: ['대쉬패널', '대시패널', 'dash_panel'], exclude: [], x: 55, y: 85, w: 110, h: 26, label: '대쉬패널', full: '대쉬 패널' },
    { code: 'A_PILLAR_L', kw: ['a필러(좌)', 'a필러좌', 'a_pillar_l'], exclude: ['우', 'right'], x: 18, y: 150, w: 16, h: 24, label: 'A', full: 'A필러(좌)' },
    { code: 'A_PILLAR_R', kw: ['a필러(우)', 'a필러우', 'a_pillar_r'], exclude: ['좌', 'left'], x: 186, y: 150, w: 16, h: 24, label: 'A', full: 'A필러(우)' },
    { code: 'B_PILLAR_L', kw: ['b필러(좌)', 'b필러좌', 'b_pillar_l'], exclude: ['우', 'right'], x: 18, y: 177, w: 16, h: 24, label: 'B', full: 'B필러(좌)' },
    { code: 'B_PILLAR_R', kw: ['b필러(우)', 'b필러우', 'b_pillar_r'], exclude: ['좌', 'left'], x: 186, y: 177, w: 16, h: 24, label: 'B', full: 'B필러(우)' },
    { code: 'C_PILLAR_L', kw: ['c필러(좌)', 'c필러좌', 'c_pillar_l'], exclude: ['우', 'right'], x: 18, y: 204, w: 16, h: 24, label: 'C', full: 'C필러(좌)' },
    { code: 'C_PILLAR_R', kw: ['c필러(우)', 'c필러우', 'c_pillar_r'], exclude: ['좌', 'left'], x: 186, y: 204, w: 16, h: 24, label: 'C', full: 'C필러(우)' },
    { code: 'FLOOR_PANEL', kw: ['플로어패널', '플로어 패널', 'floor_panel'], exclude: ['트렁크', 'trunk'], x: 37, y: 114, w: 146, h: 112, label: '플로어 패널', full: '플로어 패널' },
    { code: 'SIDE_MEMBER_REAR_L', kw: ['리어사이드멤버(좌)', '뒤사이드멤버(좌)', 'side_member_rear_left', 'side_member_rear_l', 'rear_side_member_l', 'p141'], exclude: ['앞', '프론트', 'front', '우', 'right'], x: 18, y: 231, w: 33, h: 58, label: 'R멤', full: '리어 사이드멤버(좌)' },
    { code: 'SIDE_MEMBER_REAR_R', kw: ['리어사이드멤버(우)', '뒤사이드멤버(우)', 'side_member_rear_right', 'side_member_rear_r', 'rear_side_member_r', 'p142'], exclude: ['앞', '프론트', 'front', '좌', 'left'], x: 169, y: 231, w: 33, h: 58, label: 'R멤', full: '리어 사이드멤버(우)' },
    { code: 'TRUNK_FLOOR', kw: ['트렁크플로어', '트렁크 플로어', '트렁크바닥', 'trunk_floor', 'p150'], exclude: ['리드', 'lid'], x: 55, y: 230, w: 110, h: 58, label: '트렁크플로어', full: '트렁크 플로어' },
    { code: 'REAR_PANEL', kw: ['리어패널', '리어 패널', '뒤패널', 'rear_panel', 'p160', 'p181'], exclude: ['프론트', '앞', 'front'], x: 55, y: 292, w: 110, h: 20, label: '리어패널', full: '리어 패널' }
  ];

  const hasReplaces = (selectedEncar?.replaces?.length > 0) || (selectedEncar?.replaceNames?.length > 0);
  const hasRepairs = (selectedEncar?.repairs?.length > 0) || (selectedEncar?.repairNames?.length > 0);

  return (
    <div className="space-y-2 pt-2 border-t border-[#262833]">
      <div className="flex justify-between items-center text-xs sm:text-sm">
        <span className="font-bold text-white">외판 및 주요골격 상태도</span>
        <div className="flex items-center gap-2.5 text-xs">
          <span className="flex items-center gap-1 text-rose-400 font-bold">
            <span className="w-2.5 h-2.5 rounded bg-rose-500 inline-block" /> 교환(X)
          </span>
          <span className="flex items-center gap-1 text-amber-400 font-bold">
            <span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block" /> 판금/용접(W)
          </span>
          <span className="flex items-center gap-1 text-zinc-400 font-bold">
            <span className="w-2.5 h-2.5 rounded bg-[#1e293b] inline-block border border-slate-700" /> 정상
          </span>
        </div>
      </div>

      {/* Dual SVG Container (외판 + 주요골격 아담하고 컴팩트하게 정렬) */}
      <div className="p-2.5 bg-[#0b1120] rounded-xl border border-[#1e293b] flex flex-col gap-2">
        <div className="flex justify-around items-center w-full gap-2">
          {/* Outer Panel SVG */}
          <div className="text-center flex-1">
            <div className="text-[11px] font-bold text-zinc-400 mb-0.5">외판 (1랭크/2랭크)</div>
            <svg viewBox="0 0 220 340" className="w-full max-w-[125px] mx-auto">
              <rect x="15" y="10" width="190" height="320" rx="18" fill="#0f172a" stroke="#334155" strokeWidth="1.2" />
              {outerParts.map((p, i) => {
                const fill = checkStatus(p);
                return (
                  <g key={i}>
                    <title>{p.full}</title>
                    <rect x={p.x} y={p.y} width={p.w} height={p.h} rx="4" fill={fill} stroke="#334155" strokeWidth="1.1" />
                    <text x={p.x + p.w / 2} y={p.y + p.h / 2} textAnchor="middle" dominantBaseline="middle" fontSize={p.w < 15 ? 7.5 : 9.5} fontWeight="bold" fill="#ffffff">
                      {p.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* Inner Structure SVG */}
          <div className="text-center flex-1">
            <div className="text-[11px] font-bold text-zinc-400 mb-0.5">주요골격 (차체구조)</div>
            <svg viewBox="0 0 220 340" className="w-full max-w-[125px] mx-auto">
              <rect x="15" y="10" width="190" height="320" rx="18" fill="#0f172a" stroke="#334155" strokeWidth="1.2" />
              {innerParts.map((p, i) => {
                const fill = checkStatus(p);
                return (
                  <g key={i}>
                    <title>{p.full}</title>
                    <rect x={p.x} y={p.y} width={p.w} height={p.h} rx="4" fill={fill} stroke="#334155" strokeWidth="1.1" />
                    <text x={p.x + p.w / 2} y={p.y + p.h / 2} textAnchor="middle" dominantBaseline="middle" fontSize={p.w < 20 ? 7 : 8.5} fontWeight="bold" fill="#ffffff">
                      {p.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Accident Details Text List */}
        <div className="pt-2 text-xs border-t border-[#1e293b] flex flex-col gap-1 px-1">
          {hasReplaces && (
            <div className="text-rose-400 font-medium flex items-start gap-1">
              <span className="font-bold shrink-0">🔴 교환(X):</span>
              <span>
                {(selectedEncar?.replaceNames?.length > 0
                  ? selectedEncar.replaceNames
                  : selectedEncar.replaces
                ).join(', ')}
              </span>
            </div>
          )}
          {hasRepairs && (
            <div className="text-amber-400 font-medium flex items-start gap-1">
              <span className="font-bold shrink-0">🟡 판금/용접(W):</span>
              <span>
                {(selectedEncar?.repairNames?.length > 0
                  ? selectedEncar.repairNames
                  : selectedEncar.repairs
                ).join(', ')}
              </span>
            </div>
          )}
          {!hasReplaces && !hasRepairs && (
            <div className="text-emerald-400 font-medium flex items-center gap-1">
              <span>🟢 교환/판금 없는 완전무사고 매물입니다.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
