use actix_web::{
    get, middleware::Logger, post, web, App, HttpRequest, HttpResponse, HttpServer, Responder,
};
use chrono::prelude::*;
use json::JsonValue;
use log::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::io::Write;
use std::sync::Mutex;
use std::thread;
use std::process;
use std::time::SystemTime;
use tokio::prelude::*;
use tokio::sync::mpsc::{channel, Receiver, Sender};
use tokio::sync::oneshot;

mod trigger_manager;
use trigger_manager::{
    TriggerManager, TriggerManagerCommand, TriggerManagerInfo, TriggerManagerStatusUpdateMessage,
    TriggerManagerStatusUpdateMessageData,
};

mod amqp_trigger;
use amqp_trigger::{AMQPSubscriberInfo, AMQPTrigger};

mod timer_trigger;
use timer_trigger::handle_create_timer_trigger;

mod mqtt_triggers;
use mqtt_triggers::handle_create_mqtt_trigger;

mod utils;
use utils::{create_delay, get_unique_id, send_post_json_message, WorkflowInfo};

/*
struct TriggerInfo {
    actorid: String,
    //cmd_channel_tx: TriggerCommandChannel,
}
*/

//type AppState = HashMap<String, TriggerInfo>;

#[derive(Serialize, Debug)]
struct TriggersFrontendResponse {
    status: String,
    message: String,
}

#[derive(Debug)]
pub enum TriggerCommand {
    Status,
    Stop,
    AddWorkflows(Vec<WorkflowInfo>),
    RemoveWorkflows(Vec<WorkflowInfo>),
}

#[derive(Debug, Clone, Serialize)]
pub enum TriggerStatus {
    Starting,
    Ready,
    Stopping,
    StoppedNormal,
    StoppedError,
}

type CommandResponseChannel = oneshot::Sender<(bool, String)>;
type TriggerCommandChannel = Sender<(TriggerCommand, CommandResponseChannel)>;

// for mpsc channel: Senders return Result<T,E>, Receivers return Option<T>
// for one shot channel:

/// This handler manually load request payload and parse json-rust
/// curl -H "Content-Type: application/json" -d '{"type": "amqp", "id": "1", "workflow_url" : "http://localhost:8080/", "trigger_info": {}}' http://localhost:8080/jsontest | jq -r '.message' | jq
async fn jsontest(req: HttpRequest, body: web::Bytes) -> impl Responder {
    // body is loaded, now we can deserialize json-rust
    let mut decoded_body = std::str::from_utf8(&body);
    if let Err(e) = decoded_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an utf8 string. Error: {}.",
                e.to_string()
            ),
        });
    }

    let decoded_body = decoded_body.unwrap();
    let json_body = json::parse(&decoded_body);
    if let Err(e) = json_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an a valid json object. Error: {}.",
                e.to_string()
            ),
        });
    }
    let json_body = json_body.unwrap();
    if !(json_body.is_object()
        && json_body.has_key("type")
        && json_body.has_key("id")
        && json_body.has_key("workflows")
        && json_body["workflows"].is_array()
        && json_body["workflows"].len() > 0
        && json_body.has_key("trigger_info")
        && json_body["trigger_info"].is_object()
        && json_body["trigger_info"].len() > 0)
    {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "One of the required fields, 'type', 'id', 'workflow_url', or 'trigger_info' is missing.
            'type' = 'amqp', 'mqtt', or 'timer'.
            'id' = user provided string to uniquely identify this trigger. This 'id' must be supplied while delete the trigger.
            'workflows' = list of objects of type {'worklfow_url': workflow_url, 'tag': tag}
            'trigger_info' = 'type' specific parameters for subscribing to a message queue or creating a timer
            'tag' = optional string provided by the user which is included in each workflow invocation"
            .into(),
        });
    }
    let trigger_type: String = json_body["type"].to_string();
    let trigger_id: String = json_body["id"].to_string();
    let trigger_info = &json_body["trigger_info"];

    let mut workflows_vec: Vec<WorkflowInfo> = Vec::new();
    let workflows = &json_body["workflows"];
    for i in 0..=workflows.len() {
        let workflow_info = &workflows[i];
        if !workflow_info.has_key("workflow_url") {
            return HttpResponse::Ok().json(TriggersFrontendResponse {
                status: "Failure".into(),
                message: "workflow_url missing in workflows list".into(),
            });
        }
        let tag: String = if workflow_info.has_key("tag") {
            workflow_info["tag"].to_string()
        } else {
            "".into()
        };
        workflows_vec.push(WorkflowInfo {
            workflow_url: workflow_info["workflow_url"].to_string(),
            tag,
        });
    }

    if trigger_type.eq("amqp") || trigger_type.eq("mqtt") || trigger_type.eq("timer") {
        let response: Result<String, String> = Ok("Some message".into());
        let http_response: TriggersFrontendResponse = match response {
            Ok(msg) => TriggersFrontendResponse {
                status: "Success".into(),
                message: msg,
            },
            Err(msg) => TriggersFrontendResponse {
                status: "Failure".into(),
                message: msg,
            },
        };
        return HttpResponse::Ok().json(http_response);
    } else {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "Unknow type".to_string(),
        });
    }
    // let result = json::parse(std::str::from_utf8(&body).unwrap()); // return Result
    // let injson: JsonValue = match result {
    //     Ok(v) => v,
    //     Err(e) => json::object! {"err" => e.to_string() },
    // };
    // Ok(HttpResponse::Ok()
    //     .content_type("application/json")
    //     .body(injson.dump()))
}

async fn create_trigger(req: HttpRequest, body: web::Bytes) -> impl Responder {
    // body is loaded, now we can deserialize json-rust
    let mut decoded_body = std::str::from_utf8(&body);
    if let Err(e) = decoded_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an utf8 string. Error: {}.",
                e.to_string()
            ),
        });
    }

    let decoded_body = decoded_body.unwrap();
    let json_body = json::parse(&decoded_body);
    if let Err(e) = json_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an a valid json object. Error: {}.",
                e.to_string()
            ),
        });
    }
    let json_body = json_body.unwrap();
    if !(json_body.is_object()
        && json_body.has_key("type")
        && json_body.has_key("id")
        && json_body.has_key("workflows")
        && json_body["workflows"].is_array()
        && json_body["workflows"].len() > 0
        && json_body.has_key("trigger_info")
        && json_body["trigger_info"].is_object()
        && json_body["trigger_info"].len() > 0)
    {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "One of the required fields, 'type', 'id', 'workflow_url', or 'trigger_info' is missing.
            'type' = 'amqp', 'mqtt', or 'timer'.
            'id' = user provided string to uniquely identify this trigger. This 'id' must be supplied while delete the trigger.
            'workflows' = list of objects of type {'worklfow_url': workflow_url, 'tag': tag}
            'trigger_info' = 'type' specific parameters for subscribing to a message queue or creating a timer
            'tag' = optional string provided by the user which is included in each workflow invocation"
            .into(),
        });
    }
    let trigger_type: String = json_body["type"].to_string();
    let trigger_id: String = json_body["id"].to_string();
    let trigger_info = &json_body["trigger_info"];
    let mut workflows_vec: Vec<WorkflowInfo> = Vec::new();
    let workflows = &json_body["workflows"];
    for i in 0..workflows.len() {
        let workflow_info = &workflows[i];
        if !workflow_info.has_key("workflow_url") {
            return HttpResponse::Ok().json(TriggersFrontendResponse {
                status: "Failure".into(),
                message: "workflow_url missing in workflows list".into(),
            });
        }
        let tag: String = if workflow_info.has_key("tag") {
            workflow_info["tag"].to_string()
        } else {
            "".into()
        };
        workflows_vec.push(WorkflowInfo {
            workflow_url: workflow_info["workflow_url"].to_string(),
            tag,
        });
    }
    info!(
        "[CREATE_TRIGGER] request, id: {}, type: {}, workflow: {:?}, trigger_info: {:?}",
        &trigger_id, &trigger_type, &workflows_vec, &trigger_info
    );

    if trigger_type.eq("amqp") || trigger_type.eq("mqtt") || trigger_type.eq("timer") {
        let mut trigger_manager: TriggerManager = req.app_data::<TriggerManager>().unwrap().clone();
        let response: Result<String, String> = trigger_manager
            .handle_create_trigger(
                &trigger_type,
                &trigger_id,
                workflows_vec.clone(),
                decoded_body.to_string(),
            )
            .await;
        let http_response: TriggersFrontendResponse = match response {
            Ok(msg) => {
                let tid = thread::current().id();
                let message: String = format!("Created trigger, id: {}, type: {}, workflows: {:?}, trigger_info {:?}, {:?}, {}", &trigger_id, &trigger_type, &workflows_vec, &trigger_info, tid, msg);
                info!("[CREATE_TRIGGER] {}", &message);
                TriggersFrontendResponse {
                    status: "Success".into(),
                    message,
                }
            }
            Err(msg) => {
                let message: String = format!("ERROR creating trigger, id: {}, type: {}, workflows: {:?}, trigger_info {:?}, {}", &trigger_id, &trigger_type, &workflows_vec, &trigger_info, msg);
                warn!("[CREATE_TRIGGER] {}", &message);
                TriggersFrontendResponse {
                    status: "Failure".into(),
                    message,
                }
            }
        };
        return HttpResponse::Ok().json(http_response);
    } else {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "Unknow type".to_string(),
        });
    }
}

async fn add_workflows(req: HttpRequest, body: web::Bytes) -> impl Responder {
    // body is loaded, now we can deserialize json-rust
    let mut decoded_body = std::str::from_utf8(&body);
    if let Err(e) = decoded_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an utf8 string. Error: {}.",
                e.to_string()
            ),
        });
    }

    let decoded_body = decoded_body.unwrap();
    let json_body = json::parse(&decoded_body);
    if let Err(e) = json_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an a valid json object. Error: {}.",
                e.to_string()
            ),
        });
    }

    let json_body = json_body.unwrap();
    if !(json_body.is_object()
        && json_body.has_key("id")
        && json_body.has_key("workflows")
        && json_body["workflows"].is_array()
        && json_body["workflows"].len() > 0)
    {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "One of the required fields, 'id' or 'workflows'".into(),
        });
    }
    let trigger_id: String = json_body["id"].to_string();
    let mut workflows_vec: Vec<WorkflowInfo> = Vec::new();
    let workflows = &json_body["workflows"];
    for i in 0..workflows.len() {
        let workflow_info = &workflows[i];
        if !workflow_info.has_key("workflow_url") {
            return HttpResponse::Ok().json(TriggersFrontendResponse {
                status: "Failure".into(),
                message: "workflow_url missing in workflows list".into(),
            });
        }
        let tag: String = if workflow_info.has_key("tag") {
            workflow_info["tag"].to_string()
        } else {
            "".into()
        };
        workflows_vec.push(WorkflowInfo {
            workflow_url: workflow_info["workflow_url"].to_string(),
            tag,
        });
    }
    info!(
        "[ADD_WORKFLOW] request, id: {}, workflows: {:?}",
        &trigger_id, &workflows_vec
    );

    let mut trigger_manager: TriggerManager = req.app_data::<TriggerManager>().unwrap().clone();
    let response: Result<String, String> = trigger_manager
        .handle_add_workflows(&trigger_id, workflows_vec.clone())
        .await;
    let http_response: TriggersFrontendResponse = match response {
        Ok(msg) => {
            let tid = thread::current().id();
            let message: String = format!(
                "Add workflow, id: {}, workflows: {:?}, {}",
                &trigger_id, &workflows_vec, msg
            );
            info!("[ADD_WORKFLOW] {}", &message);
            TriggersFrontendResponse {
                status: "Success".into(),
                message,
            }
        }
        Err(msg) => {
            let message: String = format!(
                "ERROR adding workflow trigger, id: {}, workflows: {:?}, {}",
                &trigger_id, &workflows_vec, msg
            );
            warn!("[ADD_WORKFLOW] {}", &message);
            TriggersFrontendResponse {
                status: "Failure".into(),
                message,
            }
        }
    };
    return HttpResponse::Ok().json(http_response);
}

async fn remove_workflows(req: HttpRequest, body: web::Bytes) -> impl Responder {
    // body is loaded, now we can deserialize json-rust
    let mut decoded_body = std::str::from_utf8(&body);
    if let Err(e) = decoded_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an utf8 string. Error: {}.",
                e.to_string()
            ),
        });
    }

    let decoded_body = decoded_body.unwrap();
    let json_body = json::parse(&decoded_body);
    if let Err(e) = json_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an a valid json object. Error: {}.",
                e.to_string()
            ),
        });
    }

    let json_body = json_body.unwrap();
    if !(json_body.is_object()
        && json_body.has_key("id")
        && json_body.has_key("workflows")
        && json_body["workflows"].is_array()
        && json_body["workflows"].len() > 0)
    {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "One of the required fields, 'id' or 'workflows'".into(),
        });
    }
    let trigger_id: String = json_body["id"].to_string();
    let mut workflows_vec: Vec<WorkflowInfo> = Vec::new();
    let workflows = &json_body["workflows"];
    for i in 0..workflows.len() {
        let workflow_info = &workflows[i];
        if !workflow_info.has_key("workflow_url") {
            return HttpResponse::Ok().json(TriggersFrontendResponse {
                status: "Failure".into(),
                message: "workflow_url missing in workflows list".into(),
            });
        }
        let tag: String = if workflow_info.has_key("tag") {
            workflow_info["tag"].to_string()
        } else {
            "".into()
        };
        workflows_vec.push(WorkflowInfo {
            workflow_url: workflow_info["workflow_url"].to_string(),
            tag,
        });
    }
    info!(
        "[REMOVE_WORKFLOWS] request, id: {}, workflows: {:?}",
        &trigger_id, &workflows_vec
    );

    let mut trigger_manager: TriggerManager = req.app_data::<TriggerManager>().unwrap().clone();
    let response: Result<String, String> = trigger_manager
        .handle_remove_workflows(&trigger_id, workflows_vec.clone())
        .await;
    let http_response: TriggersFrontendResponse = match response {
        Ok(msg) => {
            let tid = thread::current().id();
            let message: String = format!(
                "Remove workflows, id: {}, workflows: {:?}, {}",
                &trigger_id, &workflows_vec, msg
            );
            info!("[REMOVE_WORKFLOWS] {}", &message);
            TriggersFrontendResponse {
                status: "Success".into(),
                message,
            }
        }
        Err(msg) => {
            let message: String = format!(
                "ERROR removing workflows, trigger, id: {}, workflows: {:?}, {}",
                &trigger_id, &workflows_vec, msg
            );
            warn!("[REMOVE_WORKFLOWS] {}", &message);
            TriggersFrontendResponse {
                status: "Failure".into(),
                message,
            }
        }
    };
    return HttpResponse::Ok().json(http_response);
}

async fn delete_trigger(req: HttpRequest, body: web::Bytes) -> impl Responder {
    // body is loaded, now we can deserialize json-rust
    let mut decoded_body = std::str::from_utf8(&body);
    if let Err(e) = decoded_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an utf8 string. Error: {}.",
                e.to_string()
            ),
        });
    }

    let decoded_body = decoded_body.unwrap();
    let json_body = json::parse(&decoded_body);
    if let Err(e) = json_body {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: format!(
                "Unable to decode body into an a valid json object. Error: {}.",
                e.to_string()
            ),
        });
    }
    let json_body = json_body.unwrap();
    if !(json_body.is_object() && json_body.has_key("id")) {
        return HttpResponse::Ok().json(TriggersFrontendResponse {
            status: "Failure".into(),
            message: "One of the required fields, 'id' is missing.".into(),
        });
    }
    let trigger_id: String = json_body["id"].to_string();
    info!("[DELETE_TRIGGER] request, id: {}", &trigger_id);

    let mut trigger_manager: TriggerManager = req.app_data::<TriggerManager>().unwrap().clone();
    let response: Result<String, String> = trigger_manager.handle_delete_trigger(&trigger_id).await;
    let http_response: TriggersFrontendResponse = match response {
        Ok(msg) => {
            let tid = thread::current().id();
            let message: String =
                format!("Deleted trigger, id: {}, {:?}, {}", &trigger_id, tid, msg);
            info!("[DELETE_TRIGGER] {}", &message);
            TriggersFrontendResponse {
                status: "Success".into(),
                message,
            }
        }
        Err(msg) => {
            let message: String = format!("ERROR deleting trigger, id: {}, {}", &trigger_id, msg);
            warn!("[CREATE_TRIGGER] {}", &message);
            TriggersFrontendResponse {
                status: "Failure".into(),
                message,
            }
        }
    };
    return HttpResponse::Ok().json(http_response);
}

/*
async fn startactor(req: HttpRequest, data: web::Data<Mutex<AppState>>) -> impl Responder {
    let actorid = req.match_info().get("id").unwrap_or("0").to_string();
    let mut return_body = String::from("startactor response: ");
    // Critical section start
    {
        if let Ok(mut id_map) = data.lock() {
            if let Some(actor_info) = id_map.get(&actorid) {
                return_body = return_body + &format!("Actor {} exists already", &actorid);
            } else {
                return_body = return_body + &format!("Actor {} created", &actorid);
                id_map.insert(
                    String::from(actorid.clone()),
                    TriggerInfo {
                        actorid: actorid.clone(),
                    },
                );
            }
        } else {
            return_body = return_body
                + &format!(
                    "Internal error: unable to lock id_to_actor_map, could not process Actor {}",
                    &actorid
                );
        }
    } // Critical section end
    return_body
}

async fn stopactor(req: HttpRequest, data: web::Data<Mutex<AppState>>) -> impl Responder {
    let actorid = req.match_info().get("id").unwrap_or("0");
    let mut return_body = String::from("stopactor response: ");
    // Critical section start
    {
        if let Ok(mut id_map) = data.lock() {
            if let Some(actor_info) = id_map.remove(actorid) {
                return_body = return_body + &format!("Actor {} removed", &actorid);
            } else {
                return_body = return_body + &format!("Actor {} does not exist", &actorid);
            }
        } else {
            return_body = return_body
                + &format!(
                    "Internal error: unable to lock id_to_actor_map, could not process Actor {}",
                    &actorid
                );
        }
    } // Critical section end
    return_body
}
*/

async fn register_with_management(manager_info: TriggerManagerInfo) {
    let update_message = TriggerManagerStatusUpdateMessage {
        action: manager_info.management_action.clone(),
        data: TriggerManagerStatusUpdateMessageData {
            action: "start".into(),
            self_ip: manager_info.self_ip.clone(),
            trigger_status_map: HashMap::new(),
            trigger_error_map: HashMap::new(),
        },
    };
    let serialized_update_message = serde_json::to_string(&update_message).unwrap();
    loop {
        let ret = send_post_json_message(
            manager_info.management_url.clone(),
            serialized_update_message.clone(),
        )
        .await;
        if ret == false {
            warn!(
                "Unable to register with Management at: {}, with data: {}. Retrying in 1 sec.",
                &manager_info.management_url, &serialized_update_message
            );
            create_delay(1000, "management registration".into()).await;
        } else {
            info!(
                "Registered with Management at: {}, with data: {}.",
                &manager_info.management_url, &serialized_update_message
            );
            break;
        }
    }
}

async fn stopserver(req: HttpRequest) -> impl Responder {
    let mut trigger_manager: TriggerManager = req.app_data::<TriggerManager>().unwrap().clone();
    let response: Result<String, String> = trigger_manager.handle_stop().await;
    tokio::spawn(async { create_delay(1000, "".into()).await; process::exit(0); });
    HttpResponse::Ok().body("ok")
}

async fn health() -> impl Responder {
    HttpResponse::Ok().body("ok")
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    let start = std::time::Instant::now();
    if std::env::var("RUST_LOG").is_err() {
        std::env::set_var("RUST_LOG", "info");
    }
    env_logger::Builder::from_default_env()
        .format(move |buf, rec| {
            let t = start.elapsed().as_secs_f32();
            let t2 = Local::now().to_rfc2822();
            let tid = thread::current().id();
            writeln!(
                buf,
                "[{}] [{:.06}] [{}] [{:?}] [{}:{}] {}",
                t2,
                t,
                rec.level(),
                tid,
                rec.target(),
                rec.line().unwrap(),
                rec.args(),
            )
        })
        .init();

    let management_url =
        std::env::var("MANAGEMENT_URL").expect("MANAGEMENT_URL env variable not specified");
    let management_action =
        std::env::var("MANAGEMENT_ACTION").unwrap_or("triggersFrontendStatus".into());
    let update_interval: u32 = std::env::var("MANAGEMENT_UPDATE_INTERVAL_SEC")
        .unwrap_or("60".into())
        .parse::<u32>()
        .unwrap_or(60)
        * 1000;
    let port: String = std::env::var("TRIGGERS_FRONTEND_PORT").unwrap_or("8080".into());

    // let self_ip = machine_ip::get()
    //     .expect("Unable to get the IP address of the machine")
    //     .to_string();
    let self_ip = std::env::var("HOST_IP").expect("HOST_IP env variable not specified");

    let mut host_port: String = String::from("0.0.0.0:");
    host_port.push_str(&port);

    let manager_info = TriggerManagerInfo {
        management_url,
        management_action,
        update_interval,
        self_ip,
        server_url: host_port.clone(),
    };

    tokio::spawn(register_with_management(manager_info.clone())).await;

    let trigger_manager: TriggerManager = TriggerManager::spawn(manager_info.clone());

    info!(
        "Starting server on {}, Starting config: {:?}",
        &host_port, manager_info
    );
    HttpServer::new(move || {
        App::new()
            .wrap(Logger::default())
            .app_data(trigger_manager.clone())
            .route("/create_trigger", web::post().to(create_trigger))
            .route("/delete_trigger", web::post().to(delete_trigger))
            .route("/add_workflows", web::post().to(add_workflows))
            .route("/remove_workflows", web::post().to(remove_workflows))
            .route("/stop", web::get().to(stopserver))
            .route("/", web::get().to(health))
        //.route("/startactor/{id}", web::get().to(startactor))
        //.route("/stopactor/{id}", web::get().to(stopactor))
    })
    .bind(host_port.as_str())?
    .workers(3)
    .disable_signals()
    .run()
    .await
}
