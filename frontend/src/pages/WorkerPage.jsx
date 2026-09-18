import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Camera, MapPin, X, ShieldCheck, AlertCircle, RefreshCw, ArrowRight, Clock, Upload, Radio } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import StatusBadge from '../components/StatusBadge';
import SlaBadge from '../components/SlaBadge';
import VerdictBadge from '../components/VerdictBadge';
import EmptyState from '../components/EmptyState';
import CameraCapture from '../components/CameraCapture';
import { ReasonList, ScoreHeader, Photo, CategoryArt, SampleTag, PhotoEvidence } from '../components/Verification';
import { WARDS, DELAY_REASONS, categoryLabel, wardLabel } from '../constants';
import { fetchApi, imageUrl, isSamplePhoto, parseUtc, formatHours, formatDateTime } from '../api';

const TABS = [
  { key: 'due', label: 'Due' },
  { key: 'overdue', label: 'Overdue' },
  { key: 'closed', label: 'Closed' },
];

function hoursLeft(c) {
  return (parseUtc(c.sla_deadline) - Date.now()) / 3600000;
}

function ResolvePanel({ complaint, onClose, onResolved }) {
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [delayReason, setDelayReason] = useState('');
  const [delayNote, setDelayNote] = useState('');
  const [cameraOpen, setCameraOpen] = useState(false);
  const [live, setLive] = useState(null); // { lat, lng } when taken with the in-app camera
  const overdueBy = -hoursLeft(complaint); // positive when past the deadline

  function handlePhoto(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    setPreview(URL.createObjectURL(file));
    setLive(null);
  }

  function handleCapture({ file, url, lat, lng }) {
    setPhoto(file);
    setPreview(url);
    setLive({ lat, lng });
    setCameraOpen(false);
  }

  function clearPhoto() {
    setPhoto(null);
    setPreview(null);
    setLive(null);
  }

  async function submit() {
    if (!photo) return setError('Add the after photo first.');
    if (overdueBy > 0 && !delayReason) return setError('This is past the deadline. Choose a reason for the delay.');
    if (delayReason === 'Other' && !delayNote.trim()) return setError('Describe the delay when the reason is "Other".');
    setError('');
    setSubmitting(true);
    const form = new FormData();
    form.append('photo', photo);
    if (live) {
      form.append('capture_mode', 'live');
      if (live.lat != null) {
        form.append('latitude', live.lat);
        form.append('longitude', live.lng);
      }
    }
    if (overdueBy > 0) {
      form.append('delay_reason', delayReason);
      if (delayNote.trim()) form.append('delay_note', delayNote.trim());
    }
    try {
      const res = await fetchApi(`/api/complaints/${complaint.id}/resolve`, { method: 'POST', body: form });
      setResult(res);
      onResolved();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[1000] bg-slate-900/50 backdrop-blur-sm flex items-start md:items-center justify-center p-4 overflow-y-auto" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl my-8" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-4 p-6 border-b border-slate-200">
          <div>
            <p className="text-sm font-semibold text-slate-500">Complaint #{complaint.id}</p>
            <h2 className="text-xl font-bold text-slate-900">{complaint.title}</h2>
            <p className="text-sm text-slate-600 flex items-center gap-1.5 mt-1">
              <MapPin className="w-4 h-4" /> {complaint.ward} &middot; {categoryLabel(complaint.category)}
            </p>
          </div>
          <button type="button" onClick={onClose} className="p-2 rounded-xl text-slate-500 hover:bg-slate-100" aria-label="Close">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="grid sm:grid-cols-2 gap-5">
            <Photo label="Before (citizen)" path={complaint.before_image_path} tone="amber" category={complaint.category} />
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">After (your photo)</p>
              {cameraOpen ? (
                <CameraCapture onCapture={handleCapture} onCancel={() => setCameraOpen(false)} stampLabel={`Complaint #${complaint.id} | ${complaint.ward}`} />
              ) : preview ? (
                <div className="space-y-2">
                  <div className="relative">
                    <img src={preview} alt="After" className="w-full aspect-[4/3] object-cover rounded-xl border-2 border-emerald-200" />
                    <span className={`absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${live ? 'bg-[#0F6E5C] text-white' : 'bg-white/90 text-slate-600'}`}>
                      {live ? <><Radio className="w-3 h-3" /> LIVE CAPTURE</> : <><Upload className="w-3 h-3" /> UPLOADED FILE</>}
                    </span>
                  </div>
                  {!result && (
                    <button type="button" onClick={clearPhoto} className="text-sm font-semibold text-[#0F6E5C] hover:underline">
                      Retake / choose again
                    </button>
                  )}
                </div>
              ) : (
                <div className="w-full aspect-[4/3] rounded-xl border-2 border-dashed border-slate-300 flex flex-col items-center justify-center gap-3 text-center px-6">
                  <Camera className="w-9 h-9 text-slate-400" />
                  <p className="text-xs text-slate-500">Take the photo at the site, after the clean-up. The in-app camera cannot pick old photos from the gallery.</p>
                  <Button icon={Camera} onClick={() => setCameraOpen(true)}>Take live photo</Button>
                  <label className="text-xs font-semibold text-slate-500 hover:text-slate-800 cursor-pointer underline underline-offset-2">
                    <input type="file" accept="image/*" onChange={handlePhoto} className="sr-only" />
                    Upload a file instead (demo only)
                  </label>
                </div>
              )}
            </div>
          </div>

          {overdueBy > 0 && !result && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3">
              <p className="text-sm font-semibold text-[#C77700] flex items-center gap-2">
                <Clock className="w-4 h-4" /> Past the deadline by {formatHours(overdueBy)}. A reason is required.
              </p>
              <select
                value={delayReason}
                onChange={(e) => setDelayReason(e.target.value)}
                className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm focus:border-[#0F6E5C] focus:outline-none"
              >
                <option value="">Choose the reason for the delay</option>
                {DELAY_REASONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <input
                value={delayNote}
                onChange={(e) => setDelayNote(e.target.value)}
                placeholder={delayReason === 'Other' ? 'Describe the delay (required)' : 'Details (optional)'}
                maxLength={300}
                className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm focus:border-[#0F6E5C] focus:outline-none"
              />
            </div>
          )}

          {error && (
            <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-[#B42318]">
              <AlertCircle className="w-5 h-5 shrink-0" /> {error}
            </div>
          )}

          {!result ? (
            <Button size="lg" icon={submitting ? undefined : ShieldCheck} onClick={submit} disabled={submitting || !photo} className="w-full">
              {submitting ? <><Spinner size="sm" className="border-white border-t-transparent" /> Running 5 verification checks...</> : 'Mark resolved and verify'}
            </Button>
          ) : (
            <div className={`rounded-2xl border-2 p-5 space-y-4 ${result.verdict === 'VERIFIED' ? 'border-emerald-200 bg-emerald-50/40' : result.verdict === 'SUSPICIOUS' ? 'border-amber-200 bg-amber-50/40' : 'border-rose-200 bg-rose-50/40'}`}>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h3 className="font-bold text-slate-900">Verification result</h3>
                <ScoreHeader score={result.score} verdict={result.verdict} />
              </div>
              <PhotoEvidence resolution={result} complaintCreatedAt={complaint.created_at} reopenedAt={complaint.reopened_at} />
              <ReasonList reasons={result.reasons} />
              <p className={`text-sm font-semibold ${result.closed_late ? 'text-[#C77700]' : 'text-emerald-700'}`}>
                {result.closed_late
                  ? `Closed ${formatHours(result.late_by_hours)} after the deadline. Reason: ${result.delay_reason}${result.delay_note ? ` (${result.delay_note})` : ''}`
                  : 'Closed before the deadline.'}
              </p>
              <p className="text-sm text-slate-600">
                {result.verdict === 'VERIFIED'
                  ? 'Closure accepted.'
                  : 'This closure has been sent to a human reviewer. No action is taken automatically.'}
              </p>
              <div className="flex flex-col sm:flex-row gap-3">
                <Button onClick={onClose}>Back to task queue</Button>
                {result.verdict !== 'VERIFIED' && (
                  <Link to="/review"><Button variant="outline" icon={ArrowRight} className="w-full">Open review queue</Button></Link>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function WorkerPage() {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('due');
  const [ward, setWard] = useState('');
  const [selected, setSelected] = useState(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      setComplaints(await fetchApi('/api/complaints'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // /worker?resolve=ID opens the resolve panel for that complaint (linked from the Track page).
  const [params, setParams] = useSearchParams();
  useEffect(() => {
    const id = Number(params.get('resolve'));
    const target = id && complaints.find((c) => c.id === id && c.status !== 'RESOLVED');
    if (target) {
      setSelected(target);
      setParams({}, { replace: true });
    }
  }, [complaints, params, setParams]);

  const groups = useMemo(() => {
    const inWard = complaints.filter((c) => !ward || c.ward === ward);
    const open = inWard.filter((c) => c.status !== 'RESOLVED');
    const byDeadline = (a, b) => parseUtc(a.sla_deadline) - parseUtc(b.sla_deadline);
    return {
      due: open.filter((c) => hoursLeft(c) >= 0).sort(byDeadline),
      overdue: open.filter((c) => hoursLeft(c) < 0).sort(byDeadline),
      closed: inWard.filter((c) => c.status === 'RESOLVED'),
    };
  }, [complaints, ward]);

  const list = groups[tab];

  return (
    <div>
      <PageHeader title="Worker task queue" subtitle="Fix the issue, then upload an after photo taken at the site. Every closure is verified automatically.">
        <Button variant="outline" icon={RefreshCw} onClick={load}>Refresh</Button>
      </PageHeader>

      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div className="inline-flex rounded-xl bg-slate-100 p-1">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === t.key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
            >
              {t.label}
              <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-md ${t.key === 'overdue' ? 'bg-rose-100 text-[#B42318]' : 'bg-slate-200 text-slate-700'}`}>
                {groups[t.key].length}
              </span>
            </button>
          ))}
        </div>
        <select
          value={ward}
          onChange={(e) => setWard(e.target.value)}
          className="rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm focus:border-[#0F6E5C] focus:outline-none"
        >
          <option value="">All wards</option>
          {WARDS.map((w) => <option key={w.name} value={w.name}>{wardLabel(w)}</option>)}
        </select>
      </div>

      {loading && <Card className="flex justify-center py-16"><Spinner size="lg" /></Card>}
      {!loading && error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-[#B42318]">
          <AlertCircle className="w-5 h-5 shrink-0" /> {error}
        </div>
      )}
      {!loading && !error && list.length === 0 && <EmptyState title="Nothing here" description="No complaints in this list." />}

      {!loading && !error && list.length > 0 && (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {list.map((c) => {
            const left = hoursLeft(c);
            const img = imageUrl(c.before_image_path);
            return (
              <Card key={c.id} hover padding="p-0" className="overflow-hidden flex flex-col">
                {img ? (
                  <div className="relative">
                    <img src={img} alt="" loading="lazy" className="w-full aspect-[16/9] object-cover" />
                    {isSamplePhoto(c.before_image_path) && <SampleTag />}
                  </div>
                ) : (
                  <CategoryArt category={c.category} className="aspect-[16/9]" />
                )}
                <div className="p-5 flex flex-col gap-3 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-500">#{c.id} &middot; {c.ward}</span>
                    {c.status === 'RESOLVED' ? <VerdictBadge verdict={c.latest_verdict} /> : <SlaBadge slaStatus={c.sla_status} />}
                  </div>
                  <h3 className="font-bold text-slate-900 leading-snug">{c.title}</h3>
                  <p className="text-sm text-slate-600">{categoryLabel(c.category)}</p>
                  <div className="mt-auto pt-2 flex items-center justify-between gap-3">
                    {c.status === 'RESOLVED' ? (
                      <>
                        <span className="text-sm text-slate-600">
                          Score <b className="text-slate-900">{c.latest_score}</b>/100 &middot;{' '}
                          {c.sla_status === 'Breached'
                            ? <span className="font-semibold text-[#C77700]">Closed late</span>
                            : <span className="font-semibold text-emerald-700">On time</span>}
                        </span>
                        <Link to={`/track?id=${c.id}`} className="text-sm font-semibold text-[#0F6E5C] hover:underline">Details</Link>
                      </>
                    ) : (
                      <>
                        <span className={`text-sm font-semibold ${left < 0 ? 'text-[#B42318]' : left < c.sla_hours * 0.25 ? 'text-[#C77700]' : 'text-slate-700'}`}>
                          {left >= 0 ? `${formatHours(left)} left` : `Overdue ${formatHours(left)}`}
                        </span>
                        <div className="flex items-center gap-2">
                          {c.status === 'REOPENED' && <StatusBadge status="REOPENED" />}
                          <Button size="sm" icon={Camera} onClick={() => setSelected(c)}>Resolve</Button>
                        </div>
                      </>
                    )}
                  </div>
                  {c.status !== 'RESOLVED' && (
                    <p className="text-xs text-slate-400">Due {formatDateTime(c.sla_deadline)}</p>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {selected && <ResolvePanel complaint={selected} onClose={() => setSelected(null)} onResolved={load} />}
    </div>
  );
}
