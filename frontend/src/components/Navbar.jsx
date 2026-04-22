import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { submitLogoutFeedback } from "../api/auth";
import "../styles/logout-feedback-modal.css";
import { useAuth } from "../context/AuthContext";
import LogoutFeedbackModal from "./LogoutFeedbackModal";

function Navbar() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [showLogoutModal, setShowLogoutModal] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  function handleLogout() {
    setShowLogoutModal(true);
  }

  function handleSkipAndLogout() {
    setShowLogoutModal(false);
    logout();
    navigate("/login");
  }

  async function handleSubmitFeedback(payload) {
    setSubmittingFeedback(true);
    try {
      await submitLogoutFeedback(payload);
    } finally {
      setSubmittingFeedback(false);
    }
  }

  const linkClass = ({ isActive }) => "nav-link" + (isActive ? " nav-link--active" : "");

  return (
    <>
      <nav className="navbar">
        <div className="nav-brand">
          <div className="nav-brand__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none">
              <path
                d="M12 21s-7-4.75-9.5-9.25C.5 8.25 2.5 5 6 5c1.9 0 3.2 1 4 2 0.8-1 2.1-2 4-2 3.5 0 5.5 3.25 3.5 6.75C19 16.25 12 21 12 21Z"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinejoin="round"
              />
              <path
                d="M7.5 12h2.2l1.2-2.2 2.1 4.2 1.1-2H16.5"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="nav-brand__text">
            <div className="nav-brand__title">ANN-D Health Advisor</div>
            <div className="nav-brand__subtitle">AI-style guidance (educational only)</div>
          </div>
        </div>

        <div className="nav-links">
          <NavLink to="/" className={linkClass}>
            Home
          </NavLink>
          {!isAuthenticated && (
            <NavLink to="/login" className={linkClass}>
              Login
            </NavLink>
          )}
          {!isAuthenticated && (
            <NavLink to="/register" className={linkClass}>
              Register
            </NavLink>
          )}
          {isAuthenticated && (
            <NavLink to="/dashboard" className={linkClass}>
              Dashboard
            </NavLink>
          )}
          {isAuthenticated && (
            <NavLink to="/health-report" className={linkClass}>
              Health Report
            </NavLink>
          )}
          {isAuthenticated && (
            <button type="button" className="btn-outline nav-logout" onClick={handleLogout}>
              Logout
            </button>
          )}
        </div>
      </nav>

      {isAuthenticated && (
        <LogoutFeedbackModal
          open={showLogoutModal}
          onSubmit={handleSubmitFeedback}
          onSkip={handleSkipAndLogout}
          submitting={submittingFeedback}
        />
      )}
    </>
  );
}

export default Navbar;
