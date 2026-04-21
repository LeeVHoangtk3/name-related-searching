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


class ImmediateLoop:
    def call_soon_threadsafe(self, callback, *args):
        callback(*args)

    def run_in_executor(self, executor, func):
        async def runner():
            func()

        return asyncio.create_task(runner())


@pytest.mark.asyncio
async def test_search_stream_cached():
    with (
        patch("app.api.routes.resolve_entity_input", side_effect=lambda value: value),
        patch("app.api.routes.get_cache", return_value=["Q1", "Q2"]) as mock_get_cache,
        patch("app.api.routes.add_to_history"),
    ):
        response = await search_path_stream(start="Q1", target="Q2", max_depth=8, mode="fast")
        events = await collect_events(response)

    assert events == [
        {
            "event": "complete",
            "data": json.dumps({"status": "success", "path": ["Q1", "Q2"], "source": "cache"}),
        }
    ]
    mock_get_cache.assert_called_once_with("path:Q1:Q2:fast:6")


@pytest.mark.asyncio
async def test_search_stream_calculation():
    immediate_loop = ImmediateLoop()
    with (
        patch("app.api.routes.resolve_entity_input", side_effect=lambda value: value),
        patch("app.api.routes.get_cache", return_value=None) as mock_get_cache,
        patch("app.api.routes.find_path", return_value=["Q1", "Q3", "Q2"]) as mock_find_path,
        patch("app.api.routes.set_cache") as mock_set_cache,
        patch("app.api.routes.add_to_history"),
        patch("app.api.routes.asyncio.get_running_loop", return_value=immediate_loop),
    ):
        response = await search_path_stream(start="Q1", target="Q2", max_depth=8, mode="fast")
        events = await collect_events(response)

    assert events == [
        {
            "event": "complete",
            "data": json.dumps({"status": "success", "path": ["Q1", "Q3", "Q2"], "source": "api"}),
        }
    ]
    mock_get_cache.assert_called_once_with("path:Q1:Q2:fast:6")
    mock_set_cache.assert_called_once_with("path:Q1:Q2:fast:6", ["Q1", "Q3", "Q2"])
    assert mock_find_path.call_args.kwargs["max_depth"] == 6
    assert mock_find_path.call_args.kwargs["max_nodes"] == 6000
    assert mock_find_path.call_args.kwargs["get_neighbors"].keywords["limit"] == 20
    assert mock_find_path.call_args.kwargs["get_neighbors"].keywords["timeout"] == 6


@pytest.mark.asyncio
async def test_search_stream_invalid_input():
    with patch("app.api.routes.resolve_entity_input", return_value="INVALID"):
        with pytest.raises(HTTPException) as exc_info:
            await search_path_stream(start="invalid", target="Q2", max_depth=8, mode="fast")

    assert exc_info.value.status_code == 400
    assert "start/target must be a Wikidata QID" in exc_info.value.detail
