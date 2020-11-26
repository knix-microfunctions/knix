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
// use paho_mqtt as mqtt;
use rumqttc::{AsyncClient, Event, Incoming, MqttOptions, Packet, Publish, QoS};
use std::time::{Duration, SystemTime};

#[derive(Clone)]
pub struct MQTTTopicInfo {
    topic: String,
    qos: i32,
}
#[derive(Clone)]
pub struct MQTTSubscriberInfo {
    mqtt_addr: String,
    topic_names: Vec<String>,
    qos_values: Vec<u8>,
}

#[derive(Clone)]
pub struct MQTTTrigger {
    trigger_id: String,
    mqtt_sub_info: MQTTSubscriberInfo,
    workflows: Vec<WorkflowInfo>,
    // Sender return
    cmd_channel_tx: TriggerCommandChannel,
}

impl MQTTTrigger {
    pub fn spawn(
        trigger_id: &String,
        mqtt_sub_info: MQTTSubscriberInfo,
        workflows: Vec<WorkflowInfo>,
        manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
    ) -> std::result::Result<MQTTTrigger, ()> {
        let (cmd_channel_tx, cmd_channel_rx) =
            channel::<(TriggerCommand, CommandResponseChannel)>(5);
        tokio::spawn(mqtt_actor_retry_loop(
            trigger_id.clone(),
            mqtt_sub_info.clone(),
            workflows.clone(),
            cmd_channel_rx,
            manager_cmd_channel_tx,
        ));
        Ok(MQTTTrigger {
            trigger_id: trigger_id.clone(),
            mqtt_sub_info: mqtt_sub_info.clone(),
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

pub async fn handle_create_mqtt_trigger(
    trigger_id: &String,
    trigger_name: &String,
    workflows: Vec<WorkflowInfo>,
    request_body: &String,
    manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) -> std::result::Result<TriggerCommandChannel, String> {
    let json_body = json::parse(request_body).unwrap();
    let trigger_info = &json_body["trigger_info"];

    if !(trigger_info.has_key("mqtt_addr")
        && trigger_info.has_key("topics")
        && trigger_info["topics"].is_array()
        && trigger_info["topics"].len() > 0)
    {
        return Err("One of the required fields, 'mqtt_addr' or 'topics' is missing".into());
    }

    let addr = &trigger_info["mqtt_addr"].to_string();
    let addr_vec: Vec<&str> = addr.split(":").collect();
    if addr_vec.len() != 2 {
        return Err("'mqtt_addr' should be of the format <host>:<port>".into());
    } else if addr_vec[1].parse::<u16>().is_err() {
        return Err("unable to parse 'mqtt_addr'".into());
    } else {
        // all good
    }

    let topics_array = &trigger_info["topics"];
    let num_topics = topics_array.len();
    let mut topics_vec: Vec<String> = Vec::new();
    let mut qos_vec: Vec<u8> = Vec::new();
    for i in 0..num_topics {
        let topic_info = &topics_array[i];
        if !topic_info.has_key("topic") {
            return Err("topic missing in topics list".into());
        }
        topics_vec.push(topic_info["topic"].to_string());
        let qos: u8 = if topic_info.has_key("qos") {
            topic_info["qos"].as_u8().unwrap()
        } else {
            1
        };
        qos_vec.push(qos);
    }
    let mqtt_sub_info = MQTTSubscriberInfo {
        mqtt_addr: trigger_info["mqtt_addr"].to_string(),
        topic_names: topics_vec,
        qos_values: qos_vec,
    };

    let mqtt_trigger = MQTTTrigger::spawn(
        &trigger_id,
        mqtt_sub_info,
        workflows,
        manager_cmd_channel_tx,
    )
    .unwrap();

    Ok(mqtt_trigger.cmd_channel_tx)
}

async fn send_mqtt_data(
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
                    trigger_type: "mqtt".into(),
                    trigger_name: trigger_name.clone(),
                    workflow_name: workflow_info.workflow_name,
                    source: source.clone(),
                    data: v.clone(), // TODO: Figure out how to pass the String around,
                                     // without copying and keeping the borrow checker happy!
                };
                let serialized_workflow_msg = serde_json::to_string(&workflow_msg);
                debug!(
                    "[send_mqtt_data] Trigger id {}, Sending message: {}",
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
        Err(e) => {
            let data_str = format!(
                "Trigger id {}, Message received with Invalid UTF-8 sequence: {}",
                &trigger_id, e
            );
            warn!("[send_mqtt_data] {}", &data_str);
        }
    };
}

pub async fn mqtt_actor_retry_loop(
    trigger_id: String,
    mqtt_sub_info: MQTTSubscriberInfo,
    workflows: Vec<WorkflowInfo>,
    mut cmd_channel_rx: Receiver<(TriggerCommand, CommandResponseChannel)>,
    mut manager_cmd_channel_tx: TriggerManagerCommandChannelSender,
) {
    let res: std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> = mqtt_actor_loop(
        &trigger_id,
        &mqtt_sub_info,
        workflows,
        &mut cmd_channel_rx,
        &mut manager_cmd_channel_tx,
    )
    .await;
    match res {
        Ok(()) => {
            info!(
                "[mqtt_actor_retry_loop] {} amqp_actor_loop finished without errors",
                trigger_id.clone()
            );
        }
        Err(e) => {
            warn!(
                "[mqtt_actor_retry_loop] {} amqp_actor_loop finished with an error: {}",
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

pub async fn mqtt_actor_loop(
    trigger_id: &String,
    mqtt_sub_info: &MQTTSubscriberInfo,
    mut workflows: Vec<WorkflowInfo>,
    cmd_channel_rx: &mut Receiver<(TriggerCommand, CommandResponseChannel)>,
    manager_cmd_channel_tx: &mut TriggerManagerCommandChannelSender,
) -> std::result::Result<(), Box<dyn std::error::Error + Send + Sync>> {
    info!("[amqp_actor_loop] {} start", trigger_id);

    let addr = &mqtt_sub_info.mqtt_addr;
    let addr_vec: Vec<&str> = addr.split(":").collect();
    let mqtt_port = addr_vec[1].parse::<u16>().unwrap();

    let mut mqttoptions = MqttOptions::new(trigger_id.as_str(), addr_vec[0], mqtt_port);
    mqttoptions.set_keep_alive(5);

    let (mut client, mut eventloop) = AsyncClient::new(mqttoptions, 10);
    client.subscribe(mqtt_sub_info.topic_names[0].clone(), QoS::AtMostOnce).await?;

    // Create the client. Use an ID for a persistent session.
    // A real system should try harder to use a unique ID.
    // let create_opts = mqtt::CreateOptionsBuilder::new()
    //     .server_uri(addr)
    //     .client_id(trigger_id.clone())
    //     .finalize();

    // Create the client connection
    // let cli_result = mqtt::AsyncClient::new(create_opts);
    // match cli_result {
    //     Err(e) => {
    //         let ret_msg = format!(
    //             "[mqtt_actor_loop] Trigger id {}, could not get async client. Error {}",
    //             trigger_id, e
    //         );
    //         warn!("{}", ret_msg);
    //         return Err(Box::new(TriggerError {
    //             err_msg: ret_msg.clone(),
    //         }));
    //     }
    //     _ => (),
    // }

    // let mut cli = cli_result.unwrap();
    // let mut strm = cli.get_stream(25);

    // let conn_opts = mqtt::ConnectOptionsBuilder::new()
    //     .keep_alive_interval(Duration::from_secs(300))
    //     .mqtt_version(mqtt::MQTT_VERSION_3_1_1)
    //     .clean_session(false)
    //     .finalize();

    // Make the connection to the broker
    info!("Connecting to the MQTT server...");
    // cli.connect(conn_opts).await;

    // // TODO
    // cli.subscribe_many(
    //     mqtt_sub_info.topic_names.as_slice(),
    //     mqtt_sub_info.qos_values.as_slice(),
    // )
    // .await?;

    info!("[mqtt_actor_loop] {} Ready to consume", trigger_id);
    send_status_update_from_trigger_to_manager(
        trigger_id.clone(),
        TriggerStatus::Ready,
        "".into(),
        manager_cmd_channel_tx.clone(),
    )
    .await;

    // while let Some(msg_opt) = strm.next().await {
    //     if let Some(msg) = msg_opt {
    //         println!("{}", msg);
    //     } else {
    //         // A "None" means we were disconnected. Try to reconnect...
    //         println!("Lost connection. Attempting reconnect.");
    //         while let Err(err) = cli.reconnect().await {
    //             println!("Error reconnecting: {}", err);
    //             // For tokio use: tokio::time::delay_for()
    //             async_std::task::sleep(Duration::from_millis(1000)).await;
    //         }
    //     }
    // }

    loop {
        tokio::select! {
            cmd = cmd_channel_rx.recv() => {
                match cmd {
                    Some((c, resp)) => {
                        match c {
                            TriggerCommand::GetStatus => {
                                info!("[mqtt_actor_loop] {} Status cmd recv", trigger_id);

                                resp.send((true, "ok".to_string()));
                            }
                            TriggerCommand::AddWorkflows(workflows_to_add) => {
                                for workflow in workflows_to_add.clone() {
                                    let idx = find_element_index(&workflow, &workflows);
                                    if idx >= 0 {
                                        workflows.remove(idx as usize);
                                    }
                                }

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
                                info!("[mqtt_actor_loop] {} Stop cmd recv", trigger_id);
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
                        let ret_msg = format!("[mqtt_actor_loop] Trigger id {}, None recv on command channel", trigger_id);
                        warn!("{}", ret_msg);
                        return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
                    },
                }
            }
            event_result = eventloop.poll() => {
                match event_result {
                    Ok(event) => {
                        match event {
                            Event::Incoming(packet) => {
                                match packet {
                                    Packet::Publish(pub_msg) => {
                                        let payload = String::from_utf8(pub_msg.payload.as_ref().to_vec());
                                        info!("Received = topic: {}, payload {}", &pub_msg.topic, &payload.unwrap());
                                    }
                                    _ => {
                                    }
                                }
                            }
                            _ => {

                            }
                        }
                    }
                    Err(e) => {
                        break;
                    }
                }
            }
            // msg = strm.next() => {
            //     match msg {
            //         Some(delivery) => {
            //             match delivery {
            //                 Some(payload) => {
            //                     //tokio::spawn(send_mqtt_data(workflows.clone(), payload, trigger_id.clone(), payload.topic));
            //                     info!("mqtt payload: {:?}", payload)
            //                 }
            //                 None => {
            //                     let ret_msg = format!("[mqtt_actor_loop] Trigger id {}, disconnected", trigger_id);
            //                     warn!("{}", ret_msg);
            //                     // TODO retry loop?
            //                     return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
            //                 }
            //             }
            //         }
            //         None => {
            //             let ret_msg = format!("[mqtt_actor_loop] Trigger id {}, None recv on mqtt stream. Probably closed", trigger_id);
            //             warn!("{}", ret_msg);
            //             return Err(Box::new(TriggerError{ err_msg: ret_msg.clone()}));
            //         }
            //     }
            // }
        }
    }
    Ok(())
}
