use anyhow::{anyhow, Context, Result};
use pdf_models::{TranslationInput, TranslationResultItem, TranslationResults};
use reqwest::blocking::Client;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone)]
pub struct OpenAiConfig {
    pub api_key: String,
    pub model: String,
    pub source_lang: String,
    pub target_lang: String,
}

pub fn translate(input: &TranslationInput, config: &OpenAiConfig) -> Result<TranslationResults> {
    if input.items.is_empty() {
        return Ok(TranslationResults::default());
    }
    let prompt = build_prompt(input, &config.source_lang, &config.target_lang);
    let request = ChatRequest {
        model: config.model.clone(),
        response_format: ResponseFormat { kind: "json_object".to_string() },
        messages: vec![
            Message { role: "system".to_string(), content: "You translate JSON items. Return only valid JSON.".to_string() },
            Message { role: "user".to_string(), content: prompt },
        ],
    };
    let response: ChatResponse = Client::new()
        .post("https://api.openai.com/v1/chat/completions")
        .bearer_auth(&config.api_key)
        .json(&request)
        .send()
        .context("send OpenAI request")?
        .error_for_status()
        .context("OpenAI request failed")?
        .json()
        .context("parse OpenAI response")?;
    let content = response
        .choices
        .first()
        .ok_or_else(|| anyhow!("OpenAI returned no choices"))?
        .message
        .content
        .clone();
    parse_translation_json(&content)
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
    model: String,
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
