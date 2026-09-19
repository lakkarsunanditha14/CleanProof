import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, Tooltip as MapTooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LabelList, Legend, ReferenceLine,
} from 'recharts';
import { FileText, CheckCircle2, ShieldAlert, Scale, RefreshCw, AlertCircle, Flame, Info } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import { WARDS, categoryLabel } from '../constants';
import { fetchApi, imageUrl, isSamplePhoto } from '../api';

const GREEN = '#0F6E5C';
const AMBER = '#C77700';
const RED = '#B42318';
const INK = '#475569';
const GRID = '#E2E8F0';
const TARGET = 80; // on-time target used for the reference line and hotspot flag

// One state per complaint, shown on the map. Worst state wins.
function pointState(p) {
  if (p.verdict === 'LIKELY FAKE' || p.verdict === 'SUSPICIOUS') return { key: 'flagged', color: RED, label: 'Closure flagged' };
  if (p.sla_status === 'Breached') return { key: 'breached', color: AMBER, label: 'Deadline missed' };
  if (p.status === 'RESOLVED') return { key: 'verified', color: GREEN, label: 'Verified closure' };
  return { key: 'open', color: '#2563EB', label: 'Open, on time' };
}

// Short chart labels; the tooltip shows the full reason.
const SHORT_REASON = {
  'Vehicle or staff shortage': 'No vehicle / staff',
  'Heavy rain or waterlogging': 'Rain / waterlogging',
  'Access blocked (traffic, parked vehicles, event)': 'Access blocked',
  'Needed special equipment (JCB, tractor, suction machine)': 'Special equipment',
  'Waste much larger than reported': 'Larger than reported',
  Other: 'Other',
};

const LEGEND = [
  { color: '#2563EB', label: 'Open, on time' },
  { color: GREEN, label: 'Verified closure' },
  { color: AMBER, label: 'Deadline missed' },
  { color: RED, label: 'Closure flagged' },
];

function Kpi({ icon: Icon, label, value, note, color }) {
  return (
    <Card hover padding="p-5">
      <div className="flex items-center justify-between text-slate-500 mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <div className="text-3xl font-extrabold tracking-tight text-slate-900">{value}</div>
      <p className="text-xs text-slate-500 mt-1.5">{note}</p>
    </Card>
  );
}

function ChartCard({ title, subtitle, children, height = 300, empty }) {
  return (
    <Card hover className="space-y-4">
      <div>
        <h3 className="font-bold text-slate-900">{title}</h3>
        {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      {empty ? (
        <div style={{ height }} className="flex items-center justify-center rounded-xl border border-dashed border-slate-200 text-sm text-slate-500 text-center px-6">
          {empty}
        </div>
      ) : (
        <div style={{ height }}>{children}</div>
      )}
    </Card>
  );
}

// Headless Edge (offline snapshot, scripts/public_link.py) never finishes chart animations
const ANIMATE = !/Headless/.test(navigator.userAgent);
const axisProps = { tick: { fill: INK, fontSize: 12 }, axisLine: false, tickLine: false };
const tooltipProps = {
  cursor: { fill: 'rgba(15,110,92,0.06)' },
  contentStyle: { borderRadius: 12, border: '1px solid #E2E8F0', boxShadow: '0 4px 12px rgba(15,23,42,0.08)', fontSize: 13 },
};

export default function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showPoints, setShowPoints] = useState(true);
  const [showHotspots, setShowHotspots] = useState(true);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [stats, wards, categories, points, delays] = await Promise.all([
        fetchApi('/api/dashboard/stats'),
        fetchApi('/api/dashboard/sla-by-ward'),
        fetchApi('/api/dashboard/sla-by-category'),
        fetchApi('/api/dashboard/map-data'),
        fetchApi('/api/dashboard/delay-reasons'),
      ]);
      setData({ stats, wards, categories, points, delays });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const derived = useMemo(() => {
    if (!data) return null;
    const centre = Object.fromEntries(WARDS.map((w) => [w.name, [w.lat, w.lng]]));
    const wards = data.wards.filter((w) => w.total > 0).map((w) => ({
      ...w,
      centre: centre[w.ward],
      hotspot: w.adherence_percent < 50 || w.false_closures >= 8,
    }));
    return {
      wards,
      byAdherence: [...wards].sort((a, b) => a.adherence_percent - b.adherence_percent),
      byFalse: [...wards].sort((a, b) => b.false_closures - a.false_closures),
      categories: data.categories.map((c) => ({ ...c, name: `${categoryLabel(c.category)} (${c.sla_hours}h)` })),
      maxFalse: Math.max(1, ...wards.map((w) => w.false_closures)),
      synthetic: data.points.filter((p) => isSamplePhoto(p.before_image_path)).length,
      // Fit the map to every complaint (e.g. Narsapur is ~45 km outside Hyderabad)
      bounds: [
        [Math.min(...data.points.map((p) => p.latitude)), Math.min(...data.points.map((p) => p.longitude))],
        [Math.max(...data.points.map((p) => p.latitude)), Math.max(...data.points.map((p) => p.longitude))],
      ],
      delays: data.delays.map((d) => ({ ...d, label: SHORT_REASON[d.reason] || d.reason })),
    };
  }, [data]);

  return (
    <div className="space-y-8">
      <PageHeader title="Accountability dashboard" subtitle="Real deadline performance and verified closures by ward, instead of self-reported numbers.">
        <Button variant="outline" icon={RefreshCw} onClick={load}>Refresh</Button>
      </PageHeader>

      {loading && !data && <Card className="flex justify-center py-20"><Spinner size="lg" /></Card>}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-[#B42318]">
          <AlertCircle className="w-5 h-5 shrink-0" /> {error}
        </div>
      )}

      {data && derived && (
        <>
          {derived.synthetic > 0 && (
          <div className="flex items-start gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-slate-700">
            <Info className="w-5 h-5 shrink-0 text-sky-700 mt-0.5" />
            <p>
              <span className="font-semibold text-slate-900">Demo data: </span>
              {derived.synthetic} of these {data.stats.total_complaints} complaints are <b>synthetic history</b> generated to show
              how the dashboard works with a city's data (the problem statement asks for synthetic data only).
              The other {data.stats.total_complaints - derived.synthetic} are live complaints with real photos, including anything
              reported during this demo.
            </p>
          </div>
          )}

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Kpi icon={FileText} label="Complaints" value={data.stats.total_complaints} note={`${data.stats.active_complaints} open, ${data.stats.resolved_complaints} closed`} color={INK} />
            <Kpi icon={CheckCircle2} label="On time" value={`${data.stats.sla_adherence_percent}%`} note={`${data.stats.total_breached} missed the deadline`} color={GREEN} />
            <Kpi icon={ShieldAlert} label="Suspected fake closures" value={data.stats.false_closures_count} note="Flagged and not cleared by a reviewer" color={RED} />
            <Kpi icon={Scale} label="Waiting for review" value={data.stats.flagged_pending_review_count} note={<Link to="/review" className="text-[#0F6E5C] font-semibold hover:underline">Open review queue</Link>} color={AMBER} />
          </div>

          <Card className="space-y-4">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
              <div>
                <h3 className="font-bold text-slate-900">Complaint map</h3>
                <p className="text-sm text-slate-500 mt-0.5">Red circles are fake-closure hotspots. Bigger circle, more suspected fake closures in that ward.</p>
              </div>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={showPoints} onChange={(e) => setShowPoints(e.target.checked)} className="accent-[#0F6E5C] w-4 h-4" />
                  Complaints
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={showHotspots} onChange={(e) => setShowHotspots(e.target.checked)} className="accent-[#B42318] w-4 h-4" />
                  Hotspots
                </label>
              </div>
            </div>
            <div className="isolate rounded-xl overflow-hidden border border-slate-200" style={{ height: 480 }}>
              <MapContainer bounds={derived.bounds} boundsOptions={{ padding: [30, 30] }} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                {showHotspots && derived.wards.filter((w) => w.false_closures > 0).map((w) => (
                  <Circle
                    key={w.ward}
                    center={w.centre}
                    radius={400 + (w.false_closures / derived.maxFalse) * 1600}
                    pathOptions={{ color: RED, weight: 1.5, fillColor: RED, fillOpacity: 0.12 + (w.false_closures / derived.maxFalse) * 0.18 }}
                  >
                    <MapTooltip direction="top" sticky>
                      <b>{w.ward}</b>: {w.false_closures} suspected fake closures, {w.adherence_percent}% on time
                    </MapTooltip>
                  </Circle>
                ))}
                {showPoints && data.points.map((p) => {
                  const s = pointState(p);
                  return (
                    <CircleMarker
                      key={p.id}
                      center={[p.latitude, p.longitude]}
                      radius={imageUrl(p.before_image_path) ? 8 : 5}
                      pathOptions={{ color: '#ffffff', weight: 1.5, fillColor: s.color, fillOpacity: 0.9 }}
                    >
                      <Popup>
                        <div className="space-y-1 min-w-48">
                          <p className="font-bold">#{p.id} {p.title}</p>
                          <p>{p.ward} &middot; {categoryLabel(p.category)}</p>
                          <p>Status: {p.status} &middot; {p.sla_status}</p>
                          {p.verdict && <p>Verdict: {p.verdict} ({p.score}/100)</p>}
                          <Link to={`/track?id=${p.id}`}>Open complaint</Link>
                        </div>
                      </Popup>
                    </CircleMarker>
                  );
                })}
              </MapContainer>
            </div>
            <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-600">
              {LEGEND.map((l) => (
                <span key={l.label} className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full border-2 border-white shadow" style={{ background: l.color }} /> {l.label}
                </span>
              ))}
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 rounded-full border" style={{ borderColor: RED, background: 'rgba(180,35,24,0.18)' }} /> Fake-closure hotspot
              </span>
            </div>
          </Card>

          <div className="grid lg:grid-cols-2 gap-6">
            <ChartCard title="On time by ward" subtitle={`Share of complaints handled within the deadline. Dashed line = ${TARGET}% target.`}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={derived.byAdherence} layout="vertical" margin={{ top: 4, right: 48, left: 8, bottom: 4 }}>
                  <CartesianGrid horizontal={false} stroke={GRID} />
                  <XAxis type="number" domain={[0, 100]} unit="%" {...axisProps} />
                  <YAxis type="category" dataKey="ward" width={96} {...axisProps} />
                  <Tooltip {...tooltipProps} formatter={(v) => [`${v}%`, 'On time']} />
                  <ReferenceLine x={TARGET} stroke={INK} strokeDasharray="4 4" />
                  <Bar isAnimationActive={ANIMATE} dataKey="adherence_percent" fill={GREEN} radius={[0, 4, 4, 0]} barSize={18}>
                    <LabelList dataKey="adherence_percent" position="right" formatter={(v) => `${v}%`} style={{ fill: INK, fontSize: 12, fontWeight: 600 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Suspected fake closures by ward" subtitle="Closures flagged by verification and not cleared by a reviewer."
            empty={derived.byFalse.every((w) => w.false_closures === 0) && 'No suspected fake closures yet. Upload a fake after photo on the Worker page to see it appear here.'}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={derived.byFalse} layout="vertical" margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
                  <CartesianGrid horizontal={false} stroke={GRID} />
                  <XAxis type="number" allowDecimals={false} {...axisProps} />
                  <YAxis type="category" dataKey="ward" width={96} {...axisProps} />
                  <Tooltip {...tooltipProps} formatter={(v) => [v, 'Suspected fake closures']} />
                  <Bar isAnimationActive={ANIMATE} dataKey="false_closures" fill={RED} radius={[0, 4, 4, 0]} barSize={18}>
                    <LabelList dataKey="false_closures" position="right" style={{ fill: INK, fontSize: 12, fontWeight: 600 }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
          <ChartCard title="Deadlines by category" subtitle="Official SBM-U 2.0 deadline in brackets." height={280}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={derived.categories} margin={{ top: 8, right: 8, left: -12, bottom: 4 }} barGap={2}>
                <CartesianGrid vertical={false} stroke={GRID} />
                <XAxis dataKey="name" {...axisProps} />
                <YAxis allowDecimals={false} {...axisProps} />
                <Tooltip {...tooltipProps} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 13, color: INK }} />
                <Bar isAnimationActive={ANIMATE} dataKey="on_time" name="On time" stackId="a" fill={GREEN} stroke="#fff" strokeWidth={2} barSize={44} />
                <Bar isAnimationActive={ANIMATE} dataKey="breached" name="Missed deadline" stackId="a" fill={AMBER} stroke="#fff" strokeWidth={2} radius={[4, 4, 0, 0]} barSize={44} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="Why deadlines were missed" subtitle="Reason the worker gave when closing a complaint after its deadline." height={280}
            empty={derived.delays.every((d) => d.count === 0) && 'No complaints closed late yet. Resolve an overdue complaint with a delay reason to see it here.'}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={derived.delays} layout="vertical" margin={{ top: 4, right: 36, left: 8, bottom: 4 }}>
                <CartesianGrid horizontal={false} stroke={GRID} />
                <XAxis type="number" allowDecimals={false} {...axisProps} />
                <YAxis type="category" dataKey="label" width={170} {...axisProps} />
                <Tooltip {...tooltipProps} formatter={(v) => [v, 'Late closures']} labelFormatter={(_, p) => p?.[0]?.payload.reason} />
                <Bar isAnimationActive={ANIMATE} dataKey="count" fill={AMBER} radius={[0, 4, 4, 0]} barSize={16}>
                  <LabelList dataKey="count" position="right" style={{ fill: INK, fontSize: 12, fontWeight: 600 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
          </div>

          <Card padding="p-0" className="overflow-hidden">
            <div className="p-6 pb-4">
              <h3 className="font-bold text-slate-900">Ward accountability table</h3>
              <p className="text-sm text-slate-500 mt-0.5">Worst on-time performance first. Hotspot = under 50% on time or 8+ suspected fake closures.</p>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="text-left font-semibold px-6 py-3">Ward</th>
                    <th className="text-right font-semibold px-4 py-3">Complaints</th>
                    <th className="text-right font-semibold px-4 py-3">On time</th>
                    <th className="text-right font-semibold px-4 py-3">Closed late</th>
                    <th className="text-right font-semibold px-4 py-3">Overdue now</th>
                    <th className="text-right font-semibold px-4 py-3">Suspected fake</th>
                    <th className="text-left font-semibold px-6 py-3">Flag</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {derived.byAdherence.map((w) => (
                    <tr key={w.ward} className={w.hotspot ? 'bg-rose-50/40' : ''}>
                      <td className="px-6 py-3 font-semibold text-slate-900">{w.ward}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{w.total}</td>
                      <td className="px-4 py-3 text-right tabular-nums font-semibold">{w.adherence_percent}%</td>
                      <td className="px-4 py-3 text-right tabular-nums">{w.closed_late}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{w.overdue_open}</td>
                      <td className="px-4 py-3 text-right tabular-nums">{w.false_closures}</td>
                      <td className="px-6 py-3">
                        {w.hotspot ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-[#B42318] border border-rose-200">
                            <Flame className="w-3.5 h-3.5" /> Hotspot
                          </span>
                        ) : (
                          <span className="text-slate-400 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
