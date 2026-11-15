"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  Clock3,
  Radio,
  ShieldCheck,
  Wifi,
  RefreshCw,
  TrendingDown,
  TrendingUp,
  Minus,
  WifiOff,
  Database,
  CloudUpload,
  CheckCircle2,
  BadgeCheck,
  Gauge,
  Search,
  ExternalLink,
  History,
  RadioTower,
} from "lucide-react";

type Reading = {
  timestamp: string;
  heart_rate_bpm: number;
  spo2_percent: number;
  sleep_hours: number;
  exercise_minutes: number;
};

type HealthAlert = {
  id: string;
  severity: string;
  title: string;
  evidence: string;
  recommended_action: string;
  rule_id: string;
};

type MissionOverview = {
  mission: { name: string; mission_day: number; crew_member: string };
  latest: Reading;
  alert_count: number;
  status: string;
};

type QueuedPacket = {
  packet_id: string;
  queued_at: string;
  reading: Reading;
};

type TimelineEvent = {
  id: string;
  timestamp: string;
  category: "telemetry" | "alert" | "communications" | "sync";
  severity: string;
  title: string;
  description: string;
  source: string;
};

type TimelineResponse = {
  source: string;
  hours: number;
  events: TimelineEvent[];
  limitations: string;
};

type CachedDashboard = {
  overview: MissionOverview;
  readings: Reading[];
  alerts: HealthAlert[];
  baseline: BaselineSummary | null;
  healthAnalysis: HealthAnalysis | null;
  timelineEvents?: TimelineEvent[];
  updatedAt: string;
};

type QualityCheck = {
  id: string;
  label: string;
  status: string;
  detail: string;
};

type HealthAnalysis = {
  source: string;
  quality: {
    status: string;
    score: number;
    reading_count: number;
    summary: string;
    checks: QualityCheck[];
    limitations?: string;
  };
  trends: {
    status: string;
    metrics: Array<{
      metric: string;
      label: string;
      unit: string;
      reference_average: number;
      recent_average: number;
      difference: number;
      explanation: string;
    }>;
    limitations?: string;
  };
  interpretation: { status: string; message: string };
  safety_note: string;
};

type ResearchResult = {
  title: string;
  accession: string | null;
  description: string | null;
  release_date: string | null;
  organism: string | null;
  url: string;
};

type ResearchSearchResponse = {
  source: string;
  source_url: string;
  search_term: string;
  result_count: number;
  results: ResearchResult[];
  provenance_note: string;
};

type BaselineSummary = {
  source: string;
  status: string;
  metric?: string;
  reference_average?: number;
  recent_average?: number;
  difference?: number;
  trend_status?: string;
  reference_readings?: number;
  recent_readings?: number;
  explanation?: string;
  message?: string;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const TIME_RANGES = [6, 24, 72] as const;
const DASHBOARD_CACHE_KEY = "astra.dashboard-cache.v1";
const OUTBOX_KEY = "astra.telemetry-outbox.v1";
const LOCAL_TIMELINE_KEY = "astra.local-mission-events.v1";

function readOutbox(): QueuedPacket[] {
  try {
    const savedPackets = window.localStorage.getItem(OUTBOX_KEY);
    return savedPackets ? (JSON.parse(savedPackets) as QueuedPacket[]) : [];
  } catch {
    return [];
  }
}

function saveOutbox(packets: QueuedPacket[]) {
  window.localStorage.setItem(OUTBOX_KEY, JSON.stringify(packets));
}

function readLocalMissionEvents(): TimelineEvent[] {
  try {
    const savedEvents = window.localStorage.getItem(LOCAL_TIMELINE_KEY);
    return savedEvents ? (JSON.parse(savedEvents) as TimelineEvent[]) : [];
  } catch {
    return [];
  }
}

function formatTime(timestamp: string) {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function MissionDashboard() {
  const [overview, setOverview] = useState<MissionOverview | null>(null);
  const [readings, setReadings] = useState<Reading[]>([]);
  const [alerts, setAlerts] = useState<HealthAlert[]>([]);
  const [baseline, setBaseline] = useState<BaselineSummary | null>(null);
  const [healthAnalysis, setHealthAnalysis] = useState<HealthAnalysis | null>(null);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [localMissionEvents, setLocalMissionEvents] = useState<TimelineEvent[]>([]);
  const [selectedHours, setSelectedHours] = useState<number>(24);
  const [error, setError] = useState("");
  const [updatedAt, setUpdatedAt] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLinkPaused, setIsLinkPaused] = useState(false);
  const [isBrowserOnline, setIsBrowserOnline] = useState(true);
  const [pendingPackets, setPendingPackets] = useState(0);
  const [researchTerm, setResearchTerm] = useState("human spaceflight");
  const [researchResults, setResearchResults] = useState<ResearchSearchResponse | null>(null);
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchError, setResearchError] = useState("");
  const [syncMessage, setSyncMessage] = useState("No queued packets yet.");
  const latestReading = overview?.latest;

  const loadDashboard = useCallback(async (hours: number) => {
    if (isLinkPaused) {
      setError("Mission link is paused. Showing the last locally cached dashboard snapshot.");
      return;
    }

    if (typeof navigator !== "undefined" && !navigator.onLine) {
      setIsBrowserOnline(false);
      try {
        const cached = window.localStorage.getItem(DASHBOARD_CACHE_KEY);
        if (cached) {
          const snapshot = JSON.parse(cached) as CachedDashboard;
          setOverview(snapshot.overview);
          setReadings(snapshot.readings);
          setAlerts(snapshot.alerts);
          setBaseline(snapshot.baseline);
          setHealthAnalysis(snapshot.healthAnalysis ?? null);
          setTimelineEvents(snapshot.timelineEvents ?? []);
          setUpdatedAt(snapshot.updatedAt);
        }
      } catch {
        // A damaged cache should not prevent the dashboard from explaining its state.
      }
      setError("Browser is offline. Displaying cached data when available.");
      return;
    }

    setIsRefreshing(true);

    try {
      const [overviewResponse, telemetryResponse, alertsResponse, baselineResponse, analysisResponse, timelineResponse] =
        await Promise.all([
          fetch(`${API}/api/v1/mission/overview`, { cache: "no-store" }),
          fetch(`${API}/api/v1/telemetry?hours=${hours}`, { cache: "no-store" }),
          fetch(`${API}/api/v1/alerts`, { cache: "no-store" }),
          fetch(`${API}/api/v1/baseline?hours=${Math.max(hours, 6)}`, {
            cache: "no-store",
          }),
          fetch(`${API}/api/v1/health-analysis?hours=${hours}`, { cache: "no-store" }),
          fetch(`${API}/api/v1/mission/timeline?hours=${hours}`, { cache: "no-store" }),
        ]);

      const responses = [
        overviewResponse,
        telemetryResponse,
        alertsResponse,
        baselineResponse,
        analysisResponse,
        timelineResponse,
      ];
      if (responses.some((response) => !response.ok)) {
        throw new Error("One or more API requests failed.");
      }

      const [overviewData, telemetryData, alertData, baselineData, analysisData, timelineData] =
        await Promise.all(responses.map((response) => response.json()));

      setOverview(overviewData);
      setReadings(telemetryData.readings);
      setAlerts(alertData.alerts);
      setBaseline(baselineData);
      setHealthAnalysis(analysisData);
      setTimelineEvents((timelineData as TimelineResponse).events);
      const snapshot: CachedDashboard = {
        overview: overviewData,
        readings: telemetryData.readings,
        alerts: alertData.alerts,
        baseline: baselineData,
        healthAnalysis: analysisData,
        timelineEvents: (timelineData as TimelineResponse).events,
        updatedAt: new Date().toLocaleTimeString(),
      };
      setUpdatedAt(snapshot.updatedAt);
      try {
        window.localStorage.setItem(DASHBOARD_CACHE_KEY, JSON.stringify(snapshot));
      } catch {
        // The dashboard remains usable if browser storage is disabled or full.
      }
      setError("");
      setIsBrowserOnline(true);
    } catch {
      try {
        const cached = window.localStorage.getItem(DASHBOARD_CACHE_KEY);
        if (cached) {
          const snapshot = JSON.parse(cached) as CachedDashboard;
          setOverview(snapshot.overview);
          setReadings(snapshot.readings);
          setAlerts(snapshot.alerts);
          setBaseline(snapshot.baseline);
          setHealthAnalysis(snapshot.healthAnalysis ?? null);
          setTimelineEvents(snapshot.timelineEvents ?? []);
          setUpdatedAt(snapshot.updatedAt);
          setError("API unavailable. Showing the last cached snapshot; new packets can remain queued locally.");
        } else {
          setError(`Cannot reach the API at ${API}. No cached snapshot is available yet.`);
        }
      } catch {
        setError(`Cannot reach the API at ${API}. Browser cache could not be read.`);
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [isLinkPaused]);

  useEffect(() => {
    setIsBrowserOnline(navigator.onLine);
    setPendingPackets(readOutbox().length);
    setLocalMissionEvents(readLocalMissionEvents());

    const handleOnline = () => {
      setIsBrowserOnline(true);
      setError("");
      void loadDashboard(selectedHours);
    };
    const handleOffline = () => {
      setIsBrowserOnline(false);
      setError("Browser is offline. Displaying cached data when available.");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [loadDashboard, selectedHours]);

  useEffect(() => {
    void loadDashboard(selectedHours);
  }, [loadDashboard, selectedHours]);

  const searchResearch = useCallback(async (event?: { preventDefault: () => void }) => {
    event?.preventDefault();
    const term = researchTerm.trim();
    if (term.length < 2) {
      setResearchError("Enter at least two characters to search NASA OSDR.");
      return;
    }

    setResearchLoading(true);
    setResearchError("");
    try {
      const response = await fetch(
        `${API}/api/v1/research/osdr?term=${encodeURIComponent(term)}&limit=5`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        const detail = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(detail?.detail ?? `NASA OSDR search failed (${response.status}).`);
      }
      const result = await response.json() as ResearchSearchResponse;
      setResearchResults(result);
    } catch (searchError) {
      setResearchError(searchError instanceof Error ? searchError.message : "NASA OSDR search is unavailable.");
    } finally {
      setResearchLoading(false);
    }
  }, [researchTerm]);

  const recordLocalMissionEvent = useCallback((
    title: string,
    description: string,
    category: "communications" | "sync",
    severity = "info",
  ) => {
    const event: TimelineEvent = {
      id: `local-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      timestamp: new Date().toISOString(),
      category,
      severity,
      title,
      description,
      source: "Local browser demo event",
    };

    setLocalMissionEvents((currentEvents) => {
      const nextEvents = [event, ...currentEvents].slice(0, 30);
      try {
        window.localStorage.setItem(LOCAL_TIMELINE_KEY, JSON.stringify(nextEvents));
      } catch {
        // The event remains visible for this session even if storage is full.
      }
      return nextEvents;
    });
  }, []);

  const queueSamplePacket = useCallback(() => {
    const sampleReading: Reading = latestReading ?? {
      timestamp: new Date().toISOString(),
      heart_rate_bpm: 72,
      spo2_percent: 98,
      sleep_hours: 7.5,
      exercise_minutes: 30,
    };
    const packet: QueuedPacket = {
      packet_id: typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `astra-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      queued_at: new Date().toISOString(),
      reading: { ...sampleReading, timestamp: new Date().toISOString() },
    };

    const nextOutbox = [...readOutbox(), packet];
    try {
      saveOutbox(nextOutbox);
      setPendingPackets(nextOutbox.length);
      setSyncMessage(`Queued packet ${packet.packet_id.slice(0, 12)} locally.`);
      recordLocalMissionEvent("Telemetry packet queued", `Packet ${packet.packet_id.slice(0, 12)} was saved to the browser outbox.`, "communications");
    } catch {
      setSyncMessage("Browser storage is unavailable; this packet could not be queued.");
    }
  }, [latestReading, recordLocalMissionEvent]);

  const syncQueuedPackets = useCallback(async () => {
    const packetsToSync = readOutbox();
    if (!packetsToSync.length) {
      setSyncMessage("Nothing to synchronize. The local queue is empty.");
      return;
    }

    try {
      const response = await fetch(`${API}/api/v1/telemetry/sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ packets: packetsToSync }),
      });
      if (!response.ok) {
        throw new Error(`Sync request failed (${response.status}).`);
      }

      const result = await response.json() as { stored_count: number; duplicate_count: number };
      const syncedIds = new Set(packetsToSync.map((packet) => packet.packet_id));
      const remainingPackets = readOutbox().filter((packet) => !syncedIds.has(packet.packet_id));
      saveOutbox(remainingPackets);
      setPendingPackets(remainingPackets.length);
      setSyncMessage(`Sync complete: ${result.stored_count} stored, ${result.duplicate_count} duplicate retries safely ignored.`);
      recordLocalMissionEvent("Queued telemetry synchronized", `${result.stored_count} packet(s) stored; ${result.duplicate_count} duplicate retry(s) ignored.`, "sync");
    } catch {
      setSyncMessage("Sync failed. Packets remain in this browser's local queue for another attempt.");
      setPendingPackets(readOutbox().length);
      recordLocalMissionEvent("Telemetry synchronization failed", "Queued packets were retained locally for another attempt.", "sync", "warning");
    }
  }, [recordLocalMissionEvent]);

  const toggleMissionLink = useCallback(() => {
    if (isLinkPaused) {
      setIsLinkPaused(false);
      setSyncMessage("Mission link restored. Attempting to forward queued packets…");
      recordLocalMissionEvent("Simulated communications link restored", "ASTRA attempted to forward queued demonstration telemetry.", "communications");
      window.setTimeout(() => { void syncQueuedPackets(); }, 0);
    } else {
      setIsLinkPaused(true);
      setSyncMessage("Mission link paused. New demo packets will be stored in this browser.");
      recordLocalMissionEvent("Simulated communications outage", "The mission link was paused; queued demo packets remain in browser storage.", "communications", "warning");
    }
  }, [isLinkPaused, syncQueuedPackets, recordLocalMissionEvent]);

  const chartData = useMemo(
    () => readings.map((reading) => ({ ...reading, time: formatTime(reading.timestamp) })),
    [readings],
  );
  const baselineTrend = baseline?.trend_status;
  const visibleTimelineEvents = useMemo(
    () => [...timelineEvents, ...localMissionEvents]
      .sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime())
      .slice(0, 20),
    [timelineEvents, localMissionEvents],
  );

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Activity size={21} /></div>
          <div><strong>ASTRA</strong><span>MISSION HEALTH</span></div>
        </div>
        <div className="side-label">MISSION SYSTEMS</div>
        <div className="nav-item active"><Activity size={17} /> Mission overview</div>
        <div className="nav-item"><Radio size={17} /> Crew telemetry <span className="nav-soon">DEMO</span></div>
        <div className="nav-item"><AlertTriangle size={17} /> Health alerts</div>
        <div className="nav-item"><ShieldCheck size={17} /> Action protocols</div>
        <div className="sidebar-bottom">
          <span className="signal-dot" /> SIMULATION ENVIRONMENT<br />
          <span>Not for clinical use</span>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div><div className="eyebrow">FLIGHT OPERATIONS / CREW HEALTH</div><h1>Mission overview</h1></div>
          <div className="top-actions">
            <button className="refresh-button" onClick={() => void loadDashboard(selectedHours)} disabled={isRefreshing}>
              <RefreshCw size={13} className={isRefreshing ? "spinning" : ""} />
              {isRefreshing ? "UPDATING" : "REFRESH DATA"}
            </button>
            <div className="top-status"><span className={`pulse ${isLinkPaused || !isBrowserOnline || error ? "status-offline" : ""}`} /> {isLinkPaused ? "LINK PAUSED" : !isBrowserOnline ? "BROWSER OFFLINE" : error ? "API DEGRADED" : "SYSTEM ONLINE"} <span className="separator">/</span> SYNTHETIC DATA</div>
          </div>
        </header>

        {error && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}

        <section className="mission-strip">
          <div><span className="mini-label">MISSION</span><strong>{overview?.mission.name ?? "Astra Transit Simulation"}</strong></div>
          <div><span className="mini-label">MISSION ELAPSED</span><strong>DAY {overview?.mission.mission_day ?? 214}</strong></div>
          <div><span className="mini-label">CREW MEMBER</span><strong>{overview?.mission.crew_member ?? "Crew Member A"}</strong></div>
          <div><span className="mini-label">LINK STATUS</span><strong className="link-state">{isLinkPaused || !isBrowserOnline || error ? <WifiOff size={15} /> : <Wifi size={15} />} {isLinkPaused ? "PAUSED" : !isBrowserOnline ? "OFFLINE" : error ? "DEGRADED" : "LOCAL DEMO"}</strong></div>
        </section>

        <section className={`panel offline-panel ${isLinkPaused || !isBrowserOnline || error ? "offline-active" : ""}`}>
          <div className="offline-summary">
            <div className="offline-icon">{isLinkPaused || !isBrowserOnline || error ? <WifiOff size={19} /> : <Database size={19} />}</div>
            <div className="offline-copy">
              <span className="eyebrow">STORE-AND-FORWARD LINK</span>
              <h3>{isLinkPaused ? "Mission link paused" : !isBrowserOnline ? "Browser is offline" : error ? "API link unavailable" : "Mission link available"}</h3>
              <p>{isLinkPaused ? "The dashboard stops requesting live API data and keeps the last snapshot on this device." : "Dashboard snapshots are cached locally. Queue synthetic samples to demonstrate delayed delivery."}</p>
              <span className="sync-message" role="status">{syncMessage}</span>
            </div>
            <div className="outbox-count"><strong>{pendingPackets}</strong><span>QUEUED</span></div>
          </div>
          <div className="offline-actions">
            <button className="secondary-action" onClick={queueSamplePacket}><Database size={14} /> QUEUE DEMO SAMPLE</button>
            <button className="refresh-button" onClick={toggleMissionLink}><CloudUpload size={14} /> {isLinkPaused ? "RESTORE LINK & SYNC" : "SIMULATE LINK OUTAGE"}</button>
            {!isLinkPaused && pendingPackets > 0 && <button className="secondary-action" onClick={() => void syncQueuedPackets()}><CheckCircle2 size={14} /> SYNC QUEUE NOW</button>}
          </div>
          <div className="offline-disclaimer">Demo only: the browser outbox uses localStorage and the API writes synthetic packets to a local JSONL file. Do not enter real medical or astronaut data.</div>
        </section>

        <div className="section-heading">
          <div><span className="eyebrow">PHYSIOLOGICAL TELEMETRY</span><h2>Current crew snapshot</h2></div>
          <div className="updated"><Clock3 size={14} /> Updated {updatedAt || "waiting for API"}</div>
        </div>

        <section className="metrics">
          <Metric label="HEART RATE" value={latestReading ? latestReading.heart_rate_bpm.toFixed(1) : "—"} unit="bpm" detail="Trend compared below" icon={<Activity size={18} />} accent="blue" />
          <Metric label="BLOOD OXYGEN" value={latestReading ? latestReading.spo2_percent.toFixed(1) : "—"} unit="%" detail="Synthetic sensor reading" icon={<ShieldCheck size={18} />} accent="green" />
          <Metric label="SLEEP DURATION" value={latestReading ? latestReading.sleep_hours.toFixed(1) : "—"} unit="hrs" detail="Simulated 24-hour period" icon={<Clock3 size={18} />} accent="amber" />
          <Metric label="EXERCISE" value={latestReading ? String(latestReading.exercise_minutes) : "—"} unit="min" detail="Simulated daily activity" icon={<Activity size={18} />} accent="purple" />
        </section>

        <section className="main-grid">
          <div className="panel chart-panel">
            <div className="panel-head">
              <div><span className="eyebrow">TELEMETRY HISTORY</span><h3>Heart-rate trend</h3></div>
              <div className="range-switcher" aria-label="Chart time range">
                {TIME_RANGES.map((hours) => (
                  <button key={hours} className={selectedHours === hours ? "range-button selected" : "range-button"} onClick={() => setSelectedHours(hours)} aria-pressed={selectedHours === hours}>
                    {hours}h
                  </button>
                ))}
              </div>
            </div>
            <div className="chart-wrap">
              {chartData.length ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 12, right: 8, left: -18, bottom: 0 }}>
                    <defs><linearGradient id="hrFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#59b8ff" stopOpacity={0.28} /><stop offset="95%" stopColor="#59b8ff" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid stroke="#233448" strokeDasharray="3 5" vertical={false} />
                    <XAxis dataKey="time" tick={{ fill: "#71849a", fontSize: 11 }} axisLine={false} tickLine={false} minTickGap={28} />
                    <YAxis tick={{ fill: "#71849a", fontSize: 11 }} axisLine={false} tickLine={false} domain={["dataMin - 4", "dataMax + 4"]} />
                    <Tooltip contentStyle={{ background: "#101c2a", border: "1px solid #2b4056", borderRadius: 10, color: "#edf5ff" }} labelStyle={{ color: "#9eb1c5" }} />
                    <Area type="monotone" dataKey="heart_rate_bpm" name="Heart rate" stroke="#59b8ff" strokeWidth={2.5} fill="url(#hrFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <div className="empty-chart">Waiting for telemetry…</div>}
            </div>
            <div className="chart-foot"><span><i className="legend-dot" /> Synthetic telemetry</span><span>Illustrative trend — not a medical threshold</span></div>
          </div>

          <div className="panel baseline-panel">
            <div className="panel-head"><div><span className="eyebrow">EXPLAINABLE COMPARISON</span><h3>Demo baseline analysis</h3></div><span className="demo-tag">SIMULATED</span></div>
            {baseline?.status === "available" ? (
              <>
                <div className="baseline-stat-row">
                  <div><span>REFERENCE WINDOW</span><strong>{baseline.reference_average?.toFixed(1)} <small>bpm</small></strong></div>
                  <div><span>RECENT WINDOW</span><strong>{baseline.recent_average?.toFixed(1)} <small>bpm</small></strong></div>
                </div>
                <div className={`trend-result ${baselineTrend ?? "similar"}`}>
                  {baselineTrend === "increased" ? <TrendingUp size={18} /> : baselineTrend === "decreased" ? <TrendingDown size={18} /> : <Minus size={18} />}
                  <div><strong>{baselineTrend === "increased" ? "Recent average increased" : baselineTrend === "decreased" ? "Recent average decreased" : "Recent average is similar"}</strong><span>{baseline.difference !== undefined && baseline.difference > 0 ? "+" : ""}{baseline.difference?.toFixed(1)} bpm versus the reference window</span></div>
                </div>
                <p className="baseline-explanation">{baseline.explanation}</p>
                <div className="sample-count">{baseline.reference_readings} reference samples · {baseline.recent_readings} recent samples</div>
              </>
            ) : <p className="baseline-explanation">{baseline?.message ?? "Waiting for baseline comparison…"}</p>}
            <div className="baseline-warning"><ShieldCheck size={15} /> Not a clinical baseline or medical assessment.</div>
          </div>
        </section>

        <section className="panel quality-panel">
          <div className="panel-head">
            <div><span className="eyebrow">DATA QUALITY + TREND ENGINE</span><h3>Analysis integrity</h3></div>
            <span className={`quality-score ${healthAnalysis?.quality.status ?? "pending"}`}>
              <Gauge size={14} /> {healthAnalysis ? `${healthAnalysis.quality.score}/100` : "WAITING"}
            </span>
          </div>
          {healthAnalysis ? (
            <>
              <div className="quality-summary-row">
                <div>
                  <strong>{healthAnalysis.quality.status.replaceAll("_", " ").toUpperCase()}</strong>
                  <p>{healthAnalysis.quality.summary}</p>
                </div>
                <span className="sample-count">{healthAnalysis.quality.reading_count} samples checked</span>
              </div>
              <div className="quality-check-grid">
                {healthAnalysis.quality.checks.map((check) => (
                  <div className="quality-check" key={check.id}>
                    <span className={`quality-check-icon ${check.status}`}><BadgeCheck size={15} /></span>
                    <div><strong>{check.label}</strong><span>{check.detail}</span></div>
                    <small className={check.status}>{check.status.toUpperCase()}</small>
                  </div>
                ))}
              </div>
              <div className="trend-table-wrap">
                <div className="trend-table-heading"><strong>Descriptive trend comparison</strong><span>Recent mean − reference mean</span></div>
                {healthAnalysis.trends.metrics.map((metric) => (
                  <div className="trend-metric-row" key={metric.metric}>
                    <span>{metric.label}</span>
                    <span>{metric.reference_average.toFixed(1)} → {metric.recent_average.toFixed(1)} <small>{metric.unit}</small></span>
                    <strong className={metric.difference > 0 ? "positive-change" : metric.difference < 0 ? "negative-change" : "neutral-change"}>
                      {metric.difference > 0 ? "+" : ""}{metric.difference.toFixed(1)} {metric.unit}
                    </strong>
                  </div>
                ))}
              </div>
              <div className="quality-disclaimer"><ShieldCheck size={15} /> {healthAnalysis.safety_note}</div>
            </>
          ) : <p className="baseline-explanation">Waiting for data-quality analysis…</p>}
        </section>

        <section className="panel alert-panel standalone-alerts">
          <div className="panel-head"><div><span className="eyebrow">RULE-BASED MONITORING</span><h3>Health observations</h3></div><span className="count-pill">{alerts.length} ACTIVE</span></div>
          <div className="alerts-list">{alerts.length ? alerts.map((alert) => (
            <article className="alert-item" key={alert.id}>
              <div className={`alert-icon ${alert.severity}`}><AlertTriangle size={17} /></div>
              <div className="alert-copy"><div className="alert-title-row"><strong>{alert.title}</strong><span className={`severity ${alert.severity}`}>{alert.severity}</span></div><p>{alert.evidence}</p><div className="action-copy"><b>NEXT STEP</b> {alert.recommended_action}</div><span className="rule-id">{alert.rule_id}</span></div>
            </article>
          )) : <div className="no-alerts">No prototype rules triggered.</div>}</div>
        </section>

        <section className="panel mission-timeline-panel">
          <div className="panel-head">
            <div><span className="eyebrow">MISSION EVENT LOG</span><h3>Mission event timeline</h3></div>
            <span className="demo-tag">LATEST {visibleTimelineEvents.length}</span>
          </div>
          <p className="timeline-intro">A chronological view of synthetic telemetry checkpoints and rule observations, combined with local communications and synchronization actions from this browser.</p>
          {visibleTimelineEvents.length ? (
            <div className="mission-timeline" aria-live="polite">
              {visibleTimelineEvents.map((event) => (
                <article className={`timeline-event ${event.category} ${event.severity}`} key={event.id}>
                  <div className="timeline-marker">
                    {event.category === "alert" ? <AlertTriangle size={15} />
                      : event.category === "communications" ? <RadioTower size={15} />
                      : event.category === "sync" ? <CloudUpload size={15} />
                      : <Activity size={15} />}
                  </div>
                  <div className="timeline-event-copy">
                    <div className="timeline-event-heading"><strong>{event.title}</strong><time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}</time></div>
                    <p>{event.description}</p>
                    <span className="timeline-source">{event.source}</span>
                  </div>
                  <span className={`timeline-category ${event.category}`}>{event.category}</span>
                </article>
              ))}
            </div>
          ) : <div className="research-empty">Waiting for mission events…</div>}
          <div className="timeline-disclaimer"><History size={14} /> Synthetic telemetry entries are generated for demonstration. Communications and sync entries are recorded locally in this browser and are not a real spacecraft event log.</div>
        </section>

        <section className="bottom-grid">
          <div className="panel"><div className="panel-head"><div><span className="eyebrow">SYSTEM INTEGRITY</span><h3>Data pipeline</h3></div><span className="ok-pill"><span className="pulse" /> DEMO</span></div>
            <Pipeline icon={<Radio size={17} />} title="Telemetry generator" desc="Deterministic synthetic data" />
            <Pipeline icon={<Activity size={17} />} title="Health rules engine" desc="Explainable trend checks" />
            <Pipeline icon={<Wifi size={17} />} title="Frontend connection" desc="REST API · local network" status={error ? "OFFLINE" : "CONNECTED"} />
          </div>
          <div className="panel mission-note"><span className="eyebrow">DESIGN PRINCIPLE</span><h3>Explain changes. Preserve context.</h3><p>ASTRA surfaces descriptive trends, their supporting evidence, data-quality checks, and connectivity state. It does not diagnose, estimate medical risk, or replace approved crew-health procedures.</p><div className="note-footer"><ShieldCheck size={16} /> Human review remains essential</div></div>
        </section>

        <section className="panel research-panel">
          <div className="panel-head"><div><span className="eyebrow">NASA DATA DISCOVERY / LIVE METADATA SEARCH</span><h3>Open Science Data Repository</h3></div><span className="demo-tag">NASA OSDR API</span></div>
          <p className="research-intro">Search NASA OSDR's public study metadata from ASTRA. This is a real read-only catalog lookup; it does not download study measurements or feed research data into the synthetic crew dashboard.</p>
          <form className="research-search-form" onSubmit={(event) => void searchResearch(event)}>
            <label className="research-search-label" htmlFor="research-term">SEARCH STUDIES</label>
            <div className="research-search-controls">
              <input id="research-term" value={researchTerm} onChange={(event) => setResearchTerm(event.target.value)} maxLength={100} minLength={2} placeholder="e.g. human spaceflight" />
              <button className="refresh-button" type="submit" disabled={researchLoading}><Search size={14} /> {researchLoading ? "SEARCHING NASA…" : "SEARCH NASA OSDR"}</button>
            </div>
          </form>
          {researchError && <div className="research-error" role="alert">{researchError} You can still open the NASA OSDR portal below.</div>}
          {researchResults && (
            <div className="research-results" aria-live="polite">
              <div className="research-results-heading"><strong>{researchResults.result_count} result{researchResults.result_count === 1 ? "" : "s"}</strong><span>Search: “{researchResults.search_term}” · NASA OSDR metadata</span></div>
              {researchResults.results.length ? researchResults.results.map((result, index) => (
                <article className="research-result" key={`${result.accession ?? result.title}-${index}`}>
                  <div className="research-result-main"><strong>{result.title}</strong><span>{[result.accession, result.organism, result.release_date].filter(Boolean).join(" · ") || "Study metadata record"}</span>{result.description && <p>{result.description}</p>}</div>
                  <a className="research-result-link" href={result.url} target="_blank" rel="noreferrer" aria-label={`Open ${result.title} on NASA OSDR`}><ExternalLink size={14} /> OPEN RECORD</a>
                </article>
              )) : <p className="research-empty">No records were returned for this term. Try a broader search.</p>}
              <p className="research-disclaimer">{researchResults.provenance_note}</p>
            </div>
          )}
          <div className="research-links">
            <a href="https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=resources" target="_blank" rel="noreferrer"><strong>Challenge resources</strong><span>Challenge statement and linked support materials</span></a>
            <a href="https://osdr.nasa.gov/" target="_blank" rel="noreferrer"><strong>NASA OSDR portal</strong><span>Browse public space-life-sciences datasets</span></a>
            <a href="https://www.nasa.gov/hrp/" target="_blank" rel="noreferrer"><strong>NASA Human Research Program</strong><span>Background on human-spaceflight health risks</span></a>
            <a href="https://nlsp.nasa.gov/" target="_blank" rel="noreferrer"><strong>NASA Life Sciences Portal</strong><span>Human spaceflight life-sciences studies and resources</span></a>
          </div>
          <div className="research-disclaimer">Data provenance: ASTRA v0.6 searches live NASA OSDR study metadata when requested. The dashboard's crew readings and alerts remain synthetic; no NASA measurements are used as telemetry or clinical thresholds.</div>
        </section>
        <footer>ASTRA / SPACE APPS CHALLENGE 2026 <span>PROTOTYPE BUILD 0.7.0</span><span>SYNTHETIC DATA · NOT FOR CLINICAL USE</span></footer>
      </section>
    </main>
  );
}

function Metric({ label, value, unit, detail, icon, accent }: { label: string; value: string; unit: string; detail: string; icon: React.ReactNode; accent: string }) {
  return <article className="metric-card"><div className="metric-top"><span>{label}</span><span className={`metric-icon ${accent}`}>{icon}</span></div><div className="metric-value">{value}<small>{unit}</small></div><div className="metric-detail"><span className={`tiny-dot ${accent}`} />{detail}</div></article>;
}

function Pipeline({ icon, title, desc, status = "READY" }: { icon: React.ReactNode; title: string; desc: string; status?: string }) {
  return <div className="pipeline-row"><span className="pipeline-icon">{icon}</span><div><strong>{title}</strong><span>{desc}</span></div><span className="state-tag">{status}</span></div>;
}
