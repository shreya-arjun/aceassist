export default function ApiLog({ calls }) {
  return (
    <div className="log">
      <h2>API log</h2>
      <p className="muted">The same calls an ElevenLabs agent would make as tools.</p>
      {calls.length === 0 && <p className="muted">No calls yet.</p>}
      {calls.map((c, i) => (
        <details key={i} open={i === 0}>
          <summary>
            <span className={c.status >= 200 && c.status < 300 ? "status ok-text" : "status err-text"}>
              {c.status || "ERR"}
            </span>{" "}
            {c.method} {c.url}
          </summary>
          {c.body && <pre>{JSON.stringify(c.body, null, 2)}</pre>}
          <pre>{JSON.stringify(c.data, null, 2)}</pre>
        </details>
      ))}
    </div>
  );
}
