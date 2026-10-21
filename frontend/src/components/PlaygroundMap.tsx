import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

import type { Playground } from "../types/playground";

type PlaygroundMapProps = {
  playgrounds: Playground[];
};

export default function PlaygroundMap({
  playgrounds,
}: PlaygroundMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    const token = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;

    if (!container) {
      return;
    }

    if (typeof token !== "string" || !token.startsWith("pk.")) {
      setError("The map is not configured yet.");
      return;
    }

    let map: mapboxgl.Map | undefined;

    try {
      setError(null);

      map = new mapboxgl.Map({
        container,
        accessToken: token,
        style: "mapbox://styles/mapbox/streets-v12",
        center: playgrounds[0]?.location.coordinates ?? [
          -123.3656,
          48.4284,
        ],
        zoom: playgrounds.length > 0 ? 16 : 12,
      });

      map.addControl(new mapboxgl.NavigationControl());

      map.on("error", () => {
        setError("The map could not be loaded.");
      });

      const bounds = new mapboxgl.LngLatBounds();

      for (const playground of playgrounds) {
        const coordinates = playground.location.coordinates;

        new mapboxgl.Marker()
          .setLngLat(coordinates)
          .setPopup(
            new mapboxgl.Popup().setText(
              playground.name ?? "Unnamed playground",
            ),
          )
          .addTo(map);

        bounds.extend(coordinates);
      }

      if (playgrounds.length > 1) {
        map.fitBounds(bounds, {
          padding: 60,
          maxZoom: 16,
          duration: 0,
        });
      }
    } catch (cause) {
      console.error("Could not initialize map", cause);
      map?.remove();
      map = undefined;
      setError("The map could not be loaded.");
    }

    return () => map?.remove();
  }, [playgrounds]);

  return (
    <section aria-label="Playground map">
      {error && <p role="alert">{error}</p>}
      <div
        ref={containerRef}
        style={{ width: "100%", height: "450px" }}
      />
    </section>
  );
}
