#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    io::{BufRead, BufReader, Read, Write},
    net::{SocketAddr, TcpStream},
    process::{Child, Command, Stdio},
    sync::{atomic::{AtomicBool, Ordering}, mpsc, Arc, Mutex},
    time::{Duration, Instant},
};
use tauri::{Emitter, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

#[derive(Default)]
struct Service {
    child: Mutex<Option<Child>>,
    port: Mutex<Option<u16>>,
    token: String,
    closing: AtomicBool,
}

fn save_local(app: &tauri::AppHandle, filename: &str, contents: &str) -> Result<(), String> {
    let directory = app.path().app_data_dir().map_err(|_| "无法打开设置目录")?;
    let temporary = directory.join(format!("{filename}.tmp"));
    std::fs::write(&temporary, contents).map_err(|_| "无法保存本机设置")?;
    std::fs::rename(&temporary, directory.join(filename)).map_err(|_| "无法替换本机设置".to_string())
}

#[tauri::command]
fn save_preferences(app: tauri::AppHandle, json: String) -> Result<(), String> {
    if json.len() > 262144 { return Err("设置内容过长".into()); }
    let value: serde_json::Value = serde_json::from_str(&json).map_err(|_| "设置格式无效")?;
    if !value.is_object() { return Err("设置格式无效".into()); }
    save_local(&app, "preferences.json", &json)
}

#[tauri::command]
fn save_sidebar(app: tauri::AppHandle, collapsed: bool) -> Result<(), String> {
    save_local(&app, "sidebar.json", if collapsed { "true" } else { "false" })
}

fn request(port: u16, token: &str, method: &str, route: &str) -> std::io::Result<bool> {
    let address = SocketAddr::from(([127, 0, 0, 1], port));
    let mut stream = TcpStream::connect_timeout(&address, Duration::from_secs(2))?;
    stream.set_read_timeout(Some(Duration::from_secs(2)))?;
    stream.set_write_timeout(Some(Duration::from_secs(2)))?;
    write!(stream, "{method} {route} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nX-Xiliu-Desktop-Token: {token}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")?;
    let mut response = String::new();
    stream.read_to_string(&mut response)?;
    Ok(response.starts_with("HTTP/1.1 200"))
}

fn close(app: &tauri::AppHandle, service: &Arc<Service>) {
    if service.closing.swap(true, Ordering::SeqCst) { return; }
    let app = app.clone();
    let service = Arc::clone(service);
    std::thread::spawn(move || {
        if let Some(port) = *service.port.lock().unwrap() {
            let _ = request(port, &service.token, "POST", "/api/desktop/shutdown");
        }
        if let Some(mut child) = service.child.lock().unwrap().take() {
            // Closing our pipe also requests shutdown if readiness failed.
            child.stdin.take();
            let deadline = Instant::now() + Duration::from_secs(30);
            loop {
                match child.try_wait() {
                    Ok(Some(_)) => break,
                    _ if Instant::now() >= deadline => {
                        let _ = child.kill();
                        let _ = child.wait();
                        break;
                    }
                    _ => std::thread::sleep(Duration::from_millis(100)),
                }
            }
        }
        app.exit(0);
    });
}

fn main() {
    let service = Arc::new(Service {
        token: uuid::Uuid::new_v4().simple().to_string(),
        ..Service::default()
    });
    let owner = Arc::clone(&service);
    let app = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![save_preferences, save_sidebar])
        .setup(move |app| {
            let data = app.path().app_data_dir()?;
            std::fs::create_dir_all(&data)?;
            let navigation_owner = Arc::clone(&owner);
            let preferences = std::fs::read_to_string(data.join("preferences.json")).ok()
                .filter(|value| value.len() <= 262144 && serde_json::from_str::<serde_json::Value>(value)
                    .map(|value| value.is_object()).unwrap_or(false));
            let sidebar = std::fs::read_to_string(data.join("sidebar.json")).ok()
                .filter(|value| value == "true" || value == "false");
            let launch = uuid::Uuid::new_v4().to_string();
            // One seed per origin per launch; reloads retain edits made in this window.
            let seed = format!("try {{ if (sessionStorage.getItem('xiliu-desktop-launch') !== {launch}) {{ const prefs = {prefs}; const sidebar = {sidebar}; if(prefs !== null) localStorage.setItem('xiliu-preferences-v1', prefs); if(sidebar !== null) localStorage.setItem('xiliu-sidebar-collapsed', sidebar); sessionStorage.setItem('xiliu-desktop-launch', {launch}); }} }} catch (_) {{}}",
                launch=serde_json::to_string(&launch)?, prefs=serde_json::to_string(&preferences)?, sidebar=serde_json::to_string(&sidebar)?);
            let window = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .disable_drag_drop_handler()
                .initialization_script(&seed)
                .title("息流 · xiliu").inner_size(1440.0, 900.0).min_inner_size(1100.0, 720.0)
                .on_navigation(move |url| {
                    let owned_port = *navigation_owner.port.lock().unwrap();
                    matches!(url.scheme(), "tauri" | "about")
                        || url.host_str() == Some("tauri.localhost")
                        || (url.scheme() == "http" && url.host_str() == Some("127.0.0.1")
                            && url.port() == owned_port && owned_port.is_some())
                }).build()?;
            let event_app = app.handle().clone();
            let close_owner = Arc::clone(&owner);
            window.on_window_event(move |event| {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    close(&event_app, &close_owner);
                }
            });
            let bundled = app.path().resolve("xiliu-service.exe", tauri::path::BaseDirectory::Resource)?;
            let executable = if cfg!(debug_assertions) && !bundled.exists() {
                std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                    .join("binaries/xiliu-service-x86_64-pc-windows-msvc.exe")
            } else { bundled };
            let mut command = Command::new(executable);
            let log_directory = data.join("logs");
            std::fs::create_dir_all(&log_directory)?;
            let log_path = log_directory.join("service.log");
            if std::fs::metadata(&log_path).map(|value| value.len() > 2_000_000).unwrap_or(false) {
                let _ = std::fs::rename(&log_path, log_directory.join("service.previous.log"));
            }
            let log = std::fs::OpenOptions::new().create(true).append(true).open(log_path)?;
            command.arg("--data-dir").arg(&data).env("XILIU_DESKTOP_TOKEN", &owner.token)
                .current_dir(&data).stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::from(log));
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x08000000); // CREATE_NO_WINDOW
            }
            let mut child = match command.spawn() {
                Ok(child) => child,
                Err(_) => {
                    window.eval("document.getElementById('status').textContent='本地服务无法启动，请重新安装桌面应用。'")?;
                    return Ok(());
                }
            };
            let stdout = child.stdout.take().unwrap();
            *owner.child.lock().unwrap() = Some(child);
            let (sender, receiver) = mpsc::channel();
            std::thread::spawn(move || {
                for line in BufReader::new(stdout).lines().map_while(Result::ok) {
                    if let Some(value) = line.strip_prefix("XILIU_READY http://127.0.0.1:") {
                        if let Ok(port) = value.parse::<u16>() { let _ = sender.send(port); }
                    }
                }
            });
            let ready_owner = Arc::clone(&owner);
            std::thread::spawn(move || {
                if let Ok(port) = receiver.recv_timeout(Duration::from_secs(45)) {
                    *ready_owner.port.lock().unwrap() = Some(port);
                    if request(port, &ready_owner.token, "GET", "/api/desktop/ready").unwrap_or(false)
                        && !ready_owner.closing.load(Ordering::SeqCst) {
                        let url = format!("http://127.0.0.1:{port}/").parse().unwrap();
                        let _ = window.navigate(url);
                        return;
                    }
                }
                let _ = window.emit("desktop-error", "本地服务启动失败。请关闭后重试，数据仍保存在本机。");
                let _ = window.eval("document.getElementById('status').textContent='本地服务启动失败，请关闭后重试。'");
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Unable to initialize xiliu desktop");
    app.run(move |app, event| {
        if let RunEvent::ExitRequested { api, .. } = event {
            if !service.closing.load(Ordering::SeqCst) {
                api.prevent_exit();
                close(app, &service);
            }
        }
    });
}
