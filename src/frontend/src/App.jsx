import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import { Search, Loader2, Share2, History, Info, ChevronLeft, ChevronRight } from 'lucide-react';
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
  const [sidebarOpen, setSidebarOpen] = useState(true); // Trạng thái đóng/mở sidebar
  
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
        props: 'labels',
        format: 'json',
        origin: '*',
      },
    });

    const entities = response.data?.entities || {};
    const entitySummaries = {};
    for (const qid of pathIds) {
      entitySummaries[qid] = {
        label: entities[qid]?.labels?.en?.value || '',
      };
    }

    return buildPathNodeLabels(pathIds, entitySummaries, fallbackLabels);
  }, []);

  const updateGraphLabels = useCallback(async (pathIds, fallbackLabels) => {
    const pathKey = pathIds.join('>');

    try {
      const labels = await fetchPathLabels(pathIds, fallbackLabels);
      if (latestGraphPathRef.current !== pathKey) {
        return;
      }
      setGraphData(buildGraphData(pathIds, labels));
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
        const foundPath = data.path;
        setPath(foundPath);

        const fallbackLabels = buildPathNodeLabels(foundPath, {}, {
          [startValue]: startSelection?.label || (QID_PATTERN.test(startInput.trim()) ? '' : startInput.trim()),
          [targetValue]: targetSelection?.label || (QID_PATTERN.test(targetInput.trim()) ? '' : targetInput.trim()),
        });
        const pathKey = foundPath.join('>');
        latestGraphPathRef.current = pathKey;
        setGraphData(buildGraphData(foundPath, fallbackLabels));
        void updateGraphLabels(foundPath, fallbackLabels);
        fetchGlobalHistory();
      } else {
        latestGraphPathRef.current = '';
        setError('Không tìm thấy đường nối giữa hai thực thể.');
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
      setError('Đã xảy ra lỗi khi kết nối server.');
      console.error("EventSource error:", e);
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      setLoading(false);
      setProgress(null);
    });
  };

  // Click vào lịch sử để tự động chạy lại tìm kiếm
  const handleHistoryClick = (startVal, targetVal) => {
    setStartInput(startVal);
    setStartSelection({ qid: startVal, label: startVal });
    setTargetInput(targetVal);
    setTargetSelection({ qid: targetVal, label: targetVal });

    setLoading(true);
    setError(null);
    setProgress({ node_id: 'Retrieving history...', total_explored: 0, current_depth: 0, elapsed_seconds: 0 });

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
        const foundPath = data.path;
        setPath(foundPath);

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
        setError('Không tìm thấy đường nối giữa hai thực thể.');
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
      setError('Đã xảy ra lỗi khi kết nối server.');
      eventSource.close();
      if (eventSourceRef.current === eventSource) {
        eventSourceRef.current = null;
      }
      setLoading(false);
      setProgress(null);
    });
  };

  return (
    <div className="app-container">
      {/* Sidebar chứa form tìm kiếm và lịch sử */}
      <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="logo">
          <Share2 size={24} color="#a855f7" />
          <h1>WikiBFS</h1>
        </div>

        <div className="search-section">
          <h2 className="section-title">Tìm kiếm liên kết</h2>
          <div className="input-group">
            <label>BẮT ĐẦU (WIKIDATA ID)</label>
            <div className="input-with-suggestions">
              <input
                type="text"
                placeholder="Ví dụ: J.K. Rowling hoặc Q34660"
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
            <label>ĐÍCH ĐẾN (WIKIDATA ID)</label>
            <div className="input-with-suggestions">
              <input
                type="text"
                placeholder="Ví dụ: Neil Gaiman hoặc Q173746"
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
            className="search-button"
            onClick={handleSearch}
            disabled={loading}
          >
            {loading ? <Loader2 className="animate-spin" /> : <Search size={18} />}
            <span>TÌM KIẾM PATH</span>
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="history-section">
          <h2 className="section-title"><History size={16} /> Lịch sử toàn cục</h2>
          <ul className="history-list">
            {history.length > 0 ? history.map((item, index) => (
              <li 
                key={index} 
                className="history-item clickable"
                onClick={() => handleHistoryClick(item.start, item.target)}
                title={`Chạy lại ${item.start} → ${item.target}`}
              >
                <span className="dot"></span>
                <span className="history-path">{item.start} → {item.target}</span>
              </li>
            )) : <p className="empty-text">Chưa có tìm kiếm nào.</p>}
          </ul>
        </div>
      </aside>

      {/* Nút thu gọn/mở rộng sidebar bay lơ lửng */}
      <button 
        className={`sidebar-toggle ${sidebarOpen ? 'open' : 'closed'}`}
        onClick={() => setSidebarOpen(!sidebarOpen)}
        title={sidebarOpen ? "Thu gọn Sidebar" : "Mở rộng Sidebar"}
      >
        {sidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
      </button>

      {/* Main content hiển thị đồ thị và chi tiết */}
      <main className="main-content">
        <header className="main-header">
          <div className="header-info">
            <h2>Đồ thị liên kết tri thức</h2>
            <div className="stats">
              <span>Nodes: {graphData.nodes.length}</span>
              <span>Edges: {graphData.links.length}</span>
            </div>
          </div>
          <div className="header-actions">
            <Info size={20} className="info-icon" />
          </div>
        </header>

        <div className="graph-wrapper">
          {loading && <ProgressOverlay progress={progress} />}
          {graphData.nodes.length > 0 ? (
            <ConnectionGraph data={graphData} />
          ) : (
            <div className="empty-graph">
              <div className="graph-placeholder">
                <Share2 size={64} color="#444" />
              </div>
              <p>Nhập thực thể và bắt đầu tìm kiếm đường nối.</p>
            </div>
          )}
        </div>

        {path.length > 0 && (
          <div className="path-display">
            <h3>Đường đi ngắn nhất:</h3>
            <div className="path-sequence">
              {path.map((id, index) => (
                <React.Fragment key={id}>
                  <span className="path-node">{id}</span>
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
