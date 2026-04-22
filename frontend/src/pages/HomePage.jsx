import { Link } from "react-router-dom";

function HomePage() {
  return (
    <main className="container hero hero-centered">
      <div className="hero-logo" aria-label="Health logo">
        <img src="/health-logo.png" alt="Health AI logo" className="hero-logo-image" />
      </div>

      <h1>ANN-D Health Advicer</h1>
      <p>
        Voice-first chatbot, AI image symptom screening, support calling, and personalized pain-aware guidance. <br />
        <b>
          I am not a doctor. This is general information and not a diagnosis. If symptoms are severe
          or worsening, seek medical care.
        </b>
      </p>

      <div className="hero-actions">
        <Link to="/register" className="btn-primary">
          Get Started
        </Link>
        <Link to="/dashboard" className="btn-secondary">
          Symptom Monitor
        </Link>
      </div>
    </main>
  );
}

export default HomePage;
