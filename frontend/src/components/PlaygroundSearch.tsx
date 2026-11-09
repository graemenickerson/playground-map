import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import SegmentedControl from "./SegmentedControl";
import {
  PlaygroundFiltersSchema,
  type PlaygroundFilters,
} from "../types/playground";

const EMPTY_FILTERS: PlaygroundFilters = {
  q: "",
  age: null,
  washroom: false,
};

const AGE_OPTIONS = [
  { label: "Any age", value: null },
  { label: "Ages 2–5", value: "2-5" },
  { label: "Ages 5–12", value: "5-12" },
] as const;

type PlaygroundSearchProps = {
  onSearch: (filters: PlaygroundFilters) => void;
  onClear: () => void;
  isLoading: boolean;
  resultSummary: string;
  error: string | null;
};

export default function PlaygroundSearch({
  onSearch,
  onClear,
  isLoading,
  resultSummary,
  error,
}: PlaygroundSearchProps) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [validationError, setValidationError] = useState<string | null>(
    null,
  );
  const searchTimer = useRef<number | undefined>(undefined);

  useEffect(() => {
    return () => window.clearTimeout(searchTimer.current);
  }, []);

  function cancelPendingSearch() {
    window.clearTimeout(searchTimer.current);
    searchTimer.current = undefined;
  }

  function applyFilters(
    nextFilters: PlaygroundFilters,
    debounce = false,
  ) {
    cancelPendingSearch();
    setFilters(nextFilters);

    const result = PlaygroundFiltersSchema.safeParse(nextFilters);

    if (!result.success) {
      setValidationError("Check the search name and child's age range.");
      return;
    }

    setValidationError(null);
    if (debounce) {
      searchTimer.current = window.setTimeout(() => {
        searchTimer.current = undefined;
        onSearch(result.data);
      }, 300);
    } else {
      onSearch(result.data);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    applyFilters(filters);
  }

  function handleClear() {
    cancelPendingSearch();
    setFilters(EMPTY_FILTERS);
    setValidationError(null);
    onClear();
  }

  return (
    <section
      className="playground-search"
      aria-label="Playground search"
      aria-busy={isLoading}
    >
      <details open>
        <summary>Find a playground</summary>

        <form onSubmit={handleSubmit}>
          <label className="playground-search__field">
            Playground or park name
            <input
              type="search"
              name="q"
              maxLength={100}
              placeholder="Search..."
              value={filters.q}
              onChange={(event) =>
                applyFilters(
                  { ...filters, q: event.target.value },
                  true,
                )
              }
            />
          </label>

          <SegmentedControl
            label="Child’s age range"
            value={filters.age}
            options={AGE_OPTIONS}
            describedBy="child-age-help"
            onChange={(age) =>
              applyFilters({
                ...filters,
                age,
              })
            }
          />

          <p id="child-age-help" className="playground-search__hint">
            Matches equipment covering the selected age range.
          </p>

          <label className="playground-search__checkbox">
            <input
              type="checkbox"
              name="washroom"
              checked={filters.washroom}
              onChange={(event) =>
                applyFilters({
                  ...filters,
                  washroom: event.target.checked,
                })
              }
            />
            Washroom in park
          </label>

          <div className="playground-search__actions">
            <button type="button" onClick={handleClear}>
              Clear filters
            </button>
          </div>
        </form>
      </details>

      <p role="status">{resultSummary}</p>

      {(validationError || error) && (
        <p role="alert">{validationError ?? error}</p>
      )}
    </section>
  );
}
