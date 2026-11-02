"use client";

/**
 * Imperative Google Maps overlays as React components.
 * The Circle follows the pattern of the Google Maps Platform 101 React codelab
 * (googlemaps-samples/codelab-maps-platform-101-react-js, Apache-2.0): create the
 * google.maps object once, sync options from props, attach it to the map from
 * GoogleMapsContext and detach on unmount. Polygon, Polyline and DirectionsRoute
 * apply the same pattern.
 */
import { GoogleMapsContext, useMapsLibrary } from "@vis.gl/react-google-maps";
import { useContext, useEffect, useRef } from "react";

type ClickHandler = () => void;

function useOverlay<T extends { setMap(map: google.maps.Map | null): void }>(factory: () => T): T {
  const ref = useRef<T | null>(null);
  if (!ref.current) ref.current = factory();
  const map = useContext(GoogleMapsContext)?.map;
  useEffect(() => {
    if (!map) return;
    ref.current!.setMap(map);
    return () => ref.current!.setMap(null);
  }, [map]);
  return ref.current;
}

function useClick(target: google.maps.MVCObject, onClick?: ClickHandler) {
  const cb = useRef(onClick);
  cb.current = onClick;
  useEffect(() => {
    const listener = google.maps.event.addListener(target, "click", () => cb.current?.());
    return () => listener.remove();
  }, [target]);
}

export function Circle({ onClick, ...options }: google.maps.CircleOptions & { onClick?: ClickHandler }) {
  const circle = useOverlay(() => new google.maps.Circle());
  circle.setOptions(options);
  useClick(circle, onClick);
  return null;
}

export function Polygon({ onClick, ...options }: google.maps.PolygonOptions & { onClick?: ClickHandler }) {
  const polygon = useOverlay(() => new google.maps.Polygon());
  polygon.setOptions(options);
  useClick(polygon, onClick);
  return null;
}

export function Polyline(options: google.maps.PolylineOptions) {
  const line = useOverlay(() => new google.maps.Polyline());
  line.setOptions(options);
  return null;
}

/** Draws a GeoJSON FeatureCollection with the Data layer (used for open-data layers). */
export function GeoJsonLayer({
  data,
  style,
  onFeatureClick,
}: {
  data: object | null;
  style: google.maps.Data.StylingFunction | google.maps.Data.StyleOptions;
  onFeatureClick?: (props: Record<string, unknown>, latLng: google.maps.LatLngLiteral | null) => void;
}) {
  const layer = useOverlay(() => new google.maps.Data());
  const cb = useRef(onFeatureClick);
  cb.current = onFeatureClick;
  useEffect(() => {
    layer.forEach((f) => layer.remove(f));
    if (data) layer.addGeoJson(data);
  }, [layer, data]);
  useEffect(() => {
    layer.setStyle(style);
  }, [layer, style]);
  useEffect(() => {
    const l = layer.addListener("click", (e: google.maps.Data.MouseEvent) => {
      const props: Record<string, unknown> = {};
      e.feature.forEachProperty((v, k) => (props[k] = v));
      cb.current?.(props, e.latLng ? e.latLng.toJSON() : null);
    });
    return () => l.remove();
  }, [layer]);
  return null;
}

export type RouteStatus = "idle" | "loading" | "ok" | "fallback";

/**
 * Driving route via the Directions service (requires "Directions API" on the key).
 * Falls back to a straight dashed line and reports "fallback" if the request fails.
 */
export function DirectionsRoute({
  from,
  to,
  onStatus,
}: {
  from: google.maps.LatLngLiteral;
  to: google.maps.LatLngLiteral;
  onStatus?: (status: RouteStatus, summary?: string) => void;
}) {
  const routes = useMapsLibrary("routes");
  const map = useContext(GoogleMapsContext)?.map;
  const statusCb = useRef(onStatus);
  statusCb.current = onStatus;

  useEffect(() => {
    if (!routes || !map) return;
    const renderer = new routes.DirectionsRenderer({
      map,
      suppressMarkers: true,
      preserveViewport: false,
      polylineOptions: { strokeColor: "#dc2626", strokeWeight: 5, strokeOpacity: 0.85 },
    });
    let fallback: google.maps.Polyline | null = null;
    let cancelled = false;
    statusCb.current?.("loading");
    new routes.DirectionsService()
      .route({ origin: from, destination: to, travelMode: google.maps.TravelMode.DRIVING })
      .then((res) => {
        if (cancelled) return;
        renderer.setDirections(res);
        const leg = res.routes[0]?.legs[0];
        statusCb.current?.("ok", leg ? `${leg.distance?.text ?? ""} · ${leg.duration?.text ?? ""}` : undefined);
      })
      .catch(() => {
        if (cancelled) return;
        fallback = new google.maps.Polyline({
          map,
          path: [from, to],
          strokeOpacity: 0,
          icons: [{ icon: { path: "M 0,-1 0,1", strokeOpacity: 1, strokeColor: "#dc2626", scale: 3 }, offset: "0", repeat: "14px" }],
        });
        statusCb.current?.("fallback", "Directions API unavailable — straight-line distance shown");
      });
    return () => {
      cancelled = true;
      renderer.setMap(null);
      fallback?.setMap(null);
    };
  }, [routes, map, from.lat, from.lng, to.lat, to.lng]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}
