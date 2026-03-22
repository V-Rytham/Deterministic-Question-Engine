import { useState } from "react";
import { generateMcqs } from "./api.js";
import McqList from "./components/McqList.jsx";

export default function App() {
  const [bookId, setBookId] = useState("");
  const [mcqs, setMcqs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onGenerate() {
    setError("");
    setMcqs([]);
    const id = parseInt(String(bookId).trim(), 10);
    if (Number.isNaN(id) || id < 1) {
      setError("Enter a positive integer book id.");
      return;
    }

    setLoading(true);
    try {
      const data = await generateMcqs(id);
      setMcqs(data.mcqs || []);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>Deterministic MCQ Generator</h1>

      <div className="panel">
        <div className="row">
          <input
            type="text"
            inputMode="numeric"
            placeholder="Enter Book ID"
            value={bookId}
            onChange={(e) => setBookId(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && onGenerate()}
            disabled={loading}
            aria-label="Book ID"
          />
          <button type="button" onClick={onGenerate} disabled={loading}>
            {loading ? "Loading…" : "Generate MCQs"}
          </button>
        </div>
        {error ? <div className="error">{error}</div> : null}
        {loading ? (
          <p className="loading">Running pipeline or loading from DB…</p>
        ) : null}
      </div>

      <McqList mcqs={mcqs} />
    </div>
  );
}
