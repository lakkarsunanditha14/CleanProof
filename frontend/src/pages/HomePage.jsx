import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  ShieldCheck, 
  FileText, 
  Camera, 
  Cpu, 
  UserCheck, 
  CheckCircle2, 
  MapPin, 
  Clock, 
  Copy, 
  FileCode,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import Button from '../components/Button';
import Card from '../components/Card';
import Spinner from '../components/Spinner';
import { fetchApi } from '../api';

export default function HomePage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadStats() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchApi('/api/dashboard/stats');
        setStats(data);
      } catch (err) {
        console.error('Failed to load dashboard stats:', err);
        setError('Unable to connect to CleanProof API backend. Make sure the server is running on http://127.0.0.1:8000.');
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  const howItWorksSteps = [
    {
      num: '01',
      title: 'Report',
      icon: FileText,
      desc: 'Citizen files a municipal complaint with a geo-tagged before photo and issue category.',
      color: 'bg-emerald-50 text-[#0F6E5C]',
    },
    {
      num: '02',
      title: 'Resolve with Photo',
      icon: Camera,
      desc: 'Municipal worker uploads an after-photo as proof of completion to resolve the ticket.',
      color: 'bg-blue-50 text-blue-700',
    },
    {
      num: '03',
      title: 'AI + Forensic Verification',
      icon: Cpu,
      desc: 'CleanProof runs 5 automated checks: CLIP vision, GPS distance, EXIF metadata, timestamp & duplicate hash.',
      color: 'bg-purple-50 text-purple-700',
    },
    {
      num: '04',
      title: 'Human Review',
      icon: UserCheck,
      desc: 'Flagged suspicious & fake closures are queued for senior municipal supervisor audit.',
      color: 'bg-amber-50 text-[#C77700]',
    },
  ];

  const fiveChecks = [
    {
      title: '1. AI Vision (CLIP Zero-Shot)',
      icon: Cpu,
      desc: 'Zero-shot classification compares before vs. after photos against category-aware problem vs. clean prompts to measure issue reduction.',
      color: 'text-emerald-600 bg-emerald-50',
    },
    {
      title: '2. Location Verification (GPS)',
      icon: MapPin,
      desc: 'Extracts EXIF coordinates from resolution photo and calculates distance from original complaint site (flagged if >50m away).',
      color: 'text-blue-600 bg-blue-50',
    },
    {
      title: '3. Timestamp Verification',
      icon: Clock,
      desc: 'Checks EXIF DateTimeOriginal metadata to confirm resolution photo was taken after complaint creation or reopening time.',
      color: 'text-indigo-600 bg-indigo-50',
    },
    {
      title: '4. Duplicate Image Detection',
      icon: Copy,
      desc: 'Perceptual hashing (pHash) detects re-uploaded dirty before photos or recycled resolution images across complaints.',
      color: 'text-amber-600 bg-amber-50',
    },
    {
      title: '5. Camera Metadata Forensics',
      icon: FileCode,
      desc: 'Checks whether the photo carries camera EXIF metadata. Missing metadata is typical of AI-generated, edited or downloaded images.',
      color: 'text-purple-600 bg-purple-50',
    },
  ];

  return (
    <div className="space-y-16 pb-8">
      {/* Hero Section */}
      <section className="text-center py-12 md:py-16 px-4 bg-gradient-to-b from-emerald-50/70 via-white to-slate-50 rounded-3xl border border-slate-200/80 shadow-xs relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-[#0F6E5C]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />
        
        <div className="max-w-3xl mx-auto space-y-6 relative z-10">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#0F6E5C]/10 text-[#0F6E5C] text-xs font-semibold tracking-wide uppercase border border-[#0F6E5C]/20">
            <ShieldCheck className="w-4 h-4" />
            Civic Integrity & SLA Verification Engine
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-tight">
            Every 'resolved' complaint, <span className="text-[#0F6E5C] underline decoration-[#0F6E5C]/30 underline-offset-8">verified</span>.
          </h1>

          <p className="text-slate-600 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed">
            CleanProof monitors municipal SLA deadlines and uses AI zero-shot vision + EXIF camera forensics to catch fake closures before they pass.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
            <Link to="/report">
              <Button variant="primary" size="lg" icon={FileText} className="w-full sm:w-auto shadow-md">
                Report an issue
              </Button>
            </Link>
            <Link to="/dashboard">
              <Button variant="outline" size="lg" icon={TrendingUp} className="w-full sm:w-auto">
                View dashboard
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Live Stats Row */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-[#0F6E5C]" />
            Live System Performance
          </h2>
          <span className="text-xs text-slate-500 font-medium">Updated real-time from API</span>
        </div>

        {loading ? (
          <Card className="flex flex-col items-center justify-center py-12">
            <Spinner size="lg" />
            <p className="text-sm text-slate-500 mt-4 font-medium">Fetching live metrics from backend...</p>
          </Card>
        ) : error ? (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-6 text-rose-800 flex items-start gap-4 shadow-xs">
            <AlertCircle className="w-6 h-6 text-[#B42318] shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-[#B42318]">Backend Connection Issue</h3>
              <p className="text-sm mt-1 text-rose-700">{error}</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Total Complaints */}
            <Card hover padding="p-6">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Total Complaints</span>
                <FileText className="w-5 h-5 text-slate-400" />
              </div>
              <div className="text-3xl font-extrabold text-slate-900 tracking-tight">
                {stats?.total_complaints ?? 0}
              </div>
              <p className="text-xs text-slate-500 mt-2">Reported by citizens</p>
            </Card>

            {/* SLA Adherence */}
            <Card hover padding="p-6">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">SLA Adherence</span>
                <CheckCircle2 className="w-5 h-5 text-[#0F6E5C]" />
              </div>
              <div className="text-3xl font-extrabold text-[#0F6E5C] tracking-tight">
                {stats?.sla_adherence_percent ?? 0}%
              </div>
              <p className="text-xs text-slate-500 mt-2">Resolved within deadline window</p>
            </Card>

            {/* Suspected False Closures */}
            <Card hover padding="p-6">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">Suspected False Closures</span>
                <AlertTriangle className="w-5 h-5 text-[#C77700]" />
              </div>
              <div className="text-3xl font-extrabold text-[#C77700] tracking-tight">
                {stats?.false_closures_count ?? 0}
              </div>
              <p className="text-xs text-slate-500 mt-2">Flagged for supervisor review</p>
            </Card>

            {/* Active Breached */}
            <Card hover padding="p-6">
              <div className="flex items-center justify-between text-slate-500 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider">SLA Breaches</span>
                <AlertCircle className="w-5 h-5 text-[#B42318]" />
              </div>
              <div className="text-3xl font-extrabold text-[#B42318] tracking-tight">
                {stats?.total_breached ?? 0}
              </div>
              <p className="text-xs text-slate-500 mt-2">Complaints that missed their deadline</p>
            </Card>
          </div>
        )}
      </section>

      {/* How It Works Section */}
      <section className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight">How CleanProof Works</h2>
          <p className="text-slate-600 text-sm md:text-base">
            An automated end-to-end verification pipeline safeguarding civic resolution reports.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {howItWorksSteps.map((step) => {
            const Icon = step.icon;
            return (
              <Card key={step.num} hover className="relative flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-xl ${step.color} flex items-center justify-center shadow-xs`}>
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-2xl font-black text-slate-200">{step.num}</span>
                  </div>
                  <h3 className="text-lg font-bold text-slate-900 mb-2">{step.title}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{step.desc}</p>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      {/* The 5 Checks Section */}
      <section className="bg-white rounded-3xl border border-slate-200/80 p-8 md:p-10 space-y-8 shadow-xs">
        <div className="max-w-2xl space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#0F6E5C]/10 text-[#0F6E5C] text-xs font-semibold">
            <ShieldCheck className="w-3.5 h-3.5" />
            Verification Pipeline
          </div>
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight">The 5 Forensic & AI Checks</h2>
          <p className="text-slate-600 text-sm md:text-base">
            Every resolution photo uploaded by a municipal worker undergoes 5 rigorous checks before verification.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {fiveChecks.map((check, idx) => {
            const Icon = check.icon;
            return (
              <div key={idx} className="p-5 rounded-2xl border border-slate-100 bg-slate-50/60 hover:bg-white hover:shadow-lg hover:border-slate-200 motion-safe:hover:-translate-y-1 transition-all duration-200 space-y-3">
                <div className="flex items-center gap-3">
                  <div className={`w-10 h-10 rounded-xl ${check.color} flex items-center justify-center shrink-0`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <h3 className="font-bold text-slate-900 text-base">{check.title}</h3>
                </div>
                <p className="text-xs md:text-sm text-slate-600 leading-relaxed">
                  {check.desc}
                </p>
              </div>
            );
          })}
        </div>

        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-slate-500">
            Score starts at 100: issue still visible -50 (partly cleaned -10), wrong or missing location -30, duplicate photo -30, photo older than the complaint or missing time -30, no camera metadata -10.
          </p>
          <Link to="/review">
            <Button variant="outline" size="sm" icon={ArrowRight}>
              View human review queue
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
