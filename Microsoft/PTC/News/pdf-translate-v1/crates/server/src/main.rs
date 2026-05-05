use std::net::SocketAddr;

use axum::{
    extract::DefaultBodyLimit,
    http::Method,
    routing::{delete, get, post},
    Router,
};
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;

mod errors;
mod handlers;
mod state;

#[tokio::main]
async fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let workdir = std::env::var("PDFTR_WORKDIR").unwrap_or_else(|_| "./workdir".into());
    let app_state = state::AppState::new(workdir.into()).expect("create app state");

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods([Method::GET, Method::POST, Method::DELETE])
        .allow_headers(Any);

    let app = Router::new()
        .route("/api/health", get(handlers::health))
        .route("/api/documents", post(handlers::upload_document))
        .route("/api/documents/:document_id", get(handlers::get_document))
        .route(
            "/api/documents/:document_id",
            delete(handlers::delete_document),
        )
        .route(
            "/api/documents/:document_id/pages/:page_number",
            get(handlers::get_page_render_plan),
        )
        .route(
            "/api/documents/:document_id/edits",
            post(handlers::post_edit),
        )
        .route(
            "/api/documents/:document_id/download",
            get(handlers::download_document),
        )
        .with_state(app_state)
        .layer(DefaultBodyLimit::max(state::MAX_UPLOAD_BYTES))
        .layer(cors)
        .layer(TraceLayer::new_for_http());

    let addr: SocketAddr = std::env::var("PDFTR_ADDR")
        .unwrap_or_else(|_| "127.0.0.1:7878".into())
        .parse()
        .expect("PDFTR_ADDR is invalid");

    log::info!("pdftr-server listening on {addr}");
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
