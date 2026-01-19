import { useState } from 'react'

function App() {
    const [fromName, setFromName] = useState('')
    const [toName, setToName] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const response = await fetch('http://localhost:8000/find-path', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ from_name: fromName, to_name: toName }),
            })

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`)
            }

            const data = await response.json()
            setResult(data)
        } catch (err) {
            setError(err.message || 'Something went wrong')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container">
            <h1>Path Finder</h1>
            <form onSubmit={handleSubmit} className="form">
                <div className="input-group">
                    <label htmlFor="fromName">From Name:</label>
                    <input
                        id="fromName"
                        type="text"
                        value={fromName}
                        onChange={(e) => setFromName(e.target.value)}
                        placeholder="e.g. Elon Musk"
                        required
                        disabled={loading}
                    />
                </div>

                <div className="input-group">
                    <label htmlFor="toName">To Name:</label>
                    <input
                        id="toName"
                        type="text"
                        value={toName}
                        onChange={(e) => setToName(e.target.value)}
                        placeholder="e.g. Donald Trump"
                        required
                        disabled={loading}
                    />
                </div>

                <button type="submit" disabled={loading} className="submit-btn">
                    {loading ? 'Finding Path...' : 'Find Connection'}
                </button>
            </form>

            {error && <div className="error">Error: {error}</div>}

            {result && (
                <div className="result">
                    <div className="person-info">
                        <p><strong>From:</strong> {result.from_person?.label} ({result.from_person?.qid})</p>
                        <p><strong>To:</strong> {result.to_person?.label} ({result.to_person?.qid})</p>
                    </div>

                    <h3>Path:</h3>
                    {result.path === null ? (
                        <p className="no-path">{result.message || 'No connection found'}</p>
                    ) : (
                        <ul className="path-list">
                            {result.path.map((node, index) => (
                                <li key={index} className="path-item">
                                    <span className="node-name">{node.label}</span>
                                    {index < result.path.length - 1 && <span className="arrow">→</span>}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            )}
        </div>
    )
}

export default App
