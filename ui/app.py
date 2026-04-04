from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dash import Dash, Input, Output, State, dcc, html, no_update

from app_config import (
    ALLOW_PROD_INGEST,
    APP_ENV,
    ENABLE_UI_INGEST,
    INGEST_EXECUTION_MODE,
    RAG_EXECUTION_MODE,
)
from services import llm_api_wrapper, util
from services.api_client import ingest_via_api, query_rag_api
from services.rag_query import query_rag
from ingest.ingest import ingest_directory


def _extract_sources(metadatas: list[dict] | None) -> list[str]:
    if not metadatas:
        return []
    sources = []
    seen = set()
    for metadata in metadatas:
        doc_name = metadata.get("pdf_name") or metadata.get("source") or "unknown"
        title = metadata.get("title", "").strip()
        label = f"{doc_name} - {title}" if title else str(doc_name)
        if label not in seen:
            seen.add(label)
            sources.append(label)
    return sources


def _load_initial_config() -> tuple[list[str], str]:
    config = util.load_config()
    collections = config.get("collections", ["default"])
    default_collection = config.get("default_collection", collections[0])
    return collections, default_collection


def _model_options() -> list[dict[str, str]]:
    model_names = [name for name in llm_api_wrapper.MAX_TOKENS.keys() if name != "default"]
    model_names = sorted(model_names)
    return [{"label": model, "value": model} for model in model_names]


def _composer() -> html.Div:
    # Keep query input + send button as one unified, low-latency control.
    return html.Div(
        className="composer",
        children=[
            dcc.Input(
                id="query-input",
                type="text",
                placeholder="Ask something about your documents...",
                debounce=False,
                autoComplete="off",
                className="composer-input",
            ),
            html.Button("Send", id="send-button", className="composer-send", n_clicks=0),
        ],
    )


def _ingest_panel() -> html.Div:
    if not ENABLE_UI_INGEST:
        return html.Div(
            id="ingest-panel",
            className="control-item",
            children=[
                html.Label("Ingestion"),
                dcc.Input(
                    id="ingest-data-dir",
                    type="text",
                    value="test_data",
                    debounce=True,
                    autoComplete="off",
                    disabled=True,
                ),
                html.Button("Ingest", id="ingest-button", n_clicks=0, disabled=True),
                html.Div(
                    "Disabled (set ENABLE_UI_INGEST=true to enable).",
                    id="ingest-status",
                    className="status-line",
                ),
            ],
        )
    return html.Div(
        id="ingest-panel",
        className="control-item",
        children=[
            html.Label("Ingestion Data Directory"),
            dcc.Input(
                id="ingest-data-dir",
                type="text",
                value="test_data",
                debounce=True,
                autoComplete="off",
            ),
            html.Button("Ingest", id="ingest-button", n_clicks=0),
            html.Div(id="ingest-status", className="status-line"),
        ],
    )


def _query_backend(
    *,
    query_text: str,
    collection_name: str,
    n_results: int,
    model: str,
) -> tuple[str, str, list[dict]]:
    if RAG_EXECUTION_MODE == "direct":
        return query_rag(
            query_text=query_text,
            collection_name=collection_name,
            n_results=n_results,
            model=model,
        )
    return query_rag_api(
        query_text=query_text,
        collection_name=collection_name,
        n_results=n_results,
        model=model,
    )


def _ingest_backend(*, data_dir: str, collection_name: str) -> int:
    if APP_ENV == "prod" and not ALLOW_PROD_INGEST:
        raise RuntimeError("Ingest is disabled in prod. Set ALLOW_PROD_INGEST=true to allow it.")
    if INGEST_EXECUTION_MODE == "direct":
        return ingest_directory(data_dir=data_dir, collection_name=collection_name)
    return ingest_via_api(data_dir=data_dir, collection=collection_name)


def _message_item(message: dict) -> html.Div:
    role = message.get("role", "assistant")
    content = message.get("content", "")
    ts = message.get("timestamp", "")
    role_class = "msg-user" if role == "user" else "msg-assistant"
    header = "You" if role == "user" else "Assistant"
    sources = message.get("sources", [])
    context_preview = message.get("context_preview", "")
    source_block = no_update
    if role == "assistant" and sources:
        source_block = html.Div(
            className="msg-sources",
            children=[
                html.Div("Sources", className="msg-sources-title"),
                html.Ul([html.Li(source) for source in sources]),
            ],
        )
    context_block = no_update
    if role == "assistant" and context_preview:
        context_block = html.Details(
            className="msg-context",
            children=[
                html.Summary("Retrieved context"),
                dcc.Markdown(context_preview),
            ],
        )

    children = [
        html.Div(className="msg-meta", children=f"{header} · {ts}"),
        dcc.Markdown(content, className="msg-content"),
    ]
    if source_block is not no_update:
        children.append(source_block)
    if context_block is not no_update:
        children.append(context_block)
    return html.Div(
        className=f"msg {role_class}",
        children=children,
    )


def create_app() -> Dash:
    collections, default_collection = _load_initial_config()
    models = _model_options()
    default_model = llm_api_wrapper.DEFAULT_MODEL
    if not any(opt["value"] == default_model for opt in models) and models:
        default_model = models[0]["value"]

    app = Dash(__name__, assets_folder=str(Path(__file__).parent / "assets"))
    app.title = "Quack DB UI"

    app.layout = html.Div(
        className="page",
        children=[
            html.H2("Quack DB"),
            html.Div(
                className="controls",
                children=[
                    html.Div(
                        className="control-item",
                        children=[
                            html.Label("Collection"),
                            dcc.Dropdown(
                                id="collection-select",
                                options=[{"label": c, "value": c} for c in collections],
                                value=default_collection,
                                clearable=False,
                            ),
                        ],
                    ),
                    html.Div(
                        className="control-item",
                        children=[
                            html.Label("Model"),
                            dcc.Dropdown(
                                id="model-select",
                                options=models,
                                value=default_model,
                                clearable=False,
                            ),
                        ],
                    ),
                    html.Div(
                        className="control-item",
                        children=[
                            html.Label("Retrieved Chunks"),
                            dcc.Slider(
                                id="n-results",
                                min=1,
                                max=8,
                                step=1,
                                marks={i: str(i) for i in range(1, 9)},
                                value=3,
                            ),
                        ],
                    ),
                    _ingest_panel(),
                ],
            ),
            html.Div(id="status-line", className="status-line"),
            html.Div(id="messages", className="messages"),
            _composer(),
            dcc.Store(id="history-store", data=[]),
            dcc.Store(id="pending-store", data=None),
        ],
    )

    @app.callback(
        Output("send-button", "disabled"),
        Input("query-input", "value"),
    )
    def set_send_disabled(query_value: str | None):
        return not bool((query_value or "").strip())

    @app.callback(
        Output("history-store", "data"),
        Output("pending-store", "data"),
        Output("query-input", "value"),
        Output("status-line", "children"),
        Input("send-button", "n_clicks"),
        Input("query-input", "n_submit"),
        State("query-input", "value"),
        State("collection-select", "value"),
        State("model-select", "value"),
        State("n-results", "value"),
        State("history-store", "data"),
        prevent_initial_call=True,
    )
    def queue_query(
        _n_clicks: int,
        _n_submit: int,
        query_value: str | None,
        collection_name: str,
        model: str,
        n_results: int,
        history: list[dict] | None,
    ):
        query_text = (query_value or "").strip()
        if not query_text:
            return no_update, no_update, "", no_update

        history = history or []
        history.append(
            {
                "role": "user",
                "content": query_text,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
        )
        pending = {
            "query": query_text,
            "collection": collection_name,
            "model": model,
            "n_results": n_results,
        }
        return history, pending, "", "Thinking..."

    @app.callback(
        Output("history-store", "data", allow_duplicate=True),
        Output("pending-store", "data", allow_duplicate=True),
        Output("status-line", "children", allow_duplicate=True),
        Input("pending-store", "data"),
        State("history-store", "data"),
        prevent_initial_call=True,
    )
    def run_query(pending: dict | None, history: list[dict] | None):
        if not pending:
            return no_update, no_update, no_update

        history = history or []
        try:
            response_text, context_text, metadatas = _query_backend(
                query_text=pending["query"],
                collection_name=pending["collection"],
                n_results=pending["n_results"],
                model=pending["model"],
            )
            sources = _extract_sources(metadatas)
            context_preview = context_text[:2000]
        except Exception as exc:  # Keep UI resilient to backend/service errors.
            response_text = f"Error while querying service: `{exc}`"
            sources = []
            context_preview = ""

        history.append(
            {
                "role": "assistant",
                "content": response_text,
                "sources": sources,
                "context_preview": context_preview,
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
        )
        return history, None, ""

    @app.callback(
        Output("messages", "children"),
        Input("history-store", "data"),
    )
    def render_history(history: list[dict] | None):
        history = history or []
        if not history:
            return html.Div(
                className="empty",
                children="Ask a question to get started.",
            )
        return [_message_item(message) for message in history]

    @app.callback(
        Output("ingest-status", "children"),
        Input("ingest-button", "n_clicks"),
        State("ingest-data-dir", "value"),
        State("collection-select", "value"),
        prevent_initial_call=True,
    )
    def run_ingest(_n_clicks: int, data_dir: str | None, collection_name: str):
        if not ENABLE_UI_INGEST:
            return "Ingest is disabled."
        safe_data_dir = (data_dir or "").strip()
        if not safe_data_dir:
            return "Please provide a data directory."
        try:
            chunks = _ingest_backend(data_dir=safe_data_dir, collection_name=collection_name)
        except Exception as exc:
            return f"Ingest failed: {exc}"
        return f"Ingest complete: {chunks} chunks added to '{collection_name}'."

    return app


def run(host: str | None = None, port: int | None = None, debug: bool = False):
    host = host or os.getenv("UI_HOST", "0.0.0.0")
    port = port if port is not None else int(os.getenv("UI_PORT", "8050"))
    app = create_app()
    app.run(host=host, port=port, debug=debug)


