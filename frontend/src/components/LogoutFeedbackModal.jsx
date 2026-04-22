import { useEffect, useMemo, useState } from "react";

const EMOJI_BY_RATING = {
  1: "😞",
  2: "😕",
  3: "🙂",
  4: "😄",
  5: "🤩",
};

function ratingMessage(rating) {
  if (rating <= 2) return "We’re sorry to hear that.";
  if (rating === 3) return "Thanks! We’ll keep improving.";
  if (rating >= 4) return "Awesome! Glad you enjoyed it.";
  return "";
}

function LogoutFeedbackModal({ open, onSubmit, onSkip, submitting }) {
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState("");
  const [showThanks, setShowThanks] = useState(false);

  useEffect(() => {
    if (!open) return;
    setRating(0);
    setHovered(0);
    setFeedback("");
    setError("");
    setShowThanks(false);
  }, [open]);

  const activeRating = useMemo(() => hovered || rating, [hovered, rating]);

  if (!open) return null;

  async function handleSubmit() {
    if (!rating || submitting) return;
    setError("");
    try {
      await onSubmit({ rating, feedback: feedback.trim() });
      setShowThanks(true);
      window.setTimeout(() => {
        onSkip();
      }, 900);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Could not submit feedback. You can skip and logout.";
      setError(detail);
    }
  }

  return (
    <div className="logout-modal-overlay" role="presentation">
      <div
        className="logout-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="logoutModalTitle"
        aria-describedby="logoutModalDesc"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="logoutModalTitle">Before you leave, please rate your experience.</h3>
        <p id="logoutModalDesc" className="logout-modal-sub">
          Your feedback helps us improve ANN-D Health Advisor.
        </p>

        <div className="logout-stars" role="radiogroup" aria-label="Rate your experience">
          {[1, 2, 3, 4, 5].map((star) => {
            const active = star <= activeRating;
            return (
              <button
                key={star}
                type="button"
                className={"logout-star-btn" + (active ? " is-active" : "")}
                aria-label={`${star} star${star > 1 ? "s" : ""}`}
                aria-checked={rating === star}
                role="radio"
                onMouseEnter={() => setHovered(star)}
                onMouseLeave={() => setHovered(0)}
                onFocus={() => setHovered(star)}
                onBlur={() => setHovered(0)}
                onClick={() => setRating(star)}
                disabled={submitting || showThanks}
              >
                <span className="logout-star" aria-hidden="true">
                  ★
                </span>
              </button>
            );
          })}
        </div>

        {rating > 0 && (
          <div className="logout-rating-mood">
            <span className="logout-rating-emoji">{EMOJI_BY_RATING[rating]}</span>
            <span>{ratingMessage(rating)}</span>
          </div>
        )}

        <label htmlFor="logoutFeedback" className="logout-feedback-label">
          Optional feedback
        </label>
        <textarea
          id="logoutFeedback"
          className="logout-feedback-textarea"
          placeholder="Tell us what we can improve..."
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          rows={4}
          maxLength={700}
          disabled={submitting || showThanks}
        />

        {showThanks ? <div className="logout-thanks">Thank you for your feedback!</div> : null}
        {error ? <div className="logout-modal-error">{error}</div> : null}

        <div className="logout-actions">
          <button
            type="button"
            className="logout-btn logout-btn-primary"
            onClick={handleSubmit}
            disabled={!rating || submitting || showThanks}
          >
            {submitting ? "Submitting..." : "Submit & Logout"}
          </button>
          <button
            type="button"
            className="logout-btn logout-btn-secondary"
            onClick={onSkip}
            disabled={submitting || showThanks}
          >
            Skip & Logout
          </button>
        </div>
      </div>
    </div>
  );
}

export default LogoutFeedbackModal;
