import React from 'react';
import { CheckCircle2, XCircle, MinusCircle, ImageOff } from 'lucide-react';
import VerdictBadge from './VerdictBadge';
import { imageUrl } from '../api';

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

export function Photo({ label, path, tone = 'slate', src }) {
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
        <div className="w-full aspect-[4/3] rounded-xl border-2 border-dashed border-slate-200 bg-slate-50 flex flex-col items-center justify-center text-slate-400 text-sm">
          <ImageOff className="w-8 h-8 mb-2" />
          No photo (synthetic record)
        </div>
      )}
    </figure>
  );
}
