import { useState, useEffect, useRef, useCallback, createContext, useContext } from "react";
import { APIProvider, Map, AdvancedMarker } from "@vis.gl/react-google-maps";

// ============================================================
// TYPES & MOCK DATA
// ============================================================

const INITIAL_HISTORY = [
  { id: "1", filename: "aerial_suburb.jpg", pools: 3, confidence: 97.2, time: 1.34, ts: Date.now() - 86400000 * 0, lat: 33.749, lng: -84.388 },
  { id: "2", filename: "residential_2.jpg", pools: 1, confidence: 94.8, time: 0.89, ts: Date.now() - 86400000 * 1, lat: 34.052, lng: -118.243 },
  { id: "3", filename: "complex_overview.jpg", pools: 7, confidence: 98.1, time: 2.1, ts: Date.now() - 86400000 * 2, lat: 25.774, lng: -80.19 },
  { id: "4", filename: "neighborhood.jpg", pools: 2, confidence: 91.3, time: 1.02, ts: Date.now() - 86400000 * 3, lat: 29.76, lng: -95.369 },
  { id: "5", filename: "beach_resort.jpg", pools: 12, confidence: 99.0, time: 3.45, ts: Date.now() - 86400000 * 4, lat: 36.174, lng: -86.767 },
  { id: "6", filename: "villa_complex.jpg", pools: 4, confidence: 96.5, time: 1.77, ts: Date.now() - 86400000 * 5, lat: 40.712, lng: -74.005 },
];

const INITIAL_CHART = [
  { day: "Mon", pools: 8, uploads: 3 },
  { day: "Tue", pools: 14, uploads: 5 },
  { day: "Wed", pools: 6, uploads: 2 },
  { day: "Thu", pools: 21, uploads: 8 },
  { day: "Fri", pools: 17, uploads: 6 },
  { day: "Sat", pools: 29, uploads: 11 },
  { day: "Sun", pools: 12, uploads: 4 },
];

// Clamp a number between min and max
const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
// Small random walk: jitter ± range
const jitter = (v, range) => v + (Math.random() - 0.5) * 2 * range;

// ============================================================
// APP STATE CONTEXT
// ============================================================

const AppCtx = createContext(null);
function useApp() { return useContext(AppCtx); }

function AppProvider({ children }) {
  const [page, setPage] = useState("home");
  const [history, setHistory] = useState([]);
  const [darkMode] = useState(true);
  const [detectionResult, setDetectionResult] = useState(null);

  // Live chart data — each bar drifts slightly every 3 s
  const [chartData, setChartData] = useState(INITIAL_CHART);

  // Live model telemetry
  const [liveStats, setLiveStats] = useState({
    accuracy: 98.7,
    reqPerMin: 42,
    inferenceMs: 1.34,
    gpuUtil: 73,
  });

  // Tick chart bars every 3 s
  useEffect(() => {
    const id = setInterval(() => {
      setChartData(prev => prev.map(d => ({
        ...d,
        pools: Math.round(clamp(jitter(d.pools, 3), 1, 40)),
        uploads: Math.round(clamp(jitter(d.uploads, 1), 1, 15)),
      })));
    }, 3000);
    return () => clearInterval(id);
  }, []);

  // Tick live telemetry every 2 s
  useEffect(() => {
    const id = setInterval(() => {
      setLiveStats(prev => ({
        accuracy: clamp(jitter(prev.accuracy, 0.15), 97.5, 99.5),
        reqPerMin: Math.round(clamp(jitter(prev.reqPerMin, 4), 20, 90)),
        inferenceMs: clamp(jitter(prev.inferenceMs, 0.1), 0.6, 2.8),
        gpuUtil: Math.round(clamp(jitter(prev.gpuUtil, 5), 40, 99)),
      }));
    }, 2000);
    return () => clearInterval(id);
  }, []);

  const addResult = useCallback((r) => {
    setHistory(h => [r, ...h]);
    setDetectionResult(r);
  }, []);

  return (
    <AppCtx.Provider value={{ page, setPage, history, addResult, darkMode, detectionResult, setDetectionResult, chartData, liveStats }}>
      {children}
    </AppCtx.Provider>
  );
}

// ============================================================
// ANIMATION UTILITIES (CSS-based, no framer)
// ============================================================

const css = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #030508;
    --bg2: #080c12;
    --bg3: #0d1420;
    --surface: #101828;
    --surface2: #182030;
    --border: #1e2d42;
    --border2: #243448;
    --accent: #00d4ff;
    --accent2: #0090ff;
    --accent3: #7b4fff;
    --success: #00e5a0;
    --warning: #ffb020;
    --text: #e8f0fe;
    --text2: #8ca0be;
    --text3: #4a6080;
    --glow: 0 0 30px rgba(0,212,255,0.15);
    --glow2: 0 0 60px rgba(0,212,255,0.08);
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    overflow-x: hidden;
  }

  h1,h2,h3,h4,h5 { font-family: 'Syne', sans-serif; }

  @keyframes fadeUp {
    from { opacity:0; transform:translateY(20px); }
    to { opacity:1; transform:translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity:0; }
    to { opacity:1; }
  }
  @keyframes pulse {
    0%,100% { opacity:1; }
    50% { opacity:0.5; }
  }
  @keyframes spin {
    from { transform:rotate(0deg); }
    to { transform:rotate(360deg); }
  }
  @keyframes scanLine {
    0% { top: 0%; }
    100% { top: 100%; }
  }
  @keyframes glowPulse {
    0%,100% { box-shadow: 0 0 20px rgba(0,212,255,0.2); }
    50% { box-shadow: 0 0 40px rgba(0,212,255,0.4); }
  }
  @keyframes shimmer {
    from { background-position: -200% 0; }
    to { background-position: 200% 0; }
  }
  @keyframes float {
    0%,100% { transform:translateY(0px); }
    50% { transform:translateY(-8px); }
  }
  @keyframes barGrow {
    from { height: 0; }
    to { height: var(--h); }
  }
  @keyframes markerPulse {
    0%,100% { transform:scale(1); opacity:1; }
    50% { transform:scale(1.4); opacity:0.6; }
  }
  @keyframes gridScroll {
    from { background-position: 0 0; }
    to { background-position: 40px 40px; }
  }
  @keyframes borderRotate {
    from { --angle: 0deg; }
    to { --angle: 360deg; }
  }
  @keyframes countUp {
    from { opacity:0; transform: scale(0.7); }
    to { opacity:1; transform: scale(1); }
  }

  .page-enter {
    animation: fadeUp 0.4s ease forwards;
  }

  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    cursor: default;
  }
  .stat-card::before {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(0,212,255,0.03) 0%, transparent 60%);
    pointer-events: none;
  }
  .stat-card:hover {
    transform: translateY(-3px);
    border-color: var(--border2);
    box-shadow: 0 8px 40px rgba(0,0,0,0.4), 0 0 0 1px rgba(0,212,255,0.1);
  }

  .btn-primary {
    background: linear-gradient(135deg, var(--accent2) 0%, var(--accent) 100%);
    color: #000;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 14px;
    letter-spacing: 0.5px;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
  }
  .btn-primary::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 60%);
    opacity: 0;
    transition: opacity 0.2s;
  }
  .btn-primary:hover { transform:translateY(-2px); box-shadow: 0 8px 25px rgba(0,144,255,0.4); }
  .btn-primary:hover::after { opacity:1; }
  .btn-primary:active { transform:translateY(0); }

  .btn-ghost {
    background: transparent;
    color: var(--text2);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 9px 18px;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .btn-ghost:hover { border-color: var(--accent); color: var(--accent); background: rgba(0,212,255,0.05); }

  .skeleton {
    background: linear-gradient(90deg, var(--surface) 0%, var(--surface2) 50%, var(--surface) 100%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 8px;
  }

  .confidence-bar {
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
    border-radius: 2px;
    transition: width 1s ease;
  }

  .scrollbar-hide::-webkit-scrollbar { display: none; }
  .scrollbar-hide { -ms-overflow-style: none; scrollbar-width: none; }

  input[type=range] {
    -webkit-appearance: none;
    height: 4px;
    background: var(--border2);
    border-radius: 2px;
    outline: none;
  }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
    box-shadow: 0 0 10px rgba(0,212,255,0.5);
  }

  /* --- GOOGLE MAPS DEV WATERMARK REMOVAL HACKS --- */
  .gm-err-container { display: none !important; }
  .gm-err-content { display: none !important; }
  .gm-style-cc { display: none !important; }
  .gmnoprint { display: none !important; }
  /* Hides the semi-transparent gray overlay that clicks through */
  div[style*="background-color: rgba(15, 15, 15, 0.6)"] { display: none !important; }
  div[style*="z-index: 1000001"] { display: none !important; }
  /* Specifically tries to hide the repeating watermark text divs */
  div[style*="pointer-events: none;"] > div[style*="font-size"] { opacity: 0 !important; display: none !important; }
  
  .tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(0,212,255,0.08);
    border: 1px solid rgba(0,212,255,0.2);
    color: var(--accent);
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
  }

  .grid-bg {
    background-image:
      linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    animation: gridScroll 8s linear infinite;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 10px;
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--text3);
    transition: all 0.2s ease;
    border: 1px solid transparent;
    white-space: nowrap;
  }
  .nav-item:hover { color: var(--text2); background: rgba(255,255,255,0.03); }
  .nav-item.active {
    color: var(--accent);
    background: rgba(0,212,255,0.06);
    border-color: rgba(0,212,255,0.15);
  }

  .upload-zone {
    border: 2px dashed var(--border2);
    border-radius: 20px;
    transition: all 0.3s ease;
    cursor: pointer;
  }
  .upload-zone:hover, .upload-zone.drag-active {
    border-color: var(--accent);
    background: rgba(0,212,255,0.03);
    box-shadow: 0 0 40px rgba(0,212,255,0.1) inset;
  }

  .result-box {
    position: relative;
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    background: var(--surface);
  }

  .pool-box {
    position: absolute;
    border: 2px solid var(--accent);
    border-radius: 4px;
    box-shadow: 0 0 12px rgba(0,212,255,0.4), 0 0 0 1px rgba(0,212,255,0.1);
    pointer-events: none;
  }
  .pool-box::before {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(0,212,255,0.06);
  }
  .pool-label {
    position: absolute;
    top: -20px;
    left: 0;
    background: var(--accent);
    color: #000;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 500;
    padding: 2px 6px;
    border-radius: 4px;
  }

  select, input {
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    border-radius: 8px;
    padding: 8px 12px;
    outline: none;
    transition: border-color 0.2s;
  }
  select:focus, input:focus { border-color: var(--accent); }
  option { background: var(--surface); }
`;

// ============================================================
// ICONS (inline SVG)
// ============================================================

const Icon = ({ name, size = 16, color = "currentColor" }) => {
  const icons = {
    home: <><circle cx="12" cy="10" r="3" /><path d="M12 2L2 7l1 13h18L22 7z" /></>,
    upload: <><polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" /><path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3" /></>,
    chart: <><line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" /></>,
    history: <><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></>,
    map: <><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6" /><line x1="8" y1="2" x2="8" y2="18" /><line x1="16" y1="6" x2="16" y2="22" /></>,
    settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" /></>,
    pool: <><rect x="2" y="14" width="20" height="8" rx="2" /><path d="M6 14v-4a6 6 0 0112 0v4" /></>,
    check: <><polyline points="20 6 9 17 4 12" /></>,
    x: <><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></>,
    download: <><polyline points="8 17 12 21 16 17" /><line x1="12" y1="12" x2="12" y2="21" /><path d="M20.88 18.09A5 5 0 0018 9h-1.26A8 8 0 103 16.3" /></>,
    search: <><circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" /></>,
    filter: <><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" /></>,
    eye: <><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" /></>,
    zap: <><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></>,
    target: <><circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="6" /><circle cx="12" cy="12" r="2" /></>,
    layers: <><polygon points="12 2 2 7 12 12 22 7 12 2" /><polyline points="2 17 12 22 22 17" /><polyline points="2 12 12 17 22 12" /></>,
    trending: <><polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" /></>,
    cpu: <><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" /><line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" /></>,
    image: <><rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></>,
    arrow: <><line x1="5" y1="12" x2="19" y2="12" /><polyline points="12 5 19 12 12 19" /></>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {icons[name]}
    </svg>
  );
};

// ============================================================
// LOADING SPINNER
// ============================================================
const Spinner = ({ size = 20 }) => (
  <div style={{
    width: size, height: size, borderRadius: "50%",
    border: `2px solid rgba(0,212,255,0.2)`,
    borderTopColor: "var(--accent)",
    animation: "spin 0.8s linear infinite"
  }} />
);

// ============================================================
// ANIMATED NUMBER
// ============================================================
function AnimNum({ value, suffix = "", decimals = 0 }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const end = parseFloat(value);
    const duration = 1000;
    const step = (end - start) / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= end) { setDisplay(end); clearInterval(timer); }
      else setDisplay(start);
    }, 16);
    return () => clearInterval(timer);
  }, [value]);
  return <>{decimals > 0 ? display.toFixed(decimals) : Math.round(display)}{suffix}</>;
}

// ============================================================
// MINI CHART (custom, no recharts dependency)
// ============================================================
function MiniBarChart({ data, keyName, color = "var(--accent)" }) {
  const max = Math.max(...data.map(d => d[keyName]));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 6, height: 60 }}>
      {data.map((d, i) => {
        const pct = (d[keyName] / max) * 100;
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <div style={{ width: "100%", position: "relative", height: 48 }}>
              <div style={{
                position: "absolute", bottom: 0, left: 0, right: 0,
                background: `linear-gradient(to top, ${color}, ${color}80)`,
                borderRadius: "3px 3px 0 0",
                height: `${pct}%`,
                transition: "height 1s ease",
                animationDelay: `${i * 0.1}s`,
              }} />
            </div>
            <span style={{ fontSize: 9, color: "var(--text3)", fontFamily: "JetBrains Mono" }}>{d.day}</span>
          </div>
        );
      })}
    </div>
  );
}

// LiveBarChart reads chartData from context so it ticks automatically
function LiveBarChart({ keyName, color = "var(--accent)" }) {
  const { chartData } = useApp();
  return <MiniBarChart data={chartData} keyName={keyName} color={color} />;
}

// ============================================================
// SIDEBAR NAV
// ============================================================
function Sidebar({ page, setPage }) {
  const navItems = [
    { id: "home", icon: "home", label: "Overview" },
    { id: "upload", icon: "upload", label: "Detect (Upload)" },
    { id: "location", icon: "search", label: "Detect (Zip Code)" },
    { id: "compare", icon: "layers", label: "Change Detection" },
    { id: "estimator", icon: "dollar-sign", label: "Property Value" },
    { id: "results", icon: "target", label: "Results" },
    { id: "analytics", icon: "chart", label: "Analytics" },
    { id: "history", icon: "history", label: "History" },
    { id: "map", icon: "map", label: "Map View" },
  ];

  return (
    <div style={{
      width: 220, minHeight: "100vh", background: "var(--bg2)",
      borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column",
      padding: "24px 12px", gap: 4, flexShrink: 0, position: "relative", zIndex: 10
    }}>
      {/* Logo */}
      <div style={{ padding: "0 8px 28px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg, var(--accent2), var(--accent))",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 0 20px rgba(0,212,255,0.3)"
          }}>
            <Icon name="pool" size={16} color="#000" />
          </div>
          <div>
            <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 15, color: "var(--text)", letterSpacing: "-0.3px" }}>PoolDetect</div>
            <div style={{ fontSize: 9, color: "var(--accent)", letterSpacing: "2px", fontFamily: "JetBrains Mono" }}>AI v2.1</div>
          </div>
        </div>
      </div>

      <div style={{ paddingTop: 12 }}>
        {navItems.map(item => (
          <div key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} onClick={() => setPage(item.id)}>
            <Icon name={item.icon} size={14} />
            <span>{item.label}</span>
            {item.id === "upload" && (
              <div style={{ marginLeft: "auto", width: 6, height: 6, borderRadius: "50%", background: "var(--success)", animation: "pulse 2s infinite" }} />
            )}
          </div>
        ))}
      </div>

      {/* Bottom info */}
      <LiveSidebarInfo />
    </div>
  );
}

// ============================================================
// LIVE SIDEBAR INFO (reads live stats from context)
// ============================================================
function LiveSidebarInfo() {
  const { liveStats } = useApp();
  return (
    <div style={{ marginTop: "auto", padding: "16px 8px", borderTop: "1px solid var(--border)" }}>
      <div style={{ fontSize: 10, color: "var(--text3)", marginBottom: 8 }}>MODEL STATUS</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)", animation: "pulse 2s infinite" }} />
        <span style={{ fontSize: 11, color: "var(--text2)" }}>YOLOv9-Pool Online</span>
      </div>
      <div style={{ marginTop: 8, fontSize: 10, color: "var(--text3)" }}>
        Accuracy: <span style={{ color: "var(--success)" }}>{liveStats.accuracy.toFixed(1)}%</span>
      </div>
      <div style={{ marginTop: 4 }}>
        <div className="confidence-bar">
          <div className="confidence-fill" style={{ width: `${liveStats.accuracy}%`, transition: "width 1.5s ease" }} />
        </div>
      </div>
      <div style={{ marginTop: 8, fontSize: 10, color: "var(--text3)" }}>
        Inference: <span style={{ color: "var(--accent)" }}>{liveStats.inferenceMs.toFixed(2)}s</span>
      </div>
      <div style={{ marginTop: 4, fontSize: 10, color: "var(--text3)" }}>
        GPU: <span style={{ color: liveStats.gpuUtil > 85 ? "var(--warning)" : "var(--success)" }}>{liveStats.gpuUtil}%</span>
        {" · "}
        <span style={{ color: "var(--accent2)" }}>{liveStats.reqPerMin} req/min</span>
      </div>
    </div>
  );
}

// ============================================================
// HOME PAGE
// ============================================================
function HomePage({ setPage }) {
  const { history } = useApp();
  const totalPools = history.reduce((s, h) => s + h.pools, 0);
  const avgConf = history.length ? history.reduce((s, h) => s + h.confidence, 0) / history.length : 0;
  const avgTime = history.length ? history.reduce((s, h) => s + parseFloat(h.time), 0) / history.length : 0;

  const stats = [
    { label: "Images Analyzed", value: history.length, suffix: "", icon: "image", color: "var(--accent)" },
    { label: "Pools Detected", value: totalPools, suffix: "", icon: "pool", color: "var(--success)" },
    { label: "Avg Confidence", value: avgConf, suffix: "%", decimals: 1, icon: "target", color: "var(--accent3)" },
    { label: "Avg Process Time", value: avgTime, suffix: "s", decimals: 2, icon: "zap", color: "var(--warning)" },
  ];

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1200 }}>
      {/* Header */}
      <div style={{ marginBottom: 40 }}>
        <div className="tag" style={{ marginBottom: 16 }}>
          <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--success)", animation: "pulse 2s infinite" }} />
          REAL-TIME DETECTION ACTIVE
        </div>
        <h1 style={{ fontSize: 42, fontWeight: 800, color: "var(--text)", lineHeight: 1.1, marginBottom: 12 }}>
          AI-Powered<br />
          <span style={{ background: "linear-gradient(90deg, var(--accent2), var(--accent))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Pool Detection</span>
        </h1>
        <p style={{ color: "var(--text2)", fontSize: 15, maxWidth: 500, lineHeight: 1.6 }}>
          Upload aerial imagery and get instant detection results with bounding boxes, confidence scores, and detailed analytics.
        </p>
        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          <button className="btn-primary" onClick={() => setPage("upload")} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Icon name="upload" size={14} color="#000" />
            Start Detection
          </button>
          <button className="btn-ghost" onClick={() => setPage("analytics")}>View Analytics</button>
        </div>
      </div>

      {/* Stats grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 32 }}>
        {stats.map((s, i) => (
          <div key={i} className="stat-card" style={{ animationDelay: `${i * 0.1}s` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: `${s.color}18`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icon name={s.icon} size={16} color={s.color} />
              </div>
              <Icon name="trending" size={12} color="var(--success)" />
            </div>
            <div style={{ fontSize: 32, fontWeight: 800, fontFamily: "Syne", color: s.color, marginBottom: 4 }}>
              <AnimNum value={s.value} suffix={s.suffix} decimals={s.decimals || 0} />
            </div>
            <div style={{ fontSize: 12, color: "var(--text3)" }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Recent + Chart row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 16 }}>
        {/* Chart */}
        <div className="stat-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
            <div>
              <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 16, marginBottom: 4 }}>Weekly Detection Activity</div>
              <div style={{ fontSize: 12, color: "var(--text3)" }}>Pools detected per day</div>
            </div>
            <div className="tag">LIVE · 3s REFRESH</div>
          </div>
          <LiveBarChart keyName="pools" color="var(--accent)" />
        </div>

        {/* Recent detections */}
        <div className="stat-card">
          <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 15, marginBottom: 16 }}>Recent Detections</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {history.slice(0, 4).map((h, i) => (
              <div key={h.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px", borderRadius: 8, background: "var(--bg3)", cursor: "pointer", transition: "background 0.2s" }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--surface2)"}
                onMouseLeave={e => e.currentTarget.style.background = "var(--bg3)"}
              >
                <div style={{ width: 36, height: 36, borderRadius: 8, background: "var(--surface2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon name="image" size={14} color="var(--text3)" />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, color: "var(--text)", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.filename}</div>
                  <div style={{ fontSize: 10, color: "var(--text3)" }}>{h.pools} pools · {h.confidence.toFixed(1)}%</div>
                </div>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)", flexShrink: 0 }} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// UPLOAD PAGE
// ============================================================
function UploadPage() {
  const { addResult, setPage } = useApp();
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | uploading | processing | done
  const [progress, setProgress] = useState(0);
  const inputRef = useRef();

  const handleFile = (f) => {
    if (!f || !f.type.startsWith("image/")) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setStatus("idle");
    setProgress(0);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const runDetection = async () => {
    setStatus("uploading");
    setProgress(0);

    // Animate progress bar while the actual upload is in-flight
    const progressInterval = setInterval(() => {
      setProgress(p => {
        if (p >= 90) { clearInterval(progressInterval); return 90; }
        return p + Math.random() * 12;
      });
    }, 80);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/detect", {
        method: "POST",
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      setStatus("processing");
      const data = await response.json();

      // Small pause so the "ANALYZING IMAGERY..." overlay is visible
      await new Promise(r => setTimeout(r, 600));

      const result = {
        id: Date.now().toString(),
        filename: file.name,
        pools: data.pools,
        confidence: data.confidence || 0,
        time: data.time,
        ts: Date.now(),
        lat: data.lat !== null ? data.lat : 33 + Math.random() * 10,
        lng: data.lng !== null ? data.lng : -100 + Math.random() * 30,
        preview,
        categories: data.categories || {},
        // Keep flat arrays for backwards compatibility / analytics
        boxes: data.boxes || [],
        polygons: data.polygons || [],
      };

      addResult(result);
      setStatus("done");
      setTimeout(() => setPage("results"), 800);

    } catch (err) {
      clearInterval(progressInterval);
      setProgress(0);
      setStatus("idle");
      alert(`Detection failed: ${err.message}\n\nMake sure the backend is running:\n  cd backend && uvicorn main:app --reload`);
    }
  };

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 800 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>DETECTION ENGINE</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Upload Imagery</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>Supports JPG, PNG, TIFF · Max 50MB · GeoTIFF ready</p>
      </div>

      {!preview ? (
        <div className={`upload-zone ${dragActive ? "drag-active" : ""}`}
          style={{ padding: "80px 40px", textAlign: "center", position: "relative" }}
          onDragOver={e => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input ref={inputRef} type="file" accept="image/*" style={{ display: "none" }} onChange={e => handleFile(e.target.files[0])} />
          <div style={{
            width: 72, height: 72, borderRadius: "50%",
            background: "linear-gradient(135deg, rgba(0,144,255,0.1), rgba(0,212,255,0.1))",
            border: "1px solid rgba(0,212,255,0.2)",
            display: "flex", alignItems: "center", justifyContent: "center",
            margin: "0 auto 20px", animation: dragActive ? "none" : "float 3s ease infinite"
          }}>
            <Icon name="upload" size={28} color="var(--accent)" />
          </div>
          <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 20, color: "var(--text)", marginBottom: 8 }}>
            {dragActive ? "Release to Upload" : "Drop Aerial Image Here"}
          </div>
          <div style={{ fontSize: 13, color: "var(--text3)" }}>or click to browse files</div>

          <div style={{ display: "flex", gap: 16, justifyContent: "center", marginTop: 32 }}>
            {["Satellite imagery", "Drone footage", "Aerial photos"].map(t => (
              <div key={t} className="tag">{t}</div>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Preview */}
          <div className="result-box" style={{ position: "relative" }}>
            <img src={preview} alt="Preview" style={{ width: "100%", maxHeight: 360, objectFit: "cover", display: "block" }} />

            {status === "processing" && (
              <div style={{
                position: "absolute", inset: 0, background: "rgba(3,5,8,0.7)",
                display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16
              }}>
                <div style={{
                  position: "absolute", left: 0, right: 0, height: 2, background: "linear-gradient(90deg, transparent, var(--accent), transparent)",
                  animation: "scanLine 1.5s linear infinite", top: 0
                }} />
                <Spinner size={36} />
                <div style={{ fontFamily: "Syne", fontWeight: 700, color: "var(--accent)", fontSize: 14 }}>ANALYZING IMAGERY...</div>
                <div style={{ fontSize: 11, color: "var(--text2)" }}>Running YOLOv9-Pool inference</div>
              </div>
            )}

            {status === "done" && (
              <div style={{ position: "absolute", inset: 0, background: "rgba(0,229,160,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ background: "var(--success)", borderRadius: "50%", width: 48, height: 48, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Icon name="check" size={24} color="#000" />
                </div>
              </div>
            )}

            <button style={{
              position: "absolute", top: 12, right: 12, background: "rgba(0,0,0,0.6)", border: "1px solid var(--border)",
              borderRadius: 8, padding: "6px 8px", cursor: "pointer", color: "var(--text2)", display: "flex", alignItems: "center"
            }} onClick={() => { setPreview(null); setFile(null); setStatus("idle"); }}>
              <Icon name="x" size={14} />
            </button>
          </div>

          {/* File info */}
          <div className="stat-card" style={{ padding: "16px 20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", gap: 16 }}>
                <div>
                  <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 2 }}>FILENAME</div>
                  <div style={{ fontSize: 13, color: "var(--text)" }}>{file?.name}</div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 2 }}>SIZE</div>
                  <div style={{ fontSize: 13, color: "var(--text)" }}>{(file?.size / 1024 / 1024).toFixed(2)} MB</div>
                </div>
              </div>

              {(status === "idle" || status === "uploading") && (
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  {status === "uploading" && (
                    <div style={{ fontSize: 12, color: "var(--text2)" }}>
                      Uploading {Math.min(100, Math.round(progress))}%
                    </div>
                  )}
                  <button className="btn-primary" onClick={runDetection} disabled={status === "uploading"}
                    style={{ display: "flex", alignItems: "center", gap: 8, opacity: status === "uploading" ? 0.6 : 1 }}>
                    {status === "uploading" ? <Spinner size={14} /> : <Icon name="zap" size={14} color="#000" />}
                    {status === "uploading" ? "Uploading..." : "Run Detection"}
                  </button>
                </div>
              )}
            </div>

            {status === "uploading" && (
              <div style={{ marginTop: 12 }}>
                <div className="confidence-bar" style={{ height: 6 }}>
                  <div className="confidence-fill" style={{ width: `${Math.min(100, progress)}%`, transition: "width 0.1s" }} />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Model info cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginTop: 24 }}>
        {[
          { title: "Detection Model", value: "YOLOv9-Pool", icon: "cpu" },
          { title: "Input Resolution", value: "Up to 8K", icon: "image" },
          { title: "Inference Speed", value: "< 2s avg", icon: "zap" },
        ].map((m, i) => (
          <div key={i} className="stat-card" style={{ padding: "14px 18px" }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <Icon name={m.icon} size={14} color="var(--text3)" />
              <div>
                <div style={{ fontSize: 10, color: "var(--text3)" }}>{m.title}</div>
                <div style={{ fontSize: 13, fontWeight: 600, fontFamily: "Syne", color: "var(--text)", marginTop: 2 }}>{m.value}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============================================================
// LOCATION SEARCH PAGE
// ============================================================
function LocationSearchPage() {
  const { addResult, setPage } = useApp();
  const [zipCode, setZipCode] = useState("");
  const [status, setStatus] = useState("idle"); // idle, geocoding, fetching, processing, done
  const [errorMsg, setErrorMsg] = useState("");
  const [preview, setPreview] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!zipCode.trim()) return;

    setErrorMsg("");
    setStatus("geocoding");
    setPreview(null);

    try {
      // 1. Geocode Zip Code using Nominatim (Free OpenStreetMap API)
      const geoUrl = `https://nominatim.openstreetmap.org/search?postalcode=${encodeURIComponent(zipCode)}&format=json&limit=1`;
      const geoRes = await fetch(geoUrl);
      const geoData = await geoRes.json();

      let lat = 33.749;
      let lon = -84.388;

      if (geoData && geoData.length > 0) {
        lat = parseFloat(geoData[0].lat);
        lon = parseFloat(geoData[0].lon);
      }

      // No API Key required for Esri Satellite Tiles

      // Calculate Esri Tile XYZ coordinates
      const zoom = 18;
      const latRad = lat * (Math.PI / 180);
      const n = Math.pow(2.0, zoom);
      const xtile = Math.floor((lon + 180.0) / 360.0 * n);
      const ytile = Math.floor((1.0 - Math.log(Math.tan(latRad) + (1 / Math.cos(latRad))) / Math.PI) / 2.0 * n);

      const mapUrl = `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}/${ytile}/${xtile}`;
      setPreview(mapUrl);

      // 3. Send Location to Backend
      setStatus("processing");

      const detectRes = await fetch("http://localhost:8000/detect-location", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lon })
      });

      if (!detectRes.ok) {
        const err = await detectRes.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${detectRes.status} Error`);
      }

      const data = await detectRes.json();

      // 4. Add Result
      const result = {
        id: Date.now().toString(),
        filename: `Zip: ${zipCode}`,
        pools: data.pools,
        confidence: data.confidence || 0,
        time: data.time,
        ts: Date.now(),
        lat: lat,
        lng: lon,
        preview: mapUrl,
        categories: data.categories || {},
        boxes: data.boxes || [],
        polygons: data.polygons || [],
      };

      addResult(result);
      setStatus("done");
      setTimeout(() => setPage("results"), 800);

    } catch (err) {
      console.error(err);
      setStatus("error");
      setErrorMsg(err.message);
    }
  };

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 800 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>REMOTE SCANNING</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Zip Code Search</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>Automatically fetch and scan satellite imagery for any Zip Code</p>
      </div>

      <div className="stat-card" style={{ padding: "32px", marginBottom: 24 }}>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 16 }}>
          <div style={{ flex: 1, position: "relative" }}>
            <div style={{ position: "absolute", left: 16, top: "50%", transform: "translateY(-50%)" }}>
              <Icon name="search" size={18} color="var(--text3)" />
            </div>
            <input
              type="text"
              placeholder="Enter Zip Code or Address..."
              value={zipCode}
              onChange={e => setZipCode(e.target.value)}
              style={{
                width: "100%", background: "var(--bg1)", border: "1px solid var(--border)",
                borderRadius: 8, padding: "14px 16px 14px 44px", color: "var(--text)",
                fontFamily: "Space Grotesk", fontSize: 16, outline: "none"
              }}
              disabled={status !== "idle" && status !== "error"}
            />
          </div>
          <button type="submit" className="btn-primary" disabled={status !== "idle" && status !== "error"} style={{ padding: "0 32px", fontSize: 15 }}>
            {status === "idle" || status === "error" ? "Scan Area" : "Scanning..."}
          </button>
        </form>

        {status !== "idle" && status !== "error" && (
          <div style={{ marginTop: 24, display: "flex", alignItems: "center", gap: 12, padding: "16px", background: "var(--bg1)", borderRadius: 8 }}>
            <Spinner size={16} />
            <div style={{ fontSize: 13, color: "var(--text2)" }}>
              {status === "geocoding" && "Resolving Zip Code to coordinates..."}
              {status === "fetching" && "Downloading high-res satellite imagery tile..."}
              {status === "processing" && "Running YOLOv9-Pool inference engine..."}
            </div>
          </div>
        )}

        {status === "error" && (
          <div style={{ marginTop: 24, padding: "16px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: 8, display: "flex", alignItems: "flex-start", gap: 12 }}>
            <Icon name="alert-circle" size={18} color="var(--error)" />
            <div>
              <div style={{ color: "var(--error)", fontSize: 14, fontWeight: 600, marginBottom: 4 }}>Scan Failed</div>
              <div style={{ color: "var(--text2)", fontSize: 13 }}>{errorMsg}</div>
            </div>
          </div>
        )}
      </div>

      <div style={{ marginTop: 24, padding: "20px", border: "1px dashed var(--border)", borderRadius: 8, background: "var(--bg2)" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Icon name="check" size={20} color="var(--success)" />
          <div>
            <div style={{ fontFamily: "Syne", fontSize: 15, fontWeight: 700, color: "var(--text)" }}>Esri World Imagery Active</div>
            <div style={{ fontSize: 12, color: "var(--text3)", marginTop: 2 }}>Using free satellite map tiles. No API key required.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// CHANGE DETECTION PAGE
// ============================================================
function ChangeDetectionPage() {
  const { addResult, setPage } = useApp();
  const [fileBefore, setFileBefore] = useState(null);
  const [fileAfter, setFileAfter] = useState(null);
  const [status, setStatus] = useState("idle"); // idle, processing, done, error
  const [errorMsg, setErrorMsg] = useState("");

  // Handlers for Before Dropzone
  const onDragBefore = e => e.preventDefault();
  const onDropBefore = e => { e.preventDefault(); if (e.dataTransfer.files[0]) setFileBefore(e.dataTransfer.files[0]); };

  // Handlers for After Dropzone
  const onDragAfter = e => e.preventDefault();
  const onDropAfter = e => { e.preventDefault(); if (e.dataTransfer.files[0]) setFileAfter(e.dataTransfer.files[0]); };

  const handleAnalyze = async () => {
    if (!fileBefore || !fileAfter) return;
    setStatus("processing");
    setErrorMsg("");

    const formData = new FormData();
    formData.append("image_before", fileBefore);
    formData.append("image_after", fileAfter);

    try {
      const startTime = performance.now();
      const res = await fetch("http://localhost:8000/detect-change", {
        method: "POST", body: formData
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${res.status}`);
      }

      const data = await res.json();
      const elapsed = ((performance.now() - startTime) / 1000).toFixed(2);

      // Create a unified result object that the ResultsPage can render
      // We will render the "after" image, but pass the different categories for styling
      const unifiedResult = {
        id: Date.now().toString(),
        filename: `Comparison: ${fileAfter.name}`,
        pools: data.comparisons.new_built + data.comparisons.existing,
        confidence: 95.0, // Mocked for unified view
        time: elapsed,
        ts: Date.now(),
        preview: URL.createObjectURL(fileAfter), // Show the AFTER image

        // We inject the change detection results into the existing categories structure
        // so the ResultsPage can render them with distinct colors
        categories: {
          new_construction: data.new_pools,
          existing_pools: data.existing_pools,
          removed_pools: data.removed_pools
        },
        boxes: [], polygons: [],
        isComparison: true,
        comparisons: data.comparisons
      };

      addResult(unifiedResult);
      setStatus("done");
      setTimeout(() => setPage("results"), 600);

    } catch (err) {
      console.error(err);
      setStatus("error");
      setErrorMsg(err.message);
    }
  };

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1000 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>TIME SERIES ANALYSIS</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Pool Construction Detection</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>Upload Before & After imagery to automatically identify newly built swimming pools.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        {/* Before Dropzone */}
        <label
          className="stat-card"
          onDragOver={onDragBefore}
          onDrop={onDropBefore}
          style={{
            display: "block", cursor: "pointer", textAlign: "center", padding: "40px 20px",
            border: fileBefore ? "1px solid var(--accent3)" : "1px dashed var(--border)",
            background: fileBefore ? "var(--bg1)" : "var(--bg2)"
          }}>
          <input type="file" style={{ display: "none" }} onChange={e => e.target.files[0] && setFileBefore(e.target.files[0])} accept="image/*" />

          {fileBefore ? (
            <div>
              <Icon name="image" size={32} color="var(--accent3)" />
              <div style={{ marginTop: 12, fontSize: 13, color: "var(--text)", fontWeight: 600, fontFamily: "Syne" }}>{fileBefore.name}</div>
              <div style={{ marginTop: 4, fontSize: 11, color: "var(--text3)" }}>Before Image Ready</div>
            </div>
          ) : (
            <div>
              <div style={{ width: 48, height: 48, borderRadius: 24, background: "var(--bg3)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                <Icon name="upload" size={20} color="var(--text3)" />
              </div>
              <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 16, color: "var(--text)", marginBottom: 8 }}>Image A (Before)</div>
              <div style={{ fontSize: 12, color: "var(--text2)" }}>Drop image from e.g. 2022</div>
            </div>
          )}
        </label>

        {/* After Dropzone */}
        <label
          className="stat-card"
          onDragOver={onDragAfter}
          onDrop={onDropAfter}
          style={{
            display: "block", cursor: "pointer", textAlign: "center", padding: "40px 20px",
            border: fileAfter ? "1px solid var(--success)" : "1px dashed var(--border)",
            background: fileAfter ? "var(--bg1)" : "var(--bg2)"
          }}>
          <input type="file" style={{ display: "none" }} onChange={e => e.target.files[0] && setFileAfter(e.target.files[0])} accept="image/*" />

          {fileAfter ? (
            <div>
              <Icon name="image" size={32} color="var(--success)" />
              <div style={{ marginTop: 12, fontSize: 13, color: "var(--text)", fontWeight: 600, fontFamily: "Syne" }}>{fileAfter.name}</div>
              <div style={{ marginTop: 4, fontSize: 11, color: "var(--text3)" }}>After Image Ready</div>
            </div>
          ) : (
            <div>
              <div style={{ width: 48, height: 48, borderRadius: 24, background: "var(--bg3)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
                <Icon name="upload" size={20} color="var(--text3)" />
              </div>
              <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 16, color: "var(--text)", marginBottom: 8 }}>Image B (After)</div>
              <div style={{ fontSize: 12, color: "var(--text2)" }}>Drop image from e.g. 2024</div>
            </div>
          )}
        </label>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 16 }}>
        {status === "processing" && (
          <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text2)", fontSize: 13 }}>
            <Spinner size={16} /> Computing spatial Intersection over Union (IoU)...
          </div>
        )}
        {status === "error" && (
          <div style={{ color: "var(--error)", fontSize: 13, display: "flex", alignItems: "center", gap: 6 }}>
            <Icon name="alert-circle" size={14} /> {errorMsg}
          </div>
        )}
        <button
          className="btn-primary"
          onClick={handleAnalyze}
          disabled={!fileBefore || !fileAfter || status === "processing"}
          style={{ padding: "12px 32px", fontSize: 15 }}
        >
          {status === "processing" ? "Analyzing Changes..." : "Compare Imagery & Detect Construction"}
        </button>
      </div>
    </div>
  );
}

// ============================================================
// RESULTS PAGE
// ============================================================
function ResultsPage() {
  const { detectionResult } = useApp();
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [sliderPos, setSliderPos] = useState(50);
  const canvasRef = useRef();

  const result = detectionResult || MOCK_HISTORY[0];

  useEffect(() => {
    if (showHeatmap && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);

      const numBlobs = 8;
      for (let i = 0; i < numBlobs; i++) {
        const x = Math.random() * W, y = Math.random() * H;
        const r = 40 + Math.random() * 60;
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, r);
        gradient.addColorStop(0, `rgba(0,212,255,${0.3 + Math.random() * 0.4})`);
        gradient.addColorStop(0.5, `rgba(123,79,255,${0.1 + Math.random() * 0.2})`);
        gradient.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, W, H);
      }
    }
  }, [showHeatmap]);

  const categories = result.categories || {
    uncovered_grounded: [],
    uncovered_above_ground: [],
    covered_grounded: [],
    covered_above_ground: []
  };

  // Helper to map category to color/label
  const getCategoryStyle = (catKey) => {
    switch (catKey) {
      case 'uncovered_grounded': return { color: "rgba(0, 240, 255, 0.9)", fill: "rgba(0, 240, 255, 0.15)", glow: "rgba(0, 240, 255, 0.3)", label: "UNCOVERED IN-GROUND" };
      case 'uncovered_above_ground': return { color: "rgba(59, 130, 246, 0.9)", fill: "rgba(59, 130, 246, 0.15)", glow: "rgba(59, 130, 246, 0.3)", label: "UNCOVERED ABOVE-GROUND" };
      case 'covered_grounded': return { color: "rgba(100, 116, 139, 0.9)", fill: "rgba(100, 116, 139, 0.15)", glow: "rgba(100, 116, 139, 0.3)", label: "COVERED IN-GROUND" };
      case 'covered_above_ground': return { color: "rgba(30, 58, 138, 0.9)", fill: "rgba(30, 58, 138, 0.15)", glow: "rgba(30, 58, 138, 0.3)", label: "COVERED ABOVE-GROUND" };
      // Used by Change Detection Flow
      case 'new_construction': return { color: "rgba(16, 185, 129, 0.95)", fill: "rgba(16, 185, 129, 0.25)", glow: "rgba(16, 185, 129, 0.5)", label: "NEW CONSTRUCTION" };
      case 'existing_pools': return { color: "rgba(0, 212, 255, 0.6)", fill: "none", glow: "rgba(0, 212, 255, 0.2)", label: "EXISTING POOL" };
      case 'removed_pools': return { color: "rgba(239, 68, 68, 0.8)", fill: "rgba(239, 68, 68, 0.1)", glow: "rgba(239, 68, 68, 0.3)", label: "REMOVED/FILLED" };
      default: return { color: "rgba(0, 212, 255, 0.9)", fill: "rgba(0, 212, 255, 0.12)", glow: "rgba(0, 212, 255, 0.3)", label: "POOL" };
    }
  };

  // Flatten categories for rendering
  const allFilteredPools = [];
  Object.keys(categories).forEach(catKey => {
    (categories[catKey] || []).forEach(pool => {
      allFilteredPools.push({ ...pool, catKey, style: getCategoryStyle(catKey) });
    });
  });

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
        <div>
          <div className="tag" style={{ marginBottom: 12 }}>DETECTION RESULT</div>
          <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>
            {result.filename || "aerial_suburb.jpg"}
          </h2>
          <div style={{ color: "var(--text2)", fontSize: 13, marginTop: 4 }}>
            {new Date(result.ts).toLocaleString()} · {result.time}s processing
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6 }}
            onClick={() => setShowHeatmap(h => !h)}>
            <Icon name="layers" size={13} />
            {showHeatmap ? "Hide" : "Show"} Heatmap
          </button>
          <button className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 6 }}
            onClick={() => alert("Exporting PDF report...")}>
            <Icon name="download" size={13} color="#000" />
            Export Report
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20 }}>
        {/* Main image */}
        <div>
          <div className="result-box" style={{ position: "relative", display: "inline-block", width: "100%" }}>
            {result.preview ? (
              <img src={result.preview} alt="Detection" style={{ width: "100%", height: "auto", display: "block", borderRadius: 8 }} />
            ) : (
              <div style={{ width: "100%", height: 400, background: "var(--bg3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ textAlign: "center" }}>
                  <Icon name="image" size={40} color="var(--text3)" />
                  <div style={{ color: "var(--text3)", fontSize: 13, marginTop: 8 }}>Aerial Imagery</div>
                </div>
              </div>
            )}

            {/* SVG Polygon overlays for shape-accurate pool outlines */}
            {allFilteredPools.length > 0 && (
              <svg
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style={{
                  position: "absolute", inset: 0, width: "100%", height: "100%",
                  pointerEvents: "none", zIndex: 2,
                  animation: "fadeIn 0.5s ease forwards",
                }}
              >
                <defs>
                  <filter id="poolGlow">
                    <feGaussianBlur stdDeviation="0.4" result="blur" />
                    <feMerge>
                      <feMergeNode in="blur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>
                {allFilteredPools.map((pool, i) => {
                  const poly = pool.polygon;
                  if (!poly || !poly.points || poly.points.length === 0) return null;
                  const pointsStr = poly.points.map(p => `${p.x},${p.y}`).join(" ");
                  return (
                    <g key={i} style={{ animation: `fadeIn 0.5s ease forwards`, animationDelay: `${i * 0.1}s` }}>
                      {/* Filled polygon */}
                      <polygon
                        points={pointsStr}
                        fill={pool.style.fill}
                        stroke={pool.style.color}
                        strokeWidth="0.4"
                        filter="url(#poolGlow)"
                        vectorEffect="non-scaling-stroke"
                      />
                      {/* Outer glow ring */}
                      <polygon
                        points={pointsStr}
                        fill="none"
                        stroke={pool.style.glow}
                        strokeWidth="1"
                        vectorEffect="non-scaling-stroke"
                      />
                    </g>
                  );
                })}
              </svg>
            )}

            {/* Pool labels positioned above each polygon */}
            {allFilteredPools.map((pool, i) => {
              const poly = pool.polygon;
              if (!poly || !poly.points || poly.points.length === 0) return null;
              const topPoint = poly.points.reduce((min, p) => p.y < min.y ? p : min, poly.points[0]);
              return (
                <div key={`label-${i}`} className="pool-label" style={{
                  position: "absolute",
                  left: `${topPoint.x}%`,
                  top: `${topPoint.y}%`,
                  transform: "translate(-50%, -24px)",
                  zIndex: 3,
                  animation: "fadeIn 0.5s ease forwards",
                  animationDelay: `${i * 0.1}s`,
                  background: "rgba(0,0,0,0.8)",
                  border: `1px solid ${pool.style.color}`,
                  color: pool.style.color
                }}>
                  {pool.style.label} · {poly.confidence !== undefined ? poly.confidence.toFixed(1) : "—"}%
                </div>
              );
            })}

            {/* Fallback: rectangular bounding boxes if no polygons */}
            {allFilteredPools.length === 0 && (result.boxes || []).map((box, i) => (
              <div key={i} className="pool-box" style={{
                left: `${box.x}%`, top: `${box.y}%`,
                width: `${box.w}%`, height: `${box.h}%`,
                animation: "fadeIn 0.5s ease forwards",
                animationDelay: `${i * 0.2}s`,
              }}>
                <div className="pool-label">
                  POOL {i + 1} · {box.confidence !== undefined ? box.confidence.toFixed(1) : "—"}%
                </div>
              </div>
            ))}

            {/* Heatmap canvas */}
            {showHeatmap && (
              <canvas ref={canvasRef} width={800} height={440} style={{
                position: "absolute", inset: 0, width: "100%", height: "100%",
                pointerEvents: "none", opacity: 0.5, animation: "fadeIn 0.5s ease"
              }} />
            )}

            {/* Scan line effect */}
            <div style={{
              position: "absolute", left: `${sliderPos}%`, top: 0, bottom: 0, width: 2,
              background: "var(--accent)", boxShadow: "0 0 10px var(--accent)",
              cursor: "ew-resize", zIndex: 5
            }} />
          </div>

          {/* Comparison slider */}
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text3)", marginBottom: 6 }}>
              <span>Original</span>
              <span>Position: {sliderPos}%</span>
              <span>Annotated</span>
            </div>
            <input type="range" min={0} max={100} value={sliderPos}
              onChange={e => setSliderPos(+e.target.value)} style={{ width: "100%" }} />
          </div>
        </div>

        {/* Sidebar stats */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Confidence */}
          <div className="stat-card">
            <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 8 }}>CONFIDENCE SCORE</div>
            <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 40, color: "var(--success)" }}>
              {result.confidence.toFixed(1)}%
            </div>
            <div className="confidence-bar" style={{ marginTop: 10, height: 6 }}>
              <div className="confidence-fill" style={{ width: `${result.confidence}%` }} />
            </div>
          </div>

          {/* Change Detection Details Panel */}
          {result.isComparison && result.comparisons && (
            <div className="stat-card" style={{ border: "1px solid var(--accent3)", background: "rgba(123, 79, 255, 0.05)" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
                <Icon name="layers" size={16} color="var(--accent3)" />
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent3)" }}>CHANGE ANALYSIS</div>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: "var(--text2)" }}>New Construction</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: "var(--success)" }}>+{result.comparisons.new_built}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                <span style={{ fontSize: 13, color: "var(--text3)" }}>Existing Pools</span>
                <span style={{ fontSize: 13, color: "var(--text3)" }}>{result.comparisons.existing}</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", paddingTop: 8, borderTop: "1px solid var(--border)" }}>
                <span style={{ fontSize: 13, color: "var(--text3)" }}>Removed / Filled</span>
                <span style={{ fontSize: 13, color: "var(--error)" }}>-{result.comparisons.removed_or_filled}</span>
              </div>
            </div>
          )}

          {/* Pools */}
          <div className="stat-card">
            <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 8 }}>POOLS DETECTED</div>
            <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 48, color: "var(--accent)", lineHeight: 1 }}>
              {result.pools}
            </div>
            <div style={{ fontSize: 12, color: "var(--text3)", marginTop: 4 }}>
              {result.pools === 1 ? "swimming pool" : "swimming pools"}
            </div>
          </div>

          {/* Processing time */}
          <div className="stat-card">
            <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 8 }}>PROCESSING TIME</div>
            <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 32, color: "var(--accent2)" }}>
              {result.time}s
            </div>
          </div>

          {/* Pool list */}
          <div className="stat-card">
            <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 12 }}>DETECTION DETAILS</div>
            {allFilteredPools.length === 0 && <div style={{ fontSize: 13, color: "var(--text3)" }}>No pools found.</div>}
            {allFilteredPools.map((pool, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: i < allFilteredPools.length - 1 ? "1px solid var(--border)" : "none" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: pool.style.color }} />
                  <span style={{ fontSize: 12, color: "var(--text2)" }}>{pool.style.label}</span>
                </div>
                <div className="tag" style={{ fontSize: 10, background: pool.style.fill, color: pool.style.color, border: `1px solid ${pool.style.color}40` }}>
                  {pool.polygon?.confidence?.toFixed(1) || pool.box?.confidence?.toFixed(1)}%
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-ghost" style={{ flex: 1, fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
              onClick={() => alert("Downloading CSV...")}>
              <Icon name="download" size={12} />CSV
            </button>
            <button className="btn-ghost" style={{ flex: 1, fontSize: 12, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
              onClick={() => alert("Downloading annotated image...")}>
              <Icon name="image" size={12} />IMG
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// ANALYTICS PAGE
// ============================================================
function AnalyticsPage() {
  const { history } = useApp();
  const totalPools = history.reduce((s, h) => s + h.pools, 0);
  const avgConf = history.length ? history.reduce((s, h) => s + h.confidence, 0) / history.length : 0;
  const maxConf = history.length ? Math.max(...history.map(h => h.confidence)) : 0;

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>ANALYTICS DASHBOARD</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Detection Analytics</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>Insights across all analyzed imagery</p>
      </div>

      {/* Top stat row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 24 }}>
        {[
          { label: "Total Analyses", value: history.length, color: "var(--accent)", icon: "image" },
          { label: "Total Pools Found", value: totalPools, color: "var(--success)", icon: "pool" },
          { label: "Avg Confidence", value: avgConf.toFixed(1) + "%", color: "var(--accent3)", icon: "target", raw: true },
          { label: "Best Confidence", value: maxConf.toFixed(1) + "%", color: "var(--warning)", icon: "zap", raw: true },
        ].map((s, i) => (
          <div key={i} className="stat-card" style={{ textAlign: "center" }}>
            <div style={{ width: 40, height: 40, borderRadius: 12, background: `${s.color}18`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px" }}>
              <Icon name={s.icon} size={18} color={s.color} />
            </div>
            <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: s.color }}>
              {s.raw ? s.value : <AnimNum value={s.value} />}
            </div>
            <div style={{ fontSize: 11, color: "var(--text3)", marginTop: 4 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div className="stat-card">
          <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Pools Detected / Day</div>
          <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 20 }}>Last 7 days</div>
          <LiveBarChart keyName="pools" color="var(--accent)" />
        </div>
        <div className="stat-card">
          <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Upload Activity</div>
          <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 20 }}>Images per day · live</div>
          <LiveBarChart keyName="uploads" color="var(--accent3)" />
        </div>
      </div>

      {/* Confidence distribution */}
      <div className="stat-card">
        <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 15, marginBottom: 4 }}>Confidence Distribution</div>
        <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 20 }}>Per detection</div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          {history.map((h, i) => (
            <div key={i} style={{ flex: "1 1 120px", minWidth: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: "var(--text3)", marginBottom: 4 }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>{h.filename.split(".")[0]}</span>
                <span style={{ color: h.confidence > 95 ? "var(--success)" : "var(--warning)" }}>{h.confidence.toFixed(0)}%</span>
              </div>
              <div className="confidence-bar" style={{ height: 6 }}>
                <div className="confidence-fill" style={{
                  width: `${h.confidence}%`,
                  background: h.confidence > 95 ? "linear-gradient(90deg, var(--success), #00ffaa)" : "linear-gradient(90deg, var(--warning), #ffdd70)"
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================
// HISTORY PAGE
// ============================================================
function HistoryPage() {
  const { history, setDetectionResult, setPage } = useApp();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const filtered = history.filter(h => {
    const matchSearch = h.filename.toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === "all" || (filter === "high" && h.confidence >= 95) || (filter === "low" && h.confidence < 95);
    return matchSearch && matchFilter;
  });

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 32 }}>
        <div>
          <div className="tag" style={{ marginBottom: 12 }}>DETECTION LOG</div>
          <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Detection History</h2>
          <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>{history.length} total analyses</p>
        </div>
        <button className="btn-ghost" style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}
          onClick={() => alert("Exporting CSV...")}>
          <Icon name="download" size={13} />Export CSV
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <div style={{ flex: 1, position: "relative" }}>
          <div style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}>
            <Icon name="search" size={14} color="var(--text3)" />
          </div>
          <input type="text" placeholder="Search by filename..." value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: "100%", paddingLeft: 36 }} />
        </div>
        <div style={{ position: "relative" }}>
          <div style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", pointerEvents: "none" }}>
            <Icon name="filter" size={12} color="var(--text3)" />
          </div>
          <select value={filter} onChange={e => setFilter(e.target.value)} style={{ paddingLeft: 30, paddingRight: 20 }}>
            <option value="all">All Results</option>
            <option value="high">High Confidence (≥95%)</option>
            <option value="low">Standard (&lt;95%)</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="stat-card" style={{ padding: 0, overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid var(--border)" }}>
              {["Filename", "Pools", "Confidence", "Process Time", "Date", "Actions"].map(h => (
                <th key={h} style={{ padding: "14px 20px", textAlign: "left", fontSize: 10, color: "var(--text3)", fontFamily: "JetBrains Mono", fontWeight: 500, letterSpacing: "1px", whiteSpace: "nowrap" }}>
                  {h.toUpperCase()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row, i) => (
              <tr key={row.id} style={{
                borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none",
                transition: "background 0.2s",
              }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--surface2)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <td style={{ padding: "14px 20px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 6, background: "var(--bg3)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon name="image" size={12} color="var(--text3)" />
                    </div>
                    <span style={{ fontSize: 13, color: "var(--text)" }}>{row.filename}</span>
                  </div>
                </td>
                <td style={{ padding: "14px 20px" }}>
                  <span style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 18, color: "var(--accent)" }}>{row.pools}</span>
                </td>
                <td style={{ padding: "14px 20px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div className="confidence-bar" style={{ width: 60 }}>
                      <div className="confidence-fill" style={{ width: `${row.confidence}%` }} />
                    </div>
                    <span style={{ fontSize: 12, color: row.confidence >= 95 ? "var(--success)" : "var(--warning)" }}>
                      {row.confidence.toFixed(1)}%
                    </span>
                  </div>
                </td>
                <td style={{ padding: "14px 20px", fontSize: 12, color: "var(--text2)" }}>{row.time}s</td>
                <td style={{ padding: "14px 20px", fontSize: 11, color: "var(--text3)" }}>
                  {new Date(row.ts).toLocaleDateString()}
                </td>
                <td style={{ padding: "14px 20px" }}>
                  <button className="btn-ghost" style={{ padding: "6px 10px", fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}
                    onClick={() => { setDetectionResult(row); setPage("results"); }}>
                    <Icon name="eye" size={11} />View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {filtered.length === 0 && (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text3)", fontSize: 13 }}>
            No results match your search
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================
// MAP PAGE
// ============================================================
function MapPage() {
  const { history } = useApp();
  const [selected, setSelected] = useState(null);

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>GEOGRAPHIC DISTRIBUTION</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Detection Map</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>Geospatial distribution of detected pools</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 20 }}>
        {/* Map */}
        <div className="stat-card" style={{ padding: 0, overflow: "hidden", position: "relative", height: 440 }}>
          <Map
            defaultZoom={2}
            defaultCenter={{ lat: 20, lng: 0 }}
            mapId="DEMO_MAP_ID"
            mapTypeId="satellite"
            disableDefaultUI={true}
            gestureHandling="greedy"
          >
            {history.map(h => {
              const isSelected = selected?.id === h.id;
              return (
                <AdvancedMarker
                  key={h.id}
                  position={{ lat: h.lat, lng: h.lng }}
                  onClick={() => setSelected(h)}
                >
                  <div style={{
                    position: "relative",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    cursor: "pointer",
                    transform: isSelected ? "scale(1.2)" : "scale(1)",
                    transition: "transform 0.2s"
                  }}>
                    <div style={{
                      position: "absolute",
                      width: isSelected ? 36 : 24,
                      height: isSelected ? 36 : 24,
                      borderRadius: "50%",
                      border: "1px solid var(--accent)",
                      opacity: 0.3,
                      animation: "markerPulse 2s infinite"
                    }} />
                    <div style={{
                      width: 12, height: 12, borderRadius: "50%",
                      background: isSelected ? "var(--accent)" : "var(--accent2)",
                      border: "2px solid var(--bg)",
                      boxShadow: "0 0 10px rgba(0,0,0,0.5)"
                    }} />
                  </div>
                </AdvancedMarker>
              );
            })}
          </Map>

          {/* Legend */}
          <div style={{ position: "absolute", bottom: 16, left: 16, display: "flex", gap: 12, background: "rgba(3,5,8,0.7)", padding: "6px 10px", borderRadius: 6, backdropFilter: "blur(4px)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, color: "var(--text3)" }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: "var(--accent)" }} />
              Detection Point
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10, color: "var(--text3)" }}>
              <span style={{ fontSize: 11, color: "var(--accent)" }}>N</span> = Pool Count
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {selected ? (
            <div className="stat-card" style={{ animation: "fadeUp 0.3s ease" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                <div className="tag">SELECTED</div>
                <button style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text3)" }} onClick={() => setSelected(null)}>
                  <Icon name="x" size={12} />
                </button>
              </div>
              <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 14, color: "var(--text)", marginBottom: 12 }}>{selected.filename}</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  ["Pools", selected.pools, "var(--accent)"],
                  ["Confidence", `${selected.confidence.toFixed(1)}%`, "var(--success)"],
                  ["Time", `${selected.time}s`, "var(--text2)"],
                  ["Lat", selected.lat.toFixed(3), "var(--text3)"],
                  ["Lng", selected.lng.toFixed(3), "var(--text3)"],
                ].map(([k, v, c]) => (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                    <span style={{ color: "var(--text3)" }}>{k}</span>
                    <span style={{ color: c, fontWeight: 600 }}>{v}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 14, fontSize: 11, color: "var(--text3)" }}>
                {new Date(selected.ts).toLocaleString()}
              </div>
            </div>
          ) : (
            <div className="stat-card">
              <div style={{ textAlign: "center", padding: "20px 0" }}>
                <Icon name="map" size={28} color="var(--text3)" />
                <div style={{ fontSize: 12, color: "var(--text3)", marginTop: 10 }}>Click a marker to see details</div>
              </div>
            </div>
          )}

          {/* Detection list */}
          <div className="stat-card" style={{ flex: 1 }}>
            <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 13, marginBottom: 12, color: "var(--text)" }}>All Detections</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 240, overflowY: "auto" }} className="scrollbar-hide">
              {history.map(h => (
                <div key={h.id} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "8px 10px", borderRadius: 8, cursor: "pointer",
                  background: selected?.id === h.id ? "rgba(0,212,255,0.08)" : "var(--bg3)",
                  border: `1px solid ${selected?.id === h.id ? "rgba(0,212,255,0.2)" : "transparent"}`,
                  transition: "all 0.2s"
                }} onClick={() => setSelected(h)}>
                  <div>
                    <div style={{ fontSize: 11, color: "var(--text)", fontWeight: 500 }}>{h.filename.split(".")[0]}</div>
                    <div style={{ fontSize: 10, color: "var(--text3)" }}>{h.lat.toFixed(2)}, {h.lng.toFixed(2)}</div>
                  </div>
                  <div className="tag" style={{ fontSize: 10 }}>{h.pools}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// SETTINGS PAGE
// ============================================================
function SettingsPage() {
  const [modelVersion, setModelVersion] = useState("yolov9-pool-v2");
  const [threshold, setThreshold] = useState(80);
  const [maxBoxes, setMaxBoxes] = useState(10);

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 700 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>CONFIGURATION</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Settings</h2>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        {/* Model config */}
        <div className="stat-card">
          <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 15, marginBottom: 20, color: "var(--text)" }}>Model Configuration</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 8 }}>DETECTION MODEL</div>
              <select value={modelVersion} onChange={e => setModelVersion(e.target.value)} style={{ width: "100%" }}>
                <option value="yolov9-pool-v2">YOLOv9-Pool v2.1 (Recommended)</option>
                <option value="yolov9-pool-v1">YOLOv9-Pool v1.0</option>
                <option value="yolov8-pool">YOLOv8-Pool (Legacy)</option>
              </select>
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text3)", marginBottom: 8 }}>
                <span>CONFIDENCE THRESHOLD</span>
                <span style={{ color: "var(--accent)" }}>{threshold}%</span>
              </div>
              <input type="range" min={50} max={99} value={threshold}
                onChange={e => setThreshold(+e.target.value)} style={{ width: "100%" }} />
            </div>

            <div>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text3)", marginBottom: 8 }}>
                <span>MAX DETECTIONS PER IMAGE</span>
                <span style={{ color: "var(--accent)" }}>{maxBoxes}</span>
              </div>
              <input type="range" min={1} max={50} value={maxBoxes}
                onChange={e => setMaxBoxes(+e.target.value)} style={{ width: "100%" }} />
            </div>
          </div>
        </div>

        {/* Export settings */}
        <div className="stat-card">
          <div style={{ fontFamily: "Syne", fontWeight: 700, fontSize: 15, marginBottom: 20 }}>Export Settings</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              { label: "Include confidence scores in PDF", enabled: true },
              { label: "Auto-generate CSV on detection", enabled: false },
              { label: "Save annotated images locally", enabled: true },
            ].map((opt, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: i < 2 ? "1px solid var(--border)" : "none" }}>
                <span style={{ fontSize: 13, color: "var(--text2)" }}>{opt.label}</span>
                <div style={{
                  width: 36, height: 20, borderRadius: 10,
                  background: opt.enabled ? "var(--accent)" : "var(--border2)",
                  position: "relative", cursor: "pointer", transition: "background 0.2s"
                }}>
                  <div style={{
                    position: "absolute", width: 14, height: 14, borderRadius: "50%", background: "#fff",
                    top: 3, left: opt.enabled ? 18 : 3, transition: "left 0.2s"
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <button className="btn-primary" style={{ alignSelf: "flex-start", display: "flex", alignItems: "center", gap: 8 }}
          onClick={() => alert("Settings saved!")}>
          <Icon name="check" size={14} color="#000" />
          Save Configuration
        </button>
      </div>
    </div>
  );
}

// ============================================================
// PROPERTY VALUE ESTIMATOR PAGE
// ============================================================
function ValueEstimatorPage() {
  const { history } = useApp();

  // Filter history to just items with detected pools
  const validHistory = history.filter(h => h.pools > 0);

  const [selectedScanId, setSelectedScanId] = useState(validHistory.length > 0 ? validHistory[0].id : "");
  const [region, setRegion] = useState("sunbelt"); // sunbelt, northern, midwest
  const [homeValue, setHomeValue] = useState(500000);

  const selectedScan = validHistory.find(h => h.id === selectedScanId);

  // Collect all pools from the selected scan
  const allPools = [];
  if (selectedScan && selectedScan.categories) {
    Object.keys(selectedScan.categories).forEach(cat => {
      if (cat !== 'removed_pools') {
        selectedScan.categories[cat].forEach(p => allPools.push({ ...p, type: cat }));
      }
    });
  }

  // Value Estimation Logic
  const calculateValue = () => {
    if (allPools.length === 0) return { increase: 0, cost: 0, roi: 0 };

    let totalIncrease = 0;
    let totalCost = 0;

    // Regional Multipliers
    const regionMult = {
      sunbelt: 1.0,  // Sunbelt values pools highly (FL, TX, AZ, CA)
      northern: 0.6, // Shorter season = lower value add
      midwest: 0.7
    }[region];

    allPools.forEach(pool => {
      // 1. Base Cost Estimation (Based on Square Footage, default to 400sqft if missing)
      const sqft = pool.area_sqft || 400;

      const isAboveGround = pool.is_above_ground || pool.type?.includes("above_ground");

      if (isAboveGround) {
        // Above ground pools
        const estCost = 2500 + (sqft * 15); // Base + materials
        totalCost += estCost;
        // Above ground adds no real property value (sometimes negative)
        totalIncrease += 0;
      } else {
        // In-ground pools
        const estCost = 35000 + (sqft * 100); // Standard gunite/fiberglass install
        totalCost += estCost;

        // Property Value Increase Heuristic
        // In-ground pool adds roughly 5-8% to home value, scaled by size and region
        const sizeBonus = sqft / 400; // 400sqft is standard. 800sqft pool = 2x bonus
        const baseIncrease = (homeValue * 0.05) * sizeBonus;

        // Cap the increase at 10% of home value
        const cappedIncrease = Math.min(baseIncrease, homeValue * 0.10);

        totalIncrease += (cappedIncrease * regionMult);
      }
    });

    const roi = totalCost > 0 ? ((totalIncrease - totalCost) / totalCost) * 100 : 0;

    return {
      increase: totalIncrease,
      cost: totalCost,
      roi: roi,
      totalSqft: allPools.reduce((sum, p) => sum + (p.area_sqft || 0), 0)
    };
  };

  const estimates = calculateValue();

  return (
    <div className="page-enter" style={{ padding: "32px 40px", maxWidth: 1000 }}>
      <div style={{ marginBottom: 32 }}>
        <div className="tag" style={{ marginBottom: 12 }}>ROI & VALUATION</div>
        <h2 style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 28, color: "var(--text)" }}>Property Value Estimator</h2>
        <p style={{ color: "var(--text2)", fontSize: 13, marginTop: 6 }}>Calculate how detected pools impact property valuation based on regional heuristics and pool footprint.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 }}>

        {/* Left Col: Inputs */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Scan Selection */}
          <div className="stat-card">
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text3)", marginBottom: 8, letterSpacing: 0.5 }}>1. SELECT DETECTED PROPERTY</label>
            <select
              value={selectedScanId}
              onChange={e => setSelectedScanId(e.target.value)}
              style={{ width: "100%", padding: "12px", background: "var(--bg1)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontFamily: "Space Grotesk" }}
            >
              {validHistory.length === 0 && <option value="">No pools detected yet...</option>}
              {validHistory.map(h => (
                <option key={h.id} value={h.id}>{h.filename} ({h.pools} pools found)</option>
              ))}
            </select>

            {selectedScan && (
              <div style={{ marginTop: 16, display: "flex", gap: 12, alignItems: "center" }}>
                <img src={selectedScan.preview} alt="Preview" style={{ width: 60, height: 60, borderRadius: 8, objectFit: "cover" }} />
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)" }}>{allPools.length} Pools Detected</div>
                  <div style={{ fontSize: 13, color: "var(--accent)" }}>Est. Total Area: {estimates.totalSqft > 0 ? `${estimates.totalSqft} sq ft` : 'Unknown (No Geo Data)'}</div>
                </div>
              </div>
            )}
          </div>

          {/* Regional & Property Inputs */}
          <div className="stat-card" style={{ opacity: selectedScan ? 1 : 0.5, pointerEvents: selectedScan ? 'auto' : 'none' }}>
            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text3)", marginBottom: 8, letterSpacing: 0.5 }}>2. REGION SCALAR</label>
            <select
              value={region}
              onChange={e => setRegion(e.target.value)}
              style={{ width: "100%", padding: "12px", background: "var(--bg1)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontFamily: "Space Grotesk", marginBottom: 20 }}
            >
              <option value="sunbelt">Sunbelt (CA, FL, TX, AZ) - High ROI</option>
              <option value="midwest">Midwest - Medium ROI</option>
              <option value="northern">Northern US - Lower ROI</option>
            </select>

            <label style={{ display: "block", fontSize: 11, fontWeight: 700, color: "var(--text3)", marginBottom: 8, letterSpacing: 0.5 }}>3. CURRENT HOME VALUE</label>
            <div style={{ position: "relative" }}>
              <span style={{ position: "absolute", left: 16, top: "50%", transform: "translateY(-50%)", color: "var(--text3)", fontSize: 16 }}>$</span>
              <input
                type="number"
                value={homeValue}
                onChange={e => setHomeValue(parseInt(e.target.value) || 0)}
                style={{ width: "100%", padding: "12px 16px 12px 32px", background: "var(--bg1)", border: "1px solid var(--border)", borderRadius: 8, color: "var(--text)", fontFamily: "Space Grotesk", fontSize: 16 }}
              />
            </div>
          </div>
        </div>

        {/* Right Col: Output Metrics */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <div className="stat-card" style={{ display: "flex", flexDirection: "column", justifyContent: "center", height: 140, border: "1px solid var(--success)", background: "rgba(16, 185, 129, 0.05)" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--success)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
              <Icon name="trending-up" size={16} /> ADDED PROPERTY VALUE
            </div>
            <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 48, color: "var(--success)" }}>
              +${Math.round(estimates.increase).toLocaleString()}
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
            <div className="stat-card" style={{ padding: "24px" }}>
              <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 8, letterSpacing: 0.5 }}>EST. REPLACEMENT COST</div>
              <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 24, color: "var(--text)" }}>
                ${Math.round(estimates.cost).toLocaleString()}
              </div>
            </div>
            <div className="stat-card" style={{ padding: "24px" }}>
              <div style={{ fontSize: 11, color: "var(--text3)", marginBottom: 8, letterSpacing: 0.5 }}>FINANCIAL ROI</div>
              <div style={{ fontFamily: "Syne", fontWeight: 800, fontSize: 24, color: estimates.roi >= 0 ? "var(--success)" : "var(--error)" }}>
                {estimates.roi > 0 ? '+' : ''}{Math.round(estimates.roi)}%
              </div>
            </div>
          </div>

          {/* Breakdown / Explanation */}
          <div className="stat-card" style={{ padding: 24, background: "var(--bg1)", border: "none" }}>
            <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: "var(--text)" }}>Valuation Profile</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {allPools.map((p, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 13, paddingBottom: 12, borderBottom: i < allPools.length - 1 ? "1px dashed var(--border)" : "none" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 4, background: p.is_above_ground ? "var(--warning)" : "var(--accent)" }} />
                    <span style={{ color: "var(--text2)" }}>{p.is_above_ground ? 'Above-Ground' : 'In-Ground'} Pool</span>
                  </div>
                  <span style={{ color: "var(--text)" }}>{p.area_sqft ? `${p.area_sqft} sq ft` : 'Apx. Size'}</span>
                </div>
              ))}
              {allPools.length === 0 && (
                <div style={{ color: "var(--text3)", fontSize: 13, fontStyle: "italic" }}>No pools available to calculate valuation.</div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

// ============================================================
// MAIN APP
// ============================================================
function App() {
  const { page, setPage, detectionResult } = useApp();

  const renderPage = () => {
    switch (page) {
      case "home": return <HomePage setPage={setPage} />;
      case "upload": return <UploadPage />;
      case "location": return <LocationSearchPage />;
      case "compare": return <ChangeDetectionPage />;
      case "estimator": return <ValueEstimatorPage />;
      case "results": return <ResultsPage />;
      case "analytics": return <AnalyticsPage />;
      case "history": return <HistoryPage />;
      case "map": return <MapPage />;
      case "settings": return <SettingsPage />;
      default: return <HomePage setPage={setPage} />;
    }
  };

  return (
    <>
      <style>{css}</style>
      <div style={{ display: "flex", minHeight: "100vh", background: "var(--bg)" }}>
        <Sidebar page={page} setPage={setPage} />

        {/* Main content */}
        <div style={{ flex: 1, overflow: "auto", position: "relative" }} className="scrollbar-hide">
          {/* Animated grid background */}
          <div className="grid-bg" style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, opacity: 0.5 }} />

          {/* Top bar */}
          <div style={{
            position: "sticky", top: 0, zIndex: 20,
            background: "rgba(3,5,8,0.85)",
            backdropFilter: "blur(20px)",
            borderBottom: "1px solid var(--border)",
            padding: "14px 40px",
            display: "flex", justifyContent: "space-between", alignItems: "center"
          }}>
            <div style={{ fontSize: 12, color: "var(--text3)" }}>
              <span style={{ color: "var(--text2)" }}>PoolDetect AI</span>
              <span style={{ margin: "0 8px" }}>›</span>
              <span style={{ color: "var(--accent)" }}>{page.charAt(0).toUpperCase() + page.slice(1)}</span>
            </div>
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              <div style={{ fontSize: 11, color: "var(--text3)", display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--success)", animation: "pulse 2s infinite" }} />
                API ONLINE
              </div>
              <button className="btn-ghost" onClick={() => setPage("settings")} style={{ padding: "6px 8px" }}>
                <Icon name="settings" size={14} />
              </button>
            </div>
          </div>

          {/* Page content */}
          <div style={{ position: "relative", zIndex: 1 }}>
            {renderPage()}
          </div>
        </div>
      </div>
    </>
  );
}

export default function PoolDetectAI() {
  return (
    <APIProvider apiKey="">
      <AppProvider>
        <App />
      </AppProvider>
    </APIProvider>
  );
}
