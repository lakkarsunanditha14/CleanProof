import React from 'react';
import { Inbox } from 'lucide-react';

export default function EmptyState({
  title = 'No items found',
  description = 'There are no records to display at this time.',
  icon: Icon = Inbox,
  action = null,
  className = '',
}) {
  return (
    <div className={`flex flex-col items-center justify-center text-center p-8 md:p-12 bg-white rounded-2xl border border-slate-200/80 ${className}`}>
      <div className="w-14 h-14 bg-slate-50 text-slate-400 rounded-full flex items-center justify-center mb-4 border border-slate-100">
        <Icon className="w-7 h-7" />
      </div>
      <h3 className="text-lg font-semibold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm mb-6">{description}</p>
      {action}
    </div>
  );
}
