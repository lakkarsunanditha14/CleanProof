import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search, AlertCircle, Clock, MapPin, RotateCcw, UserCheck } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import StatusBadge from '../components/StatusBadge';
import SlaBadge from '../components/SlaBadge';
import { ReasonList, ScoreHeader, Photo } from '../components/Verification';
import { categoryLabel } from '../constants';
import { fetchApi, parseUtc, formatDateTime, formatHours } from '../api';

// Live time left, recalculated every 30 seconds for open complaints.
function useNow(active) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return undefined;
    const t = setInterval(() => setNow(Date.now()), 30000);
    return () => clearInterval(t);
  }, [active]);
  return now;
}

export default function TrackPage() {
  const [params, setParams] = useSearchParams();
  const [query, setQuery] = useState(params.get('id') || '');
  const [complaint, setComplaint] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reopenPhoto, setReopenPhoto] = useState(null);
  const [reopenReason, setReopenReason] = useState('');
  const [reopening, setReopening] = useState(false);
  const [reopenError, setReopenError] = useState('');

  const id = params.get('id');
  const isOpen = complaint && complaint.status !== 'RESOLVED';
  const now = useNow(isOpen);

  async function load(complaintId) {
    setLoading(true);
    setError('');
    try {
      setComplaint(await fetchApi(`/api/complaints/${complaintId}`));
    } catch (err) {
      setComplaint(null);
      setError(err.message === 'Complaint not found' ? `No complaint found with ID #${complaintId}.` : err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (id) load(id);
  }, [id]);

  function handleSearch(e) {
    e.preventDefault();
    const clean = query.trim().replace('#', '');
    if (/^\d+$/.test(clean)) setParams({ id: clean });
    else setError('Enter a complaint number, e.g. 1');
  }

  async function handleReopen(e) {
    e.preventDefault();
    setReopenError('');
    if (!reopenPhoto) return setReopenError('Please add a photo showing the issue is still there.');
    const form = new FormData();
    form.append('photo', reopenPhoto);
    if (reopenReason.trim()) form.append('reason', reopenReason.trim());
    setReopening(true);
    try {
      setComplaint(await fetchApi(`/api/complaints/${complaint.id}/reopen`, { method: 'POST', body: form }));
      setReopenPhoto(null);
      setReopenReason('');
    } catch (err) {
      setReopenError(err.message);
    } finally {
      setReopening(false);
    }
  }

  const res = complaint?.latest_resolution;
  const sla = complaint?.sla_info;
  const hoursLeft = sla ? (parseUtc(sla.deadline) - now) / 3600000 : 0;

  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader title="Track a complaint" subtitle="See the status, the deadline and whether the closure photo passed verification." />

      <form onSubmit={handleSearch} className="flex gap-3 mb-8">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Complaint ID, e.g. 1"
          inputMode="numeric"
          className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-base focus:border-[#0F6E5C] focus:outline-none focus:ring-2 focus:ring-[#0F6E5C]/20"
        />
        <Button type="submit" size="lg" icon={Search}>Track</Button>
      </form>

      {loading && (
        <Card className="flex justify-center py-16"><Spinner size="lg" /></Card>
      )}

      {!loading && error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-[#B42318]">
          <AlertCircle className="w-5 h-5 shrink-0" /> {error}
        </div>
      )}

      {!loading && complaint && (
        <div className="space-y-6">
          <Card className="space-y-5">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-slate-500">Complaint #{complaint.id}</p>
                <h2 className="text-xl md:text-2xl font-bold text-slate-900 mt-1">{complaint.title}</h2>
                <p className="text-sm text-slate-600 mt-1 flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" /> {complaint.ward} &middot; {categoryLabel(complaint.category)}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <StatusBadge status={complaint.status} />
                <SlaBadge slaStatus={sla?.status} />
              </div>
            </div>

            <div className="grid sm:grid-cols-3 gap-4">
              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Reported</p>
                <p className="font-semibold text-slate-900 mt-1">{formatDateTime(complaint.created_at)}</p>
              </div>
              <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Deadline ({complaint.sla_hours}h{complaint.reopened_at ? ', restarted on reopen' : ''})
                </p>
                <p className="font-semibold text-slate-900 mt-1">{formatDateTime(sla?.deadline)}</p>
              </div>
              <div className={`rounded-xl border p-4 ${sla?.is_breached ? 'bg-rose-50 border-rose-200' : 'bg-emerald-50 border-emerald-200'}`}>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" /> {isOpen ? 'Time left' : 'Result'}
                </p>
                <p className={`font-bold mt-1 ${sla?.is_breached ? 'text-[#B42318]' : 'text-[#0F6E5C]'}`}>
                  {isOpen
                    ? hoursLeft >= 0 ? `${formatHours(hoursLeft)} left` : `Overdue by ${formatHours(hoursLeft)}`
                    : sla?.is_breached ? `Closed ${formatHours(sla.hours_remaining)} late` : `Closed within deadline`}
                </p>
              </div>
            </div>
            {res?.closed_late && res.delay_reason && (
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
                <span className="font-semibold text-[#C77700]">Worker's reason for the delay: </span>
                <span className="text-slate-800">{res.delay_reason}{res.delay_note ? ` - ${res.delay_note}` : ''}</span>
              </div>
            )}
            {complaint.description && <p className="text-sm text-slate-600">{complaint.description}</p>}
          </Card>

          <Card className="space-y-5">
            <h3 className="font-bold text-slate-900">Photos</h3>
            <div className="grid sm:grid-cols-2 gap-5">
              <Photo label="Before (citizen)" path={complaint.before_image_path} tone="amber" />
              {res ? (
                <Photo label={`After (worker, ${formatDateTime(res.created_at)})`} path={res.after_image_path} tone="green" />
              ) : (
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">After (worker)</p>
                  <div className="w-full aspect-[4/3] rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center gap-3 text-sm text-slate-500 text-center px-6">
                    Not resolved yet. The worker uploads a photo from the site when the issue is fixed.
                    <Link to={`/worker?resolve=${complaint.id}`} className="font-semibold text-[#0F6E5C] hover:underline">
                      Resolve as worker
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </Card>

          {res && (
            <Card className="space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <h3 className="font-bold text-slate-900">Closure verification</h3>
                <ScoreHeader score={res.score} verdict={res.verdict} />
              </div>
              <ReasonList reasons={res.reasons} />
              <div className="flex items-center gap-2 text-sm rounded-xl bg-slate-50 border border-slate-200 px-4 py-3">
                <UserCheck className="w-4 h-4 text-slate-500" />
                <span className="text-slate-600">Human review:</span>
                <span className="font-semibold text-slate-900">
                  {res.human_review_status === 'PENDING'
                    ? res.verdict === 'VERIFIED' ? 'Not needed' : 'Waiting for reviewer'
                    : res.human_review_status}
                </span>
              </div>
            </Card>
          )}

          {complaint.status === 'RESOLVED' && (
            <Card className="space-y-4">
              <h3 className="font-bold text-slate-900 flex items-center gap-2">
                <RotateCcw className="w-5 h-5 text-[#C77700]" /> Is the problem still there?
              </h3>
              <p className="text-sm text-slate-600">
                Upload a new photo to reopen this complaint. The deadline restarts from now.
              </p>
              <form onSubmit={handleReopen} className="space-y-4">
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={(e) => setReopenPhoto(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl file:border-0 file:bg-slate-100 file:px-4 file:py-2.5 file:font-medium file:text-slate-800 hover:file:bg-slate-200"
                />
                <input
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  placeholder="What is still wrong? (optional)"
                  maxLength={300}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm focus:border-[#0F6E5C] focus:outline-none focus:ring-2 focus:ring-[#0F6E5C]/20"
                />
                {reopenError && <p className="text-sm text-[#B42318]">{reopenError}</p>}
                <Button type="submit" variant="danger" icon={RotateCcw} disabled={reopening}>
                  {reopening ? 'Reopening...' : 'Reopen complaint'}
                </Button>
              </form>
            </Card>
          )}

          {complaint.reopen_logs.length > 0 && (
            <Card className="space-y-4">
              <h3 className="font-bold text-slate-900">Reopen history</h3>
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {complaint.reopen_logs.map((log) => (
                  <div key={log.id} className="space-y-2">
                    <Photo label={`Reopened ${formatDateTime(log.created_at)}`} path={log.reopen_image_path} tone="amber" />
                    {log.reason && <p className="text-sm text-slate-600">{log.reason}</p>}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {!loading && !complaint && !error && (
        <Card className="text-center py-12 text-slate-500 text-sm">
          Enter a complaint ID above. Demo complaints are #1 to #6.
        </Card>
      )}
    </div>
  );
}
