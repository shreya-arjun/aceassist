export default function ErrorBox({ error, onEscalate }) {
  if (!error) return null;
  const fields = error.details?.fields;
  const alternatives = error.details?.other_stores_with_stock;
  return (
    <div className="error">
      <strong>{error.code}</strong>: {error.message}
      {fields && (
        <ul>
          {fields.map((f, i) => (
            <li key={i}>{f.field ? `${f.field}: ` : ""}{f.issue}</li>
          ))}
        </ul>
      )}
      {alternatives?.length > 0 && (
        <div>In stock at: {alternatives.map((s) => s.store_name).join(", ")}</div>
      )}
      {onEscalate && (
        <button className="link" onClick={onEscalate}>Request a callback instead</button>
      )}
    </div>
  );
}
