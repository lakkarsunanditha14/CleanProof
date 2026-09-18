import React, { useEffect, useRef, useState } from 'react';
import { Camera, X, MapPin, AlertCircle } from 'lucide-react';
import Button from './Button';

// Live in-app camera. There is no gallery option, so an old photo cannot be chosen.
// The device location is read at the moment the camera is opened and sent with the photo.
export default function CameraCapture({ onCapture, onCancel }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const [location, setLocation] = useState({ state: 'pending' });

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
        setError(err.name === 'NotAllowedError'
          ? 'Camera permission was blocked. Allow the camera for this site in the browser, then try again.'
          : 'No camera found on this device.');
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
        <span className="absolute top-3 left-3 inline-flex items-center gap-1.5 rounded-full bg-rose-600 px-2.5 py-1 text-[11px] font-bold text-white">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" /> LIVE CAMERA
        </span>
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
