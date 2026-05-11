use anyhow::{anyhow, Context, Result};
use pdf_models::{TranslationInput, TranslationResultItem, TranslationResults};
use reqwest::blocking::{Client, Response};
use reqwest::StatusCode;
use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Debug, Clone)]
pub struct OpenAiConfig {
    pub api_key: String,
    pub model: String,
    pub source_lang: String,
    pub target_lang: String,
}

#[derive(Debug, Clone)]
pub enum LlmProvider {
    OpenAi,
    AzureOpenAi,
}

#[derive(Debug, Clone)]
pub struct TranslateConfig {
    pub provider: LlmProvider,
    pub api_key: String,
    pub model: Option<String>,
    pub azure_endpoint: Option<String>,
    pub azure_deployment: Option<String>,
    pub azure_api_version: Option<String>,
    pub source_lang: String,
    pub target_lang: String,
    pub retry_max: usize,
    pub retry_base_ms: u64,
    pub timeout_secs: u64,
}

pub fn translate(input: &TranslationInput, config: &OpenAiConfig) -> Result<TranslationResults> {
    translate_with_config(input, &TranslateConfig {
        provider: LlmProvider::OpenAi,
        api_key: config.api_key.clone(),
        model: Some(config.model.clone()),
        azure_endpoint: None,
        azure_deployment: None,
        azure_api_version: None,
        source_lang: config.source_lang.clone(),
        target_lang: config.target_lang.clone(),
        retry_max: 0,
        retry_base_ms: 1000,
        timeout_secs: 120,
    })
}

pub fn translate_with_config(input: &TranslationInput, config: &TranslateConfig) -> Result<TranslationResults> {
    if input.items.is_empty() {
        return Ok(TranslationResults::default());
    }
    let prompt = build_prompt(input, &config.source_lang, &config.target_lang);
    let request = ChatRequest {
        model: match config.provider {
            LlmProvider::OpenAi => Some(config.model.clone().ok_or_else(|| anyhow!("OPENAI_MODEL is required for OpenAI provider"))?),
            LlmProvider::AzureOpenAi => None,
        },
        response_format: ResponseFormat { kind: "json_object".to_string() },
        messages: vec![
            Message { role: "system".to_string(), content: "You translate JSON items. Return only valid JSON.".to_string() },
            Message { role: "user".to_string(), content: prompt },
        ],
    };

    let client = Client::builder()
        .timeout(Duration::from_secs(config.timeout_secs.max(1)))
        .build()
        .context("build OpenAI HTTP client")?;
    let attempts = config.retry_max.saturating_add(1);
    let mut last_error = None;
    for attempt in 0..attempts {
        match send_chat_request(&client, &request, config) {
            Ok(response) => return parse_chat_response(response, config),
            Err(err) => {
                let retryable = is_retryable_error(&err);
                last_error = Some(err);
                if !retryable || attempt + 1 >= attempts {
                    break;
                }
                let delay_ms = config.retry_base_ms.saturating_mul(2_u64.saturating_pow(attempt as u32));
                std::thread::sleep(Duration::from_millis(delay_ms));
            }
        }
    }
    Err(last_error.unwrap_or_else(|| anyhow!("translation request failed")))
}

fn send_chat_request(client: &Client, request: &ChatRequest, config: &TranslateConfig) -> Result<Response> {
    let builder = match config.provider {
        LlmProvider::OpenAi => client
            .post("https://api.openai.com/v1/chat/completions")
            .bearer_auth(&config.api_key),
        LlmProvider::AzureOpenAi => {
            let endpoint = config.azure_endpoint.as_deref().ok_or_else(|| anyhow!("AZURE_OPENAI_ENDPOINT is required"))?.trim_end_matches('/');
            let deployment = config.azure_deployment.as_deref().ok_or_else(|| anyhow!("AZURE_OPENAI_DEPLOYMENT is required"))?;
            let api_version = config.azure_api_version.as_deref().unwrap_or("2024-02-15-preview");
            client
                .post(format!("{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"))
                .header("api-key", &config.api_key)
        }
    };
    builder
        .json(request)
        .send()
        .with_context(|| format!("send {} translation request", provider_name(&config.provider)))
}

fn parse_chat_response(response: Response, config: &TranslateConfig) -> Result<TranslationResults> {
    let status = response.status();
    let body = response.text().context("read OpenAI response body")?;
    if !status.is_success() {
        return Err(anyhow!("{} request failed with status {status}: {body}", provider_name(&config.provider)));
    }
    let response: ChatResponse = serde_json::from_str(&body)
        .with_context(|| format!("parse {} response JSON: {body}", provider_name(&config.provider)))?;
    let content = response
        .choices
        .first()
        .ok_or_else(|| anyhow!("{} returned no choices", provider_name(&config.provider)))?
        .message
        .content
        .clone();
    parse_translation_json(&content)
}

fn is_retryable_error(err: &anyhow::Error) -> bool {
    let text = err.to_string();
    text.contains("status 429")
        || text.contains("status 500")
        || text.contains("status 502")
        || text.contains("status 503")
        || text.contains("status 504")
        || text.contains("timed out")
        || text.contains(StatusCode::TOO_MANY_REQUESTS.as_str())
}

fn provider_name(provider: &LlmProvider) -> &'static str {
    match provider {
        LlmProvider::OpenAi => "OpenAI",
        LlmProvider::AzureOpenAi => "Azure OpenAI",
    }
}

fn build_prompt(input: &TranslationInput, source_lang: &str, target_lang: &str) -> String {
    let terms = serde_json::to_string_pretty(&input.terms).unwrap_or_else(|_| "[]".to_string());
    let items = serde_json::to_string_pretty(&input.items).unwrap_or_else(|_| "[]".to_string());
    format!(
        "Translate from {source_lang} to {target_lang}. Preserve terms with mode=preserve. Fixed translations must be applied exactly.\nterms:\n{terms}\nitems:\n{items}\nReturn JSON object: {{\"items\":[{{\"id\":\"...\",\"translated\":\"...\"}}]}}"
    )
}

fn parse_translation_json(content: &str) -> Result<TranslationResults> {
    #[derive(Deserialize)]
    struct Wrapper { items: Vec<TranslationResultItem> }
    if let Ok(wrapper) = serde_json::from_str::<Wrapper>(content) {
        return Ok(TranslationResults { items: wrapper.items });
    }
    let items = serde_json::from_str::<Vec<TranslationResultItem>>(content)
        .context("OpenAI response was not TranslationResults JSON")?;
    Ok(TranslationResults { items })
}

#[derive(Serialize)]
struct ChatRequest {
    #[serde(skip_serializing_if = "Option::is_none")]
    model: Option<String>,
    messages: Vec<Message>,
    #[serde(rename = "response_format")]
    response_format: ResponseFormat,
}

#[derive(Serialize)]
struct ResponseFormat {
    #[serde(rename = "type")]
    kind: String,
}

#[derive(Serialize, Deserialize)]
struct Message {
    role: String,
    content: String,
}

#[derive(Deserialize)]
struct ChatResponse {
    choices: Vec<Choice>,
}

#[derive(Deserialize)]
struct Choice {
    message: Message,
}
