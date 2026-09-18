import React from 'react';
import { Construction } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Button from '../components/Button';
import { Link } from 'react-router-dom';

export default function PlaceholderPage({ title, description }) {
  return (
    <div>
      <PageHeader title={title} subtitle={description} />
      <Card className="text-center py-16">
        <div className="w-16 h-16 bg-amber-50 text-[#C77700] rounded-2xl flex items-center justify-center mx-auto mb-4 border border-amber-100">
          <Construction className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-2">{title} Page Coming Soon</h2>
        <p className="text-slate-600 max-w-md mx-auto mb-6 text-sm">
          This feature module is currently under development for the CleanProof civic verification platform.
        </p>
        <Link to="/">
          <Button variant="primary">Return to Home</Button>
        </Link>
      </Card>
    </div>
  );
}
