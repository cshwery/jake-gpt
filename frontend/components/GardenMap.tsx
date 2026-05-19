"use client";

import { useEffect, useRef, useState } from "react";
import area from "@turf/area";
import bbox from "@turf/bbox";
import MapboxDraw from "@mapbox/mapbox-gl-draw";
import mapboxgl from "mapbox-gl";
import { Check, MousePointer2, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { GardenRead, GeneratedPlan, PropertyRead } from "@/types/api";
import { areaCategory, areaWarning, formatArea } from "@/lib/product";

type Props = {
  property: PropertyRead;
  garden?: GardenRead | null;
  generatedPlan?: GeneratedPlan | null;
  dimmed?: boolean;
  onPolygon?: (polygon: GeoJSON.Polygon, areaSqM: number) => void;
  onClearPolygon?: () => void;
  onSaveBoundary?: () => void;
  canSaveBoundary?: boolean;
};

const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
type DrawMode = "select" | "polygon" | "lasso";
type ScreenPoint = { x: number; y: number };

export function GardenMap({ property, garden, generatedPlan, dimmed = false, onPolygon, onClearPolygon, onSaveBoundary, canSaveBoundary = false }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const drawRef = useRef<MapboxDraw | null>(null);
  const lassoRef = useRef<ScreenPoint[]>([]);
  const onPolygonRef = useRef(onPolygon);
  const onClearPolygonRef = useRef(onClearPolygon);
  const [localPolygon, setLocalPolygon] = useState<GeoJSON.Polygon | null>(garden?.polygon_geojson ?? null);
  const [drawMode, setDrawMode] = useState<DrawMode>("select");
  const [draftPoints, setDraftPoints] = useState<ScreenPoint[]>([]);
  const [isLassoing, setIsLassoing] = useState(false);
  const [areaSqM, setAreaSqM] = useState<number | null>(garden?.area_sq_m ?? null);
  const [zoom, setZoom] = useState<number>(19);
  const areaSqFt = areaSqM == null ? garden?.area_sq_ft ?? null : areaSqM * 10.7639;

  useEffect(() => {
    onPolygonRef.current = onPolygon;
    onClearPolygonRef.current = onClearPolygon;
  }, [onClearPolygon, onPolygon]);

  useEffect(() => {
    if (!token || !container.current || mapRef.current) return;
    mapboxgl.accessToken = token;
    const map = new mapboxgl.Map({
      container: container.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [property.longitude, property.latitude],
      zoom: 19
    });
    mapRef.current = map;
    const draw = new MapboxDraw({
      displayControlsDefault: false,
      defaultMode: "simple_select"
    });
    drawRef.current = draw;
    map.addControl(draw);
    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.addControl(new mapboxgl.ScaleControl({ maxWidth: 120, unit: "imperial" }), "bottom-right");
    map.on("zoom", () => setZoom(Number(map.getZoom().toFixed(1))));

    function handleDraw() {
      const feature = draw.getAll().features.find((item) => item.geometry.type === "Polygon");
      if (!feature || feature.geometry.type !== "Polygon") return;
      draw.deleteAll();
      draw.add(feature);
      setLocalPolygon(feature.geometry);
      const nextArea = area(feature);
      setAreaSqM(nextArea);
      onPolygonRef.current?.(feature.geometry, nextArea);
    }

    function handleDelete() {
      setLocalPolygon(null);
      setAreaSqM(null);
      onClearPolygonRef.current?.();
    }

    map.on("draw.create", handleDraw);
    map.on("draw.update", handleDraw);
    map.on("draw.delete", handleDelete);
    map.on("load", () => {
      if (garden?.polygon_geojson) {
        const feature: GeoJSON.Feature<GeoJSON.Polygon> = { type: "Feature", properties: {}, geometry: garden.polygon_geojson };
        draw.add(feature);
        const bounds = bbox(feature) as [number, number, number, number];
        map.fitBounds(bounds, { padding: 60, duration: 0 });
      } else {
        map.setZoom(Math.max(map.getZoom(), 19));
      }
    });

    return () => {
      map.remove();
      mapRef.current = null;
      drawRef.current = null;
    };
  }, [garden?.polygon_geojson, property.latitude, property.longitude]);

  useEffect(() => {
    if (!token || !mapRef.current || !drawRef.current || !garden?.polygon_geojson) return;
    const feature: GeoJSON.Feature<GeoJSON.Polygon> = { type: "Feature", properties: {}, geometry: garden.polygon_geojson };
    drawRef.current.deleteAll();
    drawRef.current.add(feature);
    setLocalPolygon(garden.polygon_geojson);
    setAreaSqM(garden.area_sq_m);
    mapRef.current.fitBounds(bbox(feature) as [number, number, number, number], { padding: 80, maxZoom: 21 });
  }, [garden?.area_sq_m, garden?.polygon_geojson]);

  function savePolygon(polygon: GeoJSON.Polygon) {
    const feature: GeoJSON.Feature<GeoJSON.Polygon> = { type: "Feature", properties: {}, geometry: polygon };
    const nextArea = area(feature);
    setLocalPolygon(polygon);
    setAreaSqM(nextArea);
    setDraftPoints([]);
    setDrawMode("select");
    onPolygonRef.current?.(polygon, nextArea);
  }

  function setMapboxMode(mode: DrawMode) {
    setDrawMode(mode);
    setDraftPoints([]);
    if (!drawRef.current || !onPolygon) return;
    if (mode === "polygon") {
      drawRef.current.changeMode("draw_polygon");
    } else {
      drawRef.current.changeMode("simple_select");
    }
  }

  function clearDrawing() {
    drawRef.current?.deleteAll();
    setLocalPolygon(null);
    setAreaSqM(null);
    setDraftPoints([]);
    setDrawMode("select");
    onClearPolygonRef.current?.();
  }

  function screenToGeo(point: ScreenPoint): [number, number] {
    return [property.longitude + (point.x - 50) * 0.0000032, property.latitude - (point.y - 50) * 0.0000024];
  }

  function completeMockPolygon(points: ScreenPoint[]) {
    if (points.length < 3) return;
    const ring = points.map(screenToGeo);
    ring.push(ring[0]);
    savePolygon({ type: "Polygon", coordinates: [ring] });
  }

  function zoomToProperty() {
    mapRef.current?.flyTo({ center: [property.longitude, property.latitude], zoom: 19, essential: true });
  }

  function zoomToGarden() {
    const polygon = garden?.polygon_geojson ?? localPolygon;
    if (!polygon || !mapRef.current) return;
    mapRef.current.fitBounds(bbox({ type: "Feature", properties: {}, geometry: polygon }) as [number, number, number, number], { padding: 80, maxZoom: 21 });
  }

  function handleMockClick(event: React.PointerEvent<HTMLDivElement>) {
    if (drawMode !== "polygon" || !onPolygon) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const point = { x: ((event.clientX - rect.left) / rect.width) * 100, y: ((event.clientY - rect.top) / rect.height) * 100 };
    setDraftPoints((points) => [...points, point]);
  }

  function startLasso(event: React.PointerEvent<HTMLDivElement>) {
    if (drawMode !== "lasso" || !onPolygon) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    const point = eventPoint(event);
    lassoRef.current = [point];
    setDraftPoints([point]);
    setIsLassoing(true);
  }

  function moveLasso(event: React.PointerEvent<HTMLDivElement>) {
    if (!isLassoing || drawMode !== "lasso") return;
    const point = eventPoint(event);
    const previous = lassoRef.current[lassoRef.current.length - 1];
    if (!previous || Math.hypot(point.x - previous.x, point.y - previous.y) > 1.2) {
      lassoRef.current = [...lassoRef.current, point];
      setDraftPoints(lassoRef.current);
    }
  }

  function finishLasso(event: React.PointerEvent<HTMLDivElement>) {
    if (!isLassoing || drawMode !== "lasso") return;
    event.currentTarget.releasePointerCapture(event.pointerId);
    setIsLassoing(false);
    const points = simplifyPoints(lassoRef.current);
    if (points.length >= 3) completeMockPolygon(points);
  }

  function eventPoint(event: React.PointerEvent<HTMLDivElement>): ScreenPoint {
    const rect = event.currentTarget.getBoundingClientRect();
    return { x: ((event.clientX - rect.left) / rect.width) * 100, y: ((event.clientY - rect.top) / rect.height) * 100 };
  }

  function startMapboxLasso(event: React.PointerEvent<HTMLDivElement>) {
    if (drawMode !== "lasso" || !mapRef.current || !onPolygon) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    mapRef.current.dragPan.disable();
    const point = eventPoint(event);
    lassoRef.current = [point];
    setDraftPoints([point]);
    setIsLassoing(true);
  }

  function moveMapboxLasso(event: React.PointerEvent<HTMLDivElement>) {
    if (!isLassoing || drawMode !== "lasso") return;
    moveLasso(event);
  }

  function finishMapboxLasso(event: React.PointerEvent<HTMLDivElement>) {
    if (!isLassoing || drawMode !== "lasso" || !mapRef.current) return;
    event.currentTarget.releasePointerCapture(event.pointerId);
    mapRef.current.dragPan.enable();
    setIsLassoing(false);
    const points = simplifyPoints(lassoRef.current);
    if (points.length < 3) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const ring = points.map((point) => {
      const lngLat = mapRef.current!.unproject([(point.x / 100) * rect.width, (point.y / 100) * rect.height]);
      return [lngLat.lng, lngLat.lat] as [number, number];
    });
    ring.push(ring[0]);
    const polygon: GeoJSON.Polygon = { type: "Polygon", coordinates: [ring] };
    drawRef.current?.deleteAll();
    drawRef.current?.add({ type: "Feature", properties: {}, geometry: polygon });
    savePolygon(polygon);
  }

  if (!token) {
    return (
      <div
        className="relative h-[520px] touch-none overflow-hidden rounded-lg border border-border bg-[linear-gradient(135deg,#44523b_0%,#87906a_40%,#384331_41%,#6d7656_70%,#2d3b2f_100%)]"
        onPointerDown={startLasso}
        onPointerMove={moveLasso}
        onPointerUp={finishLasso}
        onClick={handleMockClick}
      >
        <div className={dimmed ? "absolute inset-0 bg-white/55" : "absolute inset-0 bg-black/10"} />
        <div className="absolute left-4 top-4 rounded bg-white/90 px-3 py-2 text-sm shadow">
          Mapbox token is not configured. Using mock map mode.
        </div>
        <MapAreaReadout areaSqFt={areaSqFt} zoom={zoom} />
        <PolygonOverlay polygon={localPolygon} draftPoints={draftPoints} />
        {generatedPlan ? <PlanOverlay plan={generatedPlan} polygon={localPolygon} /> : null}
        {onPolygon ? <DrawingToolbar mode={drawMode} setMode={setDrawMode} clearDrawing={clearDrawing} finishPolygon={() => completeMockPolygon(draftPoints)} canFinish={draftPoints.length >= 3} onSaveBoundary={onSaveBoundary} canSaveBoundary={canSaveBoundary} zoomToProperty={() => undefined} zoomToGarden={() => undefined} hasGarden={Boolean(garden || localPolygon)} /> : null}
      </div>
    );
  }

  return (
    <div className="relative">
      <div ref={container} className="h-[520px] rounded-lg border border-border" />
      {drawMode === "lasso" ? (
        <div
          className="absolute inset-0 touch-none"
          onPointerDown={startMapboxLasso}
          onPointerMove={moveMapboxLasso}
          onPointerUp={finishMapboxLasso}
        >
          <PolygonOverlay polygon={null} draftPoints={draftPoints} />
        </div>
      ) : null}
      {dimmed ? <div className="pointer-events-none absolute inset-0 rounded-lg bg-white/45" /> : null}
      <MapAreaReadout areaSqFt={areaSqFt} zoom={zoom} />
      {generatedPlan ? <PlanOverlay plan={generatedPlan} polygon={garden?.polygon_geojson ?? localPolygon} /> : null}
      {onPolygon ? <DrawingToolbar mode={drawMode} setMode={setMapboxMode} clearDrawing={clearDrawing} finishPolygon={() => undefined} canFinish={false} onSaveBoundary={onSaveBoundary} canSaveBoundary={canSaveBoundary} zoomToProperty={zoomToProperty} zoomToGarden={zoomToGarden} hasGarden={Boolean(garden || localPolygon)} /> : null}
    </div>
  );
}

function MapAreaReadout({ areaSqFt, zoom }: { areaSqFt: number | null; zoom: number }) {
  const warning = areaSqFt ? areaWarning(areaSqFt) : null;
  return (
    <div className="absolute right-4 top-4 max-w-xs rounded-md bg-white/95 p-3 text-xs shadow">
      <div className="font-semibold">Step 1: Confirm property and zoom in</div>
      <div className="mt-1 text-foreground/70">Click each corner of the garden polygon. Draw only the actual planting area, not the whole property.</div>
      <div className="mt-2 rounded border border-border bg-muted/40 px-2 py-1">Tip: most backyard beds are 25-500 sq ft.</div>
      <div className="mt-2 font-medium">{formatArea(areaSqFt)}</div>
      {areaSqFt ? <div className="text-foreground/60">{areaCategory(areaSqFt)}</div> : null}
      <div className="mt-1 text-foreground/60">North ↑ · zoom {zoom.toFixed(1)}</div>
      {warning ? <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2 text-amber-900">{warning}</div> : null}
    </div>
  );
}

function DrawingToolbar({
  mode,
  setMode,
  clearDrawing,
  finishPolygon,
  canFinish,
  onSaveBoundary,
  canSaveBoundary,
  zoomToProperty,
  zoomToGarden,
  hasGarden
}: {
  mode: DrawMode;
  setMode: (mode: DrawMode) => void;
  clearDrawing: () => void;
  finishPolygon: () => void;
  canFinish: boolean;
  onSaveBoundary?: () => void;
  canSaveBoundary: boolean;
  zoomToProperty: () => void;
  zoomToGarden: () => void;
  hasGarden: boolean;
}) {
  return (
    <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 rounded-lg bg-white/95 p-2 shadow">
      <Button className={mode === "polygon" ? "" : "bg-muted text-foreground"} onClick={(event) => { event.stopPropagation(); setMode(mode === "polygon" ? "select" : "polygon"); }}>
        <MousePointer2 className="mr-2 h-4 w-4" /> {mode === "polygon" ? "Complete garden" : hasGarden ? "Edit garden boundary" : "Draw garden by choosing corners"}
      </Button>
      <Button className={mode === "lasso" ? "" : "bg-muted text-foreground"} onClick={(event) => { event.stopPropagation(); setMode(mode === "lasso" ? "select" : "lasso"); }}>
        <Pencil className="mr-2 h-4 w-4" /> Draw by hand
      </Button>
      {canFinish ? (
        <Button className="bg-accent text-foreground" onClick={(event) => { event.stopPropagation(); finishPolygon(); }}>
          <Check className="mr-2 h-4 w-4" /> Finish
        </Button>
      ) : null}
      <Button className="bg-muted text-foreground" onClick={(event) => { event.stopPropagation(); clearDrawing(); }}>
        <Trash2 className="mr-2 h-4 w-4" /> Clear
      </Button>
      <Button className="bg-muted text-foreground" onClick={(event) => { event.stopPropagation(); zoomToProperty(); }}>Zoom to property</Button>
      <Button className="bg-muted text-foreground" disabled={!hasGarden} onClick={(event) => { event.stopPropagation(); zoomToGarden(); }}>Zoom to garden</Button>
      {onSaveBoundary ? <Button disabled={!canSaveBoundary} onClick={(event) => { event.stopPropagation(); onSaveBoundary(); }}>Save garden boundary</Button> : null}
    </div>
  );
}

function PolygonOverlay({ polygon, draftPoints }: { polygon: GeoJSON.Polygon | null; draftPoints: ScreenPoint[] }) {
  const savedPoints = polygon ? geoToScreenPoints(polygon) : [];
  const saved = savedPoints.map((point) => `${point.x},${point.y}`).join(" ");
  const draft = draftPoints.map((point) => `${point.x},${point.y}`).join(" ");
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
      {savedPoints.length ? <polygon points={saved} fill="rgba(251, 191, 36, 0.25)" stroke="rgb(251, 191, 36)" strokeWidth="0.8" /> : null}
      {draftPoints.length ? <polyline points={draft} fill="none" stroke="rgb(251, 191, 36)" strokeDasharray="1.5 1.5" strokeWidth="0.7" /> : null}
      {draftPoints.map((point, index) => <circle key={`${point.x}-${point.y}-${index}`} cx={point.x} cy={point.y} r="0.9" fill="rgb(251, 191, 36)" />)}
    </svg>
  );
}

function geoToScreenPoints(polygon: GeoJSON.Polygon): ScreenPoint[] {
  const ring = polygon.coordinates[0] ?? [];
  if (!ring.length) return [];
  const lngs = ring.map(([lng]) => lng);
  const lats = ring.map(([, lat]) => lat);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const lngSpan = maxLng - minLng || 1;
  const latSpan = maxLat - minLat || 1;
  return ring.slice(0, -1).map(([lng, lat]) => ({
    x: 24 + ((lng - minLng) / lngSpan) * 48,
    y: 26 + (1 - (lat - minLat) / latSpan) * 42
  }));
}

function simplifyPoints(points: ScreenPoint[]): ScreenPoint[] {
  if (points.length <= 40) return points;
  const every = Math.ceil(points.length / 40);
  return points.filter((_, index) => index % every === 0);
}

function PlanOverlay({ plan, polygon }: { plan: GeneratedPlan; polygon: GeoJSON.Polygon | null }) {
  const points = polygon ? geoToScreenPoints(polygon) : rectanglePoints();
  const bounds = boundsFor(points);
  const polygonPoints = points.map((point) => `${point.x},${point.y}`).join(" ");

  return (
    <div className="pointer-events-none absolute inset-0">
      <svg className="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
        <defs>
          <clipPath id="garden-plan-clip">
            <polygon points={polygonPoints} />
          </clipPath>
        </defs>
        <polygon points={polygonPoints} fill="rgba(255, 255, 255, 0.42)" stroke="rgb(22, 101, 52)" strokeWidth="0.8" />
        <g clipPath="url(#garden-plan-clip)">
          {Array.from({ length: plan.layout_grid.cols + 1 }).map((_, index) => {
            const x = bounds.minX + (bounds.width / plan.layout_grid.cols) * index;
            return <line key={`v-${index}`} x1={x} x2={x} y1={bounds.minY} y2={bounds.maxY} stroke="rgba(22, 101, 52, 0.45)" strokeWidth="0.35" />;
          })}
          {Array.from({ length: plan.layout_grid.rows + 1 }).map((_, index) => {
            const y = bounds.minY + (bounds.height / plan.layout_grid.rows) * index;
            return <line key={`h-${index}`} x1={bounds.minX} x2={bounds.maxX} y1={y} y2={y} stroke="rgba(22, 101, 52, 0.45)" strokeWidth="0.35" />;
          })}
        </g>
      </svg>
      {plan.items.map((item) => (
        <div
          key={`${item.plant_id}-${item.row}-${item.col}`}
          className="absolute -translate-x-1/2 -translate-y-1/2 rounded bg-primary px-2 py-1 text-xs font-semibold text-white shadow"
          style={{
            left: `${bounds.minX + (item.x_pct / 100) * bounds.width}%`,
            top: `${bounds.minY + (item.y_pct / 100) * bounds.height}%`
          }}
        >
          {item.label}
        </div>
      ))}
    </div>
  );
}

function rectanglePoints(): ScreenPoint[] {
  return [
    { x: 24, y: 26 },
    { x: 72, y: 26 },
    { x: 72, y: 68 },
    { x: 24, y: 68 }
  ];
}

function boundsFor(points: ScreenPoint[]) {
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return { minX, maxX, minY, maxY, width: maxX - minX || 1, height: maxY - minY || 1 };
}
