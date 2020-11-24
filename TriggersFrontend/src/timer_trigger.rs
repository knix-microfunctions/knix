#[allow(dead_code,unused,unused_must_use)]
use crate::utils::create_delay;
use crate::utils::send_post_json_message;
use crate::utils::WorkflowInfo;
use crate::CommandResponseChannel;
use crate::TriggerCommand;
use crate::TriggerCommandChannel;
use crate::TriggerManager;
use json::JsonValue;
use log::*;
use std::borrow::Borrow;
use std::error::Error;
use std::rc::Rc;
use tokio::stream::StreamExt;
use tokio::sync::mpsc::{channel, Receiver, Sender};
use tokio::sync::oneshot;

use crate::trigger_manager::send_status_update_from_trigger_to_manager;
use crate::trigger_manager::TriggerManagerCommandChannelSender;
use crate::utils::find_element_index;
use crate::utils::TriggerError;
use crate::utils::TriggerWorkflowMessage;
use crate::TriggerStatus;

#[derive(Clone)]
pub struct TimerInfo {
    timer_interval: u64,
}

pub struct TimerTrigger {
    trigger_id: String,
    trigger_name: String,
    timer_info: TimerInfo,
    workflows: Vec<WorkflowInfo>,
    // Sender return
    cmd_channel_tx: TriggerCommandChannel,
}

impl TimerTrigger {
    pub fn spawn(
        trigger_id: &String,
        trigger_name: &String,
        timer_info: TimerInfo,
        workflows: Vec<WorkflowInfo>,
        manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
    ) -> std::result::Result<TimerTrigger, ()> {
        let (cmd_channel_tx, cmd_channel_rx) =
            channel::<(TriggerCommand, CommandResponseChannel)>(5);
        tokio::spawn(timer_actor_retry_loop(
            trigger_id.clone(),
            trigger_name.clone(),
            timer_info.clone(),
            workflows.clone(),
            cmd_channel_rx,
            manager_cmd_channel_tx,
        ));
        Ok(TimerTrigger {
            trigger_id: trigger_id.clone(),
            trigger_name: trigger_name.clone(),
            timer_info: timer_info.clone(),
            workflows: workflows.clone(),
            cmd_channel_tx,
        })
    }
}

pub async fn handle_create_timer_trigger(
    trigger_id: &String,
    trigger_name: &String,
    workflows: Vec<WorkflowInfo>,
    request_body: &String,
    manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) -> std::result::Result<TriggerCommandChannel, String> {
    let json_body = json::parse(request_body).unwrap();
    let trigger_info = &json_body["trigger_info"];

    if !(trigger_info.has_key("timer_interval_ms") && trigger_info["timer_interval_ms"].is_number())
    {
        return Err("One of the required fields, 'timer_interval_ms' is missing".into());
    }

    if trigger_info["timer_interval_ms"].as_i64().is_none() {
        return Err("Unable to parse 'timer_interval_ms' field".into());
    }
    let interval = trigger_info["timer_interval_ms"].as_i64().unwrap();
    if interval < 20 {
        return Err("Timer interval must be >= 20ms".into());
    }
    let timer_interval: u64 = interval as u64;
    let timer_info = TimerInfo { timer_interval };

    let timer_trigger =
        TimerTrigger::spawn(&trigger_id, &trigger_name, timer_info, workflows, manager_cmd_channel_tx).unwrap();

    Ok(timer_trigger.cmd_channel_tx)
}

async fn send_timer_data(
    workflows: Vec<WorkflowInfo>,
    timer_data: String,
    trigger_id: String,
    trigger_name: String,
    source: String,
) {
    for workflow_info in workflows {
        let workflow_msg = TriggerWorkflowMessage {
            trigger_status: "ready".into(),
            trigger_type: "timer".into(),
            trigger_name: trigger_name.clone(),
            workflow_name: workflow_info.workflow_name,
            source: source.clone(),
            data: timer_data.clone(), // TODO: Figure out how to pass the String around,
                                      // without copying and keeping the borrow checker happy!
        };
        let serialized_workflow_msg = serde_json::to_string(&workflow_msg);
        info!(
            "[send_timer_data] Trigger id {}, Sending message: {}",
            trigger_id,
            serialized_workflow_msg.as_ref().unwrap()
        );
        send_post_json_message(
            workflow_info.workflow_url,
            serialized_workflow_msg.unwrap(),
            "".into(),
            workflow_info.workflow_state.clone(),
            true
        ).await;
    }
}

pub async fn timer_actor_retry_loop(
    trigger_id: String,
    trigger_name: String,
    timer_info: TimerInfo,
    workflows: Vec<WorkflowInfo>,
    mut cmd_channel_rx: Receiver<(TriggerCommand, CommandResponseChannel)>,
    mut manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) {
    let res: std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> = timer_actor_loop(
        &trigger_id,
        &trigger_name,
        &timer_info,
        workflows,
        &mut cmd_channel_rx,
        &mut manager_cmd_channel_tx,
    )
    .await;
    match res {
        Ok(()) => {
            info!(
                "[timer_actor_retry_loop] {} timer_actor_loop finished without errors",
                trigger_id.clone()
            );
        }
        Err(e) => {
            warn!(
                "[timer_actor_retry_loop] {} timer_actor_loop finished with an error: {}",
                trigger_id.clone(),
                e.to_string()
            );
            send_status_update_from_trigger_to_manager(
                trigger_id.clone(),
                TriggerStatus::StoppedError,
                format!("Error: {}", e.to_string()),
                manager_cmd_channel_tx.clone(),
            )
            .await;
        }
    }
}

pub async fn timer_actor_loop(
    trigger_id: &String,
    trigger_name: &String,
    timer_info: &TimerInfo,
    mut workflows: Vec<WorkflowInfo>,
    cmd_channel_rx: &mut Receiver<(TriggerCommand, CommandResponseChannel)>,
    manager_cmd_channel_tx: &mut TriggerManagerCommandChannelSender,
) -> std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let timer_interval = timer_info.timer_interval;
    info!(
        "[timer_actor_loop] {} start, with interval {}",
        trigger_id, timer_interval
    );

    let timer_interval = timer_info.timer_interval;
    info!("[timer_actor_loop] {} Ready", trigger_id);
    send_status_update_from_trigger_to_manager(
        trigger_id.clone(),
        TriggerStatus::Ready,
        "".into(),
        manager_cmd_channel_tx.clone(),
    )
    .await;

    loop {
        tokio::select! {
            cmd = cmd_channel_rx.recv() => {
                match cmd {
                    Some((c, resp)) => {
                        match c {
                            TriggerCommand::Status => {
                                info!("[timer_actor_loop] {} Status cmd recv", trigger_id);
                                resp.send((true, "ok".to_string()));
                            }
                            TriggerCommand::AddWorkflows(workflows_to_add) => {
                                for workflow in workflows_to_add {
                                    workflows.push(workflow.clone());
                                }
                                resp.send((true, "ok".to_string()));
                            }
                            TriggerCommand::RemoveWorkflows(workflows_to_remove) => {
                                for workflow in workflows_to_remove {
                                    let idx = find_element_index(&workflow, &workflows);
                                    if idx >= 0 {
                                        workflows.remove(idx as usize);
                                    }
                                }
                                resp.send((true, "ok".to_string()));
                            }
                            TriggerCommand::Stop => {
                                info!("[timer_actor_loop] {} Stop cmd recv", trigger_id);
                                resp.send((true, "ok".to_string()));
                                send_status_update_from_trigger_to_manager(
                                    trigger_id.clone(),
                                    TriggerStatus::StoppedNormal,
                                    "".into(),
                                    manager_cmd_channel_tx.clone(),
                                ).await;
                                break;
                            }
                        }
                    }
                    None => {
                        let ret_msg = format!("[timer_actor_loop] Trigger id {}, None recv on command channel", trigger_id);
                        warn!("{}", ret_msg);
                        return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
                    },
                }
            }
            d = create_delay(timer_interval, "TimerTrigger, status push timer".to_string()) => {
                if workflows.len() > 0 {
                    //tokio::spawn(send_timer_data(workflows.clone(), "".into(), trigger_id.clone(), trigger_name.clone(), "".into())).await;
                    send_timer_data(workflows.clone(), "".into(), trigger_id.clone(), trigger_name.clone(), "".into()).await;
                }
            }
        }
    }
    Ok(())
}
