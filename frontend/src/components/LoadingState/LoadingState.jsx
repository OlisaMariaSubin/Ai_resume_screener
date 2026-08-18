export default function LoadingState({ stage }) {
  return (
    <div className="card" role="status" aria-live="polite">
      <h2>Working…</h2>
      <p className="loading-stage">{stage}</p>
    </div>
  );
}
