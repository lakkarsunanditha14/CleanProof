import React, { useEffect, useRef, useState } from 'react';
import { Camera, X, MapPin, AlertCircle } from 'lucide-react';
import Button from './Button';
import { WARDS } from '../constants';

// Where the photo is, from measured facts only: distance to the nearest known ward centre.
// (No place-name lookup: map boundaries can name the wrong village or mandal.)
// Street name from OpenStreetMap, only when the GPS fix is precise enough (phone GPS, not
// Wi-Fi/laptop location), so a wrong street is never shown. Only the road name is used.
const STREET_MAX_ACCURACY_M = 30;

async function streetName(lat, lng) {
  try {
    const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=17&accept-language=en&lat=${lat}&lon=${lng}`);
    return (await res.json()).address?.road || '';
  } catch {
    return '';
  }
}

function nearestWard(lat, lng) {
  const km = (w) => Math.hypot((w.lat - lat) * 111, (w.lng - lng) * 111 * Math.cos((lat * Math.PI) / 180));
  const nearest = [...WARDS].sort((x, y) => km(x) - km(y))[0];
  return km(nearest) < 20 ? `near ${nearest.name} (${km(nearest).toFixed(1)} km)` : `GPS ${lat.toFixed(5)}, ${lng.toFixed(5)}`;
}

export default function CameraCapture({ onCapture, onCancel, stampLabel = 'New report' }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [location, setLocation] = useState({ state: 'pending' });
  const [now, setNow] = useState(() => new Date());
  const [street, setStreet] = useState('');

  useEffect(() => {
    if (location.state === 'ok' && location.accuracy <= STREET_MAX_ACCURACY_M) {
      streetName(location.lat, location.lng).then(setStreet);
    }
  }, [location]);

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;
    navigator.mediaDevices
      ?.getUserMedia({ video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } }, audio: false })
      .then((stream) => {
        if (cancelled) return stream.getTracks().forEach((t) => t.stop());
        streamRef.current = stream;
        videoRef.current.srcObject = stream;
      })
      .catch((err) => {
        const messages = {
          NotAllowedError: 'Camera permission was blocked. Allow the camera for this site in the browser, then try again.',
          NotReadableError: 'The camera is being used by another tab or app (for example Zoom, Teams or another CleanProof tab). Close it and try again.',
          NotFoundError: 'No camera found on this device.',
        };
        setError(messages[err.name] || `The camera could not be opened (${err.name}). Close other tabs using it and try again.`);
      });
    if (!navigator.mediaDevices) setError('This browser cannot open the camera.');

    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => !cancelled && setLocation({ state: 'ok', lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
        () => !cancelled && setLocation({ state: 'failed' }),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    } else {
      setLocation({ state: 'failed' });
    }
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  function capture() {
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      const file = new File([blob], `live_capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
      onCapture({
        file,
        url: URL.createObjectURL(blob),
        lat: location.state === 'ok' ? location.lat : null,
        lng: location.state === 'ok' ? location.lng : null,
        street,
      });
    }, 'image/jpeg', 0.9);
  }

  if (error) {
    return (
      <div className="w-full aspect-[4/3] rounded-xl border-2 border-rose-200 bg-rose-50 flex flex-col items-center justify-center gap-3 p-6 text-center">
        <AlertCircle className="w-8 h-8 text-[#B42318]" />
        <p className="text-sm text-[#B42318]">{error}</p>
        <Button variant="outline" size="sm" onClick={onCancel}>Close camera</Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden bg-slate-900">
        <video ref={videoRef} autoPlay playsInline muted onLoadedData={() => setReady(true)} className="w-full h-full object-cover" />
        <div className="absolute inset-x-0 top-0 bg-black/55 px-3 py-2 text-white text-[11px] sm:text-xs leading-snug font-semibold">
          <p className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
            CleanProof | LIVE CAPTURE | {stampLabel}
          </p>
          <p>{now.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })} IST</p>
          <p>
            {location.state === 'ok' && `${street ? `${street}, ` : ''}${nearestWard(location.lat, location.lng)}, GPS accuracy ±${Math.round(location.accuracy)} m`}
            {location.state === 'pending' && 'GPS: locating...'}
            {location.state === 'failed' && 'GPS: not available'}
          </p>
        </div>
      </div>
      <p className="text-xs text-slate-600 flex items-center gap-1.5">
        <MapPin className="w-3.5 h-3.5" />
        {location.state === 'pending' && 'Getting your location...'}
        {location.state === 'ok' && `Location captured (accuracy about ${Math.round(location.accuracy)} m)`}
        {location.state === 'failed' && 'Location not available. Allow location access, otherwise the location check fails.'}
      </p>
      <div className="flex gap-3">
        <Button icon={Camera} onClick={capture} disabled={!ready || location.state === 'pending'} className="flex-1">
          {location.state === 'pending' ? 'Waiting for location...' : 'Capture photo'}
        </Button>
        <Button variant="outline" icon={X} onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}
