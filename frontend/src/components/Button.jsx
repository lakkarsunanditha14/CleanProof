import React from 'react';

export default function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'danger' | 'subtle'
  size = 'md', // 'sm' | 'md' | 'lg'
  onClick,
  type = 'button',
  disabled = false,
  className = '',
  icon: Icon = null,
}) {
  const baseStyles = 'inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer';

  const variants = {
    primary: 'bg-[#0F6E5C] text-white hover:bg-[#0D5C4D] active:bg-[#0A4A3E] focus:ring-[#0F6E5C] shadow-sm',
    secondary: 'bg-slate-100 text-slate-800 hover:bg-slate-200 active:bg-slate-300 focus:ring-slate-400',
    outline: 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-400 active:bg-slate-100 focus:ring-[#0F6E5C]',
    danger: 'bg-[#B42318] text-white hover:bg-[#991B1B] active:bg-[#7F1D1D] focus:ring-[#B42318] shadow-sm',
    subtle: 'text-slate-600 hover:text-slate-900 hover:bg-slate-100 focus:ring-slate-300',
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2.5 text-sm gap-2',
    lg: 'px-6 py-3.5 text-base gap-2.5',
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
    >
      {Icon && <Icon className={size === 'sm' ? 'w-3.5 h-3.5' : size === 'lg' ? 'w-5 h-5' : 'w-4 h-4'} />}
      {children}
    </button>
  );
}
