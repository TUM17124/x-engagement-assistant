use std::time::{Duration, Instant};
use tauri::{AppHandle, Manager};
use tauri_plugin_updater::UpdaterExt;
use serde_json::{Value, json};
use crate::{Backend, client};

fn progress(token: &str, id: &str, state: &str, message: &str, downloaded: usize, total: Option<u64>) {
    let _ = client().post("http://127.0.0.1:8787/desktop/update-progress")
        .header("X-Desktop-Token", token)
        .json(&json!({"id":id,"state":state,"message":message,"downloaded":downloaded,"total":total})).send();
}

pub fn run(app: AppHandle, token: String, job: Value) {
    let id = job["id"].as_str().unwrap_or("").to_string();
    let version = job["version"].as_str().unwrap_or("").to_string();
    let result: Result<(), String> = (|| {
        let (update,bytes)=tauri::async_runtime::block_on(async {
        let update = app.updater_builder().timeout(Duration::from_secs(120)).build()
            .map_err(|_| "The signed updater could not start.")?.check().await
            .map_err(|_| "Could not read the signed GitHub release. Check your connection, then check for updates again.")?
            .ok_or("No newer signed update is available.")?;
        let expected = format!("https://github.com/TUM17124/x-engagement-assistant/releases/download/v{}/Social-Engagement-Command-Center-Setup.exe",version);
        if update.version != version || update.download_url.as_str() != expected {
            return Err("The release changed after your approval. Check for updates and review it again.".into());
        }
        let mut received=0usize;
        let mut last=Instant::now()-Duration::from_secs(2);
        let bytes=update.download(|chunk,total| {
            received+=chunk;
            if last.elapsed()>=Duration::from_secs(1) {
                let send_token=token.clone(); let send_id=id.clone(); let amount=received;
                std::thread::spawn(move || progress(&send_token,&send_id,"downloading","Downloading and verifying the signed installer.",amount,total));
                last=Instant::now();
            }
        },|| {}).await.map_err(|_| "Download or signature verification failed. Nothing was installed. Check for updates and try again.")?;
        Ok::<_,String>((update,bytes))
        })?;
        let received=bytes.len();
        progress(&token,&id,"installing","Verified. Saving a database backup and preparing the installer.",received,Some(received as u64));
        let ready=client().post("http://127.0.0.1:8787/desktop/prepare-update").header("X-Desktop-Token",&token)
            .send().map_err(|_| "Could not prepare the workspace. Nothing was installed.")?;
        if !ready.status().is_success() {
            return Err("An operation is still running or the backup failed. Finish current work and try updating again.".into());
        }
        // The backend performs graceful shutdown (including worker cancellation) before files change.
        for _ in 0..30 {
            std::thread::sleep(Duration::from_millis(500));
            if client().get("http://127.0.0.1:8787/health").send().is_err() { break; }
        }
        if client().get("http://127.0.0.1:8787/health").send().is_ok() {
            return Err("The workspace is still shutting down. Reopen the app before trying the update again.".into());
        }
        if let Some(child)=app.state::<Backend>().child.lock().unwrap().take() { let _=child.kill(); }
        update.install(&bytes).map_err(|_| "Windows could not start the installer. Reopen the app or download the release from GitHub.")?;
        Ok(())
    })();
    if let Err(message)=result {
        progress(&token,&id,"failed",&message,0,None);
        if let Some(window)=app.get_webview_window("main") {
            let script=format!("if(typeof errorPanel==='function')errorPanel(new Error({}), 'App update');",serde_json::to_string(&message).unwrap());
            let _=window.eval(&script);
        }
    }
}
