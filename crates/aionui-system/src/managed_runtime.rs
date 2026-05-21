use std::collections::HashMap;
use std::sync::Arc;

use aionui_api_types::{ManagedRuntimeStateResponse, UpdateManagedRuntimeStateRequest};
use aionui_common::AppError;

use crate::client_pref::ClientPrefService;

const MANAGED_RUNTIME_ACCOUNT_KEY: &str = "newApi.desktop.account";
const MANAGED_RUNTIME_CLI_PREFS_KEY: &str = "newApi.desktop.cliModelPrefs";

#[derive(Clone)]
pub struct ManagedRuntimeService {
    client_pref_service: Arc<ClientPrefService>,
}

impl ManagedRuntimeService {
    pub fn new(client_pref_service: Arc<ClientPrefService>) -> Self {
        Self { client_pref_service }
    }

    pub async fn get_state(&self) -> Result<ManagedRuntimeStateResponse, AppError> {
        let prefs = self
            .client_pref_service
            .get_preferences(Some(&[MANAGED_RUNTIME_ACCOUNT_KEY, MANAGED_RUNTIME_CLI_PREFS_KEY]))
            .await?;

        let account = prefs
            .get(MANAGED_RUNTIME_ACCOUNT_KEY)
            .cloned()
            .map(serde_json::from_value)
            .transpose()
            .map_err(|e| AppError::Internal(format!("Failed to parse managed runtime account: {e}")))?;

        let cli_model_prefs = prefs
            .get(MANAGED_RUNTIME_CLI_PREFS_KEY)
            .cloned()
            .map(serde_json::from_value::<HashMap<String, String>>)
            .transpose()
            .map_err(|e| AppError::Internal(format!("Failed to parse managed runtime prefs: {e}")))?;

        Ok(ManagedRuntimeStateResponse {
            account,
            cli_model_prefs,
        })
    }

    pub async fn update_state(
        &self,
        req: UpdateManagedRuntimeStateRequest,
    ) -> Result<ManagedRuntimeStateResponse, AppError> {
        let mut updates = HashMap::new();

        if let Some(account) = req.account {
            updates.insert(
                MANAGED_RUNTIME_ACCOUNT_KEY.to_owned(),
                match account {
                    Some(account) => serde_json::to_value(account)
                        .map_err(|e| AppError::Internal(format!("Failed to serialize managed runtime account: {e}")))?,
                    None => serde_json::Value::Null,
                },
            );
        }

        if let Some(cli_model_prefs) = req.cli_model_prefs {
            updates.insert(
                MANAGED_RUNTIME_CLI_PREFS_KEY.to_owned(),
                match cli_model_prefs {
                    Some(prefs) => serde_json::to_value(prefs)
                        .map_err(|e| AppError::Internal(format!("Failed to serialize managed runtime prefs: {e}")))?,
                    None => serde_json::Value::Null,
                },
            );
        }

        if !updates.is_empty() {
            self.client_pref_service.update_preferences(updates).await?;
        }
        self.get_state().await
    }
}
