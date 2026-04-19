import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Loader2, Share2, History, Info } from 'lucide-react';
import ConnectionGraph from './components/Graph';
import './App.css';

// API URL cho backend FastAPI
const API_BASE_URL = 'http://localhost:8000/api';

function App() {
  const [startNode, setStartNode] = useState('');
  const [targetNode, setTargetNode] = useState('');
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [path, setPath] = useState([]);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState(null);

  // Lấy lịch sử toàn cục khi ứng dụng khởi chạy
  // Fetch global history on component mount
  useEffect(() => {
    fetchGlobalHistory();
    
    // Polling mỗi 30 giây để cập nhật lịch sử mới từ người dùng khác
    // Poll every 30 seconds to update new history from other users
    const interval = setInterval(fetchGlobalHistory, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchGlobalHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/history`);
      if (response.data && response.data.history) {
        setHistory(response.data.history);
      }
    } catch (err) {
      console.error("Failed to fetch global history", err);
    }
  };

  const handleSearch = async () => {
    if (!startNode || !targetNode) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`${API_BASE_URL}/search`, {
        params: { start: startNode, target: targetNode, max_depth: 3 }
      });
      
      if (response.data.status === 'success') {
        const foundPath = response.data.path;
        setPath(foundPath);
        
        // Chuyển đổi đường đi thành định dạng graph (nodes & links)
        const nodes = foundPath.map(id => ({ id, name: id }));
        const links = [];
        for (let i = 0; i < foundPath.length - 1; i++) {
          links.push({ source: foundPath[i], target: foundPath[i+1] });
        }
        
        setGraphData({ nodes, links });
        
        // Cập nhật lại lịch sử toàn cục sau khi tìm kiếm thành công
        await fetchGlobalHistory();
      } else {
        setError('Không tìm thấy đường nối giữa hai người này.');
        setPath([]);
        setGraphData({ nodes: [], links: [] });
      }
    } catch (err) {
      setError('Đã xảy ra lỗi khi tìm kiếm. Vui lòng kiểm tra lại Wikidata ID.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar bên trái chứa form tìm kiếm và lịch sử */}
      <aside className="sidebar">
        <div className="logo">
          <Share2 size={24} color="#bb86fc" />
          <h1>WikiBFS</h1>
        </div>
        
        <div className="search-section">
          <h2 className="section-title">Tìm kiếm liên kết</h2>
          <div className="input-group">
            <label>BẮT ĐẦU (WIKIDATA ID)</label>
            <input 
              type="text" 
              placeholder="Ví dụ: Q34660 (J.K. Rowling)" 
              value={startNode}
              onChange={(e) => setStartNode(e.target.value)}
            />
          </div>
          <div className="input-group">
            <label>ĐÍCH ĐẾN (WIKIDATA ID)</label>
            <input 
              type="text" 
              placeholder="Ví dụ: Q173746 (Neil Gaiman)" 
              value={targetNode}
              onChange={(e) => setTargetNode(e.target.value)}
            />
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
              <li key={index} className="history-item">
                <span className="dot"></span>
                <span className="history-path">{item.start} → {item.target}</span>
              </li>
            )) : <p className="empty-text">Chưa có tìm kiếm nào.</p>}
          </ul>
        </div>
      </aside>

      {/* Main content hiển thị đồ thị và chi tiết */}
      <main className="main-content">
        <header className="main-header">
          <div className="header-info">
            <h2>Đồ thị liên kết</h2>
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
          {graphData.nodes.length > 0 ? (
            <ConnectionGraph data={graphData} />
          ) : (
            <div className="empty-graph">
              <div className="graph-placeholder">
                <Share2 size={64} color="#333" />
              </div>
              <p>Kết quả tìm kiếm sẽ hiển thị tại đây.</p>
            </div>
          )}
        </div>

        {path.length > 0 && (
          <div className="path-display">
            <h3>Đường đi chi tiết:</h3>
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
