import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertCircle, ShieldAlert, ShieldCheck, RefreshCw, MapPin, Scale, Clock, History } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import EmptyState from '../components/EmptyState';
import { ReasonList, ScoreHeader, Photo, PhotoEvidence } from '../components/Verification';
import { categoryLabel } from '../constants';
import { fetchApi, formatDateTime, formatHours, imageUrl } from '../api';

const DECISION_STYLE = {
  'Confirmed fake': 'bg-rose-50 text-[#B42318] border-rose-200',
  Genuine: 'bg-emerald-50 text-emerald-700 border-emerald-200',
};

function ReviewCard({ item, onDecide, busy }) {
  const pending = item.human_review_status === 'PENDING';
  // Seeded history records (for the dashboard) have no photos
  const synthetic = !imageUrl(item.complaint_before_image_path) && !imageUrl(item.after_image_path);
  return (
    <Card className="space-y-5">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            Complaint #{item.complaint_id} &middot; closed {formatDateTime(item.created_at)}
          </p>
          <h2 className="text-lg md:text-xl font-bold text-slate-900 mt-1">{item.complaint_title}</h2>
          <p className="text-sm text-slate-600 flex items-center gap-1.5 mt-1">
            <MapPin className="w-4 h-4" /> {item.complaint_ward} &middot; {categoryLabel(item.complaint_category)}
          </p>
        </div>
        <ScoreHeader score={item.score} verdict={item.verdict} />
      </div>

      {synthetic ? (
        <div className="flex items-center gap-2 rounded-xl bg-slate-50 border border-slate-200 px-4 py-3 text-sm text-slate-500">
          <History className="w-4 h-4 shrink-0" />
          Synthetic history record, generated to fill the dashboard. It has no photos.
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-5">
          <Photo label="Before (citizen)" path={item.complaint_before_image_path} tone="amber" />
          <Photo label="After (worker's proof)" path={item.after_image_path} tone="green" />
        </div>
      )}

      {item.closed_late && (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm">
          <Clock className="w-4 h-4 shrink-0 mt-0.5 text-[#C77700]" />
          <span>
            <span className="font-semibold text-[#C77700]">Closed {formatHours(item.late_by_hours)} after the deadline. </span>
            <span className="text-slate-800">Worker's reason: {item.delay_reason}{item.delay_note ? ` - ${item.delay_note}` : ''}</span>
          </span>
        </div>
      )}

      <PhotoEvidence resolution={item} complaintCreatedAt={item.complaint_created_at} reopenedAt={item.complaint_reopened_at} />

      <div className="rounded-xl bg-slate-50 border border-slate-200 p-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Why it was flagged</p>
        <ReasonList reasons={item.reasons} />
      </div>

      {pending ? (
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="danger" icon={ShieldAlert} disabled={busy} onClick={() => onDecide(item, 'Confirmed fake')} className="flex-1">
            Confirmed fake (reopen complaint)
          </Button>
          <Button variant="outline" icon={ShieldCheck} disabled={busy} onClick={() => onDecide(item, 'Genuine')} className="flex-1">
            Genuine (accept closure)
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-semibold ${DECISION_STYLE[item.human_review_status] || ''}`}>
            Reviewer decision: {item.human_review_status}
          </span>
          <Link to={`/track?id=${item.complaint_id}`} className="text-sm font-semibold text-[#0F6E5C] hover:underline">
            View complaint
          </Link>
        </div>
      )}
    </Card>
  );
}

export default function ReviewPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('pending');
  const [busyId, setBusyId] = useState(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      setItems(await fetchApi('/api/verification/flagged'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function decide(item, decision) {
    setBusyId(item.id);
    try {
      const updated = await fetchApi(`/api/verification/${item.id}/review`, {
        method: 'POST',
        body: JSON.stringify({ decision }),
      });
      setItems((prev) => prev.map((x) => (x.id === item.id ? { ...x, human_review_status: updated.human_review_status } : x)));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  const pending = useMemo(() => items.filter((i) => i.human_review_status === 'PENDING'), [items]);
  const reviewed = useMemo(() => items.filter((i) => i.human_review_status !== 'PENDING'), [items]);
  const list = tab === 'pending' ? pending : reviewed;

  return (
    <div className="max-w-5xl mx-auto">
      <PageHeader title="Human review" subtitle="The system only flags. A person compares the photos and makes the final decision.">
        <Button variant="outline" icon={RefreshCw} onClick={load}>Refresh</Button>
      </PageHeader>

      <div className="inline-flex rounded-xl bg-slate-100 p-1 mb-6">
        {[
          { key: 'pending', label: 'Waiting for review', count: pending.length },
          { key: 'reviewed', label: 'Reviewed', count: reviewed.length },
        ].map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === t.key ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
          >
            {t.label}
            <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-md ${t.key === 'pending' ? 'bg-amber-100 text-[#C77700]' : 'bg-slate-200 text-slate-700'}`}>{t.count}</span>
          </button>
        ))}
      </div>

      {loading && <Card className="flex justify-center py-16"><Spinner size="lg" /></Card>}
      {!loading && error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-[#B42318] mb-6">
          <AlertCircle className="w-5 h-5 shrink-0" /> {error}
        </div>
      )}
      {!loading && list.length === 0 && (
        <EmptyState
          icon={Scale}
          title={tab === 'pending' ? 'No closures waiting for review' : 'No decisions yet'}
          description={tab === 'pending' ? 'Flagged closures appear here automatically.' : 'Decisions you make appear here.'}
        />
      )}
      {!loading && list.length > 0 && (
        <div className="space-y-6">
          {list.map((item) => (
            <ReviewCard key={item.id} item={item} onDecide={decide} busy={busyId === item.id} />
          ))}
        </div>
      )}
    </div>
  );
}
