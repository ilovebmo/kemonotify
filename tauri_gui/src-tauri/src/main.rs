// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::HashMap;
use std::fs::{metadata, File};
use std::io::{BufRead, BufReader, Write};
use std::sync::{Arc, Mutex};
use tauri::{SystemTray, Window};

// Kemono structs
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

// Data structs
#[derive(Debug, Serialize, Deserialize)]
struct CreatorsList {
    vector: Vec<Creator>,
    hashmap: HashMap<String, Creator>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
struct TimeAndToCheck {
    time_str: String,
    to_check: Vec<String>,
}

impl TimeAndToCheck {
    fn time(&self) -> u64 {
        return self.time_str.parse::<u64>().unwrap();
    }
}

// Constants
const API: &str = "https://kemono.party/api/v1";
const LIST: &str = "/creators.txt";
const DB_FILE_PATH: &str = "storage.json";

// Commands
#[tauri::command]
async fn get_creators_list() -> Result<CreatorsList, String> {
    let creators_list = creators_list_request().await.unwrap();

    return Ok(CreatorsList {
        vector: creators_list.clone(),
        hashmap: get_creators_hashmap(creators_list).unwrap(),
    });
}

#[tauri::command]
async fn background_search(
    window: Window,
    creator_hashmap: HashMap<String, Creator>,
    time_str: String,
) {
    let time_and_to_check = Arc::new(Mutex::new(TimeAndToCheck {
        time_str,
        to_check: Vec::new(),
    }));
    loop {
        let loop_time_and_to_check = Arc::clone(&time_and_to_check);
        window.once("time-check-event", move |event| {
            let mut received = loop_time_and_to_check.lock().unwrap();
            *received = serde_json::from_str(event.payload().unwrap())
                .expect("something went wrong");
        });

        let to_check = &(*time_and_to_check.lock().unwrap()).to_check.clone();
        let time = (*time_and_to_check.lock().unwrap()).time();

        let mut current_storage = storage_hashmap();
        let mut new_posts: Vec<Post> = Vec::new();
        for creator_id in to_check {
            let most_recent_post = post_request(
                creator_hashmap
                    .get(creator_id)
                    .expect("creator not found")
                    .to_owned(),
            )
            .await
            .unwrap();
            if !current_storage.contains_key(creator_id)
                || current_storage
                    .get(creator_id)
                    .expect("creator not found")
                    .id
                    != most_recent_post.id
            {
                current_storage
                    .insert(creator_id.to_owned(), most_recent_post.clone());
                new_posts.push(most_recent_post);
            }
        }
        for creator in current_storage.clone().keys() {
            if !to_check.contains(creator) {
                current_storage.remove_entry(creator);
            }
        }

        window
            .emit("new-posts-event", new_posts)
            .expect("couldn't emit new posts");

        if !current_storage.is_empty() {
            write!(
                File::options()
                    .read(true)
                    .write(true)
                    .create(true)
                    .truncate(true)
                    .open(DB_FILE_PATH)
                    .expect("failed to update storage"),
                "{}",
                serde_json::to_string(&current_storage).unwrap()
            )
            .expect("couldn't update storage");
        }

        std::thread::sleep(std::time::Duration::from_secs(time));
    }
}

#[tauri::command]
async fn forced_search(
    creator_hashmap: HashMap<String, Creator>,
    to_check: Vec<String>,
) -> HashMap<String, Post> {
    let mut current_storage = storage_hashmap();
    let mut new_posts: HashMap<String, Post> = HashMap::new();
    for creator_id in to_check {
        let most_recent_post = post_request(
            creator_hashmap
                .get(&creator_id)
                .expect("creator not found")
                .to_owned(),
        )
        .await
        .unwrap();
        if !current_storage.contains_key(&creator_id)
            || current_storage
                .get(&creator_id)
                .expect("creator not found")
                .id
                != most_recent_post.id
        {
            current_storage
                .insert(creator_id.to_owned(), most_recent_post.clone());
            new_posts.insert(creator_id.to_owned(), most_recent_post);
        }
    }

    write!(
        File::options()
            .read(true)
            .write(true)
            .create(true)
            .truncate(true)
            .open(DB_FILE_PATH)
            .expect("failed to update storage"),
        "{}",
        serde_json::to_string(&current_storage).unwrap()
    )
    .expect("couldn't update storage");

    return new_posts;
}

// Other functions
async fn creators_list_request() -> Result<Vec<Creator>, reqwest::Error> {
    let mut creators_list: Vec<Creator> = reqwest::Client::new()
        .get(format!("{API}{LIST}"))
        .send()
        .await?
        .json()
        .await?;
    creators_list.sort();
    creators_list.reverse();

    return Ok(creators_list);
}

fn get_creators_hashmap(
    creators_list: Vec<Creator>,
) -> Result<HashMap<String, Creator>, String> {
    let mut creators_hashmap = HashMap::new();
    for creator in creators_list {
        creators_hashmap.insert(creator.id.to_owned(), creator);
    }

    return Ok(creators_hashmap);
}

async fn post_request(creator: Creator) -> Result<Post, reqwest::Error> {
    let posts: Vec<Post> = reqwest::Client::new()
        .get(format!("{}/{}/user/{}", API, creator.service, creator.id))
        .send()
        .await?
        .json()
        .await?;
    return Ok(posts[0].clone());
}

fn storage_hashmap() -> HashMap<String, Post> {
    let mut storage_as_str = String::new();
    let _buffered = BufReader::new(
        File::options()
            .read(true)
            .write(true)
            .create(true)
            .open(DB_FILE_PATH)
            .expect("failed to load storage"),
    )
    .read_line(&mut storage_as_str);
    let storage_map: HashMap<String, Post> =
        serde_json::from_str(&storage_as_str)
            .expect("failed to read storage file");

    return storage_map;
}

// main
fn main() {
    tauri::Builder::default()
        .setup(|_app| {
            match metadata(DB_FILE_PATH) {
                Ok(_) => (),
                Err(_) => {
                    write!(
                        File::options()
                            .read(true)
                            .write(true)
                            .create(true)
                            .open(DB_FILE_PATH)
                            .expect("failed to reach storage file"),
                        "{}",
                        "{}"
                    )
                    .expect("failed to initialize storage file");
                }
            };

            return Ok(());
        })
        .system_tray(SystemTray::new())
        .invoke_handler(tauri::generate_handler![
            get_creators_list,
            background_search,
            forced_search,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
