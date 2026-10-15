use serde::{Deserialize, Serialize};
use std::{
    collections::VecDeque,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc, Mutex,
    },
};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Emitter, Manager, WebviewUrl, WebviewWindow, WebviewWindowBuilder,
};

#[derive(Clone, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
pub struct Settings {
    pub enabled: bool,
    pub visible: bool,
    pub height: u32,
    #[serde(default)]
    pub chibi_scale: u32,
    pub standing_scale: u32,
    pub always_on_top: bool,
    pub form: String,
    right: Option<i32>,
    bottom: Option<i32>,
}
impl Default for Settings {
    fn default() -> Self {
        Self {
            enabled: true,
            visible: true,
            height: 96,
            chibi_scale: 100,
            standing_scale: 100,
            always_on_top: true,
            form: "chibi".into(),
            right: None,
            bottom: None,
        }
    }
}
impl Settings {
    fn normalize(&mut self) {
        // A missing chibi scale marks the older pixel-height configuration.
        if self.chibi_scale == 0 {
            self.chibi_scale = self.height.saturating_mul(100) / 96;
        }
        self.chibi_scale = normalize_scale(self.chibi_scale);
        self.standing_scale = normalize_scale(self.standing_scale);
        if self.form != "standing" {
            self.form = "chibi".into();
        }
        self.height = if self.form == "standing" {
            168 * self.standing_scale / 100
        } else {
            96 * self.chibi_scale / 100
        };
    }
}
fn normalize_scale(value: u32) -> u32 {
    ((value.clamp(100, 200) + 12) / 25) * 25
}
fn layout_size(height: u32, expanded: bool, bubble: bool, menu: bool) -> (f64, f64) {
    let width = (height as f64).max(if expanded {
        380.0
    } else if bubble {
        276.0
    } else if menu {
        146.0
    } else {
        112.0
    }) + 24.0;
    let height = height as f64
        + 24.0
        + 8.0
        + if expanded { 48.0 } else { 44.0 }
        + if bubble { 106.0 } else { 0.0 }
        + if menu { 52.0 } else { 0.0 };
    (width, height)
}

#[derive(Clone, Default, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum Phase {
    #[default]
    Idle,
    Thinking,
    Success,
    Error,
}
#[derive(Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Snapshot {
    revision: u64,
    phase: Phase,
    cid: Option<String>,
    message: String,
    count: u32,
}
impl Snapshot {
    fn accept(&mut self, mut next: Self) -> bool {
        if next.revision <= self.revision {
            return false;
        }
        next.message = next
            .message
            .split_whitespace()
            .collect::<Vec<_>>()
            .join(" ")
            .chars()
            .take(80)
            .collect();
        next.count = next.count.min(1000);
        *self = next;
        true
    }
}
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct QuickRequest {
    request_id: String,
    text: String,
    status: String,
    cid: Option<String>,
    error: Option<String>,
}
pub struct Coordinator {
    settings: Mutex<Settings>,
    snapshot: Mutex<Snapshot>,
    requests: Mutex<VecDeque<QuickRequest>>,
    port: Mutex<Option<u16>>,
    layout: Mutex<(bool, bool, bool)>,
    ready: AtomicBool,
    compose: AtomicBool,
}
impl Coordinator {
    pub fn load(app: &tauri::AppHandle) -> Self {
        let mut settings = app
            .path()
            .app_data_dir()
            .ok()
            .and_then(|path| std::fs::read_to_string(path.join("companion.json")).ok())
            .filter(|text| text.len() <= 4096)
            .and_then(|text| serde_json::from_str::<Settings>(&text).ok())
            .unwrap_or_default();
        settings.normalize();
        Self {
            settings: Mutex::new(settings),
            snapshot: Mutex::new(Snapshot::default()),
            requests: Mutex::new(VecDeque::new()),
            port: Mutex::new(None),
            layout: Mutex::new((false, false, false)),
            ready: AtomicBool::new(false),
            compose: AtomicBool::new(false),
        }
    }
}
fn trusted(window: &WebviewWindow, labels: &[&str]) -> Result<(), String> {
    if labels.contains(&window.label()) {
        Ok(())
    } else {
        Err("此窗口无法执行该操作。".into())
    }
}
pub fn enabled(app: &tauri::AppHandle) -> bool {
    app.state::<Coordinator>().settings.lock().unwrap().enabled
}
pub fn persist(app: &tauri::AppHandle) -> Result<(), String> {
    let state = app.state::<Coordinator>();
    let settings = state.settings.lock().unwrap();
    super::save_local(
        app,
        "companion.json",
        &serde_json::to_string(&*settings).map_err(|_| "桌宠设置格式错误")?,
    )
}
fn notify_settings(app: &tauri::AppHandle) -> Result<(), String> {
    let settings = app.state::<Coordinator>().settings.lock().unwrap().clone();
    app.emit("companion-settings", settings)
        .map_err(|e| e.to_string())
}
fn clamp_origin(x: i32, y: i32, width: u32, height: u32, area: (i32, i32, u32, u32)) -> (i32, i32) {
    let max_x = area.0.saturating_add(area.2.saturating_sub(width) as i32);
    let max_y = area.1.saturating_add(area.3.saturating_sub(height) as i32);
    (x.clamp(area.0, max_x), y.clamp(area.1, max_y))
}
fn monitor_index(anchor: (i32, i32), areas: &[(i32, i32, u32, u32)]) -> usize {
    let distance = |&(x, y, width, height): &(i32, i32, u32, u32)| {
        let (ax, ay) = (anchor.0 as f64, anchor.1 as f64);
        let dx = ax - ax.clamp(x as f64, x as f64 + width as f64);
        let dy = ay - ay.clamp(y as f64, y as f64 + height as f64);
        dx * dx + dy * dy
    };
    areas
        .iter()
        .enumerate()
        .min_by(|(_, a), (_, b)| distance(a).total_cmp(&distance(b)))
        .map(|(index, _)| index)
        .unwrap_or(0)
}
fn layout(app: &tauri::AppHandle) -> Result<(), String> {
    let window = match app.get_webview_window("companion") {
        Some(value) => value,
        None => return Ok(()),
    };
    let state = app.state::<Coordinator>();
    let settings = state.settings.lock().unwrap().clone();
    let (expanded, bubble, menu) = *state.layout.lock().unwrap();
    let monitors = window.available_monitors().map_err(|e| e.to_string())?;
    let areas: Vec<_> = monitors
        .iter()
        .map(|monitor| {
            let area = monitor.work_area();
            (
                area.position.x,
                area.position.y,
                area.size.width,
                area.size.height,
            )
        })
        .collect();
    let index = settings
        .right
        .zip(settings.bottom)
        .map(|anchor| monitor_index(anchor, &areas))
        .unwrap_or(0);
    let monitor = monitors.get(index).ok_or("找不到显示器")?;
    let scale = monitor.scale_factor();
    let (width, height) = layout_size(settings.height, expanded, bubble, menu);
    let physical_width = (width * scale).round() as u32;
    let physical_height = (height * scale).round() as u32;
    let area = monitor.work_area();
    let right = settings
        .right
        .unwrap_or(area.position.x + area.size.width as i32 - 24);
    let bottom = settings
        .bottom
        .unwrap_or(area.position.y + area.size.height as i32 - 24);
    let (x, y) = clamp_origin(
        right - physical_width as i32,
        bottom - physical_height as i32,
        physical_width,
        physical_height,
        (
            area.position.x,
            area.position.y,
            area.size.width,
            area.size.height,
        ),
    );
    window
        .set_size(tauri::PhysicalSize::new(physical_width, physical_height))
        .map_err(|e| e.to_string())?;
    window
        .set_position(tauri::PhysicalPosition::new(x, y))
        .map_err(|e| e.to_string())?;
    Ok(())
}
fn ensure_window(app: &tauri::AppHandle, label: &str) -> Result<WebviewWindow, String> {
    if let Some(window) = app.get_webview_window(label) {
        return Ok(window);
    }
    let port = app
        .state::<Coordinator>()
        .port
        .lock()
        .unwrap()
        .ok_or("本地服务尚未就绪，请稍后重试。")?;
    let path = if label == "companion" {
        "companion"
    } else {
        "capture"
    };
    let url = format!("http://127.0.0.1:{port}/desktop/{path}")
        .parse()
        .map_err(|_| "桌面地址无效")?;
    let mut builder = WebviewWindowBuilder::new(app, label, WebviewUrl::External(url))
        .disable_drag_drop_handler()
        .visible(false)
        .on_navigation(move |url| {
            url.scheme() == "http"
                && url.host_str() == Some("127.0.0.1")
                && url.port() == Some(port)
                && url.path() == format!("/desktop/{path}")
        });
    if label == "companion" {
        builder = builder
            .title("息流桌宠")
            .inner_size(136.0, 172.0)
            .decorations(false)
            .transparent(true)
            .shadow(false)
            .skip_taskbar(true)
            .resizable(false)
            .always_on_top(
                app.state::<Coordinator>()
                    .settings
                    .lock()
                    .unwrap()
                    .always_on_top,
            );
    } else {
        builder = builder
            .title("收进 Inbox · 息流")
            .inner_size(440.0, 600.0)
            .min_inner_size(360.0, 420.0)
            .center();
    }
    let window = builder.build().map_err(|e| e.to_string())?;
    let event_app = app.clone();
    let event_label = label.to_string();
    window.on_window_event(move |event| match event {
        tauri::WindowEvent::CloseRequested { api, .. } => {
            if event_app
                .state::<Arc<super::Service>>()
                .closing
                .load(Ordering::SeqCst)
            {
                return;
            }
            api.prevent_close();
            if let Some(window) = event_app.get_webview_window(&event_label) {
                let _ = window.hide();
            }
            if event_label == "companion" {
                event_app
                    .state::<Coordinator>()
                    .settings
                    .lock()
                    .unwrap()
                    .visible = false;
                let _ = persist(&event_app);
                let _ = notify_settings(&event_app);
            }
        }
        tauri::WindowEvent::Moved(position) if event_label == "companion" => {
            if let Some(window) = event_app.get_webview_window("companion") {
                if let Ok(size) = window.inner_size() {
                    let state = event_app.state::<Coordinator>();
                    let mut settings = state.settings.lock().unwrap();
                    settings.right = Some(position.x + size.width as i32);
                    settings.bottom = Some(position.y + size.height as i32);
                }
            }
        }
        tauri::WindowEvent::ScaleFactorChanged { .. } if event_label == "companion" => {
            let _ = layout(&event_app);
        }
        _ => {}
    });
    Ok(window)
}
pub fn show(app: &tauri::AppHandle) -> Result<(), String> {
    let window = ensure_window(app, "companion")?;
    {
        let state = app.state::<Coordinator>();
        let mut settings = state.settings.lock().unwrap();
        settings.enabled = true;
        settings.visible = true;
    }
    layout(app)?;
    window.show().map_err(|e| e.to_string())?;
    persist(app)?;
    notify_settings(app)
}
pub fn open_capture(app: &tauri::AppHandle) -> Result<(), String> {
    let window = ensure_window(app, "capture")?;
    window.show().map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())
}
pub fn start(app: &tauri::AppHandle, port: u16) -> Result<(), String> {
    let state = app.state::<Coordinator>();
    *state.port.lock().unwrap() = Some(port);
    let settings = state.settings.lock().unwrap().clone();
    if settings.enabled && settings.visible {
        show(app)?;
    }
    Ok(())
}
pub fn install_tray(app: &tauri::AppHandle) -> tauri::Result<()> {
    let main = MenuItem::with_id(app, "open", "打开息流", true, None::<&str>)?;
    let chat = MenuItem::with_id(app, "chat", "新对话", true, None::<&str>)?;
    let capture = MenuItem::with_id(app, "capture", "收进 Inbox", true, None::<&str>)?;
    let show_pet = MenuItem::with_id(app, "pet", "显示 / 隐藏桌宠", true, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "退出息流", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&main, &chat, &capture, &show_pet, &quit])?;
    let mut tray = TrayIconBuilder::new()
        .tooltip("息流 · 桌面伴侣")
        .menu(&menu)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "open" => {
                let _ = open_main(app, "/today");
            }
            "chat" => {
                app.state::<Coordinator>()
                    .compose
                    .store(true, Ordering::SeqCst);
                if show(app).is_ok() {
                    *app.state::<Coordinator>().layout.lock().unwrap() = (true, false, false);
                    let _ = layout(app);
                    let _ = app.emit_to("companion", "companion-compose", ());
                    if let Some(window) = app.get_webview_window("companion") {
                        let _ = window.set_focus();
                    }
                }
            }
            "capture" => {
                let _ = open_capture(app);
            }
            "pet" => {
                let visible = app.state::<Coordinator>().settings.lock().unwrap().visible;
                if visible {
                    if let Some(window) = app.get_webview_window("companion") {
                        let _ = window.hide();
                    }
                    app.state::<Coordinator>().settings.lock().unwrap().visible = false;
                    let _ = persist(app);
                    let _ = notify_settings(app);
                } else {
                    let _ = show(app);
                }
            }
            "quit" => {
                let _ = persist(app);
                super::close(app, app.state::<Arc<super::Service>>().inner());
            }
            _ => {}
        });
    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }
    tray.build(app)?;
    Ok(())
}
fn valid_main_path(path: &str) -> bool {
    matches!(
        path,
        "/today" | "/assistant" | "/inbox" | "/settings?section=appearance"
    ) || ["/assistant?c=", "/inbox?item="].iter().any(|prefix| {
        path.strip_prefix(prefix).is_some_and(|cid| {
            !cid.is_empty()
                && cid.len() <= 128
                && cid
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
        })
    })
}
fn open_main(app: &tauri::AppHandle, path: &str) -> Result<(), String> {
    if !valid_main_path(path) {
        return Err("无法打开此页面。".into());
    }
    let window = app.get_webview_window("main").ok_or("主窗口不可用")?;
    window.unminimize().map_err(|e| e.to_string())?;
    window.show().map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())?;
    app.emit_to("main", "companion-navigate", path)
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub fn companion_settings(
    window: WebviewWindow,
    state: tauri::State<Coordinator>,
) -> Result<Settings, String> {
    trusted(&window, &["main", "companion", "capture"])?;
    Ok(state.settings.lock().unwrap().clone())
}
#[tauri::command]
pub fn companion_set_form(
    window: WebviewWindow,
    app: tauri::AppHandle,
    form: String,
) -> Result<Settings, String> {
    trusted(&window, &["main", "companion"])?;
    if form != "chibi" && form != "standing" {
        return Err("桌宠形态无效。".into());
    }
    let settings = {
        let state = app.state::<Coordinator>();
        let mut current = state.settings.lock().unwrap();
        current.form = form;
        current.normalize();
        current.clone()
    };
    persist(&app)?;
    notify_settings(&app)?;
    Ok(settings)
}

#[tauri::command]
pub async fn companion_configure(
    window: WebviewWindow,
    app: tauri::AppHandle,
    mut settings: Settings,
) -> Result<Settings, String> {
    trusted(&window, &["main"])?;
    settings.normalize();
    {
        let state = app.state::<Coordinator>();
        let mut current = state.settings.lock().unwrap();
        settings.right = current.right;
        settings.bottom = current.bottom;
        *current = settings.clone();
    }
    persist(&app)?;
    if settings.enabled && settings.visible {
        show(&app)?;
    } else if let Some(pet) = app.get_webview_window("companion") {
        pet.hide().map_err(|e| e.to_string())?;
    }
    if let Some(pet) = app.get_webview_window("companion") {
        pet.set_always_on_top(settings.always_on_top)
            .map_err(|e| e.to_string())?;
    }
    notify_settings(&app)?;
    Ok(settings)
}
#[tauri::command]
pub async fn companion_show(window: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    trusted(&window, &["main"])?;
    show(&app)
}
#[tauri::command]
pub async fn companion_open_capture(
    window: WebviewWindow,
    app: tauri::AppHandle,
) -> Result<(), String> {
    trusted(&window, &["main", "companion"])?;
    open_capture(&app)
}
#[tauri::command]
pub fn companion_close_capture(window: WebviewWindow) -> Result<(), String> {
    trusted(&window, &["capture"])?;
    window.hide().map_err(|e| e.to_string())
}
#[tauri::command]
pub fn companion_open_main(
    window: WebviewWindow,
    app: tauri::AppHandle,
    path: String,
) -> Result<(), String> {
    trusted(&window, &["main", "companion", "capture"])?;
    open_main(&app, &path)
}
#[tauri::command]
pub fn companion_layout(
    window: WebviewWindow,
    app: tauri::AppHandle,
    expanded: bool,
    bubble: bool,
    menu: bool,
) -> Result<(), String> {
    trusted(&window, &["companion"])?;
    *app.state::<Coordinator>().layout.lock().unwrap() = (expanded, bubble, menu);
    layout(&app)
}
#[tauri::command]
pub async fn companion_drag(window: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    trusted(&window, &["companion"])?;
    window.start_dragging().map_err(|e| e.to_string())?;
    // The OS drag call posts a message and returns before the mouse is released.
    // Wait off the UI thread so the renderer can keep its held pose until release.
    #[cfg(target_os = "windows")]
    tauri::async_runtime::spawn_blocking(|| {
        #[link(name = "user32")]
        extern "system" {
            fn GetAsyncKeyState(key: i32) -> i16;
        }
        let started = std::time::Instant::now();
        while unsafe { GetAsyncKeyState(0x01) } < 0 && started.elapsed().as_secs() < 120 {
            std::thread::sleep(std::time::Duration::from_millis(16));
        }
    })
    .await
    .map_err(|e| e.to_string())?;
    layout(&app)?;
    persist(&app)
}
#[tauri::command]
pub fn companion_snapshot(
    window: WebviewWindow,
    state: tauri::State<Coordinator>,
) -> Result<Snapshot, String> {
    trusted(&window, &["main", "companion"])?;
    Ok(state.snapshot.lock().unwrap().clone())
}
#[tauri::command]
pub fn companion_publish(
    window: WebviewWindow,
    app: tauri::AppHandle,
    snapshot: Snapshot,
) -> Result<(), String> {
    trusted(&window, &["main"])?;
    let state = app.state::<Coordinator>();
    let mut current = state.snapshot.lock().unwrap();
    if current.accept(snapshot) {
        app.emit_to("companion", "companion-snapshot", current.clone())
            .map_err(|e| e.to_string())?;
    }
    Ok(())
}
#[tauri::command]
pub fn companion_ready(window: WebviewWindow, app: tauri::AppHandle) -> Result<(), String> {
    trusted(&window, &["main"])?;
    app.state::<Coordinator>()
        .ready
        .store(true, Ordering::SeqCst);
    Ok(())
}
#[tauri::command]
pub fn companion_take_compose(
    window: WebviewWindow,
    state: tauri::State<Coordinator>,
) -> Result<bool, String> {
    trusted(&window, &["companion"])?;
    Ok(state.compose.swap(false, Ordering::SeqCst))
}
#[tauri::command]
pub fn companion_submit(
    window: WebviewWindow,
    app: tauri::AppHandle,
    request_id: String,
    text: String,
) -> Result<QuickRequest, String> {
    trusted(&window, &["companion"])?;
    if uuid::Uuid::parse_str(&request_id).is_err()
        || text.trim().is_empty()
        || text.chars().count() > 20000
    {
        return Err("请输入有效的对话内容。".into());
    }
    let state = app.state::<Coordinator>();
    let mut requests = state.requests.lock().unwrap();
    if let Some(request) = requests.iter().find(|r| r.request_id == request_id) {
        if request.text != text {
            return Err("请先确认上一条消息的发送状态。".into());
        }
        return Ok(request.clone());
    }
    if !state.ready.load(Ordering::SeqCst) {
        return Err("主窗口尚未准备好，请稍后重试。".into());
    }
    while requests.len() >= 32 {
        let index = requests
            .iter()
            .position(|r| r.status != "pending")
            .ok_or("正在处理的消息过多，请稍后重试。")?;
        requests.remove(index);
    }
    let request = QuickRequest {
        request_id,
        text,
        status: "pending".into(),
        cid: None,
        error: None,
    };
    app.emit_to("main", "companion-request", &request)
        .map_err(|e| e.to_string())?;
    requests.push_back(request.clone());
    Ok(request)
}
#[tauri::command]
pub fn companion_result(
    window: WebviewWindow,
    state: tauri::State<Coordinator>,
    request_id: String,
) -> Result<QuickRequest, String> {
    trusted(&window, &["companion"])?;
    state
        .requests
        .lock()
        .unwrap()
        .iter()
        .find(|r| r.request_id == request_id)
        .cloned()
        .ok_or("消息尚未发送，请重试。".into())
}
#[tauri::command]
pub fn companion_ack(
    window: WebviewWindow,
    state: tauri::State<Coordinator>,
    request_id: String,
    cid: Option<String>,
    error: Option<String>,
) -> Result<(), String> {
    trusted(&window, &["main"])?;
    let mut requests = state.requests.lock().unwrap();
    let request = requests
        .iter_mut()
        .find(|r| r.request_id == request_id)
        .ok_or("找不到对应消息")?;
    if request.status == "pending" {
        request.status = if cid.is_some() { "accepted" } else { "failed" }.into();
        request.cid = cid;
        request.error = error.map(|text| text.chars().take(200).collect());
    }
    Ok(())
}
#[tauri::command]
pub fn companion_captured(
    window: WebviewWindow,
    app: tauri::AppHandle,
    id: String,
) -> Result<(), String> {
    trusted(&window, &["capture"])?;
    if id.is_empty() || id.len() > 128 {
        return Err("内容标识无效".into());
    }
    app.emit_to("main", "companion-captured", id)
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_size_migrates_and_each_form_restores_its_own_scale() {
        let mut legacy: Settings =
            serde_json::from_str(r#"{"height":128,"enabled":true}"#).unwrap();
        legacy.normalize();
        assert_eq!(legacy.height, 120);
        let saved = serde_json::to_value(&legacy).unwrap();
        assert_eq!(saved["chibiScale"], 125);
        assert_eq!(saved["standingScale"], 100);
        let mut standing: Settings =
            serde_json::from_str(r#"{"form":"standing","chibiScale":125,"standingScale":150}"#)
                .unwrap();
        standing.normalize();
        assert_eq!(standing.height, 252);
        standing.form = "chibi".into();
        standing.normalize();
        assert_eq!(standing.height, 120);
        let mut restored: Settings =
            serde_json::from_str(&serde_json::to_string(&standing).unwrap()).unwrap();
        restored.form = "standing".into();
        restored.normalize();
        assert_eq!(restored.height, 252);
    }

    #[test]
    fn default_sizes_and_scale_limits_are_safe() {
        assert_eq!(Settings::default().height, 96);
        let mut settings: Settings =
            serde_json::from_str(r#"{"form":"standing","chibiScale":1,"standingScale":99999}"#)
                .unwrap();
        settings.normalize();
        assert_eq!(settings.height, 336);
        settings.form = "invalid".into();
        settings.normalize();
        assert_eq!(settings.form, "chibi");
        assert_eq!(settings.height, 96);
    }

    #[test]
    fn captured_item_navigation_is_local_and_validated() {
        assert!(valid_main_path("/inbox?item=content-123"));
        assert!(valid_main_path("/settings?section=appearance"));
        assert!(!valid_main_path(
            "/settings?section=appearance&redirect=evil"
        ));
        assert!(valid_main_path("/assistant?c=chat_123"));
        assert!(!valid_main_path("https://example.com"));
        assert!(!valid_main_path("/inbox?item=123&redirect=evil"));
        assert!(!valid_main_path("/inbox?item="));
    }

    #[test]
    fn stale_snapshots_are_ignored_and_summary_is_bounded() {
        let mut current = Snapshot::default();
        let newer = Snapshot {
            revision: 9,
            phase: Phase::Thinking,
            message: "进展".repeat(100),
            ..Snapshot::default()
        };
        assert!(current.accept(newer));
        assert_eq!(current.message.chars().count(), 80);
        assert!(!current.accept(Snapshot {
            revision: 8,
            ..Snapshot::default()
        }));
        assert_eq!(current.revision, 9);
    }

    #[test]
    fn compact_window_reserves_space_for_the_dock_and_expansion() {
        assert_eq!(layout_size(96, false, false, false), (136.0, 172.0));
        assert_eq!(layout_size(168, false, false, false), (192.0, 244.0));
        assert_eq!(layout_size(168, true, true, true), (404.0, 406.0));
        assert_eq!(layout_size(336, true, true, true), (404.0, 574.0));
    }

    #[test]
    fn offscreen_anchor_uses_nearest_monitor_not_the_primary() {
        let areas = [
            (0, 0, 1920, 1040),
            (1920, 0, 1920, 1040),
            (-1920, 0, 1920, 1040),
        ];
        assert_eq!(monitor_index((3890, 1070), &areas), 1);
        assert_eq!(monitor_index((-1950, 1080), &areas), 2);
        assert_eq!(monitor_index((2900, 1050), &areas), 1);
        assert_eq!(monitor_index((1400, 900), &areas), 0);
    }

    #[test]
    fn restored_anchor_stays_inside_available_monitor() {
        assert_eq!(
            clamp_origin(9999, -900, 320, 400, (0, 0, 1920, 1040)),
            (1600, 0)
        );
        assert_eq!(
            clamp_origin(-5000, 5000, 116, 116, (-1920, 0, 1920, 1040)),
            (-1920, 924)
        );
    }
}
