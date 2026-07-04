import asyncio
import json
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.routes import search_path_stream


async def collect_events(response):
    events = []
    async for event in response.body_iterator:
        events.append(event)
    return events


async def mock_find_path_gen(*args, **kwargs):
    yield {"type": "progress", "node_id": "Q1", "total_explored": 1, "current_depth": 0, "elapsed_seconds": 0.1}
    yield {"type": "complete", "path": ["Q1", "Q3", "Q2"]}


@pytest.mark.asyncio
async def test_search_stream_cached():
    mock_graph = {
        "nodes": [{"id": "Q1", "name": "Q1"}, {"id": "Q2", "name": "Q2"}], 
        "links": [{"source": "Q1", "target": "Q2", "p_label": "link"}]
    }
    with (
        patch("app.api.routes.resolve_entity_input", side_effect=lambda value: value),
        patch("app.api.routes.get_cache", return_value=["Q1", "Q2"]) as mock_get_cache,
        patch("app.api.routes.add_to_history"),
        patch("app.api.routes.minimize_graph_payload", return_value=mock_graph),
    ):
        response = await search_path_stream(start="Q1", target="Q2", max_depth=8, mode="fast")
        events = await collect_events(response)

    assert events == [
        {
            "event": "complete",
            "data": json.dumps({"status": "success", "graph": mock_graph, "source": "cache"}),
        }
    ]
    mock_get_cache.assert_called_once_with("path:Q1:Q2:fast:6")


@pytest.mark.asyncio
async def test_search_stream_calculation():
    mock_graph = {
        "nodes": [{"id": "Q1", "name": "Q1"}, {"id": "Q3", "name": "Q3"}, {"id": "Q2", "name": "Q2"}], 
        "links": []
    }
    with (
        patch("app.api.routes.resolve_entity_input", side_effect=lambda value: value),
        patch("app.api.routes.get_cache", return_value=None) as mock_get_cache,
        patch("app.api.routes.find_path", new=mock_find_path_gen),
        patch("app.api.routes.set_cache") as mock_set_cache,
        patch("app.api.routes.add_to_history"),
        patch("app.api.routes.minimize_graph_payload", return_value=mock_graph),
    ):
        response = await search_path_stream(start="Q1", target="Q2", max_depth=8, mode="fast")
        events = await collect_events(response)

    assert len(events) == 2
    assert events[0] == {
        "event": "progress",
        "data": json.dumps({"node_id": "Q1", "total_explored": 1, "current_depth": 0, "elapsed_seconds": 0.1})
    }
    assert events[1] == {
        "event": "complete",
        "data": json.dumps({"status": "success", "graph": mock_graph, "source": "api"}),
    }
    mock_get_cache.assert_called_once_with("path:Q1:Q2:fast:6")
    mock_set_cache.assert_called_once_with("path:Q1:Q2:fast:6", ["Q1", "Q3", "Q2"])


@pytest.mark.asyncio
async def test_search_stream_invalid_input():
    with patch("app.api.routes.resolve_entity_input", return_value="INVALID"):
        with pytest.raises(HTTPException) as exc_info:
            await search_path_stream(start="invalid", target="Q2", max_depth=8, mode="fast")

    assert exc_info.value.status_code == 400
    assert "start/target must be a Wikidata QID" in exc_info.value.detail
