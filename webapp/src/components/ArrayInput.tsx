interface Props {
  label: string;
  values: string[];
  onChange: (v: string[]) => void;
  placeholder?: string;
  hint?: string;
  max?: number;
}

export function ArrayInput({
  label,
  values,
  onChange,
  placeholder,
  hint,
  max = 16,
}: Props) {
  const rows = values.length ? values : [""];
  const set = (i: number, v: string) => {
    const next = [...rows];
    next[i] = v;
    onChange(next.filter((x, idx) => x !== "" || idx < next.length));
  };
  const add = () => onChange([...values, ""]);
  const remove = (i: number) => onChange(values.filter((_, idx) => idx !== i));

  return (
    <div style={{ marginBottom: 12 }}>
      <label>
        {label}{" "}
        <span className="faint tiny">
          ({values.filter((v) => v.trim()).length}
          {max ? ` / ${max}` : ""})
        </span>
      </label>
      {hint && (
        <div className="faint tiny" style={{ marginBottom: 6 }}>
          {hint}
        </div>
      )}
      {rows.map((v, i) => (
        <div className="array-input-row" key={i}>
          <input
            value={v}
            placeholder={placeholder}
            onChange={(e) => set(i, e.target.value)}
          />
          <button
            type="button"
            className="small ghost"
            onClick={() => remove(i)}
            disabled={values.length === 0}
            title="Remove"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="small"
        onClick={add}
        disabled={values.length >= max}
      >
        + Add
      </button>
    </div>
  );
}
