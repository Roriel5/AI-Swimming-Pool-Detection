export interface Detection {
  confidence: number;
  bbox: [number, number, number, number]; // [xmin, ymin, xmax, ymax]
}

export interface GeoFeature {
  type: "Feature";
  properties: {
    confidence: number;
    pool_type?: string;
    type_confidence?: number;
  };
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
}

export interface RiskResult {
  risk_score: number;
  risk_level: "Low" | "Medium" | "High";
  risk_factors: string[];
}

export interface CoordinateDetectionResponse {
  type: "FeatureCollection";
  features: GeoFeature[];
  pools_detected: number;
  pools: Detection[];
  risk?: RiskResult;
}

export interface ImageDetectionResponse {
  pools_detected: number;
  detections: Detection[];
  pools: Detection[];
}

export interface TimeSeriesResponse {
  pool_added: boolean;
  pool_removed?: boolean;
  pools_added: number;
  pools_removed: number;
  change_detected: boolean;
  current_pool_count?: number;
  previous_pool_count?: number;
  current_count?: number;
  historical_count?: number;
}

export interface ScanAreaResponse {
  type: "FeatureCollection";
  features: GeoFeature[];
  pools_detected: number;
  tiles_scanned: number;
  risk: RiskResult;
}

export interface CoordinatePayload {
  lat: number;
  lng: number;
}

export interface AnalysisResult {
  coordinates: { lat: number; lng: number } | null;
  detections: Detection[];
  geoFeatures: GeoFeature[];
  loading: boolean;
  error: string | null;
  source: "coordinates" | "upload" | null;
  risk: RiskResult | null;
  timeSeries: TimeSeriesResponse | null;
  timeSeriesLoading: boolean;
  scanResult: ScanAreaResponse | null;
  scanLoading: boolean;
}

export type MapStyle = "satellite" | "streets";
