import requests
import json

def test_search_stream():
    url = "http://localhost:8000/search/stream"
    params = {
        "start": "Q34660",  # J. K. Rowling
        "target": "Q173746", # Neil Gaiman
        "max_depth": 3,
        "mode": "fast"
    }
    
    print(f"Testing SSE stream: {url}")
    try:
        response = requests.get(url, params=params, stream=True, timeout=30)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("event:"):
                    print(f"Event: {decoded_line[6:].strip()}")
                elif decoded_line.startswith("data:"):
                    data = json.loads(decoded_line[5:].strip())
                    print(f"Data: {json.dumps(data, indent=2)}")
                elif decoded_line.startswith(":"):
                    # SSE keep-alive
                    pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Note: This requires the backend server to be running at localhost:8000
    print("This test requires the backend server to be running.")
    print("Run: cd NAME-RELATED-SEARCHING/backend && uvicorn app.main:app --reload")
    # test_search_stream()
