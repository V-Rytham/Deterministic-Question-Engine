const base =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "http://localhost:5000";

/**
 * @param {number} bookId
 * @returns {Promise<{ mcqs: { question: string; options: string[]; correct_answer: string }[] }>}
 */
export async function generateMcqs(bookId) {
  const res = await fetch(`${base}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: bookId }),
  });

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Invalid JSON from server (${res.status})`);
  }

  if (!res.ok) {
    const detail = data.detail;
    const msg =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg || d).join("; ")
          : JSON.stringify(detail || data);
    throw new Error(msg || `Request failed (${res.status})`);
  }

  return data;
}
