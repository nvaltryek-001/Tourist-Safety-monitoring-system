export type Role = "SUPER_ADMIN" | "ADMIN" | "POLICE" | "TOURIST";

export interface StaffUser {
  id: number;
  name: string;
  email: string;
  role: Role;
}

export interface Session {
  token: string;
  expiresAt: string;
  user: StaffUser;
}

export interface Tourist {
  tourist_code: string;
  name: string;
  phone: string | null;
  college_email: string | null;
  enrollment_number: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  emergency_contact_email: string | null;
  latitude: number | null;
  longitude: number | null;
  location_accuracy: number | null;
  safety_status: string;
  last_location_update: string | null;
  location_stale: boolean | null;
  consent_given: boolean;
  created_at: string;
}

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Zone {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  zone_type: string;
  risk_level: string | null;
  description: string | null;
  active: boolean;
  geometry: GeoJSONGeometry | null;
  source: string | null;
  verification_status: string | null;
  category?: string | null;
  evidence?: string | null;
  synthetic: boolean;
  college_demo: boolean;
  updated_at: string | null;
}

export interface GeoJSONGeometry {
  type: "Polygon" | "MultiPolygon";
  coordinates: number[][][] | number[][][][];
}

export interface TimelineEvent {
  id: number;
  action: string;
  actor_type: string;
  actor_name: string | null;
  from_status: string | null;
  to_status: string | null;
  note: string | null;
  created_at: string;
}

export interface SOSAlert {
  id: number;
  tourist_code: string;
  tourist_name?: string;
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  message: string | null;
  alert_type: string;
  status: "OPEN" | "ACKNOWLEDGED" | "RESPONDING" | "RESOLVED" | "CANCELLED";
  assigned_officer_id: number | null;
  assigned_officer?: { id: number; name: string; badge_number: string | null };
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_outcome: string | null;
  resolution_notes: string | null;
  timeline?: TimelineEvent[];
  distance_meters?: number;
}

export interface Advisory {
  code: string;
  kind: string;
  risk_level: string;
  reason: string;
  evidence: Record<string, unknown>;
  recommended_action: string;
  confidence: number | null;
  timestamp: string;
}

export interface TouristAssessment {
  tourist_code: string;
  name: string;
  safety_status: string;
  risk_score: number;
  risk_level: string;
  advisories: Advisory[];
  kind: string;
}

export interface Overview {
  generated_at: string;
  kpis: Record<string, number>;
  tourist_status_distribution: Record<string, number>;
  zone_type_distribution: Record<string, number>;
  zone_risk_distribution: Record<string, number>;
  recent_sos: { id: number; tourist_code: string; status: string; alert_type: string; created_at: string }[];
  recent_events: { id: number; action: string; actor_type: string; target: string | null; created_at: string }[];
  stale_after_minutes: number;
}

export interface Officer {
  id: number;
  name: string;
  badge_number: string | null;
  station: string | null;
  active_incidents: number;
}

export interface AppNotification {
  id: number;
  category: string;
  title: string;
  body: string | null;
  created_at: string;
  read_at: string | null;
  related_sos_id: number | null;
}

export interface LiveEvent {
  type: string;
  data: Record<string, unknown>;
}

export type FacilityType = "POLICE" | "HOSPITAL" | "CLINIC" | "FIRE_STATION" | "PHARMACY";

export interface Facility {
  id: number;
  facility_type: FacilityType;
  name: string;
  latitude: number;
  longitude: number;
  phone: string | null;
  address: string | null;
  district: string | null;
  opening_hours: string | null;
  emergency: boolean | null;
  source: string;
  source_ref: string | null;
  active: boolean;
  distance_meters?: number;
}

export interface NearestHelp {
  location: { latitude: number; longitude: number } | null;
  police: Facility | null;
  hospital: Facility | null;
  fire_station: Facility | null;
}

export interface RouteRequest {
  from: [number, number];
  to: [number, number];
  label?: string;
}

export interface WeatherInfo {
  available: boolean;
  error?: string;
  current?: { temperature_2m?: number; precipitation?: number; wind_gusts_10m?: number; weather_code?: number };
  weather_risk_score?: number;
  weather_risk_level?: string;
  reasons?: string[];
  attribution?: string;
}
