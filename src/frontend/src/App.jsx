import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { Search, Loader2, Share2, History, Info } from 'lucide-react';
import ConnectionGraph from './components/Graph';
import ProgressOverlay from './components/ProgressOverlay';
import { buildGraphData, buildPathNodeLabels } from './lib/graphData';
import './App.css';

// API URL cho backend FastAPI
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
const SEARCH_MAX_DEPTH = 8;
const SEARCH_MODE = 'fast';
const WIKIDATA_ENTITY_API = 'https://www.wikidata.org/w/api.php';
const QID_PATTERN = /^Q\d+$/i;

function App() {
  const [startInput, setStartInput] = useState('');
  const [targetInput, setTargetInput] = useState('');
  const [startSelection, setStartSelection] = useState(null);
  const [targetSelection, setTargetSelection] = useState(null);
  const [startSuggestions, setStartSuggestions] = useState([]);
  const [targetSuggestions, setTargetSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [path, setPath] = useState([]);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);
  
  // activeTab có thể là 'search', 'history' hoặc null (khi thanh panel trượt đóng)
  const [activeTab, setActiveTab] = useState('search');

  const latestGraphPathRef = useRef('');
  const eventSourceRef = useRef(null);

  // Cleanup SSE on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const fetchGlobalHistory = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/history`);
      if (response.data && response.data.history) {
        setHistory(response.data.history);
      }
    } catch (err) {
      console.error("Failed to fetch global history", err);
    }
  }, []);

  // Lấy lịch sử khi ứng dụng khởi chạy
  useEffect(() => {
    const initialFetchTimer = setTimeout(() => {
      fetchGlobalHistory();
    }, 0);

    const interval = setInterval(fetchGlobalHistory, 30000);
    return () => {
      clearTimeout(initialFetchTimer);
      clearInterval(interval);
    };
  }, [fetchGlobalHistory]);

  const fetchSuggestions = async (query, setSuggestionState) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/suggestions`, {
        params: { q: query, limit: 8 },
      });
      setSuggestionState(response.data?.suggestions || []);
    } catch (err) {
      setSuggestionState([]);
      console.error("Failed to fetch suggestions", err);
    }
  };

  const fetchPathLabels = useCallback(async (pathIds, fallbackLabels) => {
    const response = await axios.get(WIKIDATA_ENTITY_API, {
      params: {
        action: 'wbgetentities',
        ids: pathIds.join('|'),
        languages: 'en',
        props: 'labels|sitelinks',
        format: 'json',
        origin: '*',
      },
    });

    const entities = response.data?.entities || {};
    const entitySummaries = {};
    for (const qid of pathIds) {
      const entity = entities[qid] || {};
      const label = entity.labels?.en?.value || '';
      
      // Resolve Vietnamese Wikipedia first, fallback to English
      let wikipediaUrl = '';
      const sitelinks = entity.sitelinks || {};
      if (sitelinks.viwiki) {
        wikipediaUrl = `https://vi.wikipedia.org/wiki/${encodeURIComponent(sitelinks.viwiki.title.replace(/ /g, '_'))}`;
      } else if (sitelinks.enwiki) {
        wikipediaUrl = `https://en.wikipedia.org/wiki/${encodeURIComponent(sitelinks.enwiki.title.replace(/ /g, '_'))}`;
      } else {
        wikipediaUrl = label 
          ? `https://en.wikipedia.org/wiki/${encodeURIComponent(label.replace(/ /g, '_'))}` 
          : `https://www.wikidata.org/wiki/${qid}`;
      }

      entitySummaries[qid] = {
        label: label,
        wikipediaUrl: wikipediaUrl
      };
    }

    return entitySummaries;
  }, []);

  const updateGraphLabels = useCallback(async (pathIds, fallbackLabels) => {
    const pathKey = pathIds.join('>');

    try {
      const entitySummaries = await fetchPathLabels(pathIds, fallbackLabels);
      if (latestGraphPathRef.current !== pathKey) {
        return;
      }

      const labels = {};
      const pathObjects = [];
      for (const qid of pathIds) {
        const summaryLabel = entitySummaries[qid]?.label?.trim?.() || '';
        const fallbackLabel = fallbackLabels[qid]?.trim?.() || '';
        const label = summaryLabel || fallbackLabel || qid;
        labels[qid] = label;

        pathObjects.push({
          qid: qid,
          label: label,
          wikipediaUrl: entitySummaries[qid]?.wikipediaUrl || `https://www.wikidata.org/wiki/${qid}`
        });
      }

      setGraphData(buildGraphData(pathIds, labels));
      setPath(pathObjects);
    } catch (err) {
      console.error('Failed to fetch path labels', err);
    }
  }, [fetchPathLabels]);

  useEffect(() => {
    const query = startInput.trim();
    if (query.length < 2 || (startSelection && query === startSelection.label)) {
      return;
    }

    const timer = setTimeout(() => {
      fetchSuggestions(query, setStartSuggestions);
    }, 300);

    return () => clearTimeout(timer);
  }, [startInput, startSelection]);

  useEffect(() => {
    const query = targetInput.trim();
    if (query.length < 2 || (targetSelection && query === targetSelection.label)) {
      return;
    }

    const timer = setTimeout(() => {
      fetchSuggestions(query, setTargetSuggestions);
    }, 300);

    return () => clearTimeout(timer);
  }, [targetInput, targetSelection]);

  const handleStartChange = (value) => {
    setStartInput(value);
    if (value.trim().length < 2) {
      setStartSuggestions([]);
    }
    if (!startSelection || value !== startSelection.label) {
      setStartSelection(null);
    }
  };

  const handleTargetChange = (value) => {
    setTargetInput(value);
    if (value.trim().length < 2) {
      setTargetSuggestions([]);
    }
    if (!targetSelection || value !== targetSelection.label) {
      setTargetSelection(null);
    }
  };

  const handleSuggestionSelect = (field, item) => {
    if (field === 'start') {
      setStartInput(item.label);
      setStartSelection(item);
      setStartSuggestions([]);
      return;
    }
    setTargetInput(item.label);
    setTargetSelection(item);
    setTargetSuggestions([]);
  };

  const handleSearch = () => {
    const startValue = startSelection?.qid || startInput.trim();
    const targetValue = targetSelection?.qid || targetInput.trim();

    if (!startValue || !targetValue) return;

    setLoading(true);
    setError(null);
    setProgress({ node_id: 'Initializing...', total_explored: 0, current_depth: 0, elapsed_seconds: 0 });
    
    // Tự động đóng bảng panel để tối ưu không gian hiển thị đồ thị khi tìm kiếm
    setActiveTab(null);

    const url = new URL(`${API_BASE_URL}/search/stream`);
    url.searchParams.append('start', startValue);
    url.searchParams.append('target', targetValue);
    url.searchParams.append('max_depth', SEARCH_MAX_DEPTH);
    url.searchParams.append('mode', SEARCH_MODE);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(data);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      if (data.status === 'success') {
        // Lấy danh sách QID thực sự từ data.path (được backend trả về)
        const foundPath = data.path || [];
        const initialPathObjects = foundPath.map(qid => ({
          qid: qid,
          label: qid,
          wikipediaUrl: `https://www.wikidata.org/wiki/${qid}`
        }));
        setPath(initialPathObjects);

        const fallbackLabels = buildPathNodeLabels(foundPath, {}, {
          [startValue]: startSelection?.label || (QID_PATTERN.test(startInput.trim()) ? '' : startInput.trim()),
          [targetValue]: targetSelection?.label || (QID_PATTERN.test(targetInput.trim()) ? '' : targetInput.trim()),
        });
        const pathKey = foundPath.join('>');
        latestGraphPathRef.current = pathKey;
        
        // Khởi tạo đồ thị với nhãn thu gọn ban đầu, sau đó cập nhật nhãn đầy đủ từ Wikidata
        setGraphData(buildGraphData(foundPath, fallbackLabels));
        void updateGraphLabels(foundPath, fallbackLabels);
        fetchGlobalHistory();
      } else {
        latestGraphPathRef.current = '';
        setError('No path found between the two entities.');
        setPath([]);
        setGraphData({ nodes: [], links: [] });
      }
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      setLoading(false);
      setProgress(null);
    });

    eventSource.addEventListener('error', (e) => {
      setError('An error occurred while connecting to the server.');
      console.error("EventSource error:", e);
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      setLoading(false);
      setProgress(null);
    });
  };

  // Xem lại lịch sử (Replay)
  const handleHistoryClick = (startVal, targetVal) => {
    setStartInput(startVal);
    setStartSelection({ qid: startVal, label: startVal });
    setTargetInput(targetVal);
    setTargetSelection({ qid: targetVal, label: targetVal });

    setLoading(true);
    setError(null);
    setProgress({ node_id: 'Retrieving history...', total_explored: 0, current_depth: 0, elapsed_seconds: 0 });
    
    // Tự động đóng bảng panel để xem đồ thị tối đa
    setActiveTab(null);

    const url = new URL(`${API_BASE_URL}/search/stream`);
    url.searchParams.append('start', startVal);
    url.searchParams.append('target', targetVal);
    url.searchParams.append('max_depth', SEARCH_MAX_DEPTH);
    url.searchParams.append('mode', SEARCH_MODE);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const eventSource = new EventSource(url.toString());
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(data);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      if (data.status === 'success') {
        const foundPath = data.path || [];
        const initialPathObjects = foundPath.map(qid => ({
          qid: qid,
          label: qid,
          wikipediaUrl: `https://www.wikidata.org/wiki/${qid}`
        }));
        setPath(initialPathObjects);

        const fallbackLabels = buildPathNodeLabels(foundPath, {}, {
          [startVal]: startVal,
          [targetVal]: targetVal,
        });
        const pathKey = foundPath.join('>');
        latestGraphPathRef.current = pathKey;
        setGraphData(buildGraphData(foundPath, fallbackLabels));
        void updateGraphLabels(foundPath, fallbackLabels);
        fetchGlobalHistory();
      } else {
        latestGraphPathRef.current = '';
        setError('No path found between the two entities.');
        setPath([]);
        setGraphData({ nodes: [], links: [] });
      }
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      setLoading(false);
      setProgress(null);
    });

    eventSource.addEventListener('error', (e) => {
      setError('An error occurred while connecting to the server.');
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      setLoading(false);
      setProgress(null);
    });
  };

  const toggleTab = (tabName) => {
    setActiveTab(activeTab === tabName ? null : tabName);
  };

  return (
    <div className="app-container">
      {/* 1. Left Dock cố định (Fixed Bar) - Chứa Logo và các nút Tab điều hướng */}
      <aside className="left-dock">
        <div className="dock-logo" title="WikiBFS">
          <Share2 size={26} color="#facc15" className="logo-icon" />
        </div>

        <div className="dock-tabs">
          <button 
            className={`dock-tab-btn ${activeTab === 'search' ? 'active' : ''}`}
            onClick={() => toggleTab('search')}
            title="Search Links"
          >
            <Search size={22} />
          </button>
          
          <button 
            className={`dock-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => toggleTab('history')}
            title="Search History"
          >
            <History size={22} />
          </button>
        </div>

        <div className="dock-footer">
          <Info size={20} className="info-icon" title="About Application" />
        </div>
      </aside>

      {/* 2. Sliding Panel (Bảng nội dung trượt) - Hiển thị tùy theo tab đang chọn */}
      <div className={`sliding-panel ${activeTab ? 'open' : 'closed'}`}>
        {activeTab === 'search' && (
          <div className="panel-content">
            <h2 className="panel-title">Search Links</h2>
            
            <div className="input-group">
              <label>START ENTITY (WIKIDATA ID)</label>
              <div className="input-with-suggestions">
                <input
                  type="text"
                  placeholder="e.g. J.K. Rowling or Q34660"
                  value={startInput}
                  onChange={(e) => handleStartChange(e.target.value)}
                  onBlur={() => setTimeout(() => setStartSuggestions([]), 150)}
                />
                {startSuggestions.length > 0 && (
                  <ul className="suggestion-list">
                    {startSuggestions.map((item) => (
                      <li
                        key={`start-${item.qid}`}
                        className="suggestion-item"
                        onMouseDown={() => handleSuggestionSelect('start', item)}
                      >
                        <span className="suggestion-label">{item.label}</span>
                        <span className="suggestion-meta">
                          {item.qid}
                          {item.source === 'history' ? ' · history' : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <div className="input-group">
              <label>TARGET ENTITY (WIKIDATA ID)</label>
              <div className="input-with-suggestions">
                <input
                  type="text"
                  placeholder="e.g. Neil Gaiman or Q173746"
                  value={targetInput}
                  onChange={(e) => handleTargetChange(e.target.value)}
                  onBlur={() => setTimeout(() => setTargetSuggestions([]), 150)}
                />
                {targetSuggestions.length > 0 && (
                  <ul className="suggestion-list">
                    {targetSuggestions.map((item) => (
                      <li
                        key={`target-${item.qid}`}
                        className="suggestion-item"
                        onMouseDown={() => handleSuggestionSelect('target', item)}
                      >
                        <span className="suggestion-label">{item.label}</span>
                        <span className="suggestion-meta">
                          {item.qid}
                          {item.source === 'history' ? ' · history' : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>

            <button
              className="search-button game-btn"
              onClick={handleSearch}
              disabled={loading}
            >
              <div>
                <span>
                  {loading ? <Loader2 className="animate-spin" /> : <Search size={18} />}
                  FIND PATH
                </span>
              </div>
            </button>

            {error && <div className="error-message">{error}</div>}
          </div>
        )}

        {activeTab === 'history' && (
          <div className="panel-content">
            <h2 className="panel-title">Search History</h2>
            <ul className="history-list">
              {history.length > 0 ? history.map((item, index) => (
                <li 
                  key={index} 
                  className="history-item clickable"
                  onClick={() => handleHistoryClick(item.start, item.target)}
                  title={`Click to replay path ${item.start} → ${item.target}`}
                >
                  <span className="dot"></span>
                  <span className="history-path">{item.start} → {item.target}</span>
                </li>
              )) : <p className="empty-text">No searches yet.</p>}
            </ul>
          </div>
        )}
      </div>

      {/* 3. Main content hiển thị đồ thị và chi tiết */}
      <main className="main-content">
        <header className="main-header">
          <div className="header-info">
            <h2>Knowledge Link Graph</h2>
            <div className="stats">
              <span>Nodes: {graphData.nodes.length}</span>
              <span>Edges: {graphData.links.length}</span>
            </div>
          </div>
        </header>

        <div className="graph-wrapper">
          {loading && <ProgressOverlay progress={progress} />}
          {graphData.nodes.length > 0 ? (
            <ConnectionGraph data={graphData} />
          ) : (
            <div className="empty-graph">
              <div className="graph-placeholder">
                <Share2 size={64} color="#facc15" />
              </div>
              <p>Enter entities and start searching for links.</p>
            </div>
          )}
        </div>

        {path.length > 0 && (
          <div className="path-display">
            <h3>Shortest Path:</h3>
            <div className="path-sequence">
              {path.map((node, index) => (
                <React.Fragment key={node.qid || node}>
                  <a 
                    href={node.wikipediaUrl || `https://www.wikidata.org/wiki/${node.qid || node}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="path-node"
                    title={`View Wikipedia for ${node.label || node.qid || node}`}
                  >
                    {node.label || node.qid || node}
                  </a>
                  {index < path.length - 1 && <span className="path-arrow">→</span>}
                </React.Fragment>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
