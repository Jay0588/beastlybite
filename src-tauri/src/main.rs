// J.A.Y. Tauri Desktop Shell
// Handles: system tray, window management, auto-launch, IPC bridge, global shortcuts

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    AppHandle, CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu,
    SystemTrayMenuItem, WindowEvent,
};
use tauri::GlobalShortcutManager;
use std::process::{Command, Child};
use std::sync::Mutex;

struct BackendProcess(Mutex<Option<Child>>);

// ─── Tauri Commands (callable from frontend) ───────────────────────────────

#[tauri::command]
fn show_window(app: AppHandle) {
    if let Some(window) = app.get_window("main") {
        window.show().ok();
        window.set_focus().ok();
        window.unminimize().ok();
    }
}

#[tauri::command]
fn hide_window(app: AppHandle) {
    if let Some(window) = app.get_window("main") {
        window.hide().ok();
    }
}

#[tauri::command]
fn minimize_window(app: AppHandle) {
    if let Some(window) = app.get_window("main") {
        window.minimize().ok();
    }
}

#[tauri::command]
fn maximize_window(app: AppHandle) {
    if let Some(window) = app.get_window("main") {
        if window.is_maximized().unwrap_or(false) {
            window.unmaximize().ok();
        } else {
            window.maximize().ok();
        }
    }
}

#[tauri::command]
fn close_to_tray(app: AppHandle) {
    if let Some(window) = app.get_window("main") {
        window.hide().ok();
    }
}

#[tauri::command]
fn get_platform() -> String {
    std::env::consts::OS.to_string()
}

#[tauri::command]
fn open_external(url: String) {
    #[cfg(target_os = "windows")]
    Command::new("cmd").args(["/c", "start", &url]).spawn().ok();
    #[cfg(target_os = "macos")]
    Command::new("open").arg(&url).spawn().ok();
    #[cfg(target_os = "linux")]
    Command::new("xdg-open").arg(&url).spawn().ok();
}

// ─── System Tray ───────────────────────────────────────────────────────────

fn build_system_tray() -> SystemTray {
    let show     = CustomMenuItem::new("show".to_string(),    "Open J.A.Y.");
    let chat     = CustomMenuItem::new("chat".to_string(),    "New Conversation");
    let separator = SystemTrayMenuItem::Separator;
    let voice    = CustomMenuItem::new("voice".to_string(),   "Voice Mode");
    let sep2     = SystemTrayMenuItem::Separator;
    let quit     = CustomMenuItem::new("quit".to_string(),    "Quit J.A.Y.");

    let menu = SystemTrayMenu::new()
        .add_item(show)
        .add_item(chat)
        .add_native_item(separator)
        .add_item(voice)
        .add_native_item(sep2)
        .add_item(quit);

    SystemTray::new().with_menu(menu).with_tooltip("J.A.Y. — Just Assists You")
}

fn handle_tray_event(app: &AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::LeftClick { .. } => {
            show_window(app.clone());
        }
        SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
            "show" => { show_window(app.clone()); }
            "chat" => {
                show_window(app.clone());
                app.emit_all("navigate", "/chat").ok();
            }
            "voice" => {
                show_window(app.clone());
                app.emit_all("navigate", "/voice").ok();
            }
            "quit" => {
                // Stop backend
                if let Some(state) = app.try_state::<BackendProcess>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(mut child) = guard.take() {
                            child.kill().ok();
                        }
                    }
                }
                std::process::exit(0);
            }
            _ => {}
        },
        _ => {}
    }
}

// ─── Backend Management ────────────────────────────────────────────────────

fn start_backend() -> Option<Child> {
    // Try to start the Python FastAPI backend
    let backend_paths = [
        "./backend/start.sh",
        "../backend/start.sh",
        "python",
    ];

    // Attempt with uvicorn directly
    let result = Command::new("uvicorn")
        .args(["app.main:app", "--host", "0.0.0.0", "--port", "8000"])
        .current_dir("../backend")
        .spawn();

    match result {
        Ok(child) => {
            println!("[J.A.Y.] Backend started (PID: {})", child.id());
            Some(child)
        }
        Err(e) => {
            eprintln!("[J.A.Y.] Could not auto-start backend: {}", e);
            eprintln!("[J.A.Y.] Please start backend manually: cd backend && uvicorn app.main:app");
            None
        }
    }
}

// ─── Main ──────────────────────────────────────────────────────────────────

fn main() {
    // Start backend process
    let backend_child = start_backend();

    tauri::Builder::default()
        .manage(BackendProcess(Mutex::new(backend_child)))
        .system_tray(build_system_tray())
        .on_system_tray_event(handle_tray_event)
        .invoke_handler(tauri::generate_handler![
            show_window,
            hide_window,
            minimize_window,
            maximize_window,
            close_to_tray,
            get_platform,
            open_external,
        ])
        .on_window_event(|event| {
            // Minimize to tray instead of closing
            if let WindowEvent::CloseRequested { api, .. } = event.event() {
                event.window().hide().ok();
                api.prevent_close();
            }
        })
        .setup(|app| {
            let app_handle = app.handle();

            // Register global shortcut: Ctrl+Shift+J to show/hide
            let mut shortcut_manager = app.global_shortcut_manager();
            let app_handle_clone = app_handle.clone();
            shortcut_manager
                .register("Ctrl+Shift+J", move || {
                    if let Some(window) = app_handle_clone.get_window("main") {
                        if window.is_visible().unwrap_or(false) {
                            window.hide().ok();
                        } else {
                            window.show().ok();
                            window.set_focus().ok();
                        }
                    }
                })
                .ok();

            // Register Ctrl+Shift+V for voice
            let app_handle_v = app_handle.clone();
            shortcut_manager
                .register("Ctrl+Shift+V", move || {
                    if let Some(window) = app_handle_v.get_window("main") {
                        window.show().ok();
                        window.set_focus().ok();
                        app_handle_v.emit_all("navigate", "voice").ok();
                    }
                })
                .ok();

            println!("[J.A.Y.] Desktop shell initialized");
            println!("[J.A.Y.] Shortcuts: Ctrl+Shift+J (toggle), Ctrl+Shift+V (voice)");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error running J.A.Y.");
}
