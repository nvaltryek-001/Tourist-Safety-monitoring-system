import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

export type FacilityType = "POLICE" | "HOSPITAL" | "CLINIC" | "FIRE_STATION" | "PHARMACY";

export interface Facility {
  id: number;
  facility_type: FacilityType;
  name: string;
  latitude: number;
  longitude: number;
  phone: string | null;
  address: string | null;
  distance_meters?: number;
}

export interface NearbyHelp {
  location: { latitude: number; longitude: number };
  police: Facility | null;
  hospital: Facility | null;
  fire_station: Facility | null;
  nearby: Facility[];
}

export const FACILITY_COLOR: Record<FacilityType, string> = {
  POLICE: "#1d4ed8",
  HOSPITAL: "#be123c",
  CLINIC: "#e11d48",
  FIRE_STATION: "#c2410c",
  PHARMACY: "#059669",
};

export const FACILITY_LABEL: Record<FacilityType, string> = {
  POLICE: "Police",
  HOSPITAL: "Hospital",
  CLINIC: "Clinic",
  FIRE_STATION: "Fire station",
  PHARMACY: "Pharmacy",
};

export function useNearbyHelp(lat?: number | null, lon?: number | null) {
  const [data, setData] = useState<NearbyHelp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      const q = lat != null && lon != null ? `?lat=${lat}&lon=${lon}` : "";
      setData(await api<NearbyHelp>(`/api/v1/me/nearby-help${q}`));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load nearby help");
    } finally {
      setLoading(false);
    }
  }, [lat, lon]);
  useEffect(() => {
    void load();
  }, [load]);
  return { data, error, loading, reload: load };
}
