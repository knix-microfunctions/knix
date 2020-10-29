#[allow(dead_code,unused,unused_must_use)]
use json::JsonValue;
use log::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, SystemTime};
use tokio::signal::unix::{signal, SignalKind};
use tokio::stream::StreamExt;
use tokio::sync::mpsc::{channel, Receiver, Sender};
use tokio::sync::oneshot;

use crate::amqp_trigger::handle_create_amqp_trigger;
use crate::mqtt_triggers::handle_create_mqtt_trigger;
use crate::timer_trigger::handle_create_timer_trigger;
use crate::utils::create_delay;
use crate::utils::send_get_message;
use crate::utils::send_post_json_message;
use crate::utils::string_to_trigger_status;
use crate::utils::trigger_status_to_string;
use crate::utils::WorkflowInfo;
use crate::CommandResponseChannel;
use crate::TriggerCommand;
use crate::TriggerCommandChannel;
use crate::TriggerStatus;

#[derive(Clone, Debug)]
pub struct TriggerManagerInfo {
    pub management_url: String,
    pub management_request_host_header: String,
    pub management_action: String,
    pub update_interval: u32,
    pub self_ip_port: String,
    pub server_url: String,
}

#[derive(Serialize)]
pub struct TriggerManagerStatusUpdateMessageData {
    pub action: String,
    pub self_ip_port: String,
    pub trigger_status_map: HashMap<String, TriggerStatus>,
    pub trigger_error_map: HashMap<String, String>,
    pub user: HashMap<String, String>,
}

#[derive(Serialize)]
pub struct TriggerManagerStatusUpdateMessage {
    pub action: String,
    pub data: TriggerManagerStatusUpdateMessageData,
}

#[derive(Debug, Clone)]
pub enum TriggerManagerCommand {
    RegisterTriggerId(String),                             // id
    RegisterTriggerChannel(String, TriggerCommandChannel), // id, sending channel to trigger actor
    UpdateTriggerStatus(String, TriggerStatus, String), // id, status, status_message (incase of error)
    GetTriggerStatus(String),                           // id, status_msg (incase of error)
    StopTrigger(String),                                // id
    DeleteTrigger(String),                              // id
    AddWorkflows(String, Vec<WorkflowInfo>),            // id, Workflows to be added
    RemoveWorkflows(String, Vec<WorkflowInfo>),         // id, Workflows to be removed
    StopManager,
}
pub type TriggerManagerCommandChannelSender =
    Sender<(TriggerManagerCommand, CommandResponseChannel)>;
pub type TriggerManagerCommandChannelReceiver =
    Receiver<(TriggerManagerCommand, CommandResponseChannel)>;

#[derive(Clone)]
pub struct TriggerManager {
    pub cmd_channel_tx: TriggerManagerCommandChannelSender,
}

impl TriggerManager {
    pub fn spawn(manager_info: TriggerManagerInfo) -> Self {
        let (mut cmd_channel_tx, mut cmd_channel_rx) =
            channel::<(TriggerManagerCommand, CommandResponseChannel)>(100);

        tokio::spawn(trigger_manager_actor_loop(
            manager_info.clone(),
            cmd_channel_rx,
        ));

        TriggerManager { cmd_channel_tx }
    }

    pub async fn send_cmd(
        &mut self,
        trigger_id: &String,
        cmd: TriggerManagerCommand,
    ) -> Result<String, String> {
        let (resp_tx, resp_rx) = oneshot::channel::<(bool, String)>();
        let send_result = self.cmd_channel_tx.send((cmd.clone(), resp_tx)).await;
        match send_result {
            Ok(m) => {
                // No error on sending channel, so check for a response
                let response = resp_rx.await;
                match response {
                    // No error on response channel
                    Ok((status, message)) => {
                        if status {
                            debug!(
                                "[send_cmd] {}, cmd {:?}, response: status {}, message: {}",
                                &trigger_id, &cmd, status, message
                            );
                            Ok(message)
                        } else {
                            warn!(
                                "[send_cmd] {}, cmd {:?}, Error msg response: status {}, message: {}",
                                &trigger_id, &cmd, status, message
                            );
                            Err(message)
                        }
                    }
                    Err(e) => {
                        // Some error on response channel
                        warn!(
                            "[send_cmd] {}, cmd {:?}, Error on response channel: {}",
                            &trigger_id,
                            &cmd,
                            e.to_string()
                        );
                        Err(e.to_string())
                    }
                }
            }
            Err(e) => {
                // Error on sending channel
                warn!(
                    "[send_cmd] {} Error on sending channel: {}",
                    &trigger_id,
                    e.to_string()
                );
                Err(e.to_string())
            }
        }
    }

    pub async fn send_register_trigger_id_msg(
        &mut self,
        trigger_id: &String,
    ) -> Result<String, String> {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::RegisterTriggerId(trigger_id.clone()),
        )
        .await
    }

    pub async fn send_register_trigger_channel_msg(
        &mut self,
        trigger_id: &String,
        chan: TriggerCommandChannel,
    ) -> Result<String, String> {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::RegisterTriggerChannel(trigger_id.clone(), chan),
        )
        .await
    }

    pub async fn send_update_trigger_status_msg(
        &mut self,
        trigger_id: &String,
        status: TriggerStatus,
        status_message: &String,
    ) -> Result<String, String> {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::UpdateTriggerStatus(
                trigger_id.clone(),
                status,
                status_message.clone(),
            ),
        )
        .await
    }

    pub async fn send_get_status_msg(
        &mut self,
        trigger_id: &String,
    ) -> Option<(TriggerStatus, String)> {
        let status = self
            .send_cmd(
                &trigger_id,
                TriggerManagerCommand::GetTriggerStatus(trigger_id.clone()),
            )
            .await;
        match status {
            Ok(status) => {
                let status = json::parse(&status).unwrap();
                Some((
                    string_to_trigger_status(&status["status"].to_string()),
                    status["status_msg"].to_string(),
                ))
            }
            Err(msg) => None,
        }
    }

    pub async fn send_stop_trigger_msg(&mut self, trigger_id: &String) -> Result<String, String> {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::StopTrigger(trigger_id.clone()),
        )
        .await
    }

    pub async fn send_delete_trigger_msg(&mut self, trigger_id: &String) {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::DeleteTrigger(trigger_id.clone()),
        )
        .await;
    }

    pub async fn send_add_workflows_msg(
        &mut self,
        trigger_id: &String,
        workflows: Vec<WorkflowInfo>,
    ) -> Result<String, String> {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::AddWorkflows(trigger_id.clone(), workflows.clone()),
        )
        .await
    }

    pub async fn send_remove_workflows_msg(
        &mut self,
        trigger_id: &String,
        workflows: Vec<WorkflowInfo>,
    ) -> Result<String, String> {
        self.send_cmd(
            &trigger_id,
            TriggerManagerCommand::RemoveWorkflows(trigger_id.clone(), workflows.clone()),
        )
        .await
    }

    pub async fn send_stop_manager_msg(&mut self) -> Result<String, String> {
        self.send_cmd(&"".to_string(), TriggerManagerCommand::StopManager)
            .await
    }

    pub async fn register_trigger_if_not_present_or_stopped(
        &mut self,
        trigger_id: &String,
    ) -> bool {
        let status = self.send_get_status_msg(&trigger_id).await;
        match status {
            Some((status, status_msg)) => match status {
                TriggerStatus::Starting | TriggerStatus::Ready => false,
                _ => {
                    self.send_delete_trigger_msg(&trigger_id).await;
                    self.send_register_trigger_id_msg(&trigger_id).await;
                    true
                }
            },
            None => {
                self.send_register_trigger_id_msg(&trigger_id).await;
                true
            }
        }
    }

    pub async fn wait_for_trigger_ready(
        &mut self,
        trigger_id: &String,
        timeout_ms: i64,
    ) -> std::result::Result<TriggerStatus, String> {
        const decrement: u64 = 500;
        create_delay(decrement, "trigger_ready_wait".into()).await;
        let mut time_remaining: i64 = timeout_ms - decrement as i64;
        let mut curr_status: Option<TriggerStatus> = None;
        let mut curr_status_msg: String = "".into();
        loop {
            let status = self.send_get_status_msg(&trigger_id).await;
            match status {
                Some((status, status_msg)) => match status {
                    TriggerStatus::Ready => {
                        curr_status = Some(status);
                        break;
                    }
                    TriggerStatus::Starting => {
                        curr_status = Some(status);
                        time_remaining -= decrement as i64;
                        create_delay(decrement, "trigger_ready_wait".into()).await;
                    }
                    TriggerStatus::Stopping => {
                        curr_status = Some(status);
                        time_remaining -= decrement as i64;
                        create_delay(decrement, "trigger_ready_wait".into()).await;
                    }
                    TriggerStatus::StoppedNormal | TriggerStatus::StoppedError => {
                        curr_status = Some(status);
                        curr_status_msg = status_msg;
                        break;
                    }
                },
                None => {
                    error!(
                        "Trying to wait for status of trigger ({}), when status value does not exist",
                        &trigger_id
                    );
                    break;
                }
            }
            if time_remaining < 0 {
                break;
            }
        }

        if let None = curr_status {
            return Err("Unable to get status of the trigger".into());
        } else if let TriggerStatus::Ready | TriggerStatus::Starting = curr_status.as_ref().unwrap()
        {
            Ok(curr_status.unwrap())
        } else {
            Err(curr_status_msg)
        }
    }

    pub async fn handle_create_trigger(
        &mut self,
        trigger_type: &String,
        trigger_id: &String,
        workflows: Vec<WorkflowInfo>,
        request_body: String,
    ) -> Result<String, String> {
        // this will return false if the trigger_id is already registered with either Ready or Starting state
        let id_registered = self
            .register_trigger_if_not_present_or_stopped(&trigger_id)
            .await;

        if id_registered {
            let trigger_spawned = match trigger_type.as_str() {
                "amqp" => {
                    handle_create_amqp_trigger(
                        &trigger_id,
                        workflows,
                        &request_body,
                        self.cmd_channel_tx.clone(),
                    )
                    .await
                }
                "mqtt" => {
                    handle_create_mqtt_trigger(
                        &trigger_id,
                        workflows,
                        &request_body,
                        self.cmd_channel_tx.clone(),
                    )
                    .await
                }
                "timer" => {
                    handle_create_timer_trigger(
                        &trigger_id,
                        workflows,
                        &request_body,
                        self.cmd_channel_tx.clone(),
                    )
                    .await
                }
                _ => Err("unsuported type".into()),
            };

            match trigger_spawned {
                Ok(chan) => {
                    // wait for getting ready or timeout while in Starting state
                    let ready_result = self.wait_for_trigger_ready(&trigger_id, 4000).await;
                    match ready_result {
                        Ok(status) => {
                            // Either the trigger is ready or is starting
                            let chan_registered = self
                                .send_register_trigger_channel_msg(&trigger_id, chan.clone())
                                .await;
                            match chan_registered {
                                Ok(status_msg) => return Ok(status_msg),
                                Err(status_msg) => {
                                    let ret_msg = format!(
                                        "Unable to register channel for trigger {}. Error: {}",
                                        &trigger_id, status_msg
                                    );
                                    warn!("{}", &ret_msg);
                                    self.send_delete_trigger_msg(&trigger_id).await;
                                    return Err(ret_msg);
                                }
                            }
                        }
                        Err(msg) => {
                            // Either the trigger has stopped, or something else
                            warn!(
                                "Unable to get ready status for trigger {}, Error: {}",
                                &trigger_id, &msg
                            );
                            return Err(msg);
                        }
                    }
                }
                Err(msg) => {
                    self.send_delete_trigger_msg(&trigger_id).await;
                    return Err(msg);
                }
            }
        } else {
            Err(format!(
                "Trigger {} exists in either Starting or Ready state",
                &trigger_id
            ))
        }
    }

    pub async fn handle_add_workflows(
        &mut self,
        trigger_id: &String,
        workflows: Vec<WorkflowInfo>,
    ) -> Result<String, String> {
        self.send_add_workflows_msg(&trigger_id, workflows).await
    }

    pub async fn handle_remove_workflows(
        &mut self,
        trigger_id: &String,
        workflows: Vec<WorkflowInfo>,
    ) -> Result<String, String> {
        self.send_remove_workflows_msg(&trigger_id, workflows).await
    }

    pub async fn handle_delete_trigger(&mut self, trigger_id: &String) -> Result<String, String> {
        let (alive, status_msg) = self.is_trigger_alive(&trigger_id).await;
        if alive {
            let stop_result = self.send_stop_trigger_msg(&trigger_id).await;
            self.send_delete_trigger_msg(&trigger_id).await;
            match stop_result {
                Ok(status_msg) => {
                    let ret_msg = format!(
                        "[handle_delete_trigger] Trigger id {} stopped. {}",
                        &trigger_id, status_msg
                    );
                    info!("{}", &ret_msg);
                    return Ok(ret_msg);
                }
                Err(status_msg) => {
                    let ret_msg = format!(
                        "[handle_delete_trigger] Error while stopping Trigger id {}. {}",
                        &trigger_id, status_msg
                    );
                    warn!("{}", &ret_msg);
                    return Err(ret_msg);
                }
            }
        } else {
            let ret_msg = format!(
                "[handle_delete_trigger] Ignoring delete command for trigger id {}. {}",
                &trigger_id, &status_msg
            );
            warn!("{}", ret_msg);
            self.send_delete_trigger_msg(&trigger_id).await;
            return Err(ret_msg);
        }
    }

    async fn is_trigger_alive(&mut self, trigger_id: &String) -> (bool, String) {
        let status = self.send_get_status_msg(&trigger_id).await;
        match status {
            Some((status, status_msg)) => match status {
                TriggerStatus::Ready | TriggerStatus::Starting => {
                    return (true, status_msg);
                }
                TriggerStatus::Stopping
                | TriggerStatus::StoppedNormal
                | TriggerStatus::StoppedError => {
                    return (false, status_msg);
                }
            },
            None => {
                let ret_msg = format!(
                    "[is_trigger_alive] Trying to get for status of trigger ({}), when status value does not exist",
                    &trigger_id
                );
                error!("{}", &ret_msg);
                return (false, ret_msg);
            }
        }
    }

    pub async fn handle_stop(&mut self) -> Result<String, String> {
        self.send_stop_manager_msg().await
    }
}

pub async fn send_status_update_from_trigger_to_manager(
    trigger_id: String,
    status: TriggerStatus,
    status_message: String,
    mut manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) {
    let (resp_tx, resp_rx) = oneshot::channel::<(bool, String)>();
    let send_result = manager_cmd_channel_tx
        .send((
            TriggerManagerCommand::UpdateTriggerStatus(trigger_id.clone(), status, status_message),
            resp_tx,
        ))
        .await;
    match send_result {
        Ok(m) => (),
        Err(e) => {
            // Error on sending channel
            warn!(
                "[send_status_update_from_trigger_to_manager] {} Error on sending channel: {}",
                &trigger_id,
                e.to_string()
            );
        }
    }
}

async fn report_status_to_management(management_url: String, data: String, host_header: String) {
    info!(
        "[report_status_to_management] POST to {}, with data {}",
        management_url, &data
    );
    tokio::spawn(send_post_json_message(management_url, data, host_header));
}

async fn send_server_stop_msg(url: String) {
    tokio::spawn(send_get_message(format!("http://{}/stop", &url)));
}

async fn send_shutdown_messages(
    id_to_trigger_status_map: &mut HashMap<String, TriggerStatus>,
    id_to_trigger_error_map: &mut HashMap<String, String>,
    id_to_trigger_chan_map: &mut HashMap<String, TriggerCommandChannel>,
    manager_info: TriggerManagerInfo,
) {
    for (trigger_id, _) in id_to_trigger_status_map.iter() {
        id_to_trigger_error_map.insert(
            trigger_id.clone(),
            "TriggerFrontend shutdown initiated".into(),
        );
    }
    let update_message = TriggerManagerStatusUpdateMessage {
        action: manager_info.management_action.clone(),
        data: TriggerManagerStatusUpdateMessageData {
            action: "stop".into(),
            self_ip_port: manager_info.self_ip_port.clone(),
            trigger_status_map: HashMap::new(),
            trigger_error_map: id_to_trigger_error_map.clone(),
            user: HashMap::new(),
        },
    };
    let serialized_update_message = serde_json::to_string(&update_message);
    let posted = send_post_json_message(
        manager_info.management_url.clone(),
        serialized_update_message.unwrap(),
        manager_info.management_request_host_header.clone(),
    )
    .await;
    if posted == false {
        error!("Unable to send shutdown message to management");
    } else {
        warn!("Sent shutdown message to management");
    }

    let mut new_id_to_trigger_status_map = HashMap::new();
    for (trigger_id, _) in id_to_trigger_status_map.iter() {
        new_id_to_trigger_status_map.insert(trigger_id.clone(), TriggerStatus::Stopping);
    }

    *id_to_trigger_status_map = new_id_to_trigger_status_map;

    for (_, chan) in id_to_trigger_chan_map.iter() {
        let mut trigger_channel = chan.clone();
        tokio::spawn(async move {
            let (resp_tx, resp_rx) = oneshot::channel::<(bool, String)>();
            trigger_channel.send((TriggerCommand::Stop, resp_tx)).await;
        });
    }
}

async fn trigger_manager_actor_loop(
    manager_info: TriggerManagerInfo,
    mut cmd_channel_rx: Receiver<(TriggerManagerCommand, CommandResponseChannel)>,
) -> Result<(), ()> {
    info!("[trigger_manager_actor_loop] start");

    let mut id_to_trigger_status_map: HashMap<String, TriggerStatus> = HashMap::new();
    let mut id_to_trigger_chan_map: HashMap<String, TriggerCommandChannel> = HashMap::new();
    let mut id_to_trigger_error_map: HashMap<String, String> = HashMap::new(); // this is to store error messages
    let mut signal_sigint = signal(SignalKind::interrupt()).unwrap();
    let mut signal_sigterm = signal(SignalKind::terminate()).unwrap();
    let mut signal_sigquit = signal(SignalKind::quit()).unwrap();

    loop {
        tokio::select! {
            cmd = cmd_channel_rx.recv() => {
                match cmd {
                    Some((c, resp)) => {
                        match c {
                            TriggerManagerCommand::RegisterTriggerId(trigger_id) => {
                                info!("[RegisterTriggerId] cmd recv for id {}", &trigger_id);
                                let curr_status = id_to_trigger_status_map.insert(trigger_id.clone(), TriggerStatus::Starting);
                                match curr_status {
                                    Some(curr_status) => warn!("[RegisterTriggerId] Trigger id {} already existed with status {}. Status overwritten to Starting", &trigger_id, trigger_status_to_string(&curr_status)),
                                    None => (),
                                }
                                id_to_trigger_chan_map.remove(&trigger_id);
                                id_to_trigger_error_map.remove(&trigger_id);
                                resp.send((true, "ok".to_string()));
                            }
                            TriggerManagerCommand::RegisterTriggerChannel(trigger_id, chan) => {
                                info!("[RegisterTriggerChannel] cmd recv for id {}", trigger_id);
                                // status must exist
                                // only accept a channel when you are in either Starting or Ready state.
                                let curr_status = id_to_trigger_status_map.get(&trigger_id);
                                match curr_status {
                                    Some(curr_status) => {
                                        match curr_status {
                                            TriggerStatus::Ready | TriggerStatus::Starting => {
                                                id_to_trigger_chan_map.insert(trigger_id, chan);
                                                resp.send((true, "ok".to_string()));
                                            }
                                            _ => {
                                                let ret_msg = format!("[RegisterTriggerChannel] Ignoring attempt to register a channel for trigger id {} in state: {}", &trigger_id, trigger_status_to_string(&curr_status));
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                    None => {
                                        // status does not exist, but we trying to register an actor channel
                                        if id_to_trigger_chan_map.contains_key(&trigger_id) {
                                            // channel exists
                                            id_to_trigger_chan_map.remove(&trigger_id);
                                            //id_to_trigger_error_map.remove(&trigger_id);
                                            let ret_msg = format!("[RegisterTriggerChannel] Ignoring attempt to register a channel for non-existent trigger id {}. Existing channel removed.", &trigger_id);
                                            warn!("{}", ret_msg);
                                            resp.send((false, ret_msg));
                                        } else {
                                            let ret_msg = format!("[RegisterTriggerChannel] Ignoring attempt to register a channel for non-existent trigger id {}", &trigger_id);
                                            warn!("{}", ret_msg);
                                            resp.send((false, ret_msg));
                                        }
                                    }
                                }
                            }
                            TriggerManagerCommand::UpdateTriggerStatus(trigger_id, status_update, status_msg) => {
                                info!("[UpdateTriggerStatus] cmd recv for id {}, status {}", trigger_id, trigger_status_to_string(&status_update));
                                let current_status = id_to_trigger_status_map.get(&trigger_id);
                                match current_status {
                                    // Ensure that the status exists in the id to status map
                                    Some(current_status) => {
                                        // status exists
                                        // Now look at what exactly is the status update being sent
                                        match status_update {
                                            TriggerStatus::Ready => {
                                                // If the status update is 'Ready' then the trigger should ideally be in 'Starting' state
                                                match current_status {
                                                    TriggerStatus::Starting => {
                                                        id_to_trigger_status_map.insert(trigger_id, status_update);
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                    _ => {
                                                        let ret_msg = format!("[UpdateTriggerStatus] Ignoring attempt to change status of trigger id {} to Ready from {} state", &trigger_id, trigger_status_to_string(current_status));
                                                        warn!("{}", ret_msg);
                                                        resp.send((false, ret_msg));
                                                    }
                                                }
                                            }
                                            // If we stopped normally then update status
                                            TriggerStatus::StoppedNormal => {
                                                id_to_trigger_status_map.insert(trigger_id.clone(), status_update);
                                                id_to_trigger_chan_map.remove(&trigger_id);
                                                id_to_trigger_error_map.remove(&trigger_id);
                                                resp.send((true, "ok".to_string()));
                                            }
                                            // If we stopped with error, then add error message to error map and remove from status map
                                            TriggerStatus::StoppedError => {
                                                let ret_msg = format!("[UpdateTriggerStatus] Trigger id {} stopped with Error: {}", &trigger_id, &status_msg);
                                                warn!("{}", ret_msg);
                                                // remove the trigger from the status map
                                                id_to_trigger_status_map.remove(&trigger_id);
                                                // insert error message in error map
                                                id_to_trigger_error_map.insert(trigger_id.clone(), status_msg);
                                                id_to_trigger_chan_map.remove(&trigger_id);
                                                resp.send((true, "ok".to_string()));
                                            }
                                            TriggerStatus::Starting | TriggerStatus::Stopping => {
                                                let ret_msg = format!("[UpdateTriggerStatus] Ignoring attempt to change status of Trigger id {} to {}, from an actor", &trigger_id, trigger_status_to_string(&status_update));
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                    None => {
                                        // status does not exist
                                        id_to_trigger_chan_map.remove(&trigger_id);
                                        id_to_trigger_error_map.remove(&trigger_id);
                                        let ret_msg = format!("[UpdateTriggerStatus] Ignoring attempt to change status of a non existent Trigger id {} to {}", &trigger_id, trigger_status_to_string(&status_update));
                                        warn!("{}", ret_msg);
                                        resp.send((false, ret_msg));
                                    }
                                }
                            }
                            TriggerManagerCommand::GetTriggerStatus(trigger_id) => {
                                info!("[GetTriggerStatus] cmd recv for id {}", &trigger_id);
                                let trigger_status = id_to_trigger_status_map.get(&trigger_id);
                                let trigger_error_status = id_to_trigger_error_map.get(&trigger_id);
                                match trigger_status {
                                    Some(status) => {
                                        let jsonmsg: JsonValue = json::object! {"status" => trigger_status_to_string(status), "status_msg" => "" };
                                        resp.send((true, jsonmsg.dump()));
                                    }
                                    None => {
                                        // status does not exist
                                        id_to_trigger_chan_map.remove(&trigger_id);
                                        // check if we have trigger_id in error map (that is if it stopped with error)
                                        match trigger_error_status {
                                            Some(status_message) => {
                                                let jsonmsg: JsonValue = json::object! {"status" => trigger_status_to_string(&TriggerStatus::StoppedError), "status_msg" => status_message.clone() };
                                                resp.send((true, jsonmsg.dump()));
                                            }
                                            None => {
                                                // we dont have the trigger in error map and status map
                                                let ret_msg = format!("[GetTriggerStatus] Ignoring attempt to get status of a non existent Trigger id {}", &trigger_id);
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                }
                            }
                            TriggerManagerCommand::StopTrigger(trigger_id) => {
                                // this is the only place where we will use the channel to the trigger actor
                                info!("[StopTrigger] cmd for Trigger id {}", &trigger_id);
                                match id_to_trigger_status_map.get(&trigger_id) {
                                    Some(status) => {
                                        let trigger_chan = id_to_trigger_chan_map.get(&trigger_id);
                                        match trigger_chan {
                                            Some(chan) => {
                                                // send a message only if the status is Starting or Ready
                                                match status {
                                                    TriggerStatus::Starting | TriggerStatus::Ready => {
                                                        id_to_trigger_status_map.insert(trigger_id.clone(), TriggerStatus::Stopping);
                                                        let mut trigger_channel = chan.clone();
                                                        // do not wait here, as it might create a deadlock, since the trigger actor will
                                                        // try to send back a status update after the stop command has been received.
                                                        tokio::spawn(async move {
                                                            let (resp_tx, resp_rx) = oneshot::channel::<(bool, String)>();
                                                            trigger_channel.send((TriggerCommand::Stop, resp_tx)).await;
                                                        });
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                    _ => {
                                                        warn!("[StopTrigger] Ignoring attempt to stop Trigger id {}, as Trigger already in {} state", trigger_id, trigger_status_to_string(&status));
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                }
                                            }
                                            None => {
                                                //id_to_trigger_error_map.remove(&trigger_id);
                                                let ret_msg = format!("[StopTrigger] Ignoring attempt to stop Trigger id {} in status {}, with a non-existent channel", &trigger_id, trigger_status_to_string(&status));
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                    None => {
                                        id_to_trigger_chan_map.remove(&trigger_id);
                                        let trigger_status_error = id_to_trigger_error_map.get(&trigger_id);
                                        match trigger_status_error {
                                            Some(status_msg) => {
                                                let ret_msg = format!("[StopTrigger] Ignoring attempt to stop Trigger id {}, which stopped previously with Error: {}", &trigger_id, status_msg);
                                                warn!("{}", ret_msg);
                                                resp.send((true, ret_msg));
                                            }
                                            None => {
                                                let ret_msg = format!("[StopTrigger] Ignoring attempt to stop a non existent Trigger id {}", &trigger_id);
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                }
                            }
                            TriggerManagerCommand::DeleteTrigger(trigger_id) => {
                                info!("[DeleteTrigger] cmd recv for id {}", trigger_id);
                                id_to_trigger_status_map.remove(&trigger_id);
                                id_to_trigger_chan_map.remove(&trigger_id);
                                id_to_trigger_error_map.remove(&trigger_id);
                                resp.send((true, "ok".to_string()));
                            }
                            TriggerManagerCommand::AddWorkflows(trigger_id, workflows) => {
                                info!("[AddWorkflows] cmd recv for id {}", trigger_id);
                                match id_to_trigger_status_map.get(&trigger_id) {
                                    Some(status) => {
                                        let trigger_chan = id_to_trigger_chan_map.get(&trigger_id);
                                        match trigger_chan {
                                            Some(chan) => {
                                                // send a message only if the status is Starting or Ready
                                                match status {
                                                    TriggerStatus::Starting | TriggerStatus::Ready => {
                                                        let mut trigger_channel = chan.clone();
                                                        // do not wait here, as it might create a deadlock, since the trigger actor will
                                                        // try to send back a status update after the stop command has been received.
                                                        tokio::spawn(async move {
                                                            let (resp_tx, resp_rx) = oneshot::channel::<(bool, String)>();
                                                            trigger_channel.send((TriggerCommand::AddWorkflows(workflows), resp_tx)).await;
                                                        });
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                    _ => {
                                                        warn!("[AddWorkflows] Ignoring attempt to add workflows for Trigger id {}, as Trigger already in {} state", trigger_id, trigger_status_to_string(&status));
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                }
                                            }
                                            None => {
                                                //id_to_trigger_error_map.remove(&trigger_id);
                                                let ret_msg = format!("[AddWorkflows] Ignoring attempt to add workflows for Trigger id {} in status {}, with a non-existent channel", &trigger_id, trigger_status_to_string(&status));
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                    None => {
                                        id_to_trigger_chan_map.remove(&trigger_id);
                                        let trigger_status_error = id_to_trigger_error_map.get(&trigger_id);
                                        match trigger_status_error {
                                            Some(status_msg) => {
                                                let ret_msg = format!("[AddWorkflows] Ignoring attempt to add workflows for Trigger id {}, which stopped previously with Error: {}", &trigger_id, status_msg);
                                                warn!("{}", ret_msg);
                                                resp.send((true, ret_msg));
                                            }
                                            None => {
                                                let ret_msg = format!("[AddWorkflows] Ignoring attempt to add workflows for a non existent Trigger id {}", &trigger_id);
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                }
                            }
                            TriggerManagerCommand::RemoveWorkflows(trigger_id, workflows) => {
                                info!("[RemoveWorkflows] cmd recv for id {}", trigger_id);
                                match id_to_trigger_status_map.get(&trigger_id) {
                                    Some(status) => {
                                        let trigger_chan = id_to_trigger_chan_map.get(&trigger_id);
                                        match trigger_chan {
                                            Some(chan) => {
                                                // send a message only if the status is Starting or Ready
                                                match status {
                                                    TriggerStatus::Starting | TriggerStatus::Ready => {
                                                        let mut trigger_channel = chan.clone();
                                                        // do not wait here, as it might create a deadlock, since the trigger actor will
                                                        // try to send back a status update after the stop command has been received.
                                                        tokio::spawn(async move {
                                                            let (resp_tx, resp_rx) = oneshot::channel::<(bool, String)>();
                                                            trigger_channel.send((TriggerCommand::RemoveWorkflows(workflows), resp_tx)).await;
                                                        });
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                    _ => {
                                                        warn!("[RemoveWorkflows] Ignoring attempt to add workflows for Trigger id {}, as Trigger already in {} state", trigger_id, trigger_status_to_string(&status));
                                                        resp.send((true, "ok".to_string()));
                                                    }
                                                }
                                            }
                                            None => {
                                                //id_to_trigger_error_map.remove(&trigger_id);
                                                let ret_msg = format!("[RemoveWorkflows] Ignoring attempt to add workflows for Trigger id {} in status {}, with a non-existent channel", &trigger_id, trigger_status_to_string(&status));
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                    None => {
                                        id_to_trigger_chan_map.remove(&trigger_id);
                                        let trigger_status_error = id_to_trigger_error_map.get(&trigger_id);
                                        match trigger_status_error {
                                            Some(status_msg) => {
                                                let ret_msg = format!("[RemoveWorkflows] Ignoring attempt to add workflows for Trigger id {}, which stopped previously with Error: {}", &trigger_id, status_msg);
                                                warn!("{}", ret_msg);
                                                resp.send((true, ret_msg));
                                            }
                                            None => {
                                                let ret_msg = format!("[RemoveWorkflows] Ignoring attempt to add workflows for a non existent Trigger id {}", &trigger_id);
                                                warn!("{}", ret_msg);
                                                resp.send((false, ret_msg));
                                            }
                                        }
                                    }
                                }
                            }

                            TriggerManagerCommand::StopManager => {
                                info!("[StopManager] cmd recv");
                                send_shutdown_messages(&mut id_to_trigger_status_map, &mut id_to_trigger_error_map, &mut id_to_trigger_chan_map, manager_info.clone()).await;
                                create_delay(4000, "shutdown wait".into()).await;
                                resp.send((true, "ok".to_string()));
                                break;
                            }
                        }
                    }
                    None => {
                        warn!("[trigger_manager_actor_loop] None recv on command channel. Stopping manager");
                        send_server_stop_msg(manager_info.server_url.clone()).await;
                    },
                }
            }
            d = create_delay(manager_info.update_interval as u64, "TriggerManager, status push timer".to_string()) => {
                info!("[trigger_manager_actor_loop] Reporting status to {}", &manager_info.management_url);
                let update_message = TriggerManagerStatusUpdateMessage {
                    action: manager_info.management_action.clone(),
                    data: TriggerManagerStatusUpdateMessageData {
                        action: "status".into(),
                        self_ip_port: manager_info.self_ip_port.clone(),
                        trigger_status_map: id_to_trigger_status_map.clone(),
                        trigger_error_map: id_to_trigger_error_map.clone(),
                        user: HashMap::new(),
                    }
                };

                let serialized_update_message = serde_json::to_string(&update_message);
                tokio::spawn(report_status_to_management(manager_info.management_url.clone(), serialized_update_message.unwrap(), manager_info.management_request_host_header.clone()));
                // we have reported it to management, so clear the error map
                id_to_trigger_error_map.clear();
            }
            s1 = signal_sigint.recv() => {
                warn!("SIGINT Received, TriggerManager shutdown started");
                send_server_stop_msg(manager_info.server_url.clone()).await;
            }
            s2 = signal_sigterm.recv() => {
                warn!("SIGTERM Received, TriggerManager shutdown started");
                send_server_stop_msg(manager_info.server_url.clone()).await;
            }
            s3 = signal_sigquit.recv() => {
                warn!("SIGQUIT Received, TriggerManager shutdown started");
                send_server_stop_msg(manager_info.server_url.clone()).await;
            }
        }
    }

    info!("[trigger_manager_actor_loop] end");
    Ok(())
}
