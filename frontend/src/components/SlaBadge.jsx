import React from 'react';

export default function SlaBadge({ slaStatus, className = '' }) {
  const normStatus = (slaStatus || '').toLowerCase();

  let style = 'bg-slate-100 text-slate-700 border-slate-200';
  let dotColor = 'bg-slate-400';
  let label = slaStatus || 'Unknown';

  if (normStatus.includes('on time') || normStatus === 'on_time') {
    style = 'bg-emerald-50 text-emerald-700 border-emerald-200';
    dotColor = 'bg-emerald-500';
    label = 'On time';
  } else if (normStatus.includes('near deadline') || normStatus === 'near_deadline') {
    style = 'bg-amber-50 text-[#C77700] border-amber-200';
    dotColor = 'bg-[#C77700]';
    label = 'Near deadline';
  } else if (normStatus.includes('breached') || normStatus === 'breached') {
    style = 'bg-rose-50 text-[#B42318] border-rose-200';
    dotColor = 'bg-[#B42318]';
    label = 'Breached';
  }

  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${style} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${dotColor}`} />
      {label}
    </span>
  );
}
