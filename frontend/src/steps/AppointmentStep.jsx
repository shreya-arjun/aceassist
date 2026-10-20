import { useEffect, useState } from "react";
import { api } from "../api.js";
import ErrorBox from "./ErrorBox.jsx";

// Two-phase booking, mirroring what the voice agent must do:
//   1. send confirmed=false -> backend validates and returns a read-back summary (409 confirmation_required)
//   2. shopper explicitly confirms -> resend with confirmed=true -> appointment is stored
export default function AppointmentStep({ product, stores, storeId, onEscalate }) {
  const [form, setForm] = useState({ service_type: "demo", customer_name: "", phone: "", preferred_time: "", notes: "" });
  const [summary, setSummary] = useState(null);
  const [booked, setBooked] = useState(null);
  const [error, setError] = useState(null);

  // Any change invalidates a pending confirmation.
  useEffect(() => setSummary(null), [form, product?.id, storeId]);

  const update = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  const storeName = stores.find((s) => s.id === storeId)?.name;

  const send = async (confirmed) => {
    setError(null);
    const body = {
      ...form,
      store_id: storeId,
      product_id: product?.id ?? null,
      notes: form.notes || null,
      confirmed,
    };
    try {
      setBooked(await api.bookAppointment(body));
      setSummary(null);
    } catch (err) {
      if (err.code === "confirmation_required") setSummary(err.details.summary);
      else setError(err);
    }
  };

  return (
    <section>
      <h2>3. Request a demo or restringing</h2>
      <p className="muted">
        Store: {storeName || "—"} · Racket: {product?.name || "none selected (fine for restringing)"}
      </p>
      <form className="grid" onSubmit={(e) => { e.preventDefault(); send(false); }}>
        <label>
          Service
          <select name="service_type" value={form.service_type} onChange={update}>
            <option value="demo">Demo the selected racket</option>
            <option value="restring">Restringing</option>
          </select>
        </label>
        <label>
          Name
          <input name="customer_name" value={form.customer_name} onChange={update} />
        </label>
        <label>
          Phone
          <input name="phone" value={form.phone} onChange={update} placeholder="(415) 555-0134" />
        </label>
        <label>
          Preferred time
          <input name="preferred_time" type="datetime-local" value={form.preferred_time} onChange={update} />
        </label>
        <label className="wide">
          Notes (optional)
          <input name="notes" value={form.notes} onChange={update} />
        </label>
        <button type="submit">Review details</button>
      </form>

      <ErrorBox error={error} onEscalate={() => onEscalate(`Couldn't book a ${form.service_type}: ${error?.message}`)} />

      {summary && (
        <div className="confirm">
          <p>Please confirm: <strong>{summary}</strong></p>
          <button onClick={() => send(true)}>Yes, book it</button>
          <button className="secondary" onClick={() => setSummary(null)}>Edit</button>
        </div>
      )}

      {booked && (
        <div className="ok">
          Request #{booked.appointment_id} saved ({booked.status}): {booked.summary}. {booked.next_step}
        </div>
      )}
    </section>
  );
}
