import assert from 'node:assert/strict';
import test from 'node:test';

import { NODE_RADIUS, buildGraphData, buildPathNodeLabels } from '../src/lib/graphData.js';

test('buildPathNodeLabels prefers fetched labels and falls back to known selections', () => {
  const labels = buildPathNodeLabels(
    ['Q1', 'Q2', 'Q3'],
    {
      Q2: { label: 'Bob' },
    },
    {
      Q1: 'Alice',
    }
  );

  assert.deepEqual(labels, {
    Q1: 'Alice',
    Q2: 'Bob',
    Q3: 'Q3',
  });
});

test('buildGraphData preserves the path order and uses resolved names', () => {
  const graph = buildGraphData(['Q1', 'Q2', 'Q3'], {
    Q1: 'Alice',
    Q2: 'Bob',
    Q3: 'Carol',
  });

  assert.deepEqual(graph.nodes, [
    { id: 'Q1', name: 'Alice' },
    { id: 'Q2', name: 'Bob' },
    { id: 'Q3', name: 'Carol' },
  ]);
  assert.deepEqual(graph.links, [
    { source: 'Q1', target: 'Q2' },
    { source: 'Q2', target: 'Q3' },
  ]);
});

test('node radius is larger than the previous compact size', () => {
  assert.equal(NODE_RADIUS, 9);
});
