import { useEffect, useState } from "react";
import PlaygroundMap from "./components/PlaygroundMap";
import {
  EquipmentReviewListSchema,
  type EquipmentReview,
} from "./types/equipment-review";
import {
  PlaygroundListSchema,
  type PlaygroundList,
} from "./types/playground";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; data: PlaygroundList };

export default function App() {
  const [state, setState] = useState<LoadState>({
    status: "loading",
  });
  const [reviewEquipment, setReviewEquipment] = useState<
    EquipmentReview[]
  >([]);
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPlaygrounds() {
      try {
        const response = await fetch("/api/playgrounds", {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`API request failed (${response.status})`);
        }

        const raw: unknown = await response.json();
        const data = PlaygroundListSchema.parse(raw);

        if (!controller.signal.aborted) {
          setState({ status: "ready", data });
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        console.error("Could not load playgrounds", error);
        setState({
          status: "error",
          message: "Could not load playgrounds. Check that Flask is running.",
        });
      }
    }

    void loadPlaygrounds();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadReviewEquipment() {
      try {
        const response = await fetch("/equipment-review.json", {
          signal: controller.signal,
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error(
            `Review request failed (${response.status})`,
          );
        }

        const raw: unknown = await response.json();
        const data = EquipmentReviewListSchema.parse(raw);

        if (!controller.signal.aborted) {
          setReviewEquipment(data);
          setReviewError(null);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        console.error("Could not load equipment review points", error);
        setReviewError("Equipment review points could not be loaded.");
      }
    }

    void loadReviewEquipment();

    return () => controller.abort();
  }, []);

  return (
    <main>
      <h1>Victoria playgrounds</h1>

      {state.status === "loading" && (
        <p role="status">Loading playgrounds…</p>
      )}

      {state.status === "error" && (
        <p role="alert">{state.message}</p>
      )}

      {state.status === "ready" && (
        <>
          <PlaygroundMap
            playgrounds={state.data.items}
            reviewEquipment={reviewEquipment}
          />

          {reviewError && <p role="alert">{reviewError}</p>}

          {state.data.items.length === 0 ? (
            <p>No playgrounds have been added yet.</p>
          ) : (
            <ul>
              {state.data.items.map((playground) => (
                <li key={playground._id}>
                  {playground.name ?? "Unnamed playground"}
                </li>
              ))}
            </ul>
          )}

          {state.data.hasMore && (
            <p>Showing the first {state.data.items.length} playgrounds.</p>
          )}
        </>
      )}
    </main>
  );
}
