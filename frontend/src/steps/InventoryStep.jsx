import { useEffect, useState } from "react";
import { api } from "../api.js";
import ErrorBox from "./ErrorBox.jsx";

export default function InventoryStep({ product, stores, storeId, onStoreChange }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  // Never show a stale availability answer for a different racket/store.
  useEffect(() => {
    setResult(null);
    setError(null);
  }, [product?.id, storeId]);

  const check = async () => {
    try {
      setResult(await api.inventory(product.id, storeId));
    } catch (err) {
      setError(err);
    }
  };

  return (
    <section>
      <h2>2. Check store inventory</h2>
      {!product ? (
        <p className="muted">Select a racket above first.</p>
      ) : (
        <>
          <div className="row">
            <span>
              <strong>{product.name}</strong> at
            </span>
            <select value={storeId} onChange={(e) => onStoreChange(e.target.value)}>
              {stores.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
            <button onClick={check}>Check stock</button>
          </div>
          <ErrorBox error={error} />
          {result && (
            <div className={result.in_stock ? "ok" : "notice"}>
              {result.in_stock
                ? `In stock: ${result.quantity} at ${result.store_name}.`
                : `Not in stock at ${result.store_name}.`}
              {result.other_stores_with_stock.length > 0 && (
                <div>
                  Available at:{" "}
                  {result.other_stores_with_stock.map((s) => (
                    <button key={s.store_id} className="link" onClick={() => onStoreChange(s.store_id)}>
                      {s.store_name} ({s.quantity})
                    </button>
                  ))}
                </div>
              )}
              {!result.in_stock && result.other_stores_with_stock.length === 0 && (
                <div>Not available at any store right now.</div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
