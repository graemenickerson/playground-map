import { useId } from "react";

type SegmentedControlProps<T extends string | null> = {
  label: string;
  value: T;
  options: readonly {
    label: string;
    value: T;
  }[];
  onChange: (value: T) => void;
  describedBy?: string;
};

export default function SegmentedControl<T extends string | null>({
  label,
  value,
  options,
  onChange,
  describedBy,
}: SegmentedControlProps<T>) {
  const labelId = useId();

  return (
    <div className="segmented-control">
      <span id={labelId} className="segmented-control__label">
        {label}
      </span>

      <div
        className="segmented-control__buttons"
        role="group"
        aria-labelledby={labelId}
        aria-describedby={describedBy}
      >
        {options.map((option) => (
          <button
            key={option.value ?? "any"}
            type="button"
            aria-pressed={value === option.value}
            onClick={() => {
              if (option.value !== value) {
                onChange(option.value);
              }
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
