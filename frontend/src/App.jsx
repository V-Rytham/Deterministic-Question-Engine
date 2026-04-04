import { useRef, useState } from "react";
import { generateMcqs } from "./api.js";
import McqList from "./components/McqList.jsx";
import ProductShowcase from "./components/ProductShowcase.jsx";

export default function App() {
  const [bookIdInput, setBookIdInput] = useState("");
  const [mcqs, setMcqs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const generatorRef = useRef(null);

  function resolveBookId() {
    const trimmed = String(bookIdInput).trim();
    if (!trimmed) {
      return null;
    }

    const numeric = Number(trimmed);
    if (!Number.isInteger(numeric) || numeric < 1) {
      return null;
    }

    return numeric;
  }

  async function onGenerate() {
    setError("");
    setMcqs([]);
    const id = resolveBookId();

    if (!id) {
      setError("Please enter a valid positive Gutenberg Book ID (numbers only).");
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

  function scrollToGenerator() {
    generatorRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="app">
      <ProductShowcase onTryClick={scrollToGenerator} />

      <div className="panel" id="generator-panel" ref={generatorRef}>
        <div className="panel-title-row">
          <h2>Generate MCQs</h2>
          <p>Enter a Gutenberg Book ID to run the deterministic pipeline.</p>
        </div>

        <div className="row">
          <div className="book-id-input-wrap">
            <label htmlFor="book-id-input" className="book-id-label">
              Enter Gutenberg Book ID (e.g., 1342)
            </label>
            <input
              id="book-id-input"
              type="text"
              inputMode="numeric"
              pattern="[0-9]*"
              placeholder="e.g., 1342 for Pride and Prejudice"
              value={bookIdInput}
              onChange={(event) => {
                const next = event.target.value.replace(/\D+/g, "");
                setBookIdInput(next);
                if (error) {
                  setError("");
                }
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  onGenerate();
                }
              }}
              disabled={loading}
              aria-label="Enter Gutenberg Book ID"
            />
            <p className="book-id-help">
              Find book IDs at{" "}
              <a href="https://www.gutenberg.org/" target="_blank" rel="noreferrer">
                Project Gutenberg
              </a>
              .
            </p>
            <p className="book-id-help">
              <a href="https://www.gutenberg.org/ebooks/" target="_blank" rel="noreferrer">
                Don’t know the ID? Browse books on Project Gutenberg
              </a>
            </p>
          </div>

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
