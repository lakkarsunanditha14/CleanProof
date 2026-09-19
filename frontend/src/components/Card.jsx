import React from 'react';

export default function Card({
  children,
  className = '',
  hover = false,
  padding = 'p-6',
}) {
  return (
    <div
      className={`bg-white rounded-2xl border border-slate-200/80 shadow-sm shadow-slate-100 ${
        hover ? 'transition-all duration-200 hover:shadow-lg hover:border-slate-300 motion-safe:hover:-translate-y-1' : ''
      } ${padding} ${className}`}
    >
      {children}
    </div>
  );
}
