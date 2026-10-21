import { useEffect, useState } from "react";
import PlaygroundMap from "./components/PlaygroundMap";
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
          <PlaygroundMap playgrounds={state.data.items} />

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
