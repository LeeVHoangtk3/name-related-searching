import React from 'react';
import { Loader2 } from 'lucide-react';

const ProgressOverlay = ({ progress }) => {
  if (!progress) return null;
  return (
    <div className="progress-overlay">
      <div className="progress-card">
        <Loader2 className="animate-spin" size={32} color="#bb86fc" />
        <div className="progress-info">
          <h3>Scanning: <span className="highlight">{progress.node_id}</span></h3>
          <div className="progress-stats">
            <span>Nodes: {progress.total_explored}</span>
            <span>Depth: {progress.current_depth}</span>
            <span>Time: {progress.elapsed_seconds}s</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgressOverlay;
