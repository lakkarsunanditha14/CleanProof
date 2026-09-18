// Must match backend/app/config.py (SLA_HOURS and VALID_WARDS).
export const CATEGORIES = [
  { value: 'garbage dump', label: 'Garbage dump', slaHours: 12 },
  { value: 'unswept street', label: 'Unswept street', slaHours: 24 },
  { value: 'blocked drain', label: 'Blocked drain', slaHours: 48 },
  { value: 'construction debris', label: 'Construction debris', slaHours: 72 },
];

export const WARDS = [
  { name: 'Ameerpet', lat: 17.4375, lng: 78.4483 },
  { name: 'Kukatpally', lat: 17.4948, lng: 78.3996 },
  { name: 'Madhapur', lat: 17.4483, lng: 78.3915 },
  { name: 'Secunderabad', lat: 17.4399, lng: 78.4983 },
  { name: 'Dilsukhnagar', lat: 17.3688, lng: 78.5247 },
  { name: 'Mehdipatnam', lat: 17.395, lng: 78.44 },
  { name: 'Begumpet', lat: 17.4447, lng: 78.4664 },
  { name: 'LB Nagar', lat: 17.3457, lng: 78.5522 },
  { name: 'Narsapur', lat: 17.7375, lng: 78.2842, district: 'Medak' }, // approximate town centre
];

export function wardLabel(w) {
  return w.district ? `${w.name} (${w.district} district)` : w.name;
}

export function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label || value;
}

// Must match DELAY_REASONS in backend/app/config.py.
export const DELAY_REASONS = [
  'Vehicle or staff shortage',
  'Heavy rain or waterlogging',
  'Access blocked (traffic, parked vehicles, event)',
  'Needed special equipment (JCB, tractor, suction machine)',
  'Waste much larger than reported',
  'Other',
];
