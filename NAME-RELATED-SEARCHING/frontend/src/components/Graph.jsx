import React from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { NODE_RADIUS } from '../lib/graphData';

// Thành phần hiển thị đồ thị liên kết sử dụng react-force-graph
// Component to display connection graph using react-force-graph
const ConnectionGraph = ({ data }) => {
  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ForceGraph2D
        graphData={data}
        nodeLabel={(node) => `${node.name} (${node.id})`}
        nodeColor={() => '#bb86fc'}
        linkColor={() => '#03dac6'}
        linkDirectionalArrowLength={3.5}
        linkDirectionalArrowRelPos={1}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.name || node.id;
          const fontSize = 14 / globalScale;
          ctx.font = `${fontSize}px Inter, sans-serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map((dimension) => dimension + fontSize * 0.55);

          // Vẽ vòng tròn node lớn hơn để nổi bật hơn
          ctx.beginPath();
          ctx.arc(node.x, node.y, NODE_RADIUS, 0, 2 * Math.PI, false);
          ctx.fillStyle = '#bb86fc';
          ctx.fill();

          // Vẽ nền cho text
          ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
          ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

          // Vẽ tên node
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = '#fff';
          ctx.fillText(label, node.x, node.y);
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
