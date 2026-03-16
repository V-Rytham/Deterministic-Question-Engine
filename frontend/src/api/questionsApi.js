const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function fetchQuestionsByIsbn(isbn) {
  const response = await fetch(`${API_BASE}/questions/${isbn}`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

export async function downloadAllQuestions(isbn) {
  const response = await fetch(`${API_BASE}/questions/all/${isbn}`);
  if (!response.ok) {
    throw new Error("Unable to download questions for this ISBN yet.");
  }
  const questions = await response.json();
  const blob = new Blob([JSON.stringify(questions, null, 2)], { type: "application/json" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = `questions_${isbn}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(href);
}
