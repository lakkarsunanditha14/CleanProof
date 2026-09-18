import React from 'react';

export default function VerdictBadge({ verdict, className = '' }) {
  const normVerdict = (verdict || '').toUpperCase();

  let style = 'bg-slate-100 text-slate-700 border-slate-200';
  let dotColor = 'bg-slate-400';

  if (normVerdict === 'VERIFIED') {
    style = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    dotColor = 'bg-emerald-500';
  } else if (normVerdict === 'SUSPICIOUS') {
    style = 'bg-amber-50 text-[#C77700] border-amber-200';
    dotColor = 'bg-[#C77700]';
  } else if (normVerdict === 'LIKELY FAKE' || normVerdict === 'FAKE') {
    style = 'bg-rose-50 text-[#B42318] border-rose-200';
    dotColor = 'bg-[#B42318]';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold border tracking-wide ${style} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dotColor}`} />
      {normVerdict || 'UNVERIFIED'}
    </span>
  );
}
