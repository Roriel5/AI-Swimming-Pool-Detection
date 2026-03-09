"use client";

import { useState, useCallback } from "react";
import type { AnalysisResult, ScanAreaResponse } from "@/types";
import {
  detectByCoordinates,
  detectImage,
  fetchTimeSeries,
  scanArea,
} from "@/api/detection";

const initialState: AnalysisResult = {
  coordinates: null,
  detections: [],
  geoFeatures: [],
  loading: false,
  error: null,
  source: null,
  risk: null,
  timeSeries: null,
  timeSeriesLoading: false,
  scanResult: null,
  scanLoading: false,
};

export function useDetection() {
  const [result, setResult] = useState<AnalysisResult>(initialState);

  const runCoordinateDetection = useCallback(async (lat: number, lng: number) => {
    setResult((prev) => ({
      ...prev,
      coordinates: { lat, lng },
      detections: [],
      geoFeatures: [],
      loading: true,
      error: null,
      source: "coordinates",
      risk: null,
      timeSeries: null,
      scanResult: null,
    }));

    try {
      const data = await detectByCoordinates(lat, lng);
      setResult((prev) => ({
        ...prev,
        detections: data.pools,
        geoFeatures: data.features || [],
        loading: false,
        risk: data.risk || null,
      }));
      return data.pools;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Detection failed";
      setResult((prev) => ({
        ...prev,
        loading: false,
        error: message,
      }));
      return [];
    }
  }, []);

  const runImageDetection = useCallback(async (file: File) => {
    setResult({
      ...initialState,
      loading: true,
      source: "upload",
    });

    try {
      const data = await detectImage(file);
      setResult((prev) => ({
        ...prev,
        detections: data.pools,
        geoFeatures: [],
        loading: false,
      }));
      return data.pools;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Image detection failed";
      setResult((prev) => ({
        ...prev,
        loading: false,
        error: message,
      }));
      return [];
    }
  }, []);

  const runTimeSeries = useCallback(async (lat: number, lng: number) => {
    setResult((prev) => ({ ...prev, timeSeriesLoading: true, timeSeries: null }));
    try {
      const data = await fetchTimeSeries(lat, lng);
      setResult((prev) => ({ ...prev, timeSeries: data, timeSeriesLoading: false }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Time-series failed";
      setResult((prev) => ({ ...prev, timeSeriesLoading: false, error: message }));
    }
  }, []);

  const runScanArea = useCallback(
    async (north: number, south: number, east: number, west: number, zoom?: number) => {
      setResult((prev) => ({ ...prev, scanLoading: true, scanResult: null }));
      try {
        const data = await scanArea(north, south, east, west, zoom);
        setResult((prev) => ({
          ...prev,
          scanResult: data,
          geoFeatures: data.features || [],
          scanLoading: false,
        }));
        return data;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Scan failed";
        setResult((prev) => ({ ...prev, scanLoading: false, error: message }));
        return null;
      }
    },
    []
  );

  const clearResults = useCallback(() => {
    setResult(initialState);
  }, []);

  return {
    result,
    runCoordinateDetection,
    runImageDetection,
    runTimeSeries,
    runScanArea,
    clearResults,
  };
}
