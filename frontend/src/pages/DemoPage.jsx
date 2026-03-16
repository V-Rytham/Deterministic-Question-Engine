import { useState } from "react";
import QuestionCard from "../components/QuestionCard";
import { downloadAllQuestions, fetchQuestionsByIsbn } from "../api/questionsApi";

export default function DemoPage() {
  const [isbn, setIsbn] = useState("");
  const [questions, setQuestions] = useState([]);
  const [statusMessage, setStatusMessage] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleGenerate = async () => {
    if (!isbn.trim()) {
      setError("Please enter an ISBN.");
      return;
    }

    setError("");
    setStatusMessage("");
    setQuestions([]);
    setIsLoading(true);

    try {
      const data = await fetchQuestionsByIsbn(isbn.trim());
      if (data.status === "completed") {
        setQuestions((data.questions || []).slice(0, 5));
      } else if (data.status === "unavailable") {
        setError("This book cannot be processed because it is not available on Project Gutenberg.");
      } else {
        setStatusMessage(data.message || "Generating questions from the book...");
      }
    } catch (requestError) {
      setError(requestError.message || "Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = async () => {
    try {
      await downloadAllQuestions(isbn.trim());
    } catch (requestError) {
      setError(requestError.message || "Could not download all questions.");
    }
  };

  return (
    <main className="page">
      <section className="hero">
        <h1>Automated Book Question Generator</h1>
        <p>Generate verification questions automatically from book content.</p>
      </section>

      <section className="controls card">
        <label htmlFor="isbn-input">Enter ISBN</label>
        <div className="input-row">
          <input
            id="isbn-input"
            type="text"
            placeholder="9780141439600"
            value={isbn}
            onChange={(event) => setIsbn(event.target.value)}
          />
          <button type="button" onClick={handleGenerate} disabled={isLoading}>
            Generate Questions
          </button>
        </div>
      </section>

      {isLoading && <p className="status">Generating questions from the book...</p>}
      {!isLoading && statusMessage && <p className="status">{statusMessage}</p>}
      {error && <p className="error">{error}</p>}

      {questions.length > 0 && (
        <section className="questions-list">
          {questions.map((question, index) => (
            <QuestionCard key={question.question_id || `${question.question}-${index}`} question={question} index={index} />
          ))}
          <button type="button" className="download-btn" onClick={handleDownload}>
            Download All Questions
          </button>
        </section>
      )}
    </main>
  );
}
