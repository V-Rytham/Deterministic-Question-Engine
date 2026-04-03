import { useRef, useState } from "react";
import { generateMcqs, searchBooks } from "./api.js";
import BookSearchInput from "./components/BookSearchInput.jsx";
import McqList from "./components/McqList.jsx";
import ProductShowcase from "./components/ProductShowcase.jsx";

export default function App() {
  const [bookQuery, setBookQuery] = useState("");
  const [selectedBook, setSelectedBook] = useState(null);
  const [mcqs, setMcqs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const generatorRef = useRef(null);

  function resolveBookId() {
    if (selectedBook?.id) {
      return selectedBook.id;
    }

    const fallbackId = parseInt(String(bookQuery).trim(), 10);
    if (Number.isNaN(fallbackId) || fallbackId < 1) {
      return null;
    }

    return fallbackId;
  }

  async function onGenerate() {
    setError("");
    setMcqs([]);
    const id = resolveBookId();

    if (!id) {
      setError("Select a book suggestion or enter a positive Gutenberg ID.");
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
          <p>Search by title or paste a Gutenberg ID to run the deterministic pipeline.</p>
        </div>

        <div className="row">
          <BookSearchInput
            value={bookQuery}
            onValueChange={setBookQuery}
            onBookSelect={setSelectedBook}
            searchBooks={searchBooks}
            disabled={loading}
            onEnter={onGenerate}
          />

          <button type="button" onClick={onGenerate} disabled={loading}>
            {loading ? "Loading…" : "Generate MCQs"}
          </button>
        </div>

        {selectedBook ? (
          <p className="selected-book">
            Selected: <strong>{selectedBook.title}</strong> (ID: {selectedBook.id})
          </p>
        ) : null}

        {error ? <div className="error">{error}</div> : null}
        {loading ? (
          <p className="loading">Running pipeline or loading from DB…</p>
        ) : null}
      </div>

      <McqList mcqs={mcqs} />
    </div>
  );
}
