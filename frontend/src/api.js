// Empty = same address as the page; the dev server passes /api and /static on to the backend.
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

// The cloud host accepts requests up to 4.5 MB; larger photos are shrunk before upload.
const MAX_UPLOAD = 4 * 1024 * 1024;

// Copies the camera data (EXIF: time, GPS) of `original` into the shrunk JPEG, with the
// orientation reset to normal because the browser already drew the pixels upright.
async function withExif(original, shrunk) {
  const src = new Uint8Array(await original.slice(0, 256 * 1024).arrayBuffer());
  const out = new Uint8Array(await shrunk.arrayBuffer());
  for (let i = 2; i + 4 < src.length && src[i] === 0xff; ) {
    const len = (src[i + 2] << 8) | src[i + 3];
    const isExif = src[i + 1] === 0xe1 && String.fromCharCode(...src.slice(i + 4, i + 8)) === 'Exif';
    if (isExif) {
      const app1 = src.slice(i, i + 2 + len);
      const tiff = 10;
      const le = app1[tiff] === 0x49;
      const u16 = (o) => (le ? app1[o] | (app1[o + 1] << 8) : (app1[o] << 8) | app1[o + 1]);
      const ifd = tiff + (le ? app1[tiff + 4] | (app1[tiff + 5] << 8) : (app1[tiff + 6] << 8) | app1[tiff + 7]);
      for (let e = 0; e < u16(ifd); e++) {
        const entry = ifd + 2 + e * 12;
        if (u16(entry) === 0x0112) { app1[entry + 8] = le ? 1 : 0; app1[entry + 9] = le ? 0 : 1; }
      }
      return new Blob([out.slice(0, 2), app1, out.slice(2)], { type: 'image/jpeg' });
    }
    if (src[i + 1] === 0xda) break; // image data starts: no EXIF
    i += 2 + len;
  }
  return shrunk;
}

async function shrinkPhoto(file) {
  if (!(file instanceof File) || file.size <= MAX_UPLOAD || !file.type.startsWith('image/')) return file;
  const img = await createImageBitmap(file);
  const scale = Math.min(1, 2560 / Math.max(img.width, img.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(img.width * scale);
  canvas.height = Math.round(img.height * scale);
  canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
  let blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.9));
  if (file.type === 'image/jpeg') blob = await withExif(file, blob);
  return new File([blob], file.name.replace(/\.\w+$/, '') + '.jpg', { type: 'image/jpeg' });
}

export async function fetchApi(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;
  if (options.body instanceof FormData && options.body.get('photo') instanceof File) {
    options.body.set('photo', await shrinkPhoto(options.body.get('photo')));
  }

  const defaultHeaders = {};
  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = 'API Request Failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch (e) {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail || `HTTP ${response.status}`);
  }

  return response.json();
}

// The backend stores absolute file paths and serves the files from /static/images.
export function imageUrl(path) {
  if (!path || !/\.(jpe?g|png|webp)$/i.test(path)) return null;
  return `${API_BASE_URL}/static/images/${path.split(/[\\/]/).pop()}`;
}

// Synthetic history records use sample photos (history_*.jpg), which the UI tags as samples.
export function isSamplePhoto(path) {
  return /(^|[\\/])history_[^\\/]*$/.test(path || '');
}

// Backend datetimes are UTC without a timezone suffix.
export function parseUtc(value) {
  if (!value) return null;
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`);
}

export function formatDateTime(value) {
  const d = parseUtc(value);
  return d ? d.toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '-';
}

export function formatHours(hours) {
  const totalMinutes = Math.round(Math.abs(hours) * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h >= 48) return `${Math.floor(h / 24)}d ${h % 24}h`;
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export { API_BASE_URL };
