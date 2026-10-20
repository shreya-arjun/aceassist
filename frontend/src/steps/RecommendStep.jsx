import { useState } from "react";
import { api } from "../api.js";
import ErrorBox from "./ErrorBox.jsx";

export default function RecommendStep({ selected, onSelect, onEscalate }) {
  const [form, setForm] = useState({ max_price: 150, skill_level: "intermediate", playing_style: "" });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      setResult(await api.searchProducts(form));
    } catch (err) {
      setResult(null);
      setError(err);
    }
  };

  return (
    <section>
      <h2>1. Recommend a racket</h2>
      <form onSubmit={submit} className="row">
        <label>
          Budget ($)
          <input name="max_price" type="number" min="1" value={form.max_price} onChange={update} />
        </label>
        <label>
          Experience
          <select name="skill_level" value={form.skill_level} onChange={update}>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </label>
        <label>
          Playing style
          <select name="playing_style" value={form.playing_style} onChange={update}>
            <option value="">No preference</option>
            <option value="power">Power</option>
            <option value="control">Control</option>
            <option value="spin">Spin</option>
            <option value="all-court">All-court</option>
          </select>
        </label>
        <button type="submit">Find rackets</button>
      </form>

      <ErrorBox error={error} />

      {result && result.count === 0 && (
        <div className="notice">
          {result.suggestion}{" "}
          <button className="link" onClick={() => onEscalate("No racket fit my budget; want advice.")}>
            Request a callback
          </button>
        </div>
      )}

      <div className="cards">
        {result?.results.map((p) => (
          <div key={p.id} className={`card ${selected?.id === p.id ? "selected" : ""}`}>
            <strong>{p.name}</strong> <span className="muted">{p.brand}</span>
            <div className="price">${p.price.toFixed(2)}</div>
            <div className="muted">
              {p.playing_style} · {p.skill_levels.join(", ")} · {p.head_size_sq_in} sq in · {p.weight_g} g
            </div>
            <p>{p.description}</p>
            <button onClick={() => onSelect(p)}>{selected?.id === p.id ? "Selected" : "Select"}</button>
          </div>
        ))}
      </div>
    </section>
  );
}
