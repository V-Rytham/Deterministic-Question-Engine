import { useEffect, useMemo, useState } from "react";

const pipelineStages = [
  {
    icon: "📚",
    title: "Fetch Book",
    detail: "Pulls Gutenberg content by ID and validates source metadata.",
  },
  {
    icon: "✂️",
    title: "Split & Clean",
    detail: "Normalizes text, removes noise, and chunks passages deterministically.",
  },
  {
    icon: "🧠",
    title: "NLP Processing",
    detail: "Runs predictable NLP transforms to capture meaningful sentence structure.",
  },
  {
    icon: "🔍",
    title: "Fact Extraction",
    detail: "Extracts candidate facts and evidence spans in a structured format.",
  },
  {
    icon: "❓",
    title: "MCQ Generation",
    detail: "Builds MCQs with stable logic so the same input yields the same output.",
  },
];

const featureCards = [
  {
    icon: "⚡",
    title: "Deterministic Output",
    description: "Same book + same pipeline = same MCQs every run.",
  },
  {
    icon: "🔁",
    title: "Reproducible Pipeline",
    description: "Every stage is explicit, traceable, and easy to verify.",
  },
  {
    icon: "🧩",
    title: "Structured NLP Extraction",
    description: "Facts and context are extracted in machine-friendly structure.",
  },
  {
    icon: "🚀",
    title: "API-Ready Backend",
    description: "Designed for product integration and programmatic workflows.",
  },
];

export default function ProductShowcase({ onTryClick }) {
  const [activeStep, setActiveStep] = useState(0);
  const [taglineIndex, setTaglineIndex] = useState(0);

  const taglines = useMemo(
    () => [
      "Deterministic in.",
      "Structured through every stage.",
      "Reproducible questions out.",
    ],
    []
  );

  useEffect(() => {
    const timer = window.setInterval(() => {
      setTaglineIndex((prev) => (prev + 1) % taglines.length);
    }, 2500);

    return () => window.clearInterval(timer);
  }, [taglines]);

  return (
    <section className="showcase" aria-label="Product overview and pipeline">
      <div className="hero-glow" aria-hidden="true" />
      <div className="hero-panel glass">
        <p className="hero-kicker">Deterministic Question Engine</p>
        <h1 className="hero-title">Turn any Gutenberg book into reliable MCQs in one click.</h1>
        <p className="hero-tagline" key={taglineIndex}>
          {taglines[taglineIndex]}
        </p>
        <button type="button" className="hero-cta" onClick={onTryClick}>
          Try it with a book
        </button>

        <div className="micro-demo" aria-label="Pipeline demo animation">
          <span>Book</span>
          <span className="demo-arrow">→</span>
          <span>Processing</span>
          <span className="demo-arrow">→</span>
          <span>Questions</span>
        </div>
      </div>

      <div className="pipeline glass">
        <div className="pipeline-header">
          <h2>How it works</h2>
          <span>Tap a stage to reveal details</span>
        </div>

        <div className="pipeline-track" role="tablist" aria-label="Pipeline stages">
          <div
            className="pipeline-progress"
            style={{ "--progress": `${(activeStep / (pipelineStages.length - 1)) * 100}%` }}
            aria-hidden="true"
          />
          {pipelineStages.map((stage, index) => (
            <button
              key={stage.title}
              type="button"
              role="tab"
              aria-selected={index === activeStep}
              className={`stage ${index === activeStep ? "active" : ""}`}
              onMouseEnter={() => setActiveStep(index)}
              onFocus={() => setActiveStep(index)}
              onClick={() => setActiveStep(index)}
            >
              <span className="stage-icon" aria-hidden="true">
                {stage.icon}
              </span>
              <span>{stage.title}</span>
            </button>
          ))}
        </div>

        <article className="stage-detail" role="tabpanel" aria-live="polite">
          <div className="detail-icon" aria-hidden="true">
            {pipelineStages[activeStep].icon}
          </div>
          <div>
            <h3>{pipelineStages[activeStep].title}</h3>
            <p>{pipelineStages[activeStep].detail}</p>
          </div>
        </article>
      </div>

      <div className="features">
        {featureCards.map((feature) => (
          <article key={feature.title} className="feature-card glass">
            <div className="feature-icon" aria-hidden="true">
              {feature.icon}
            </div>
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
