#[allow(dead_code,unused,unused_must_use)]
use crate::TriggerStatus;
use log::*;
use rand::prelude::*;
use serde::{Deserialize, Serialize};
use std::time::{Duration, SystemTime};
use tokio::time::delay_for;
use reqwest::header::{HeaderMap, HeaderName, HeaderValue};
use regex::Regex;

fn get_domain_suffix(url: &str) -> &str {
    let re = Regex::new(r"^.+://([^\.]+)\.(.*)").unwrap();
    match re.captures(url) {
        Some(caps) =>  caps.get(2).unwrap().as_str().clone(),
        None => ""
    }
}

fn get_internal_workflow_url<'a>(workflow_url: &'a str, management_url: &'a str) -> String {
    let re = Regex::new(r"^.+://([^\.]+)\.(.*)").unwrap();
    let suffix = get_domain_suffix(management_url);
    match re.captures(workflow_url) {
        Some(caps) => format!("http://{}.{}", &caps[1], suffix).as_str().to_string().clone(),
        None => "".to_string()
    }
}

pub fn get_modified_url_for_k8s<'a>(workflow_url: &'a str) -> String {
    match std::env::var("KUBERNETES_SERVICE_HOST") {
        Ok(_) => { 
            let management_url = std::env::var("MANAGEMENT_URL").expect("MANAGEMENT_URL env variable not specified");
            get_internal_workflow_url(workflow_url, &management_url).clone()
        }
        Err(_) => workflow_url.to_string().clone()
    }
}

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

pub fn should_ignore_message(ignore_message_probability: f32) -> bool {
    if ignore_message_probability == 0.00 {
        return false;
    }
    let mut r: f32 = rand::thread_rng().gen();
    r = r * 100.00;
    if r >= 0.00 && r < 100.00 && r <= ignore_message_probability {
        return true;
    } else {
        return false;
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct WorkflowInfo {
    pub workflow_name: String,
    pub workflow_url: String,
    pub workflow_state: String,
}

#[derive(Serialize)]
pub struct TriggerWorkflowMessage {
    pub trigger_status: String,
    pub trigger_type: String,
    pub trigger_name: String,
    pub workflow_name: String,
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
            "".into(),
            "".into(),
            true
        )));
    }
    for handle in handles {
        handle.await;
    }
}

pub fn generate_customer_headers(workflow_state: String) -> HeaderMap {
    let mut custom_headers: HeaderMap = HeaderMap::new();
    if workflow_state.len() > 0 {
        custom_headers.insert(
            HeaderName::from_static("x-mfn-action"),
            HeaderValue::from_static("trigger-event"),
        );
        custom_headers.insert(
            HeaderName::from_static("x-mfn-action-data"),
            HeaderValue::from_str(workflow_state.as_str()).unwrap(),
        );
    }
    return custom_headers;
}

pub async fn send_post_json_message(url: String, json_body: String, host_header: String, workflow_state: String, async_exec: bool) -> bool {
    let client = reqwest::Client::new();
    let custom_headers: HeaderMap = generate_customer_headers(workflow_state);
    let res;
    if host_header.len() > 0 {
        if async_exec == true {
            res = client
            .post(&url)
            .header("Host", host_header.as_str())
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .query(&[("async", "true")])
            .body(json_body)
            .send()
            .await;
        } else {
            res = client
            .post(&url)
            .header("Host", host_header.as_str())
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .body(json_body)
            .send()
            .await;
        }
    } else {
        if async_exec == true {
            res = client
            .post(&url)
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .query(&[("async", "true")])
            .body(json_body)
            .send()
            .await;
        } else {
            res = client
            .post(&url)
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .body(json_body)
            .send()
            .await;
        }
    }
    if res.is_ok() {
        let ret_body = res.unwrap().text().await;
        if ret_body.is_ok() {
            debug!("Response: {}", ret_body.unwrap());
            return true;
        } else {
            warn!(
                "Unable to get reponse body for workflow invocation, {}",
                url
            );
            return false;
        }
    } else {
        warn!("Error response from workflow invocation, {}", url);
        return false;
    }
}

pub async fn send_post_json_message_with_client(client: &reqwest::Client, url: String, json_body: String, host_header: String, workflow_state: String, async_exec: bool) -> bool {
    let custom_headers: HeaderMap = generate_customer_headers(workflow_state);
    let res;
    if host_header.len() > 0 {
        if async_exec == true {
            res = client
            .post(&url)
            .header("Host", host_header.as_str())
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .query(&[("async", "true")])
            .body(json_body)
            .send()
            .await;
        } else {
            res = client
            .post(&url)
            .header("Host", host_header.as_str())
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .body(json_body)
            .send()
            .await;
        }
    } else {
        if async_exec == true {
            res = client
            .post(&url)
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .query(&[("async", "true")])
            .body(json_body)
            .send()
            .await;
        } else {
            res = client
            .post(&url)
            .header("Content-Type", "application/json")
            .headers(custom_headers)
            .body(json_body)
            .send()
            .await;
        }
    }
    if res.is_ok() {
        let ret_body = res.unwrap().text().await;
        if ret_body.is_ok() {
            debug!("Response: {}", ret_body.unwrap());
            return true;
        } else {
            debug!(
                "Unable to get reponse body for workflow invocation, {}",
                url
            );
            return false;
        }
    } else {
        debug!("Error response from workflow invocation, {}", url);
        return false;
    }
}

pub async fn send_get_message(url: String) -> bool {
    let client = reqwest::Client::new();
    let res = client.get(&url).send().await;
    if res.is_ok() {
        let ret_body = res.unwrap().text().await;
        if ret_body.is_ok() {
            debug!("Response: {}", ret_body.unwrap());
            return true;
        } else {
            warn!("Unable to get reponse body for get invocation, {}", url);
            return false;
        }
    } else {
        warn!("Error response from get invocation, {}", url);
        return false;
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
        if workflow_to_search.workflow_name.eq(&workflow.workflow_name)
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
