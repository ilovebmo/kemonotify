// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::HashMap;
use tauri::{Manager, Window, SystemTray};

// the payload type must implement `Serialize` and `Clone`.
#[derive(Clone, serde::Serialize)]
struct Payload {
    message: String,
}

#[derive(Debug, Serialize, Deserialize, Eq, PartialEq, PartialOrd, Clone)]
struct Creator {
    favorited: i32,
    id: String,
    indexed: i32,
    name: String,
    service: String,
    updated: i32,
}

impl Ord for Creator {
    fn cmp(&self, other: &Self) -> Ordering {
        self.favorited.cmp(&other.favorited)
    }
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct PartCreator {
    service: String,
    id: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Post {
    id: String,
    user: String,
    service: String,
    title: String,
    content: String,
    embed: HashMap<String, String>,
    shared_file: bool,
    added: Option<String>,
    published: Option<String>,
    edited: Option<String>,
    file: Option<Upload>,
    attachments: Option<Vec<Upload>>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Upload {
    name: Option<String>,
    path: Option<String>,
}

const API: &str = "https://kemono.party/api/v1";
const LIST: &str = "/creators.txt";
// const HOUR: u64 = 3600;

#[tauri::command]
async fn get_creators_list() -> Result<Vec<Creator>, String> {
    async fn creator_list_req() -> Result<Vec<Creator>, reqwest::Error> {
        let mut creator_list: Vec<Creator> = reqwest::Client::new()
            .get(format!("{API}{LIST}"))
            .send()
            .await?
            .json()
            .await?;
        creator_list.sort();
        creator_list.reverse();

        return Ok(creator_list);
    }

    return match tauri::async_runtime::spawn(creator_list_req())
        .await
        .expect("something went wrong")
    {
        Ok(a) => Ok(a),
        Err(b) => Err(b.to_string()),
    };
}

#[tauri::command]
async fn filter_by_name(
    creator_list: Vec<Creator>,
    input_name: String,
) -> Result<Vec<Creator>, String> {
    let creators_is_in: Vec<Creator> = creator_list
        .iter()
        .cloned()
        .filter(|c| c.name.to_lowercase().contains(&input_name.to_lowercase()))
        .collect();

    return Ok(creators_is_in);
}

#[tauri::command]
async fn update_check_list(
    js_check_list: Option<HashMap<String, PartCreator>>,
    service: String,
    id: String,
) -> HashMap<String, PartCreator> {
    let mut check_list = match js_check_list {
        Some(a) => a,
        None => HashMap::new(),
    };

    if check_list.contains_key(&id) {
        check_list.remove(&id);
    } else {
        check_list.insert(id.clone(), PartCreator { id, service });
    }
    return check_list;
}

#[tauri::command]
async fn get_list_of_names(
    the_checklist: Option<HashMap<String, PartCreator>>,
    creator_list: Vec<Creator>,
) -> String {
    let creator_map = make_vec_hashmap(&creator_list);
    let mut r = String::new();
    let check_list = match the_checklist {
        Some(a) => a,
        None => HashMap::new(),
    };
    for key in check_list.keys() {
        r.push_str(&creator_map.get(key).expect("something went wrong").name);
        r.push_str(" on ");
        r.push_str(&creator_map.get(key).expect("something went wrong").service);
        r.push_str("<br />");
    }

    return r;
}

fn make_vec_hashmap(creator_list: &Vec<Creator>) -> HashMap<&String, &Creator> {
    let mut creator_map = HashMap::new();
    for creator in creator_list {
        creator_map.insert(&creator.id, creator);
    }
    return creator_map;
}

async fn start_looking(
    the_checklist: Option<HashMap<String, PartCreator>>,
) -> Result<String, String> {
    let the_checklist = the_checklist.unwrap();
    let iter_len = &the_checklist.len();

    let (tx, mut rx) = tauri::async_runtime::channel::<Vec<Post>>(100);

    async fn get_post(creator: &PartCreator) -> Result<Vec<Post>, reqwest::Error> {
        let post: Vec<Post> = reqwest::Client::new()
            .get(format!("{}/{}/user/{}", API, creator.service, creator.id))
            .send()
            .await?
            .json()
            .await?;

        return Ok(post);
    }

    tauri::async_runtime::spawn(async move {
        for creator in the_checklist.values() {
            if let Err(_) = tx
                .send(get_post(creator).await.expect("something went wrong"))
                .await
            {
                println!("receiver dropped");
                return;
            }
        }
    });

    let mut res: String = String::new();

    for _i in 0..*iter_len {
        let post = rx.recv().await;
        let solve = match post {
            Some(a) => a,
            None => Vec::new(),
        };
        res.push_str(&format!("{} on {}: <a href=\"https://kemono.su/{}/user/{}/post/{}\" target=\"_blank\">{}</a>", 
        &solve[0].user.to_string(),
        solve[0].service.to_string(),
        &solve[0].service.to_string(),
        solve[0].user.to_string(),
        solve[0].id.to_string(),
        solve[0].title.to_string()
        ).to_string());
        res.push_str("</br>");
    }

    return Ok(res);
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct TimeList {
    time_s: String,
    list: Option<HashMap<String, PartCreator>>,
}

impl TimeList {
    fn time(&self) -> u64 {
        return self.time_s.parse::<u64>().unwrap();
    }
}

#[tauri::command]
async fn background_search(
    the_window: Window,
    the_checklist: Option<HashMap<String, PartCreator>>,
) {
    let g = std::sync::Arc::new(tauri::async_runtime::Mutex::new(TimeList {
        time_s: "5".to_string(),
        list: the_checklist.clone(),
    }));

    tauri::async_runtime::spawn(async move {
        let a = std::sync::Arc::clone(&g);
        loop {
            let b = std::sync::Arc::clone(&a);
            the_window.once("recv-event", move |e| {
                let c = std::sync::Arc::clone(&b);
                tauri::async_runtime::spawn(async move {
                    let mut msg = c.lock().await;
                    *msg =
                        serde_json::from_str(e.payload().unwrap()).expect("something went wrong");
                    println!("{:?}", e);
                });
            });
            let look_list: Option<HashMap<String, PartCreator>> = (*g.lock().await).clone().list;
            let time_in = (*g.lock().await).clone().time();

            let posts: String = match look_list {
                None => "None".to_string(),
                Some(a) => start_looking(Some(a).clone()).await.unwrap(),
            };

            println!("{:?}", posts);

            the_window
                .emit_all(
                    "test-event",
                    Payload {
                        message: if posts.to_string() == "None".to_string() {
                            "".to_string()
                        } else {
                            posts.into()
                        },
                    },
                )
                .unwrap();
            std::thread::sleep(std::time::Duration::from_secs(time_in));
        }
    });
}

fn main() {
    tauri::Builder::default()
        .system_tray(SystemTray::new())
        .invoke_handler(tauri::generate_handler![
            get_creators_list,
            filter_by_name,
            update_check_list,
            get_list_of_names,
            background_search,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
