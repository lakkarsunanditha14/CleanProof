import React from 'react';
import { CheckCircle2, XCircle, MinusCircle, ImageOff, Trash2, Droplets, BrickWall, Leaf, History } from 'lucide-react';
import VerdictBadge from './VerdictBadge';
import { imageUrl } from '../api';
import { categoryLabel } from '../constants';

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
        <a href={url} target="_blank" rel="noreferrer">
          <img src={url} alt={label || 'Photo'} className={`w-full aspect-[4/3] object-cover rounded-xl border-2 ${ring}`} />
        </a>
      ) : (
        <CategoryArt category={category} />
      )}
    </figure>
  );
}
