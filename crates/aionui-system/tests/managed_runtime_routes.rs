use std::sync::Arc;

use axum::body::Body;
use axum::http::{Request, StatusCode};
use http_body_util::BodyExt;
use tower::ServiceExt;

use aionui_db::{
    SqliteClientPreferenceRepository, SqliteProviderRepository, SqliteSettingsRepository, init_database_memory,
};
use aionui_system::{
    ClientPrefService, ManagedRuntimeService, ModelFetchService, ProtocolDetectionService, ProviderService,
    SettingsService, SystemRouterState, VersionCheckService, system_routes,
};

const TEST_ENCRYPTION_KEY: [u8; 32] = [0x42; 32];

fn build_state(db: &aionui_db::Database) -> SystemRouterState {
    let provider_repo = Arc::new(SqliteProviderRepository::new(db.pool().clone()));
    let client_pref_service =
        ClientPrefService::new(Arc::new(SqliteClientPreferenceRepository::new(db.pool().clone())));
    let http_client = reqwest::Client::new();
    SystemRouterState {
        settings_service: SettingsService::new(Arc::new(SqliteSettingsRepository::new(db.pool().clone()))),
        managed_runtime_service: ManagedRuntimeService::new(Arc::new(client_pref_service.clone())),
        client_pref_service,
        provider_service: ProviderService::new(provider_repo.clone(), TEST_ENCRYPTION_KEY),
        model_fetch_service: ModelFetchService::new(provider_repo, TEST_ENCRYPTION_KEY, http_client.clone()),
        protocol_detection_service: ProtocolDetectionService::new(http_client.clone()),
        version_check_service: VersionCheckService::new(http_client, "0.1.0".to_owned()),
    }
}

async fn body_json(resp: axum::response::Response) -> serde_json::Value {
    let bytes = resp.into_body().collect().await.unwrap().to_bytes();
    serde_json::from_slice(&bytes).unwrap()
}

fn get_request(uri: &str) -> Request<Body> {
    Request::builder().method("GET").uri(uri).body(Body::empty()).unwrap()
}

fn json_request(method: &str, uri: &str, body: serde_json::Value) -> Request<Body> {
    Request::builder()
        .method(method)
        .uri(uri)
        .header("content-type", "application/json")
        .body(Body::from(serde_json::to_vec(&body).unwrap()))
        .unwrap()
}

#[tokio::test]
async fn managed_runtime_defaults_empty() {
    let db = init_database_memory().await.unwrap();
    let app = system_routes(build_state(&db));

    let resp = app.oneshot(get_request("/api/settings/managed-runtime")).await.unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let json = body_json(resp).await;
    assert_eq!(json["success"], true);
    assert_eq!(json["data"], serde_json::json!({}));
}

#[tokio::test]
async fn managed_runtime_roundtrip_account_and_prefs() {
    let db = init_database_memory().await.unwrap();
    let app = system_routes(build_state(&db));

    let put_resp = app
        .oneshot(json_request(
            "PUT",
            "/api/settings/managed-runtime",
            serde_json::json!({
              "account": {
                "logged_in": true,
                "base_url": "https://api.mxou.cn",
                "models": ["mimo-v2.5"],
                "updated_at": 123,
                "user": {
                  "id": 2,
                  "username": "halo",
                  "display_name": "Halo"
                },
                "managed_provider_id": "desktop-newapi-managed-provider"
              },
              "cli_model_prefs": {
                "claude": "mimo-v2.5",
                "openclaw": "mimo-v2.5"
              }
            }),
        ))
        .await
        .unwrap();

    assert_eq!(put_resp.status(), StatusCode::OK);
    let put_json = body_json(put_resp).await;
    assert_eq!(put_json["data"]["account"]["logged_in"], true);
    assert_eq!(put_json["data"]["cli_model_prefs"]["claude"], "mimo-v2.5");

    let app2 = system_routes(build_state(&db));
    let get_resp = app2
        .oneshot(get_request("/api/settings/managed-runtime"))
        .await
        .unwrap();

    assert_eq!(get_resp.status(), StatusCode::OK);
    let get_json = body_json(get_resp).await;
    assert_eq!(get_json["data"]["account"]["base_url"], "https://api.mxou.cn");
    assert_eq!(get_json["data"]["account"]["user"]["username"], "halo");
    assert_eq!(get_json["data"]["cli_model_prefs"]["openclaw"], "mimo-v2.5");
}

#[tokio::test]
async fn managed_runtime_put_null_clears_state() {
    let db = init_database_memory().await.unwrap();
    let app = system_routes(build_state(&db));

    let _ = app
        .oneshot(json_request(
            "PUT",
            "/api/settings/managed-runtime",
            serde_json::json!({
              "account": {
                "logged_in": true,
                "base_url": "https://api.mxou.cn",
                "models": ["mimo-v2.5"],
                "updated_at": 123
              },
              "cli_model_prefs": {
                "claude": "mimo-v2.5"
              }
            }),
        ))
        .await
        .unwrap();

    let app2 = system_routes(build_state(&db));
    let clear_resp = app2
        .oneshot(json_request(
            "PUT",
            "/api/settings/managed-runtime",
            serde_json::json!({
              "account": null,
              "cli_model_prefs": null
            }),
        ))
        .await
        .unwrap();

    assert_eq!(clear_resp.status(), StatusCode::OK);
    let clear_json = body_json(clear_resp).await;
    assert_eq!(clear_json["data"], serde_json::json!({}));
}

#[tokio::test]
async fn managed_runtime_partial_update_preserves_other_state() {
    let db = init_database_memory().await.unwrap();
    let app = system_routes(build_state(&db));

    let _ = app
        .oneshot(json_request(
            "PUT",
            "/api/settings/managed-runtime",
            serde_json::json!({
              "account": {
                "logged_in": true,
                "base_url": "https://api.mxou.cn",
                "models": ["mimo-v2.5"],
                "updated_at": 123
              },
              "cli_model_prefs": {
                "claude": "mimo-v2.5"
              }
            }),
        ))
        .await
        .unwrap();

    let app2 = system_routes(build_state(&db));
    let update_resp = app2
        .oneshot(json_request(
            "PUT",
            "/api/settings/managed-runtime",
            serde_json::json!({
              "cli_model_prefs": {
                "claude": "deepseek-v4-pro",
                "openclaw": "deepseek-v4-pro"
              }
            }),
        ))
        .await
        .unwrap();

    assert_eq!(update_resp.status(), StatusCode::OK);
    let update_json = body_json(update_resp).await;
    assert_eq!(update_json["data"]["account"]["base_url"], "https://api.mxou.cn");
    assert_eq!(update_json["data"]["cli_model_prefs"]["claude"], "deepseek-v4-pro");
    assert_eq!(update_json["data"]["cli_model_prefs"]["openclaw"], "deepseek-v4-pro");
}
