use crate::TriggerStatus;
use log::*;
use rand::prelude::*;
use serde::{Deserialize, Serialize};
use std::time::{Duration, SystemTime};
use tokio::time::delay_for;

pub async fn create_delay(delay_duration_ms: u64, log_prefix: String) {
    let now = SystemTime::now();
    delay_for(Duration::from_millis(delay_duration_ms)).await;
    debug!(
        "{} delay for {}ms end, elapsed {:?}",
        log_prefix,
        delay_duration_ms,
        now.elapsed(),
    );
}

pub fn get_unique_id() -> String {
    let r: f64 = rand::thread_rng().gen();
    let u: u32 = (r * 100000000.0 as f64) as u32;
    format!("[{}]", u)
}

#[derive(Clone, Debug, Serialize)]
pub struct WorkflowInfo {
    pub workflow_url: String,
    pub tag: String,
}

#[derive(Serialize)]
pub struct TriggerWorkflowMessage {
    pub trigger_type: String,
    pub tag: String,
    pub source: String,
    pub data: String,
}

use std::error::Error;
use std::fmt;

#[derive(Debug)]
pub struct TriggerError {
    pub err_msg: String,
}

impl fmt::Display for TriggerError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.err_msg)
    }
}

impl Error for TriggerError {}

pub fn trigger_status_to_string(status: &TriggerStatus) -> String {
    match status {
        TriggerStatus::Starting => "Starting".into(),
        TriggerStatus::Ready => "Ready".into(),
        TriggerStatus::Stopping => "Stopping".into(),
        TriggerStatus::StoppedNormal => "StoppedNormal".into(),
        TriggerStatus::StoppedError => "StoppedError".into(),
    }
}

pub fn string_to_trigger_status(status: &String) -> TriggerStatus {
    match status.as_str() {
        "Starting" => TriggerStatus::Starting,
        "Ready" => TriggerStatus::Ready,
        "Stopping" => TriggerStatus::Stopping,
        "StoppedNormal" => TriggerStatus::StoppedNormal,
        "StoppedError" => TriggerStatus::StoppedError,
        _ => {
            error!("Unknown status string");
            TriggerStatus::StoppedNormal
        }
    }
}

pub async fn send_multiple_post_json_messages(urls: std::vec::Vec<String>, json_body: String) {
    let mut handles = Vec::new();
    for url in urls {
        handles.push(tokio::spawn(send_post_json_message(
            url.clone(),
            json_body.clone(),
        )));
    }
    for handle in handles {
        handle.await;
    }
}

pub async fn send_post_json_message(url: String, json_body: String) {
    let client = reqwest::Client::new();
    let res = client
        .post(&url)
        .header("Content-Type", "application/json")
        .body(json_body)
        .send()
        .await;
    if res.is_ok() {
        let ret_body = res.unwrap().text().await;
        if ret_body.is_ok() {
            debug!("Response: {}", ret_body.unwrap());
        } else {
            warn!(
                "Unable to get reponse body for workflow invocation, {}",
                url
            );
        }
    } else {
        warn!("Error response from workflow invocation, {}", url);
    }
}

pub fn find_element_index(
    workflow_to_search: &WorkflowInfo,
    workflows: &Vec<WorkflowInfo>,
) -> isize {
    let mut i = -1;
    let mut found = false;
    for workflow in workflows {
        i += 1;
        if workflow_to_search.workflow_url.eq(&workflow.workflow_url)
            && workflow_to_search.tag.eq(&workflow.tag)
        {
            found = true;
            break;
        }
    }
    if found {
        return i;
    } else {
        return -1;
    }
}
