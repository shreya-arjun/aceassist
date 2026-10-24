import { useState } from "react";
import { api } from "../api.js";
import ErrorBox from "./ErrorBox.jsx";

export default function CallbackStep({ stores, reason, onReasonChange }) {
  const [form, setForm] = useState({ customer_name: "", phone: "", store_id: "" });
  const [done, setDone] = useState(null);
  const [error, setError] = useState(null);

  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      setDone(await api.requestCallback({ ...form, reason, store_id: form.store_id || null }));
    } catch (err) {
      setError(err);
    }
  };

  return (
    <section id="callback">
      <h2>4. Request a callback</h2>
      <p className="muted">The fallback when the assistant can't help.</p>
      <form className="grid" onSubmit={submit}>
        <label>
          Name
          <input name="customer_name" value={form.customer_name} onChange={update} />
        </label>
        <label>
          Phone
          <input name="phone" value={form.phone} onChange={update} />
        </label>
        <label>
          Store (optional)
          <select name="store_id" value={form.store_id} onChange={update}>
            <option value="">Any store</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>
        </label>
        <label className="wide">
          What do you need help with?
          <input value={reason} onChange={(e) => onReasonChange(e.target.value)} />
        </label>
        <button type="submit">Request callback</button>
      </form>
      <ErrorBox error={error} />
      {done && <div className="ok">Callback #{done.callback_id} logged. {done.message}</div>}
    </section>
  );
}
