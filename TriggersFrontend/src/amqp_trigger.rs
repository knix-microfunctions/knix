#[allow(dead_code,unused,unused_must_use)]
use crate::utils::create_delay;
use crate::utils::send_post_json_message;
use crate::utils::WorkflowInfo;
use crate::CommandResponseChannel;
use crate::TriggerCommand;
use crate::TriggerCommandChannel;
use crate::TriggerManager;
use json::JsonValue;
use lapin::{
    options::*, types::FieldTable, Channel, Connection, ConnectionProperties, Consumer, Queue,
    Result,
};
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
pub struct AMQPSubscriberInfo {
    amqp_addr: String,
    routing_key: String,
    exchange: String,
    durable: bool,
    exclusive: bool,
    auto_ack: bool,
}

pub struct AMQPTrigger {
    trigger_id: String,
    trigger_name: String,
    amqp_sub_info: AMQPSubscriberInfo,
    workflows: Vec<WorkflowInfo>,
    // Sender return
    cmd_channel_tx: TriggerCommandChannel,
}

impl AMQPTrigger {
    pub fn spawn(
        trigger_id: &String,
        trigger_name: &String,
        amqp_sub_info: AMQPSubscriberInfo,
        workflows: Vec<WorkflowInfo>,
        manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
    ) -> std::result::Result<AMQPTrigger, ()> {
        let (cmd_channel_tx, cmd_channel_rx) =
            channel::<(TriggerCommand, CommandResponseChannel)>(5);
        tokio::spawn(amqp_actor_retry_loop(
            trigger_id.clone(),
            trigger_name.clone(),
            amqp_sub_info.clone(),
            workflows.clone(),
            cmd_channel_rx,
            manager_cmd_channel_tx,
        ));
        Ok(AMQPTrigger {
            trigger_id: trigger_id.clone(),
            trigger_name: trigger_name.clone(),
            amqp_sub_info: amqp_sub_info.clone(),
            workflows: workflows.clone(),
            cmd_channel_tx,
        })
    }

    // pub async fn get_status(&mut self) -> std::result::Result<String, ()> {
    //     let mut response = Err(());
    //     let (resp_tx, resp_rx) = oneshot::channel();
    //     let send_result = self
    //         .cmd_channel_tx
    //         .send((TriggerCommand::Status, resp_tx))
    //         .await;
    //     if let Ok(m) = send_result {
    //         response = match resp_rx.await {
    //             Ok(msg) => {
    //                 debug!("[get_status] {} status response: {}", &self.trigger_id, msg);
    //                 Ok(msg)
    //             }
    //             _ => {
    //                 info!("[get_status] {} Error status response", &self.trigger_id);
    //                 Err(())
    //             }
    //         };
    //     }
    //     response
    // }

    // pub async fn stop(&mut self) -> std::result::Result<String, ()> {
    //     let mut response = Err(());
    //     let (resp_tx, resp_rx) = oneshot::channel();
    //     let send_result = self
    //         .cmd_channel_tx
    //         .send((TriggerCommand::Stop, resp_tx))
    //         .await;
    //     if let Ok(m) = send_result {
    //         response = match resp_rx.await {
    //             Ok(msg) => {
    //                 debug!("[stop] {} stop response: {}", &self.trigger_id, msg);
    //                 Ok(msg)
    //             }
    //             _ => {
    //                 info!("[stop] {} Error stop response", &self.trigger_id);
    //                 Err(())
    //             }
    //         };
    //     }
    //     response
    // }

    // pub async fn is_alive(&mut self) -> bool {
    //     if let Ok(msg) = self.get_status().await {
    //         return true;
    //     } else {
    //         return false;
    //     }
    // }
}

pub async fn handle_create_amqp_trigger(
    trigger_id: &String,
    trigger_name: &String,
    workflows: Vec<WorkflowInfo>,
    request_body: &String,
    manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) -> std::result::Result<TriggerCommandChannel, String> {
    let json_body = json::parse(request_body).unwrap();
    let trigger_info = &json_body["trigger_info"];

    if !(trigger_info.has_key("amqp_addr") && trigger_info.has_key("routing_key")) {
        return Err("One of the required fields, 'amqp_addr' or 'routing_key' is missing".into());
    }

    let amqp_sub_info = AMQPSubscriberInfo {
        amqp_addr: trigger_info["amqp_addr"].to_string(),
        routing_key: trigger_info["routing_key"].to_string(),
        exchange: if trigger_info.has_key("exchange") {
            trigger_info["exchange"].to_string()
        } else {
            "".into()
        },
        durable: if trigger_info.has_key("durable") {
            trigger_info["durable"].as_bool().unwrap()
        } else {
            false
        },
        exclusive: if trigger_info.has_key("exclusive") {
            trigger_info["exclusive"].as_bool().unwrap()
        } else {
            false
        },
        auto_ack: if trigger_info.has_key("auto_ack") {
            trigger_info["auto_ack"].as_bool().unwrap()
        } else {
            true
        },
    };

    let amqp_trigger = AMQPTrigger::spawn(
        &trigger_id,
        &trigger_name, 
        amqp_sub_info,
        workflows,
        manager_cmd_channel_tx,
    )
    .unwrap();

    Ok(amqp_trigger.cmd_channel_tx)
}

async fn send_amqp_data(
    workflows: Vec<WorkflowInfo>,
    amqp_data: std::vec::Vec<u8>,
    trigger_id: String,
    trigger_name: String,
    source: String,
) {
    let workflow_msg: TriggerWorkflowMessage;
    match String::from_utf8(amqp_data) {
        Ok(v) => {
            for workflow_info in workflows {
                let workflow_msg = TriggerWorkflowMessage {
                    trigger_status: "ready".into(),
                    trigger_type: "amqp".into(),
                    trigger_name: trigger_name.clone(),
                    workflow_name: workflow_info.workflow_name,
                    source: source.clone(),
                    data: v.clone(), // TODO: Figure out how to pass the String around,
                                     // without copying and keeping the borrow checker happy!
                };
                let serialized_workflow_msg = serde_json::to_string(&workflow_msg);
                debug!(
                    "[send_amqp_data] Trigger id {}, Sending message: {}",
                    trigger_id,
                    serialized_workflow_msg.as_ref().unwrap()
                );
                tokio::spawn(send_post_json_message(
                    workflow_info.workflow_url,
                    serialized_workflow_msg.unwrap(),
                    "".into(),
                    workflow_info.workflow_state.clone(),
                ));
            }
        }
        Err(e) => {
            let data_str = format!(
                "Trigger id {}, Message received with Invalid UTF-8 sequence: {}",
                &trigger_id, e
            );
            warn!("[send_amqp_data] {}", &data_str);
        }
    };
}

pub async fn amqp_actor_retry_loop(
    trigger_id: String,
    trigger_name: String,
    amqp_sub_info: AMQPSubscriberInfo,
    workflows: Vec<WorkflowInfo>,
    mut cmd_channel_rx: Receiver<(TriggerCommand, CommandResponseChannel)>,
    mut manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) {
    let res: std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> = amqp_actor_loop(
        &trigger_id,
        &trigger_name,
        &amqp_sub_info,
        workflows,
        &mut cmd_channel_rx,
        &mut manager_cmd_channel_tx,
    )
    .await;
    match res {
        Ok(()) => {
            info!(
                "[amqp_actor_retry_loop] {} amqp_actor_loop finished without errors",
                trigger_id.clone()
            );
        }
        Err(e) => {
            warn!(
                "[amqp_actor_retry_loop] {} amqp_actor_loop finished with an error: {}",
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

pub async fn amqp_actor_loop(
    trigger_id: &String,
    trigger_name: &String,
    amqp_sub_info: &AMQPSubscriberInfo,
    mut workflows: Vec<WorkflowInfo>,
    cmd_channel_rx: &mut Receiver<(TriggerCommand, CommandResponseChannel)>,
    manager_cmd_channel_tx: &mut TriggerManagerCommandChannelSender,
) -> std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("[amqp_actor_loop] {} start", trigger_id);

    let addr = &amqp_sub_info.amqp_addr;
    let conn: lapin::Connection =
        Connection::connect(addr, ConnectionProperties::default()).await?;
    info!("[amqp_actor_loop] {} connected", trigger_id);

    //receive channel
    let channel: Channel = conn.create_channel().await?;
    info!(
        "[amqp_actor_loop] {} state: {:?}",
        trigger_id,
        conn.status().state()
    );

    let eops = ExchangeDeclareOptions {
        durable: amqp_sub_info.durable,
        ..ExchangeDeclareOptions::default()
    };
    let exchange = channel
        .exchange_declare(
            &amqp_sub_info.exchange,
            lapin::ExchangeKind::Topic,
            eops,
            FieldTable::default(),
        )
        .await?;

    info!("[amqp_actor_loop] {} After exchange_declare", trigger_id);

    let qops = QueueDeclareOptions {
        durable: amqp_sub_info.durable,
        exclusive: amqp_sub_info.exclusive,
        ..QueueDeclareOptions::default()
    };
    let queue: lapin::Queue = channel
        .queue_declare("", qops, FieldTable::default())
        .await?;

    info!(
        "[amqp_actor_loop] {} Declared queue {:?}",
        trigger_id, queue
    );

    let qbind_response = channel
        .queue_bind(
            queue.name().as_str(),
            &amqp_sub_info.exchange,
            &amqp_sub_info.routing_key,
            QueueBindOptions::default(),
            FieldTable::default(),
        )
        .await?;

    info!("[amqp_actor_loop] {} After queue bind", trigger_id);

    let cops = BasicConsumeOptions {
        no_ack: amqp_sub_info.auto_ack,
        ..BasicConsumeOptions::default()
    };
    let mut consumer: Consumer = channel
        .basic_consume(queue.name().as_str(), "", cops, FieldTable::default())
        .await?;

    info!("[amqp_actor_loop] {} Ready to consume", trigger_id);
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
                                info!("[amqp_actor_loop] {} Status cmd recv", trigger_id);
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
                                info!("[amqp_actor_loop] {} Stop cmd recv", trigger_id);
                                resp.send((true, "ok".to_string()));
                                conn.close(0, "closing").await;
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
                        let ret_msg = format!("[amqp_actor_loop] Trigger id {}, None recv on command channel", trigger_id);
                        warn!("{}", ret_msg);
                        return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
                    },
                }
            }
            msg = consumer.next() => {
                match msg {
                    Some(delivery) => {
                        match delivery {
                            Ok((chan, amqp_msg)) => {
                                tokio::spawn(send_amqp_data(workflows.clone(), amqp_msg.data, trigger_id.clone(), trigger_name.clone(), amqp_sub_info.routing_key.clone()));
                            }
                            Err(e) => {
                                let ret_msg = format!("[amqp_actor_loop] Trigger id {}, recv a msg on amqp channel, but unwrapping produced an error: {:?}", trigger_id, e);
                                warn!("{}", ret_msg);
                                return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
                            }
                        }
                    }
                    None => {
                        let ret_msg = format!("[amqp_actor_loop] Trigger id {}, None recv on amqp channel. Probably closed", trigger_id);
                        warn!("{}", ret_msg);
                        return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
                    }
                }
            }
        }
    }
    Ok(())
}
