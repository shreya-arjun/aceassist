import { Component } from "react";

// Keeps a voice-panel crash from unmounting the whole app (and the manual demo).
export default class VoiceErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Voice panel crashed:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <section className="voice">
        <h2>Voice assistant</h2>
        <div className="error">
          The voice panel hit an error: {this.state.error.message}. The workflow below still works.{" "}
          <button className="link" onClick={() => this.setState({ error: null })}>Reload voice panel</button>
        </div>
      </section>
    );
  }
}
