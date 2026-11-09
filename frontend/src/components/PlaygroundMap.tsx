import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

import type { Playground, SiteType } from "../types/playground";
import {
  ReviewLocationSchema,
  type EquipmentReview,
} from "../types/equipment-review";

const EMPTY_REVIEW: EquipmentReview[] = [];

const REVIEW_LABELS: Record<EquipmentReview["reason"], string> = {
  invalid_location: "Invalid location",
  no_park_match: "No matching park",
  multiple_park_matches: "Multiple matching parks",
  group_contains_assigned_equipment: "Group includes assigned equipment",
  group_validation_failed: "Playground group needs review",
};

const PIN_COLOURS: Record<SiteType, string> = {
  park: "#15803d",
  popup: "#eab308",
  school: "#9333ea",
  unknown: "#6b7280",
};

const SITE_LABELS: Record<SiteType, string> = {
  park: "Park playground",
  popup: "Pop-up playground",
  school: "School playground",
  unknown: "Unclassified playground",
};

type PlaygroundMapProps = {
  playgrounds: Playground[];
  reviewEquipment?: EquipmentReview[];
};

export default function PlaygroundMap({
  playgrounds,
  reviewEquipment = EMPTY_REVIEW,
}: PlaygroundMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | undefined>(undefined);
  const hasFittedRef = useRef(false);
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

    const reviewPoints = reviewEquipment.flatMap((equipment) => {
      const result = ReviewLocationSchema.safeParse(equipment.location);

      return result.success
        ? [{ equipment, coordinates: result.data.coordinates }]
        : [];
    });

    const pointCount = playgrounds.length + reviewPoints.length;

    let map = mapRef.current;
    const markers: mapboxgl.Marker[] = [];

    try {
      setError(null);

      if (!map) {
        map = new mapboxgl.Map({
          container,
          accessToken: token,
          style: "mapbox://styles/mapbox/streets-v12",
          center: [-123.3656, 48.4284],
          zoom: 12,
        });
        mapRef.current = map;

        map.addControl(new mapboxgl.NavigationControl());

        map.on("error", () => {
          setError("The map could not be loaded.");
        });
      }

      const bounds = new mapboxgl.LngLatBounds();

      for (const playground of playgrounds) {
        const coordinates = playground.location.coordinates;

        const marker = new mapboxgl.Marker({
          color: PIN_COLOURS[playground.siteType],
        })
          .setLngLat(coordinates)
          .setPopup(
            new mapboxgl.Popup().setText(
              `${playground.name ?? "Unnamed playground"} — ${
                SITE_LABELS[playground.siteType]
              }`,
            ),
          )
          .addTo(map);

        markers.push(marker);
        bounds.extend(coordinates);
      }

      for (const { equipment, coordinates } of reviewPoints) {
        const description = [
          `Equipment record ${equipment.sourceRecordId}`,
          `Equipment ID: ${equipment.equipmentId}`,
          REVIEW_LABELS[equipment.reason],
          equipment.details,
        ]
          .filter(Boolean)
          .join(" — ");

        const marker = new mapboxgl.Marker({ color: "#dc2626" })
          .setLngLat(coordinates)
          .setPopup(new mapboxgl.Popup().setText(description))
          .addTo(map);

        markers.push(marker);
        bounds.extend(coordinates);
      }

      if (!hasFittedRef.current && playgrounds.length > 0) {
        if (pointCount > 1) {
          map.fitBounds(bounds, {
            padding: 60,
            maxZoom: 16,
            duration: 0,
          });
        } else {
          map.jumpTo({
            center: playgrounds[0].location.coordinates,
            zoom: 16,
          });
        }

        hasFittedRef.current = true;
      }
    } catch (cause) {
      console.error("Could not initialize map", cause);
      map?.remove();
      map = undefined;
      mapRef.current = undefined;
      hasFittedRef.current = false;
      setError("The map could not be loaded.");
    }

    return () => {
      markers.forEach((marker) => marker.remove());
    };
  }, [playgrounds, reviewEquipment]);

  useEffect(() => {
    return () => {
      mapRef.current?.remove();
      mapRef.current = undefined;
      hasFittedRef.current = false;
    };
  }, []);

  return (
    <section aria-label="Playground map">
      {error && <p role="alert">{error}</p>}
      <div
        ref={containerRef}
        style={{ width: "100%", height: "1000px" }}
      />
    </section>
  );
}
