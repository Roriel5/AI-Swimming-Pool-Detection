import type {
  CoordinateDetectionResponse,
  ImageDetectionResponse,
  TimeSeriesResponse,
  ScanAreaResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function detectByCoordinates(
  lat: number,
  lng: number
): Promise<CoordinateDetectionResponse> {
  const res = await fetch(`${API_BASE}/detect-by-coordinates`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lat, lng }),
  });

  if (!res.ok) {
    throw new Error(`Detection failed: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function detectImage(
  file: File
): Promise<ImageDetectionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/detect-image`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(`Image detection failed: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function fetchTimeSeries(
  lat: number,
  lng: number,
  zoom: number = 18
): Promise<TimeSeriesResponse> {
  const res = await fetch(`${API_BASE}/time-series-analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lat, lng, zoom }),
  });

  if (!res.ok) {
    throw new Error(`Time-series analysis failed: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function scanArea(
  north: number,
  south: number,
  east: number,
  west: number,
  zoom: number = 18
): Promise<ScanAreaResponse> {
  const res = await fetch(`${API_BASE}/scan-area`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ north, south, east, west, zoom }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || `Area scan failed: ${res.status}`);
  }

  return res.json();
}
