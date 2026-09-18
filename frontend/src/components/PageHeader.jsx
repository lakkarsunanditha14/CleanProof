import React from 'react';

export default function PageHeader({
  title,
  subtitle,
  children,
  badge = null,
}) {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 mb-8 border-b border-slate-200">
      <div>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight">{title}</h1>
          {badge}
        </div>
        {subtitle && <p className="mt-1 text-slate-600 text-sm md:text-base max-w-3xl">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-3 shrink-0">{children}</div>}
    </div>
  );
}
