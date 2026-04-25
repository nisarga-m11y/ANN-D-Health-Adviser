import React from "react";

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    // Surface render crashes instead of leaving the app blank.
    console.error("App render error:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="container auth-page">
          <div className="auth-card" role="alert">
            <h2 style={{ marginTop: 0 }}>Something went wrong</h2>
            <p style={{ marginBottom: 0 }}>
              The app hit a rendering error. Refresh the page, and if this keeps happening, we
              should check the latest browser console error together.
            </p>
          </div>
        </main>
      );
    }

    return this.props.children;
  }
}

export default AppErrorBoundary;
