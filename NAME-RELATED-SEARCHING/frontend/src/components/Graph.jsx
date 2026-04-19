import React from 'react';
import ForceGraph2D from 'react-force-graph-2d';

// Thành phần hiển thị đồ thị liên kết sử dụng react-force-graph
// Component to display connection graph using react-force-graph
const ConnectionGraph = ({ data }) => {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ForceGraph2D
        graphData={data}
        nodeLabel="id"
        nodeColor={() => '#bb86fc'}
        linkColor={() => '#03dac6'}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.id;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Inter, sans-serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2);

          // Vẽ nền cho text
          ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
          ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

          // Vẽ text ID
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#fff';
          ctx.fillText(label, node.x, node.y);

          // Vẽ vòng tròn node
          ctx.beginPath();
          ctx.arc(node.x, node.y, 4, 0, 2 * Math.PI, false);
          ctx.fillStyle = '#bb86fc';
          ctx.fill();
        }}
        // Hiệu ứng di chuột vào node
        onNodeHover={(node) => {
          document.body.style.cursor = node ? 'pointer' : null;
        }}
      />
    </div>
  );
};

export default ConnectionGraph;
