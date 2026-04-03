const base =
  import.meta.env.VITE_API_BASE?.replace(/\/$/, "") || "http://localhost:5000";

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function fetchJson(url, init) {
  const res = await fetch(url, init);
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`Invalid JSON from server (${res.status})`);
  }
  return { res, data };
}

export async function searchBooks(query, signal) {
  const term = String(query || "").trim();
  if (term.length < 2) return [];

  const url = `${base}/books/search?q=${encodeURIComponent(term)}&limit=8`;
  const { res, data } = await fetchJson(url, { signal });

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

  return Array.isArray(data) ? data : [];
}

export async function getMcqs(bookId, limit = 10) {
  const { res, data } = await fetchJson(`${base}/mcqs/${bookId}?limit=${limit}`);
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

/**
 * @param {number} bookId
 * @returns {Promise<{ mcqs: { question: string; options: string[]; correct_answer: string }[] }>}
 */
export async function generateMcqs(bookId) {
  const { res, data } = await fetchJson(`${base}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ book_id: bookId }),
  });

  // If the backend returns 202, the pipeline is running in the background.
  // Poll /mcqs until results exist (Render-friendly: avoids gateway timeouts).
  if (res.status === 202) {
    const maxMinutes = 30;
    const intervalMs = 10_000;
    const maxTries = Math.ceil((maxMinutes * 60_000) / intervalMs);

    for (let i = 0; i < maxTries; i++) {
      await sleep(intervalMs);
      const out = await getMcqs(bookId, 10);
      if (out?.mcqs?.length) return out;
    }
    throw new Error(
      "Still processing after 30 minutes. Check backend logs or try again.",
    );
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
