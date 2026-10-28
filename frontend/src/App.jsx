import { lazy, Suspense, useEffect, useState } from "react";
import { api, setCallListener } from "./api.js";
import RecommendStep from "./steps/RecommendStep.jsx";
import InventoryStep from "./steps/InventoryStep.jsx";
import AppointmentStep from "./steps/AppointmentStep.jsx";
import CallbackStep from "./steps/CallbackStep.jsx";
import ApiLog from "./ApiLog.jsx";

// The voice SDK is large; load it separately so the manual demo stays light.
const VoicePanel = lazy(() => import("./voice/VoicePanel.jsx"));

export default function App() {
  const [stores, setStores] = useState([]);
  const [product, setProduct] = useState(null);
  const [storeId, setStoreId] = useState("");
  const [calls, setCalls] = useState([]);
  const [callbackReason, setCallbackReason] = useState("");

  useEffect(() => {
    setCallListener((call) => setCalls((prev) => [call, ...prev].slice(0, 20)));
    api.stores().then((d) => {
      setStores(d.stores);
      setStoreId(d.stores[0]?.id || "");
    }).catch(() => {});
  }, []);

  const escalate = (reason) => {
    setCallbackReason(reason);
    document.getElementById("callback")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="layout">
      <header>
        <h1>AceAssist</h1>
        <p>Baseline Tennis Co. shopping assistant · backend workflow demo</p>
      </header>

      <main>
        <Suspense fallback={<section className="voice"><p className="muted">Loading voice assistant…</p></section>}>
          <VoicePanel />
        </Suspense>
        <RecommendStep selected={product} onSelect={setProduct} onEscalate={escalate} />
        <InventoryStep product={product} stores={stores} storeId={storeId} onStoreChange={setStoreId} />
        <AppointmentStep product={product} stores={stores} storeId={storeId} onEscalate={escalate} />
        <CallbackStep stores={stores} reason={callbackReason} onReasonChange={setCallbackReason} />
      </main>

      <aside>
        <ApiLog calls={calls} />
      </aside>
    </div>
  );
}
