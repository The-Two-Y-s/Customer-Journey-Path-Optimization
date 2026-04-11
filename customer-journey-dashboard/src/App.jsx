import React, { useState, useEffect, useRef, useCallback } from "react";

/* ═══ PALETTE ═════════════════════════════════════════ */
const C = {
  bg: "#05080f", card: "rgba(12,16,30,0.85)",
  bdr: "rgba(255,255,255,0.07)", bdr2: "rgba(255,255,255,0.12)",
  v1: "#7c3aed", v2: "#a78bfa", b1: "#2563eb",
  c1: "#0891b2", c2: "#22d3ee",
  e1: "#059669", e2: "#34d399",
  a1: "#d97706", a2: "#fbbf24",
  r1: "#dc2626", r2: "#fb7185",
  tx: "#f0f4ff", txS: "#c8d0e8", mu: "#8b95b5", dm: "#556078", wh: "#fff",
  gV: "linear-gradient(135deg,#7c3aed,#4f46e5)",
  gC: "linear-gradient(135deg,#0891b2,#06b6d4)",
  gE: "linear-gradient(135deg,#059669,#10b981)",
  gA: "linear-gradient(135deg,#d97706,#f59e0b)",
  gR: "linear-gradient(135deg,#dc2626,#f87171)",
  gH: "linear-gradient(135deg,#7c3aed,#2563eb,#0891b2,#059669)",
};
const F = "'Sora','DM Sans',system-ui,sans-serif";

/* ═══ GRAPH ═══════════════════════════════════════════ */
const NODES = [
  { id: "landing", label: "Landing", x: 55, y: 220 },
  { id: "search", label: "Search", x: 220, y: 75 },
  { id: "browse", label: "Browse", x: 220, y: 365 },
  { id: "prodA", label: "Product A", x: 400, y: 50 },
  { id: "prodB", label: "Product B", x: 400, y: 220 },
  { id: "wish", label: "Wishlist", x: 400, y: 390 },
  { id: "reviews", label: "Reviews", x: 570, y: 95 },
  { id: "cart", label: "Cart", x: 570, y: 300 },
  { id: "checkout", label: "Checkout", x: 740, y: 195 },
  { id: "drop", label: "Drop-off", x: 740, y: 395 },
];
const EDGES = [
  { f: "landing", t: "search", p: .45 }, { f: "landing", t: "browse", p: .30 }, { f: "landing", t: "drop", p: .25 },
  { f: "search", t: "prodA", p: .40 }, { f: "search", t: "prodB", p: .35 }, { f: "search", t: "drop", p: .25 },
  { f: "browse", t: "prodA", p: .50 }, { f: "browse", t: "wish", p: .30 }, { f: "browse", t: "drop", p: .20 },
  { f: "prodA", t: "reviews", p: .55 }, { f: "prodA", t: "cart", p: .30 }, { f: "prodA", t: "drop", p: .15 },
  { f: "prodB", t: "cart", p: .60 }, { f: "prodB", t: "drop", p: .40 },
  { f: "wish", t: "prodB", p: .60 }, { f: "wish", t: "drop", p: .40 },
  { f: "reviews", t: "cart", p: .70 }, { f: "reviews", t: "drop", p: .30 },
  { f: "cart", t: "checkout", p: .75 }, { f: "cart", t: "drop", p: .25 },
];
const NM = Object.fromEntries(NODES.map(n => [n.id, n]));
const NI = { landing: "\u{1F3E0}", search: "\u{1F50D}", browse: "\u{1F4C2}", prodA: "\u{1F4E6}", prodB: "\u{1F4E6}", wish: "\u{1F49C}", reviews: "\u2B50", cart: "\u{1F6D2}", checkout: "\u2705", drop: "\u2716" };
const ep = (e) => {
  const s = NM[e.f], t = NM[e.t], mx = (s.x + t.x) / 2;
  return `M${s.x} ${s.y} C${mx} ${s.y} ${mx} ${t.y} ${t.x} ${t.y}`;
};
const bz = (fx, fy, tx, ty, t) => {
  const mx = (fx + tx) / 2, u = 1 - t;
  return {
    x: u * u * u * fx + 3 * u * u * t * mx + 3 * u * t * t * mx + t * t * t * tx,
    y: u * u * u * fy + 3 * u * u * t * fy + 3 * u * t * t * ty + t * t * t * ty
  };
};

/* ═══ DATA ════════════════════════════════════════════ */
const SD = {
  0.001: { a: "3.3\u00D7", f: "1.6\u00D7", p: "30.6%", e: "53.3%", d: "Conservative \u2014 most paths preserved." },
  0.01: { a: "24.7\u00D7", f: "4.4\u00D7", p: "5.6%", e: "7.1%", d: "Moderate \u2014 good balance." },
  0.05: { a: "123.6\u00D7", f: "5.7\u00D7", p: "4.7%", e: "1.4%", d: "Aggressive \u2014 massive pruning." },
  0.1: { a: "242.6\u00D7", f: "6.4\u00D7", p: "4.4%", e: "0.7%", d: "Very aggressive pruning." },
  0.5: { a: "738\u00D7", f: "7.2\u00D7", p: "4.2%", e: "0.1%", d: "Extreme \u2014 only top edges survive." },
};
const MD = [{ s: "1K", b: 83.8, p: 4.4 }, { s: "5K", b: 342.9, p: 4.5 }, { s: "10K", b: 655, p: 4.5 }];
const AD = [
  { n: "RetailRocket (event)", f: 78, a: 82, sp: "5.8\u00D7" },
  { n: "RetailRocket (item)", f: 1, a: 84, sp: "3.4\u00D7" },
  { n: "RecSys 2015", f: 0, a: 83, sp: "1.8\u00D7" },
];

/* ═══ HOOKS & COMPONENTS ══════════════════════════════ */
function useStagger(n, b = 80) {
  const [v, setV] = useState(Array(n).fill(false));
  useEffect(() => {
    const ts = [];
    for (let i = 0; i < n; i++) ts.push(setTimeout(() => setV(prev => { const c = [...prev]; c[i] = true; return c; }), b * i));
    return () => ts.forEach(clearTimeout);
  }, [n, b]);
  return v;
}

function Glass({ children, style = {}, glow, animate, delay = 0 }) {
  const [show, setShow] = useState(!animate);
  useEffect(() => { if (animate) { const t = setTimeout(() => setShow(true), delay); return () => clearTimeout(t); } }, [animate, delay]);
  return (
    <div style={{
      background: C.card, backdropFilter: "blur(24px)", borderRadius: 20,
      border: `1px solid ${C.bdr}`, position: "relative", overflow: "hidden",
      opacity: show ? 1 : 0, transform: show ? "translateY(0)" : "translateY(16px)",
      transition: "opacity .6s cubic-bezier(.4,0,.2,1),transform .6s cubic-bezier(.4,0,.2,1)", ...style
    }}>
      {glow && <div style={{ position: "absolute", top: -50, right: -50, width: 180, height: 180, background: `radial-gradient(circle,${glow}12,transparent 70%)`, pointerEvents: "none" }} />}
      {children}
    </div>
  );
}

/* ═══ DIJKSTRA ════════════════════════════════════════ */
function solveDijkstra(tau = 0) {
  const dist = {}, prev = {}, steps = [];
  NODES.forEach(n => { dist[n.id] = Infinity; prev[n.id] = null; });
  dist.landing = 0;
  const pq = [{ id: "landing", c: 0 }];
  const T = tau > 0 ? -Math.log(tau) : Infinity;
  while (pq.length) {
    pq.sort((a, b) => a.c - b.c);
    const u = pq.shift();
    if (u.c > dist[u.id]) continue;
    steps.push({ type: "visit", node: u.id, cost: u.c });
    for (const e of EDGES.filter(e => e.f === u.id)) {
      const w = -Math.log(e.p), nc = dist[u.id] + w;
      if (nc > T) { steps.push({ type: "prune", edge: e, cost: nc }); continue; }
      const better = nc < dist[e.t];
      steps.push({ type: "relax", edge: e, cost: nc, better });
      if (better) { dist[e.t] = nc; prev[e.t] = u.id; pq.push({ id: e.t, c: nc }); }
    }
  }
  const path = []; let c = "checkout";
  while (prev[c]) { const e = EDGES.find(x => x.f === prev[c] && x.t === c); if (e) path.unshift(e); c = prev[c]; }
  steps.push({ type: "done", path, found: path.length > 0 && dist.checkout < Infinity, prob: dist.checkout < Infinity ? Math.exp(-dist.checkout) : 0 });
  return steps;
}

/* ═══ PARTICLES ═══════════════════════════════════════ */
function Particles({ edges, pathEdges, W, H }) {
  const ref = useRef(null), ps = useRef([]), raf = useRef(null);
  useEffect(() => {
    const cv = ref.current; if (!cv) return;
    const ctx = cv.getContext("2d"); cv.width = W * 2; cv.height = H * 2; ctx.scale(2, 2); ps.current = [];
    let cartT = 0;
    const showCart = pathEdges.length > 0;
    const pCoords = pathEdges.map(e => ({ fx: NM[e.f].x, fy: NM[e.f].y, tx: NM[e.t].x, ty: NM[e.t].y }));
    function frame() {
      ctx.clearRect(0, 0, W, H);
      if (Math.random() < .35) edges.forEach(e => {
        if (Math.random() > e.p * .45) return;
        const s = NM[e.f], t = NM[e.t], isP = pathEdges.some(pe => pe.f === e.f && pe.t === e.t);
        ps.current.push({ fx: s.x, fy: s.y, tx: t.x, ty: t.y, t: 0, spd: .002 + Math.random() * .004,
          col: isP ? C.e2 : e.t === "checkout" ? C.e1 : e.t === "drop" ? "#283040" : C.c2,
          sz: isP ? 2.5 : 1.4, op: isP ? .8 : .35 });
      });
      ps.current = ps.current.filter(p => p.t < 1);
      ps.current.forEach(p => {
        p.t += p.spd; const { x, y } = bz(p.fx, p.fy, p.tx, p.ty, p.t);
        const a = Math.sin(p.t * Math.PI) * p.op;
        ctx.globalAlpha = a; ctx.fillStyle = p.col;
        ctx.beginPath(); ctx.arc(x, y, p.sz, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = a * .15; ctx.shadowColor = p.col; ctx.shadowBlur = 10;
        ctx.beginPath(); ctx.arc(x, y, p.sz + 4, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0; ctx.globalAlpha = 1;
      });
      if (showCart && pCoords.length > 0) {
        cartT += .003; if (cartT > 1) cartT = 0;
        const tot = pCoords.length, gT = cartT * tot, si = Math.min(Math.floor(gT), tot - 1), lT = gT - si;
        const seg = pCoords[si], { x, y } = bz(seg.fx, seg.fy, seg.tx, seg.ty, lT);
        ctx.globalAlpha = .12; ctx.shadowColor = C.e1; ctx.shadowBlur = 20;
        ctx.beginPath(); ctx.arc(x, y, 10, 0, Math.PI * 2); ctx.fillStyle = C.e1; ctx.fill();
        ctx.shadowBlur = 0; ctx.globalAlpha = .9; ctx.font = "14px sans-serif"; ctx.textAlign = "center";
        ctx.fillText("\u{1F6D2}", x, y + 5); ctx.globalAlpha = 1;
      }
      raf.current = requestAnimationFrame(frame);
    }
    frame(); return () => cancelAnimationFrame(raf.current);
  }, [edges, pathEdges, W, H]);
  return <canvas ref={ref} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} />;
}

/* ═══ JOURNEY GRAPH ═══════════════════════════════════ */
function JourneyGraph({ tau, onTauChange }) {
  const W = 840, H = 470;
  const [hov, setHov] = useState(null);
  const [hovE, setHovE] = useState(-1);
  const [visited, setVisited] = useState(new Set());
  const [relaxing, setRelaxing] = useState(null);
  const [pruned, setPruned] = useState(new Set());
  const [pathE, setPathE] = useState([]);
  const [done, setDone] = useState(false);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(300);
  const [stepLog, setStepLog] = useState([]);
  const [stepIdx, setStepIdx] = useState(-1);
  const tmr = useRef(null);

  const reset = useCallback(() => {
    if (tmr.current) clearInterval(tmr.current);
    setVisited(new Set()); setRelaxing(null); setPruned(new Set());
    setPathE([]); setDone(false); setRunning(false); setStepLog([]); setStepIdx(-1);
  }, []);

  const run = useCallback(() => {
    reset();
    const steps = solveDijkstra(tau);
    setRunning(true); let i = 0;
    tmr.current = setInterval(() => {
      if (i >= steps.length) { clearInterval(tmr.current); setRunning(false); return; }
      const s = steps[i]; setStepIdx(i);
      setStepLog(prev => [...prev.slice(-8), s]);
      if (s.type === "visit") setVisited(p => new Set([...p, s.node]));
      if (s.type === "relax") setRelaxing(s.edge);
      if (s.type === "prune") { setRelaxing(s.edge); setPruned(p => new Set([...p, `${s.edge.f}-${s.edge.t}`])); }
      if (s.type === "done") { setPathE(s.path); setDone(true); setRelaxing(null); }
      i++;
    }, speed);
  }, [tau, speed, reset]);

  useEffect(() => () => { if (tmr.current) clearInterval(tmr.current); }, []);

  const isOnPath = (f, t) => pathE.some(e => e.f === f && e.t === t);
  const isPruned = (f, t) => pruned.has(`${f}-${t}`);

  /* ── FIX: select dropdown style ── */
  const selectStyle = {
    background: "#0d1224", color: C.a2, border: `1px solid ${C.bdr2}`,
    borderRadius: 10, padding: "6px 12px", fontSize: 12, fontWeight: 700, fontFamily: F,
    appearance: "auto", WebkitAppearance: "auto",
  };

  return (
    <div>
      {/* Controls */}
      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
        <button onClick={run} disabled={running} style={{
          padding: "9px 24px", borderRadius: 12, border: "none", fontSize: 12, fontWeight: 700,
          cursor: running ? "default" : "pointer", fontFamily: F,
          background: running ? "rgba(255,255,255,0.05)" : C.gH, color: C.wh,
          boxShadow: running ? "none" : "0 4px 20px rgba(124,58,237,0.3)",
          transition: "all .3s", opacity: running ? .6 : 1
        }}>
          {running ? `Step ${stepIdx + 1}...` : done ? "Run again" : "Run Dijkstra"}
        </button>
        <button onClick={reset} style={{
          padding: "9px 18px", borderRadius: 12, border: `1px solid ${C.bdr2}`,
          background: "rgba(255,255,255,0.03)", color: C.mu, fontSize: 12, fontWeight: 600,
          cursor: "pointer", fontFamily: F
        }}>Reset</button>

        <div style={{ display: "flex", alignItems: "center", gap: 8, marginLeft: "auto" }}>
          <label style={{ fontSize: 11, color: C.dm }}>Threshold</label>
          <select value={tau} onChange={e => onTauChange(+e.target.value)} style={selectStyle}>
            {[0, 0.001, 0.01, 0.05, 0.1, 0.5].map(v => (
              <option key={v} value={v} style={{ background: "#0d1224", color: C.a2 }}>
                {v === 0 ? "\u03C4 = 0 (baseline)" : `\u03C4 = ${v}`}
              </option>
            ))}
          </select>
          <label style={{ fontSize: 11, color: C.dm, marginLeft: 8 }}>Speed</label>
          <input type="range" min={60} max={600} step={20} value={660 - speed}
            onChange={e => setSpeed(660 - +e.target.value)} style={{ width: 70, accentColor: C.c1 }} />
        </div>
      </div>

      {/* Graph */}
      <Glass glow={C.v1} style={{ padding: 0 }}>
        {/* Aurora */}
        <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none" }}>
          <div style={{ position: "absolute", top: "-20%", left: "-8%", width: "45%", height: "55%", background: "radial-gradient(ellipse,rgba(124,58,237,0.07),transparent 70%)", filter: "blur(60px)" }} />
          <div style={{ position: "absolute", bottom: "-15%", right: "-5%", width: "40%", height: "50%", background: "radial-gradient(ellipse,rgba(8,145,178,0.05),transparent 70%)", filter: "blur(60px)" }} />
        </div>

        {/* Grid */}
        <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: .03 }} viewBox={`0 0 ${W} ${H}`}>
          {Array.from({ length: 18 }, (_, i) => <line key={`v${i}`} x1={i * 50} y1={0} x2={i * 50} y2={H} stroke="#fff" strokeWidth={.5} />)}
          {Array.from({ length: 10 }, (_, i) => <line key={`h${i}`} x1={0} y1={i * 50} x2={W} y2={i * 50} stroke="#fff" strokeWidth={.5} />)}
        </svg>

        {/* Stage labels */}
        <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} viewBox={`0 0 ${W} ${H}`}>
          {["Awareness", "Discovery", "Evaluation", "Intent", "Outcome"].map((s, i) => (
            <React.Fragment key={s}>
              <text x={55 + i * 170} y={H - 20} textAnchor="middle" fill={C.dm} fontSize={9} fontFamily={F} letterSpacing=".1em">{s.toUpperCase()}</text>
              <text x={55 + i * 170} y={H - 6} textAnchor="middle" fontSize={12}>{["\u{1F3E0}", "\u{1F50D}", "\u{1F4E6}", "\u2B50", "\u2705"][i]}</text>
            </React.Fragment>
          ))}
        </svg>

        <Particles edges={EDGES.filter(e => !isPruned(e.f, e.t))} pathEdges={pathE} W={W} H={H} />

        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", display: "block", position: "relative", zIndex: 2 }}>
          <defs>
            <filter id="gl"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            <filter id="gl2"><feGaussianBlur stdDeviation="8" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
            <linearGradient id="gpP" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor={C.c1} /><stop offset="100%" stopColor={C.e1} /></linearGradient>
            <linearGradient id="gpV" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor={C.v1} /><stop offset="100%" stopColor={C.b1} /></linearGradient>
            <linearGradient id="gpA" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor={C.a1} /><stop offset="100%" stopColor="#ea580c" /></linearGradient>
            <linearGradient id="gpE" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor={C.e1} /><stop offset="100%" stopColor={C.c1} /></linearGradient>
            <linearGradient id="gpR" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor={C.r1} /><stop offset="100%" stopColor={C.r2} /></linearGradient>
          </defs>

          {/* Edges */}
          {EDGES.map((e, i) => {
            const onP = isOnPath(e.f, e.t), pr = isPruned(e.f, e.t);
            const isRel = relaxing && relaxing.f === e.f && relaxing.t === e.t;
            const isDr = e.t === "drop";
            const isH = hovE === i || (hov && (hov === e.f || hov === e.t));
            let col = isDr ? "#182030" : "url(#gpV)", op = .08, sw = Math.max(e.p * 5, .7);
            if (isH) { op = .5; sw = Math.max(e.p * 7, 1.5); }
            if (onP) { col = "url(#gpP)"; op = 1; sw = 4; }
            if (isRel && !onP) { col = "url(#gpA)"; op = .85; sw = 3; }
            if (pr) { col = "url(#gpR)"; op = .12; sw = 1; }
            return (
              <g key={`e${i}`}>
                {onP && <path d={ep(e)} fill="none" stroke={C.e1} strokeWidth={sw + 14} opacity={.05} filter="url(#gl2)" />}
                <path d={ep(e)} fill="none" stroke={col} strokeWidth={sw} opacity={op}
                  strokeDasharray={pr ? "5 5" : "none"} strokeLinecap="round"
                  style={{ transition: "all .4s ease", cursor: "pointer" }}
                  onMouseEnter={() => setHovE(i)} onMouseLeave={() => setHovE(-1)} />
                {isH && !pr && (
                  <React.Fragment>
                    <rect x={(NM[e.f].x + NM[e.t].x) / 2 - 34} y={(NM[e.f].y + NM[e.t].y) / 2 - 24}
                      width={68} height={34} rx={8} fill="rgba(5,8,15,0.92)" stroke={C.bdr2} />
                    <text x={(NM[e.f].x + NM[e.t].x) / 2} y={(NM[e.f].y + NM[e.t].y) / 2 - 8}
                      textAnchor="middle" fill={C.txS} fontSize={11} fontWeight={700} fontFamily={F}
                      style={{ pointerEvents: "none" }}>{Math.round(e.p * 100)}%</text>
                    <text x={(NM[e.f].x + NM[e.t].x) / 2} y={(NM[e.f].y + NM[e.t].y) / 2 + 7}
                      textAnchor="middle" fill={C.dm} fontSize={8} fontFamily={F}
                      style={{ pointerEvents: "none" }}>w={(-Math.log(e.p)).toFixed(2)}</text>
                  </React.Fragment>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map(n => {
            const isV = visited.has(n.id), onP = pathE.some(e => e.f === n.id || e.t === n.id);
            const isH = hov === n.id, isSrc = n.id === "landing", isTgt = n.id === "checkout";
            const isPr = [...pruned].some(k => k.endsWith(`-${n.id}`)) && !onP;
            const isDr = n.id === "drop";
            let gid = isDr ? "" : isSrc ? "gpA" : isTgt ? "gpE" : "gpV";
            let fOp = .06, sw = 1.5, tc = C.txS;
            if (isV) { fOp = .15; sw = 2; }
            if (onP && done) { gid = isTgt ? "gpE" : "gpP"; fOp = .22; sw = 2.5; tc = C.wh; }
            if (isPr) { fOp = .03; gid = "gpR"; sw = 1; tc = C.dm; }
            if (isH) { fOp += .05; sw += .5; }
            const rx = 36, ry = 24;
            return (
              <g key={n.id} onMouseEnter={() => setHov(n.id)} onMouseLeave={() => setHov(null)} style={{ cursor: "pointer" }}>
                {(isSrc || isTgt) && !done && (
                  <ellipse cx={n.x} cy={n.y} rx={rx + 2} ry={ry + 2} fill="none" stroke={isTgt ? C.e1 : C.a1} strokeWidth={1} opacity={.4}>
                    <animate attributeName="rx" values={`${rx};${rx + 14};${rx}`} dur="2.5s" repeatCount="indefinite" />
                    <animate attributeName="ry" values={`${ry};${ry + 10};${ry}`} dur="2.5s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values=".4;0;.4" dur="2.5s" repeatCount="indefinite" />
                  </ellipse>
                )}
                {onP && done && (
                  <ellipse cx={n.x} cy={n.y} rx={rx + 10} ry={ry + 10} fill={isTgt ? C.e1 : C.c1} opacity={.08} filter="url(#gl)">
                    <animate attributeName="opacity" values=".08;.15;.08" dur="3s" repeatCount="indefinite" />
                  </ellipse>
                )}
                <ellipse cx={n.x} cy={n.y} rx={rx} ry={ry} fill={C.bg} stroke={gid ? `url(#${gid})` : C.dm} strokeWidth={sw} style={{ transition: "all .35s ease" }} />
                <ellipse cx={n.x} cy={n.y} rx={rx - 2} ry={ry - 2} fill={gid ? `url(#${gid})` : "#374151"} opacity={fOp} style={{ transition: "opacity .35s" }} />
                <text x={n.x} y={n.y - 6} textAnchor="middle" fontSize={12} style={{ pointerEvents: "none" }}>{NI[n.id]}</text>
                <text x={n.x} y={n.y + 10} textAnchor="middle" dominantBaseline="central" fill={tc} fontSize={n.label.length > 8 ? 9 : 10}
                  fontWeight={onP ? 700 : 500} fontFamily={F} style={{ pointerEvents: "none", transition: "fill .3s" }}>{n.label}</text>
                {isV && (
                  <g transform={`translate(${n.x + rx - 6},${n.y - ry + 2})`}>
                    <circle r={6} fill={onP && done ? C.e1 : "rgba(5,8,15,0.9)"} stroke={onP && done ? C.e2 : C.v1} strokeWidth={1} />
                    <text textAnchor="middle" dy="3" fill={onP && done ? C.bg : C.c2} fontSize={6} fontWeight={800} fontFamily={F}>{onP && done ? "\u2713" : "\u2022"}</text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>

        {/* Live log - bottom left, inside graph but small */}
        {running && stepLog.length > 0 && (
          <div style={{ position: "absolute", bottom: 14, left: 14, background: "rgba(5,8,15,0.9)", borderRadius: 14, padding: "10px 14px", backdropFilter: "blur(12px)", maxWidth: 300, border: `1px solid ${C.bdr}`, maxHeight: 120, overflow: "hidden" }}>
            <div style={{ fontSize: 9, color: C.dm, marginBottom: 4, textTransform: "uppercase", letterSpacing: ".1em" }}>Execution log</div>
            {stepLog.slice(-5).map((s, i) => (
              <div key={i} style={{ fontSize: 10, fontFamily: "'JetBrains Mono',monospace", marginBottom: 1, opacity: .45 + i * .11,
                color: s.type === "visit" ? C.c2 : s.type === "relax" ? (s.better ? C.e2 : C.dm) : s.type === "prune" ? C.r2 : C.a2 }}>
                {s.type === "visit" && `\u25B8 Visit ${s.node} (cost=${s.cost.toFixed(2)})`}
                {s.type === "relax" && `  ${s.better ? "\u2713" : "\u00B7"} Relax ${s.edge.f}\u2192${s.edge.t} (${s.cost.toFixed(2)})`}
                {s.type === "prune" && `  \u2715 Prune ${s.edge.f}\u2192${s.edge.t} (${s.cost.toFixed(2)} > ${(-Math.log(tau)).toFixed(2)})`}
              </div>
            ))}
          </div>
        )}
      </Glass>

      {/* FIX: Result panel BELOW graph, not overlapping */}
      {done && (
        <Glass style={{ padding: "16px 24px", marginTop: 12 }} glow={pathE.length ? C.e1 : C.r1}>
          <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <div style={{ fontSize: 15, fontWeight: 700, background: pathE.length ? C.gE : C.gR, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              {pathE.length ? "Optimal path found" : "No path found"}
            </div>
            {pathE.length > 0 && (
              <React.Fragment>
                <div style={{ fontSize: 12, color: C.mu, lineHeight: 1.6 }}>
                  {["landing", ...pathE.map(e => e.t)].map((id, i, a) => (
                    <span key={id}>
                      <span style={{ fontSize: 14 }}>{NI[id]}</span>
                      <span style={{ color: id === "checkout" ? C.e2 : C.c2, fontWeight: 600, margin: "0 3px" }}>{NM[id].label}</span>
                      {i < a.length - 1 && <span style={{ color: C.dm, margin: "0 2px" }}>{"\u2192"}</span>}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: C.dm }}>P = {pathE.reduce((acc, e) => acc * e.p, 1).toExponential(3)} · Cost = {pathE.reduce((acc, e) => acc + (-Math.log(e.p)), 0).toFixed(2)}</div>
                <div style={{ fontSize: 13, fontWeight: 700, background: C.gE, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Gap: 0.00%</div>
              </React.Fragment>
            )}
            {!pathE.length && <div style={{ fontSize: 12, color: C.dm }}>{"\u03C4"} = {tau} pruned the optimal path entirely.</div>}
          </div>
        </Glass>
      )}

      {/* Legend */}
      <div style={{ display: "flex", gap: 16, marginTop: 12, flexWrap: "wrap", justifyContent: "center" }}>
        {[{ c: C.v1, l: "Explored" }, { c: C.e1, l: "Optimal path" }, { c: C.a1, l: "Relaxing" }, { c: C.r1, l: "Pruned (\u03C4)" }, { c: "#475569", l: "Drop-off" }].map(x => (
          <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10, color: C.mu }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: x.c, boxShadow: `0 0 8px ${x.c}40` }} />{x.l}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ═══ TAU EXPLORER ════════════════════════════════════ */
function TauExplorer() {
  const [tau, setTau] = useState(0.01);
  const ts = [.001, .01, .05, .1, .5];
  const cl = ts.reduce((a, b) => Math.abs(b - tau) < Math.abs(a - tau) ? b : a);
  const d = SD[cl];
  const vis = useStagger(4, 120);
  return (
    <Glass style={{ padding: "28px 32px" }} glow={C.v1} animate delay={0}>
      <div style={{ fontSize: 17, fontWeight: 700, color: C.tx, marginBottom: 4 }}>Explore the {"\u03C4"} trade-off</div>
      <div style={{ fontSize: 12, color: C.dm, marginBottom: 20 }}>Data from 2,160 synthetic experiment runs</div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
        <span style={{ fontSize: 13, color: C.mu, fontWeight: 600 }}>{"\u03C4"}</span>
        <input type="range" min={-3} max={-0.3} step={.01} value={Math.log10(tau)}
          onChange={e => setTau(Math.pow(10, +e.target.value))} style={{ flex: 1, accentColor: C.v1 }} />
        <span style={{ fontSize: 18, fontWeight: 800, minWidth: 52, textAlign: "right", fontVariantNumeric: "tabular-nums",
          background: C.gA, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          {tau < .01 ? tau.toFixed(3) : tau < .1 ? tau.toFixed(2) : tau.toFixed(1)}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
        {[{ l: "All-run speedup", v: d.a, g: C.gA }, { l: "Found-only", v: d.f, g: C.gC },
          { l: "Path-found rate", v: d.p, g: C.gE }, { l: "Edges examined", v: d.e, g: C.gV }].map((m, i) => (
          <div key={i} style={{ background: "rgba(255,255,255,0.025)", borderRadius: 14, padding: "16px 14px", textAlign: "center",
            border: `1px solid ${C.bdr}`, opacity: vis[i] ? 1 : 0, transform: vis[i] ? "scale(1)" : "scale(0.9)",
            transition: "all .5s cubic-bezier(.4,0,.2,1)" }}>
            <div style={{ fontSize: 9, color: C.dm, textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 6 }}>{m.l}</div>
            <div style={{ fontSize: 22, fontWeight: 800, background: m.g, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{m.v}</div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 14, padding: "12px 16px", background: "rgba(124,58,237,0.06)", border: "1px solid rgba(124,58,237,0.1)", borderRadius: 12, fontSize: 12, color: C.mu, lineHeight: 1.7 }}>
        {d.d} <span style={{ color: C.e2, fontWeight: 600 }}>All found paths: 0.00% optimality gap.</span>
      </div>
    </Glass>
  );
}

/* ═══ RESULTS ═════════════════════════════════════════ */
function SpeedupBars() {
  const [vis, setVis] = useState(false);
  useEffect(() => { const t = setTimeout(() => setVis(true), 300); return () => clearTimeout(t); }, []);
  const data = [{ tau: "0.001", all: 3.3, found: 1.6 }, { tau: "0.01", all: 24.7, found: 4.4 }, { tau: "0.05", all: 123.6, found: 5.7 }, { tau: "0.1", all: 242.6, found: 6.4 }, { tau: "0.5", all: 738, found: 7.2 }];
  return (
    <Glass style={{ padding: "28px 32px" }} glow={C.a1} animate delay={0}>
      <div style={{ fontSize: 17, fontWeight: 700, color: C.tx, marginBottom: 4 }}>Two speedup regimes</div>
      <div style={{ fontSize: 12, color: C.dm, marginBottom: 8 }}>All runs include fast failures. Found-only is the honest comparison.</div>
      <div style={{ display: "flex", gap: 20, marginBottom: 20 }}>
        {[{ g: C.gA, l: "All runs" }, { g: C.gC, l: "Found only" }].map((x, i) => (
          <span key={i} style={{ fontSize: 11, display: "flex", alignItems: "center", gap: 6, color: C.mu }}>
            <span style={{ width: 16, height: 6, borderRadius: 3, background: x.g }} />{x.l}</span>
        ))}
      </div>
      {data.map((d, i) => (
        <div key={i} style={{ marginBottom: 14, display: "grid", gridTemplateColumns: "60px 1fr 78px", gap: 12, alignItems: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, textAlign: "right", background: C.gV, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{"\u03C4"}={d.tau}</span>
          <div>
            <div style={{ height: 14, background: "rgba(255,255,255,0.03)", borderRadius: 7, overflow: "hidden", marginBottom: 4 }}>
              <div style={{ height: "100%", borderRadius: 7, width: vis ? `${d.all / 738 * 100}%` : "0%", background: C.gA, transition: `width 1.2s cubic-bezier(.4,0,.2,1) ${i * .1}s` }} />
            </div>
            <div style={{ height: 8, background: "rgba(255,255,255,0.03)", borderRadius: 4, overflow: "hidden" }}>
              <div style={{ height: "100%", borderRadius: 4, width: vis ? `${d.found / 7.2 * 100}%` : "0%", background: C.gC, transition: `width 1.2s cubic-bezier(.4,0,.2,1) ${i * .1 + .3}s` }} />
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 13, fontWeight: 700, background: C.gA, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{d.all}{"\u00D7"}</div>
            <div style={{ fontSize: 10, background: C.gC, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{d.found}{"\u00D7"} found</div>
          </div>
        </div>
      ))}
    </Glass>
  );
}

function Results() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <SpeedupBars />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        {/* Memory */}
        <Glass style={{ padding: "28px 32px" }} glow={C.a1} animate delay={100}>
          <div style={{ fontSize: 17, fontWeight: 700, color: C.tx, marginBottom: 4 }}>Memory: O(V) vs O(1)</div>
          <div style={{ fontSize: 12, color: C.dm, marginBottom: 18 }}>Peak memory (KB) {"\u2014"} pruned {"\u03C4"}=0.01</div>
          {MD.map((r, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: C.mu, marginBottom: 5, fontWeight: 500 }}>|V| = {r.s}</div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <div style={{ flex: 1, height: 16, background: "rgba(255,255,255,0.03)", borderRadius: 8, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${r.b / 700 * 100}%`, background: C.gA, borderRadius: 8 }} />
                </div>
                <span style={{ fontSize: 11, color: C.a2, minWidth: 56, textAlign: "right", fontWeight: 600 }}>{r.b} KB</span>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                <div style={{ flex: 1, height: 10, background: "rgba(255,255,255,0.03)", borderRadius: 5, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${Math.max(r.p / 700 * 100, .8)}%`, background: C.gC, borderRadius: 5 }} />
                </div>
                <span style={{ fontSize: 11, color: C.c2, minWidth: 56, textAlign: "right", fontWeight: 600 }}>{r.p} KB</span>
              </div>
            </div>
          ))}
        </Glass>
        {/* Adaptive */}
        <Glass style={{ padding: "28px 32px" }} glow={C.e1} animate delay={200}>
          <div style={{ fontSize: 17, fontWeight: 700, color: C.tx, marginBottom: 4 }}>Adaptive {"\u03C4"} breakthrough</div>
          <div style={{ fontSize: 12, color: C.dm, marginBottom: 18 }}>Path-found rate: fixed vs adaptive</div>
          {AD.map((d, i) => (
            <div key={i} style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 12, color: C.txS, fontWeight: 500 }}>{d.n}</span>
                <span style={{ fontSize: 10, color: C.dm }}>{d.sp}</span>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                {[{ v: d.f, g: C.gR, l: "Fixed" }, { v: d.a, g: C.gE, l: "Adaptive" }].map((b, j) => (
                  <div key={j} style={{ flex: 1 }}>
                    <div style={{ fontSize: 9, color: C.dm, marginBottom: 3, fontWeight: 500 }}>{b.l}</div>
                    <div style={{ height: 22, background: "rgba(255,255,255,0.03)", borderRadius: 11, overflow: "hidden", position: "relative" }}>
                      <div style={{ height: "100%", width: `${b.v}%`, background: b.g, borderRadius: 11, transition: "width 1.2s", minWidth: b.v > 0 ? 4 : 0 }} />
                      <span style={{ position: "absolute", left: 10, top: 4, fontSize: 11, color: "#fff", fontWeight: 700 }}>{b.v}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div style={{ padding: "12px 16px", background: "rgba(5,150,105,0.06)", border: "1px solid rgba(5,150,105,0.12)", borderRadius: 12, fontSize: 12, color: C.mu, lineHeight: 1.6 }}>
            0{"\u2192"}83% path-found with <span style={{ color: C.e2, fontWeight: 700 }}>0.00% gap</span> across all 449 adaptive found paths.
          </div>
        </Glass>
      </div>
      {/* Hypothesis */}
      <Glass style={{ padding: "28px 32px" }} glow={C.v1} animate delay={300}>
        <div style={{ fontSize: 17, fontWeight: 700, color: C.tx, marginBottom: 16 }}>Hypothesis: supported</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
          {[{ s: "179/180", d: "significant speedup (Wilcoxon p < 0.05)", g: C.gV },
            { s: "0/706", d: "paths with non-zero gap", g: C.gE },
            { s: "18,882\u00D7", d: "max speedup (incl. fast failures)", g: C.gA },
            { s: "44", d: "tests across 13 classes", g: C.gC }].map((f, i) => (
            <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "16px 12px",
              background: "rgba(255,255,255,0.02)", borderRadius: 16, textAlign: "center", border: `1px solid ${C.bdr}`,
              transition: "transform .2s", cursor: "default" }}
              onMouseEnter={e => e.currentTarget.style.transform = "translateY(-2px)"}
              onMouseLeave={e => e.currentTarget.style.transform = ""}>
              <div style={{ fontSize: 24, fontWeight: 800, fontVariantNumeric: "tabular-nums", background: f.g, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{f.s}</div>
              <div style={{ fontSize: 10, color: C.dm, marginTop: 6, lineHeight: 1.4 }}>{f.d}</div>
            </div>
          ))}
        </div>
      </Glass>
    </div>
  );
}

/* ═══ ANIMATED NUMBER ═════════════════════════════════ */
function AN({ value, suffix = "", gradient, size = 28 }) {
  const [d, setD] = useState(0);
  const r = useRef(null);
  useEffect(() => {
    const n = parseFloat(String(value).replace(/[^0-9.]/g, ""));
    if (isNaN(n)) { setD(value); return; }
    const s = performance.now();
    function t(now) {
      const p = Math.min((now - s) / 1200, 1);
      const e = 1 - Math.pow(1 - p, 3);
      setD(n >= 100 ? Math.round(n * e).toLocaleString() : +(n * e).toFixed(n % 1 === 0 ? 0 : 1));
      if (p < 1) r.current = requestAnimationFrame(t);
    }
    r.current = requestAnimationFrame(t);
    return () => cancelAnimationFrame(r.current);
  }, [value]);
  return <span style={{ fontSize: size, fontWeight: 800, fontVariantNumeric: "tabular-nums", letterSpacing: "-.02em", background: gradient, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{d}{suffix}</span>;
}

/* ═══ APP ═════════════════════════════════════════════ */
export default function App() {
  const [tab, setTab] = useState("journey");
  const [tau, setTau] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const kpiVis = useStagger(4, 100);
  useEffect(() => { setTimeout(() => setLoaded(true), 60); }, []);

  const tabs = [
    { id: "journey", label: "Live pathfinding", icon: "\u25B7" },
    { id: "explore", label: "\u03C4 Explorer", icon: "\u2699" },
    { id: "analysis", label: "Full results", icon: "\u2261" },
  ];

  return (
    <div style={{ fontFamily: F, background: C.bg, color: C.tx, minHeight: "100vh", padding: "24px 16px 60px", opacity: loaded ? 1 : 0, transition: "opacity .6s ease", position: "relative" }}>
      <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      <style>{`*{box-sizing:border-box}input[type=range]{height:5px}
        select{color-scheme:dark}
        select:focus{outline:1px solid ${C.v1}}
        ::selection{background:rgba(124,58,237,0.3)}
        option{background:#0d1224;color:#c8d0e8}`}</style>

      {/* Background aurora */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden" }}>
        <div style={{ position: "absolute", top: "-20%", left: "-15%", width: "55%", height: "55%", background: "radial-gradient(ellipse,rgba(124,58,237,0.05),transparent 70%)", filter: "blur(80px)" }} />
        <div style={{ position: "absolute", bottom: "-15%", right: "-10%", width: "50%", height: "50%", background: "radial-gradient(ellipse,rgba(8,145,178,0.04),transparent 70%)", filter: "blur(80px)" }} />
      </div>

      <div style={{ maxWidth: 940, margin: "0 auto", position: "relative", zIndex: 1 }}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 10, letterSpacing: ".2em", color: C.dm, textTransform: "uppercase", marginBottom: 8 }}>AT70.02 Algorithm Design & Analysis</div>
          <h1 style={{ fontSize: 30, fontWeight: 800, margin: "0 0 8px", letterSpacing: "-.02em", background: C.gH, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Customer Journey Path Optimization</h1>
          <div style={{ fontSize: 14, color: C.mu }}>The Two Y's {"\u2014"} Yolanda Lim & Yosakorn Sirisoot {"\u2014"} AIT 2025</div>
        </div>

        {/* KPIs */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,minmax(0,1fr))", gap: 12, marginBottom: 24 }}>
          {[
            { l: "Experiments", v: "3000", s: "", g: C.gV, d: "2,160 synthetic + 840 real", gl: C.v1 },
            { l: "Optimality gap", v: "0.00", s: "%", g: C.gE, d: "All 706 found paths", gl: C.e1 },
            { l: "Max speedup", v: "18882", s: "\u00D7", g: C.gA, d: "RetailRocket item-level", gl: C.a1 },
            { l: "Adaptive \u03C4", v: "82", s: "\u201384%", g: C.gC, d: "path-found vs 0\u20131% fixed \u03C4", gl: C.c1 },
          ].map((k, i) => (
            <div key={i} style={{
              background: C.card, backdropFilter: "blur(20px)", borderRadius: 18,
              border: `1px solid ${C.bdr}`, padding: "20px 22px", position: "relative", overflow: "hidden",
              opacity: kpiVis[i] ? 1 : 0, transform: kpiVis[i] ? "translateY(0)" : "translateY(20px)",
              transition: "opacity .6s cubic-bezier(.4,0,.2,1),transform .6s cubic-bezier(.4,0,.2,1)"
            }}>
              <div style={{ position: "absolute", top: -40, right: -40, width: 160, height: 160, background: `radial-gradient(circle,${k.gl}10,transparent 70%)`, pointerEvents: "none" }} />
              <div style={{ fontSize: 10, color: C.dm, textTransform: "uppercase", letterSpacing: ".1em", marginBottom: 8 }}>{k.l}</div>
              <AN value={k.v} suffix={k.s} gradient={k.g} />
              <div style={{ fontSize: 11, color: C.dm, marginTop: 6 }}>{k.d}</div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 3, marginBottom: 20, background: "rgba(12,16,30,0.7)", backdropFilter: "blur(16px)", borderRadius: 16, padding: 4, border: `1px solid ${C.bdr}` }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              flex: 1, padding: "12px 16px", borderRadius: 12, border: "none",
              background: tab === t.id ? "rgba(124,58,237,0.1)" : "transparent",
              color: tab === t.id ? C.tx : C.dm, fontSize: 13, fontWeight: 600,
              cursor: "pointer", fontFamily: F, transition: "all .25s",
              boxShadow: tab === t.id ? "inset 0 0 0 1px rgba(124,58,237,0.2)" : "none"
            }}>
              <span style={{ marginRight: 6, opacity: .6 }}>{t.icon}</span>{t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        {tab === "journey" && (
          <div>
            <div style={{ fontSize: 13, color: C.mu, marginBottom: 16, lineHeight: 1.7 }}>
              Watch <span style={{ background: C.gC, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", fontWeight: 700 }}>Probability-Pruned Dijkstra</span> explore a customer journey graph.
              Set <span style={{ background: C.gA, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent", fontWeight: 700 }}>{"\u03C4"} {">"} 0</span> to see pruning {"\u2014"} the {"\u{1F6D2}"} follows the optimal path when found.
            </div>
            <JourneyGraph tau={tau} onTauChange={setTau} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginTop: 16 }}>
              {[
                { t: "Algorithm", v: "Prob-Pruned Dijkstra", d: "w = -log(p)\nMin weight \u2261 max probability", g: C.gV },
                { t: "Guarantee", v: "0% optimality gap", d: "Found paths always match\nbaseline exactly (0/706)", g: C.gE },
                { t: "Trade-off", v: "Reachability only", d: "Aggressive \u03C4 \u2192 fewer paths\nbut those found are optimal", g: C.gA },
              ].map((m, i) => (
                <Glass key={i} style={{ padding: "16px 20px" }} animate delay={i * 80}>
                  <div style={{ fontSize: 9, color: C.dm, textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 4 }}>{m.t}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, background: m.g, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>{m.v}</div>
                  <div style={{ fontSize: 11, color: C.dm, marginTop: 6, lineHeight: 1.5, whiteSpace: "pre-line" }}>{m.d}</div>
                </Glass>
              ))}
            </div>
          </div>
        )}
        {tab === "explore" && <TauExplorer />}
        {tab === "analysis" && <Results />}

        <div style={{ textAlign: "center", marginTop: 40, fontSize: 11, color: C.dm }}>
          The Two Y's {"\u00B7"} Aye Khin Khin Hpone (Yolanda) {"\u00B7"} Yosakorn Sirisoot {"\u00B7"} Asian Institute of Technology 2025
        </div>
      </div>
    </div>
  );
}
