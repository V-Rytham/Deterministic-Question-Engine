import { useEffect, useMemo, useRef, useState } from "react";

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function HighlightedText({ text, query }) {
  const parts = useMemo(() => {
    if (!query?.trim()) return [text];
    const safeQuery = escapeRegExp(query.trim());
    const regex = new RegExp(`(${safeQuery})`, "ig");
    return text.split(regex);
  }, [text, query]);

  return (
    <>
      {parts.map((part, idx) =>
        part.toLowerCase() === query.trim().toLowerCase() ? (
          <mark key={`${part}-${idx}`} className="suggestion-match">
            {part}
          </mark>
        ) : (
          <span key={`${part}-${idx}`}>{part}</span>
        ),
      )}
    </>
  );
}

export default function BookSearchInput({
  value,
  onValueChange,
  onBookSelect,
  searchBooks,
  disabled,
  onEnter,
}) {
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isSearching, setIsSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    if (value.trim().length < 2) {
      setResults([]);
      setOpen(false);
      setActiveIndex(-1);
      setSearched(false);
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setIsSearching(true);
      setSearched(true);
      try {
        const books = await searchBooks(value.trim(), controller.signal);
        setResults(books);
        setOpen(true);
        setActiveIndex(books.length ? 0 : -1);
      } catch {
        if (!controller.signal.aborted) {
          setResults([]);
          setOpen(true);
          setActiveIndex(-1);
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsSearching(false);
        }
      }
    }, 350);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [value, searchBooks]);

  useEffect(() => {
    function onOutsideClick(event) {
      if (!wrapperRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onOutsideClick);
    return () => document.removeEventListener("mousedown", onOutsideClick);
  }, []);

  function selectBook(book) {
    onValueChange(book.title);
    onBookSelect(book);
    setOpen(false);
    setActiveIndex(-1);
  }

  function onKeyDown(event) {
    if (!open || !results.length) {
      if (event.key === "Enter") onEnter();
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((prev) => (prev + 1) % results.length);
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((prev) => (prev - 1 + results.length) % results.length);
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      if (activeIndex >= 0) {
        selectBook(results[activeIndex]);
      } else {
        onEnter();
      }
    }

    if (event.key === "Escape") {
      setOpen(false);
    }
  }

  const showEmptyState = open && searched && !isSearching && !results.length && value.trim().length >= 2;

  return (
    <div className="book-search" ref={wrapperRef}>
      <input
        type="text"
        placeholder="Search for a book (e.g., Pride and Prejudice)"
        value={value}
        onChange={(event) => {
          onValueChange(event.target.value);
          onBookSelect(null);
        }}
        onFocus={() => {
          if (results.length || isSearching || showEmptyState) {
            setOpen(true);
          }
        }}
        onKeyDown={onKeyDown}
        disabled={disabled}
        aria-label="Search by book title or enter Gutenberg ID"
        aria-autocomplete="list"
        aria-expanded={open}
      />

      {open ? (
        <div className="book-dropdown" role="listbox">
          {isSearching ? <div className="book-message">Searching...</div> : null}

          {!isSearching &&
            results.map((book, idx) => (
              <button
                key={book.id}
                type="button"
                className={`book-option ${idx === activeIndex ? "active" : ""}`}
                onMouseDown={(event) => {
                  event.preventDefault();
                  selectBook(book);
                }}
              >
                <span className="book-title" title={book.title}>
                  📖 <HighlightedText text={book.title} query={value} />
                </span>
                <span className="book-author">✍️ {book.author}</span>
              </button>
            ))}

          {showEmptyState ? <div className="book-message">No results found</div> : null}
        </div>
      ) : null}
    </div>
  );
}
