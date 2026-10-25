#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde_json::{json, Value};
use std::{io::{BufRead, BufReader, Write}, path::PathBuf, process::{Child, ChildStdin, ChildStdout, Command, Stdio}, sync::Mutex};
use tauri::Manager;

struct Engine {
    child: Child,
    input: ChildStdin,
    output: BufReader<ChildStdout>,
    next_id: u64,
}

impl Engine {
    fn start(app: &tauri::AppHandle) -> Result<Self, String> {
        let res = app.path().resource_dir().map_err(|e| e.to_string())?;
        let bin = res.join("bin").join(if cfg!(windows) { "sprfst.exe" } else { "sprfst" });
        let entry = res.join("engine").join("main.spf");
        let mut child = Command::new(&bin)
            .args(["run", entry.to_str().ok_or("invalid resource path")?, "--", "--serve"])
            .current_dir(&res)
            .env("SPRFST_HOME", &res)
            .env("SREON_RES", &res)
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null())
            .spawn().map_err(|e| format!("could not start Sreon engine: {e}"))?;
        let input = child.stdin.take().ok_or("engine stdin unavailable")?;
        let mut output = BufReader::new(child.stdout.take().ok_or("engine stdout unavailable")?);
        let mut hello = String::new();
        output.read_line(&mut hello).map_err(|e| e.to_string())?;
        if hello.trim().is_empty() { let _ = child.kill(); return Err("engine exited during startup".into()); }
        Ok(Self { child, input, output, next_id: 1 })
    }

    fn request(&mut self, mut request: Value) -> Result<Value, String> {
        let id = self.next_id;
        self.next_id += 1;
        request["id"] = json!(id);
        serde_json::to_writer(&mut self.input, &request).map_err(|e| e.to_string())?;
        self.input.write_all(b"\n").and_then(|_| self.input.flush()).map_err(|e| e.to_string())?;
        let mut line = String::new();
        self.output.read_line(&mut line).map_err(|e| e.to_string())?;
        if line.is_empty() { return Err("engine closed its response stream".into()); }
        serde_json::from_str(&line).map_err(|e| format!("invalid engine response: {e}"))
    }
}

struct EngineState(Mutex<Option<Engine>>);

#[tauri::command]
fn engine_request(state: tauri::State<'_, EngineState>, request: Value) -> Result<Value, String> {
    let mut guard = state.0.lock().map_err(|_| "engine lock poisoned".to_string())?;
    let engine = guard.as_mut().ok_or("engine has not started")?;
    engine.request(request)
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let engine = Engine::start(app.handle());
            match engine {
                Ok(engine) => { app.manage(EngineState(Mutex::new(Some(engine)))); }
                Err(error) => {
                    eprintln!("Sreon startup failed: {error}");
                    app.manage(EngineState(Mutex::new(None)));
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![engine_request])
        .run(tauri::generate_context!())
        .expect("failed to run Sreon");
}
