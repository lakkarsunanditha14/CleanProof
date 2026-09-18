import React from 'react';
import { CheckCircle2, XCircle, MinusCircle, ImageOff, Trash2, Droplets, BrickWall, Leaf, History, Camera, Upload, MapPin, Fingerprint, AlertTriangle } from 'lucide-react';
import VerdictBadge from './VerdictBadge';
import { imageUrl, isSamplePhoto, parseUtc, formatDateTime, formatHours } from '../api';
import { categoryLabel } from '../constants';

export function SampleTag() {
  return (
    <span className="absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-semibold text-slate-600 shadow-sm">
      <History className="w-3 h-3" /> Sample photo, synthetic history
    </span>
  );
}

// Shown instead of a photo for synthetic history records, which never had photos.
const CATEGORY_ART = {
  'garbage dump': { icon: Trash2, bg: '#FFF7E6', ink: '#B45309' },
  'blocked drain': { icon: Droplets, bg: '#E8F4FD', ink: '#0369A1' },
  'construction debris': { icon: BrickWall, bg: '#F6F1EC', ink: '#9A3412' },
  'unswept street': { icon: Leaf, bg: '#EAF7F1', ink: '#0F6E5C' },
};

export function CategoryArt({ category, className = 'aspect-[4/3] rounded-xl' }) {
  const art = CATEGORY_ART[category];
  if (!art) {
    return (
      <div className={`w-full bg-slate-50 border-2 border-dashed border-slate-200 flex flex-col items-center justify-center text-slate-400 text-sm ${className}`}>
        <ImageOff className="w-8 h-8 mb-2" />
        No photo
      </div>
    );
  }
  const Icon = art.icon;
  return (
    <div
      className={`relative w-full overflow-hidden flex flex-col items-center justify-center gap-3 ${className}`}
      style={{
        backgroundColor: art.bg,
        backgroundImage: `radial-gradient(${art.ink}1f 1.2px, transparent 1.2px)`,
        backgroundSize: '14px 14px',
      }}
    >
      <div className="w-16 h-16 rounded-2xl bg-white shadow-sm flex items-center justify-center" style={{ color: art.ink }}>
        <Icon className="w-8 h-8" strokeWidth={1.75} />
      </div>
      <p className="text-sm font-semibold" style={{ color: art.ink }}>{categoryLabel(category)}</p>
      <span className="absolute top-3 left-3 inline-flex items-center gap-1 rounded-full bg-white/85 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
        <History className="w-3 h-3" /> Historical record, no photo
      </span>
    </div>
  );
}

// Reasons end with "(Pass)" or "(-NN pts)"; anything else (e.g. check unavailable) is neutral.
function reasonKind(reason) {
  if (/\(Pass\)/i.test(reason)) return 'pass';
  if (/-\d+\s*pts/i.test(reason)) return 'fail';
  return 'neutral';
}

export function ReasonList({ reasons }) {
  return (
    <ul className="space-y-2.5">
      {reasons.map((text) => {
        const kind = reasonKind(text);
        const Icon = kind === 'pass' ? CheckCircle2 : kind === 'fail' ? XCircle : MinusCircle;
        const color = kind === 'pass' ? 'text-emerald-600' : kind === 'fail' ? 'text-[#B42318]' : 'text-slate-400';
        return (
          <li key={text} className="flex items-start gap-2.5 text-sm text-slate-700">
            <Icon className={`w-4.5 h-4.5 shrink-0 mt-0.5 ${color}`} />
            <span>{text}</span>
          </li>
        );
      })}
    </ul>
  );
}

export function ScoreHeader({ score, verdict }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-3xl font-extrabold text-slate-900">
        {score}
        <span className="text-base text-slate-400">/100</span>
      </span>
      <VerdictBadge verdict={verdict} />
    </div>
  );
}

export function Photo({ label, path, tone = 'slate', src, category }) {
  const url = src || imageUrl(path);
  const ring = tone === 'green' ? 'border-emerald-200' : tone === 'amber' ? 'border-amber-200' : 'border-slate-200';
  return (
    <figure className="space-y-2">
      {label && <figcaption className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</figcaption>}
      {url ? (
        <a href={url} target="_blank" rel="noreferrer" className="relative block">
          <img src={url} alt={label || 'Photo'} loading="lazy" className={`w-full aspect-[4/3] object-cover rounded-xl border-2 ${ring}`} />
          {isSamplePhoto(path) && <SampleTag />}
        </a>
      ) : (
        <CategoryArt category={category} />
      )}
    </figure>
  );
}

function formatDistance(m) {
  return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

const EVIDENCE_TONE = {
  good: { Icon: CheckCircle2, color: 'text-emerald-600', box: 'border-emerald-200 bg-emerald-50/50' },
  warn: { Icon: AlertTriangle, color: 'text-[#C77700]', box: 'border-amber-200 bg-amber-50/60' },
  bad: { Icon: XCircle, color: 'text-[#B42318]', box: 'border-rose-200 bg-rose-50/50' },
};

function EvidenceRow({ icon: RowIcon, label, value, note, tone }) {
  const t = EVIDENCE_TONE[tone];
  return (
    <div className={`rounded-xl border p-3.5 flex items-start gap-3 ${t.box}`}>
      <RowIcon className="w-5 h-5 text-slate-500 shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
        <p className="font-semibold text-slate-900 mt-0.5">{value}</p>
        <p className={`text-sm mt-0.5 flex items-center gap-1.5 ${t.color}`}>
          <t.Icon className="w-4 h-4 shrink-0" /> {note}
        </p>
      </div>
    </div>
  );
}

// When and where the after photo was really taken, read from the photo file (EXIF),
// compared with when the complaint was reported (or reopened) and when the photo was uploaded.
export function PhotoEvidence({ resolution: r, complaintCreatedAt, reopenedAt }) {
  const start = parseUtc(reopenedAt || complaintCreatedAt);
  const startWord = reopenedAt ? 'reopened' : 'reported';
  const taken = parseUtc(r.photo_taken_at);
  const uploaded = parseUtc(r.created_at);
  const hours = (a, b) => (a - b) / 3600000;

  let takenNote;
  let takenTone;
  if (!taken) {
    takenNote = 'No date inside the photo, so its age cannot be proven';
    takenTone = 'bad';
  } else if (start && taken < start) {
    takenNote = `${formatHours(hours(start, taken))} BEFORE the complaint was ${startWord}`;
    takenTone = 'bad';
  } else {
    takenNote = `${formatHours(hours(taken, start))} after the complaint was ${startWord}`;
    takenTone = 'good';
  }

  let uploadNote = 'Photo age unknown';
  let uploadTone = 'bad';
  if (taken) {
    const age = Math.max(0, hours(uploaded, taken));
    uploadTone = age > 24 ? 'warn' : 'good';
    uploadNote = age > 24
      ? `Taken ${formatHours(age)} before upload, possibly an old photo`
      : `Taken ${formatHours(age)} before upload (fresh)`;
  }

  const hasGps = r.photo_latitude != null;
  const dist = r.gps_distance_meters;
  const near = hasGps && dist != null && dist <= 50;
  let placeNote = 'No GPS inside the photo';
  if (hasGps) {
    if (dist == null) placeNote = 'Distance not available';
    else placeNote = near ? `${formatDistance(dist)} from the complaint spot` : `${formatDistance(dist)} away from the complaint spot`;
  }

  return (
    <div className="space-y-3">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Photo evidence</p>
        <p className="text-sm text-slate-500">Read automatically from the photo file, not typed by the worker.</p>
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        <EvidenceRow icon={Camera} label="Photo taken" value={taken ? formatDateTime(r.photo_taken_at) : 'Not recorded'} note={takenNote} tone={takenTone} />
        <EvidenceRow icon={Upload} label="Uploaded" value={formatDateTime(r.created_at)} note={uploadNote} tone={uploadTone} />
        <EvidenceRow
          icon={MapPin}
          label="Taken at"
          value={hasGps ? `${r.photo_latitude.toFixed(5)}, ${r.photo_longitude.toFixed(5)}` : 'Not recorded'}
          note={placeNote}
          tone={near ? 'good' : 'bad'}
        />
        <EvidenceRow
          icon={Fingerprint}
          label="Camera data"
          value={r.has_exif_metadata ? 'Present' : 'Missing'}
          note={r.has_exif_metadata ? 'Photo carries its original camera data' : 'Typical of AI-generated, edited or downloaded images'}
          tone={r.has_exif_metadata ? 'good' : 'bad'}
        />
      </div>
    </div>
  );
}
