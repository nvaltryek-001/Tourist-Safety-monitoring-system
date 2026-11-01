/**
 * Grid clustering for map markers. Points are bucketed by a grid whose cell
 * size shrinks as the zoom level grows, so clusters split apart on zoom-in.
 */
export interface ClusterPoint<T> {
  lat: number;
  lon: number;
  item: T;
}

export interface Cluster<T> {
  lat: number;
  lon: number;
  items: T[];
}

export function cellSizeDegrees(zoom: number): number {
  return 360 / Math.pow(2, Math.max(0, Math.min(22, zoom))) / 4;
}

export function clusterPoints<T>(points: ClusterPoint<T>[], zoom: number, threshold = 40): Cluster<T>[] {
  if (points.length <= threshold || zoom >= 16) {
    return points.map((p) => ({ lat: p.lat, lon: p.lon, items: [p.item] }));
  }
  const size = cellSizeDegrees(zoom);
  const cells = new Map<string, { lat: number; lon: number; items: T[] }>();
  for (const p of points) {
    const key = `${Math.floor(p.lat / size)}:${Math.floor(p.lon / size)}`;
    const cell = cells.get(key);
    if (cell) {
      cell.lat += p.lat;
      cell.lon += p.lon;
      cell.items.push(p.item);
    } else {
      cells.set(key, { lat: p.lat, lon: p.lon, items: [p.item] });
    }
  }
  return [...cells.values()].map((c) => ({ lat: c.lat / c.items.length, lon: c.lon / c.items.length, items: c.items }));
}
