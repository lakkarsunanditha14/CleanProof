import React from 'react';

export default function StatusBadge({ status, className = '' }) {
  const normStatus = (status || '').toUpperCase();

  const styles = {
    OPEN: 'bg-blue-50 text-blue-700 border-blue-200',
    RESOLVED: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    REOPENED: 'bg-amber-50 text-[#C77700] border-amber-200',
  };

  const defaultStyle = 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${
        styles[normStatus] || defaultStyle
      } ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${
        normStatus === 'RESOLVED' ? 'bg-emerald-500' :
        normStatus === 'REOPENED' ? 'bg-amber-500' : 'bg-blue-500'
      }`} />
      {normStatus}
    </span>
  );
}
