export const NODE_RADIUS = 9;

export function buildPathNodeLabels(path, entitySummaries = {}, fallbackLabels = {}) {
  const labels = {};

  for (const qid of path) {
    const summaryLabel = entitySummaries[qid]?.label?.trim?.() || '';
    const fallbackLabel = fallbackLabels[qid]?.trim?.() || '';
    labels[qid] = summaryLabel || fallbackLabel || qid;
  }

  return labels;
}

export function buildGraphData(path, labelsById = {}) {
  const nodes = path.map((id) => ({
    id,
    name: labelsById[id] || id,
  }));
  const links = [];

  for (let index = 0; index < path.length - 1; index += 1) {
    links.push({ source: path[index], target: path[index + 1] });
  }

  return { nodes, links };
}
