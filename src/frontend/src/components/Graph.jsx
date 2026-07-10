import React, { useRef, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { NODE_RADIUS } from '../lib/graphData';

// Component to display connection graph using react-force-graph
const ConnectionGraph = ({ data }) => {
  const fgRef = useRef();

  useEffect(() => {
    if (!fgRef.current || !data || !data.nodes) return;
    const fg = fgRef.current;

    if (data.nodes.length > 100) {
      // Assign clusters based on the last digit of QID
      data.nodes.forEach(node => {
        const qidNum = parseInt(node.id.substring(1)) || 0;
        node.cluster = qidNum % 10; // 10 clusters
      });

      // Simple cluster centers in 2D space
      const clusterCenters = {
        0: { x: -120, y: -120 },
        1: { x: 0, y: -180 },
        2: { x: 120, y: -120 },
        3: { x: -180, y: 0 },
        4: { x: 0, y: 0 },
        5: { x: 180, y: 0 },
        6: { x: -120, y: 120 },
        7: { x: 0, y: 180 },
        8: { x: 120, y: 120 },
        9: { x: 50, y: -50 }
      };

      // Enforce D3 structural node grouping (clustering force)
      fg.d3Force('cluster', (alpha) => {
        data.nodes.forEach(node => {
          const center = clusterCenters[node.cluster] || { x: 0, y: 0 };
          node.vx += (center.x - node.x) * 0.08 * alpha;
          node.vy += (center.y - node.y) * 0.08 * alpha;
        });
      });

      // Reduce repulsion force to make clusters stable and smooth
      fg.d3Force('charge').strength(-30);
      fg.d3Force('link').distance(40);
    } else {
      // Restore default physics for small graphs
      fg.d3Force('cluster', null);
      fg.d3Force('charge').strength(-120);
      fg.d3Force('link').distance(60);
    }
  }, [data]);

  const isLargeGraph = data?.nodes?.length > 100;

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <ForceGraph2D
        ref={fgRef}
        graphData={data}
        nodeLabel={(node) => `${node.name} (${node.id})`}
        nodeColor={() => '#facc15'}
        linkColor={() => '#292524'}
        linkWidth={2.5}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        cooldownTicks={isLargeGraph ? 50 : 100} // Limit simulation run calculations for large graph
        nodeCanvasObject={(node, ctx, globalScale) => {
          // Draw node circle with thick dark border
          ctx.beginPath();
          ctx.arc(node.x, node.y, NODE_RADIUS, 0, 2 * Math.PI, false);
          ctx.fillStyle = '#facc15';
          ctx.fill();
          ctx.lineWidth = 1.5;
          ctx.strokeStyle = '#292524';
          ctx.stroke();

          // Only render text label details when zoomed in close enough or on small graphs
          if (globalScale >= 1.5 || !isLargeGraph) {
            const label = node.name || node.id;
            const fontSize = isLargeGraph ? (10 / globalScale) : (14 / globalScale);
            ctx.font = `bold ${fontSize}px Poppins, sans-serif`;
            const textWidth = ctx.measureText(label).width;
            const bckgDimensions = [textWidth, fontSize].map((dimension) => dimension + fontSize * 0.55);

            // Draw background rectangle for readability
            ctx.fillStyle = '#292524';
            ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

            // Draw text
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#fafaf9';
            ctx.fillText(label, node.x, node.y);
          }
        }}
        onNodeHover={(node) => {
          document.body.style.cursor = node ? 'pointer' : null;
        }}
      />
    </div>
  );
};

export default ConnectionGraph;
