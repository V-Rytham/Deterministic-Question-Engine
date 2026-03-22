const LABELS = ["A", "B", "C", "D"];

export default function McqList({ mcqs }) {
  if (!mcqs?.length) return null;

  return (
    <section className="panel" aria-live="polite">
      {mcqs.map((m, i) => (
        <div key={i} className="mcq">
          <div className="mcq-q">
            Q{i + 1}. {m.question}
          </div>
          {(m.options || []).map((opt, j) => (
            <div key={j} className="mcq-opt">
              {LABELS[j]}. {opt}
            </div>
          ))}
        </div>
      ))}
    </section>
  );
}
