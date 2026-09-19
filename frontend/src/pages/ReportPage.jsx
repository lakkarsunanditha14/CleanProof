import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Camera, MapPin, Crosshair, CheckCircle2, AlertCircle, Send, Search } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import Card from '../components/Card';
import Button from '../components/Button';
import Spinner from '../components/Spinner';
import SlaBadge from '../components/SlaBadge';
import CameraCapture from '../components/CameraCapture';
import { CATEGORIES, WARDS, categoryLabel, wardLabel } from '../constants';
import { fetchApi, formatDateTime } from '../api';
import exifr from 'exifr';

const inputClass =
  'w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#0F6E5C] focus:outline-none focus:ring-2 focus:ring-[#0F6E5C]/20';

function Field({ label, hint, children }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-semibold text-slate-800">{label}</span>
      {children}
      {hint && <span className="block text-xs text-slate-500">{hint}</span>}
    </label>
  );
}

export default function ReportPage() {
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0].value);
  const [ward, setWard] = useState(WARDS[0].name);
  const [description, setDescription] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [locating, setLocating] = useState(false);
  const [locationNote, setLocationNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [hasPhotoGps, setHasPhotoGps] = useState(null);

  async function handlePhoto(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    setPreview(URL.createObjectURL(file));

    try {
      const exifData = await exifr.parse(file, { gps: true, datetime: true });
      if (exifData && exifData.latitude != null && exifData.longitude != null) {
        setLatitude(exifData.latitude.toFixed(6));
        setLongitude(exifData.longitude.toFixed(6));
        setHasPhotoGps(true);
        const timeStr = exifData.DateTimeOriginal ? exifData.DateTimeOriginal.toLocaleString() : 'unknown time';
        setLocationNote(`Location taken from the photo (taken ${timeStr}).`);
      } else {
        setHasPhotoGps(false);
        setLocationNote('This photo has no location. Choose the ward or enter the location where the photo was taken.');
      }
    } catch (err) {
      setHasPhotoGps(false);
      setLocationNote('This photo has no location. Choose the ward or enter the location where the photo was taken.');
    }
  }

  function handleCapture({ file, url, lat, lng }) {
    setPhoto(file);
    setPreview(url);
    setCameraOpen(false);
    if (lat != null) {
      setLatitude(lat.toFixed(6));
      setLongitude(lng.toFixed(6));
      setLocationNote('Location taken from the live photo.');
      setHasPhotoGps(true);
    } else {
      setHasPhotoGps(null);
    }
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setLocationNote('Location is not available in this browser. Use the ward centre instead.');
      return;
    }
    setLocating(true);
    setLocationNote('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        setLocationNote(`Location captured (accuracy about ${Math.round(pos.coords.accuracy)} m).`);
        setLocating(false);
      },
      () => {
        setLocationNote('Could not get your location. Allow location access, or use the ward centre.');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  function useWardCentre() {
    const w = WARDS.find((x) => x.name === ward);
    setLatitude(String(w.lat));
    setLongitude(String(w.lng));
    setLocationNote(`Using the centre of ${w.name}.`);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (!photo) return setError('Please add a photo of the issue.');
    if (!title.trim()) return setError('Please add a short title.');
    if (latitude === '' || longitude === '') return setError('Please add the location.');

    const form = new FormData();
    form.append('photo', photo);
    form.append('title', title.trim());
    form.append('category', category);
    form.append('ward', ward);
    form.append('latitude', latitude);
    form.append('longitude', longitude);
    if (description.trim()) form.append('description', description.trim());

    setSubmitting(true);
    try {
      const complaint = await fetchApi('/api/complaints', { method: 'POST', body: form });
      setCreated(complaint);
    } catch (err) {
      setError(err.message || 'Could not submit the complaint.');
    } finally {
      setSubmitting(false);
    }
  }

  function reset() {
    setCreated(null);
    setPhoto(null);
    setPreview(null);
    setTitle('');
    setDescription('');
    setLatitude('');
    setLongitude('');
    setLocationNote('');
    setHasPhotoGps(null);
  }

  if (created) {
    return (
      <div className="max-w-xl mx-auto">
        <Card className="text-center space-y-5" padding="p-8">
          <div className="w-14 h-14 mx-auto rounded-full bg-emerald-50 text-[#0F6E5C] flex items-center justify-center">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Complaint submitted</h1>
            <p className="text-slate-600 mt-1">Keep this ID to track your complaint.</p>
          </div>
          <div className="text-5xl font-extrabold text-[#0F6E5C] tracking-tight">#{created.id}</div>
          <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-sm text-left space-y-2">
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Category</span>
              <span className="font-medium">{categoryLabel(created.category)}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Ward</span>
              <span className="font-medium">{created.ward}</span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Must be resolved by</span>
              <span className="font-medium">{formatDateTime(created.sla_deadline)}</span>
            </div>
            <div className="flex justify-between gap-4 items-center">
              <span className="text-slate-500">SLA</span>
              <SlaBadge slaStatus={created.sla_info?.status} />
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link to={`/track?id=${created.id}`}>
              <Button icon={Search} className="w-full sm:w-auto">Track this complaint</Button>
            </Link>
            <Button variant="outline" onClick={reset}>Report another issue</Button>
          </div>
        </Card>
      </div>
    );
  }

  const selected = CATEGORIES.find((c) => c.value === category);

  return (
    <div className="max-w-3xl mx-auto">
      <PageHeader
        title="Report an issue"
        subtitle="Add a photo and the location. The department must resolve it within the official deadline for its category."
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <Card className="space-y-5">
          <h2 className="font-bold text-slate-900 flex items-center gap-2">
            <Camera className="w-5 h-5 text-[#0F6E5C]" /> Photo of the issue
          </h2>
          {cameraOpen ? (
            <CameraCapture onCapture={handleCapture} onCancel={() => setCameraOpen(false)} />
          ) : (
          <label className="block cursor-pointer">
            <input type="file" accept="image/*" capture="environment" onChange={handlePhoto} className="sr-only" />
            {preview ? (
              <div className="relative">
                <img src={preview} alt="Selected issue" className="w-full max-h-80 object-cover rounded-xl border border-slate-200" />
                <span className="absolute bottom-3 right-3 bg-white/95 text-slate-700 text-xs font-medium px-3 py-1.5 rounded-lg shadow">
                  Change photo
                </span>
              </div>
            ) : (
              <div className="border-2 border-dashed border-slate-300 rounded-xl py-12 text-center hover:border-[#0F6E5C] hover:bg-emerald-50/40 transition-colors">
                <Camera className="w-10 h-10 mx-auto text-slate-400" />
                <p className="mt-3 font-medium text-slate-700">Upload a photo</p>
                <p className="text-xs text-slate-500 mt-1">JPG or PNG</p>
              </div>
            )}
          </label>
          )}
          {!cameraOpen && (
            <Button variant={preview ? 'outline' : 'primary'} icon={Camera} onClick={() => setCameraOpen(true)} className="w-full">
              {preview ? 'Retake with live camera' : 'Take live photo (fills the location too)'}
            </Button>
          )}
        </Card>

        <Card className="space-y-5">
          <h2 className="font-bold text-slate-900">Details</h2>
          <Field label="Title">
            <input className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Garbage pile near the bus stop" maxLength={120} />
          </Field>
          <div className="grid sm:grid-cols-2 gap-5">
            <Field label="Category" hint={selected && `Official deadline: ${selected.slaHours} hours`}>
              <select className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </Field>
            <Field label="Ward">
              <select className={inputClass} value={ward} onChange={(e) => setWard(e.target.value)}>
                {WARDS.map((w) => (
                  <option key={w.name} value={w.name}>{wardLabel(w)}</option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Description (optional)">
            <textarea className={`${inputClass} min-h-24`} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Anything that helps the team find and fix it" maxLength={500} />
          </Field>
        </Card>

        <Card className="space-y-5">
          <h2 className="font-bold text-slate-900 flex items-center gap-2">
            <MapPin className="w-5 h-5 text-[#0F6E5C]" /> Location
          </h2>
          <div className="flex flex-col sm:flex-row gap-3">
            {hasPhotoGps !== false && (
              <Button variant="primary" icon={Crosshair} onClick={useMyLocation} disabled={locating}>
                {locating ? 'Getting location...' : 'Use my location'}
              </Button>
            )}
            <Button variant="outline" icon={MapPin} onClick={useWardCentre}>Use ward centre</Button>
          </div>
          {locationNote && <p className="text-xs text-slate-600">{locationNote}</p>}
          <div className="grid grid-cols-2 gap-5">
            <Field label="Latitude">
              <input className={inputClass} type="number" step="any" value={latitude} onChange={(e) => setLatitude(e.target.value)} placeholder="17.4375" />
            </Field>
            <Field label="Longitude">
              <input className={inputClass} type="number" step="any" value={longitude} onChange={(e) => setLongitude(e.target.value)} placeholder="78.4483" />
            </Field>
          </div>
        </Card>

        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-[#B42318]">
            <AlertCircle className="w-5 h-5 shrink-0" />
            {error}
          </div>
        )}

        <Button type="submit" size="lg" icon={submitting ? undefined : Send} disabled={submitting} className="w-full">
          {submitting ? <><Spinner size="sm" className="border-white border-t-transparent" /> Submitting...</> : 'Submit complaint'}
        </Button>
      </form>
    </div>
  );
}
