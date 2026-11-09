import { useEffect, useState } from "react";
import PlaygroundMap from "./components/PlaygroundMap";
import PlaygroundSearch from "./components/PlaygroundSearch";
import "./components/PlaygroundSearch.css";
import {
  EquipmentReviewListSchema,
  type EquipmentReview,
} from "./types/equipment-review";
import {
  PlaygroundListSchema,
  type Playground,
  type PlaygroundFilters,
  type PlaygroundList,
} from "./types/playground";

const EMPTY_PLAYGROUNDS: Playground[] = [];

type LoadState = {
  data: PlaygroundList | null;
  isLoading: boolean;
  error: string | null;
};

export default function App() {
  const [state, setState] = useState<LoadState>({
    data: null,
    isLoading: true,
    error: null,
  });
  const [appliedFilters, setAppliedFilters] =
    useState<PlaygroundFilters>({
      q: "",
      age: null,
      washroom: false,
    });
  const [reviewEquipment, setReviewEquipment] = useState<
    EquipmentReview[]
  >([]);
  const [reviewError, setReviewError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    setState((previous) => ({
      ...previous,
      isLoading: true,
      error: null,
    }));

    async function loadPlaygrounds() {
      try {
        const parameters = new URLSearchParams();

        if (appliedFilters.q) {
          parameters.set("q", appliedFilters.q);
        }
        if (appliedFilters.age !== null) {
          parameters.set("age", String(appliedFilters.age));
        }
        if (appliedFilters.washroom) {
          parameters.set("washroom", "true");
        }

        const queryString = parameters.toString();
        const url = queryString
          ? `/api/playgrounds?${queryString}`
          : "/api/playgrounds";

        const response = await fetch(url, {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`API request failed (${response.status})`);
        }

        const raw: unknown = await response.json();
        const data = PlaygroundListSchema.parse(raw);

        if (!controller.signal.aborted) {
          setState({ data, isLoading: false, error: null });
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        console.error("Could not load playgrounds", error);
        setState((previous) => ({
          ...previous,
          isLoading: false,
          error: "Could not load playgrounds. Please try searching again.",
        }));
      }
    }

    void loadPlaygrounds();

    return () => controller.abort();
  }, [appliedFilters]);

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

  const playgrounds = state.data?.items ?? EMPTY_PLAYGROUNDS;
  const count = playgrounds.length;

  let resultSummary: string;

  if (state.isLoading) {
    resultSummary = state.data
      ? "Updating results…"
      : "Loading playgrounds…";
  } else if (state.error) {
    resultSummary = state.data
      ? `Showing previous results (${count}).`
      : "No results loaded.";
  } else if (state.data?.hasMore) {
    resultSummary = `Showing the first ${count} matching playgrounds.`;
  } else {
    resultSummary =
      `${count} ${count === 1 ? "playground" : "playgrounds"} found.`;
  }

  function clearFilters() {
    setAppliedFilters({
      q: "",
      age: null,
      washroom: false,
    });
  }

  return (
    <main>
      <h1>Victoria playgrounds</h1>

      <div className="playground-explorer">
        <PlaygroundMap
          playgrounds={playgrounds}
          reviewEquipment={reviewEquipment}
        />

        <PlaygroundSearch
          onSearch={setAppliedFilters}
          onClear={clearFilters}
          isLoading={state.isLoading}
          resultSummary={resultSummary}
          error={state.error}
        />
      </div>

      {reviewError && <p role="alert">{reviewError}</p>}

      {state.data && (
        <section aria-label="Matching playgrounds">
          {count === 0 ? (
            <p>No playgrounds match these filters.</p>
          ) : (
            <ul>
              {playgrounds.map((playground) => (
                <li key={playground._id}>
                  {playground.name ?? "Unnamed playground"}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
