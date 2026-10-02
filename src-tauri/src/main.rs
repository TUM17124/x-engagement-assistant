#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
use std::{sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}}, time::Duration};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent, RunEvent, menu::{Menu, MenuItem}, tray::TrayIconBuilder};
use tauri_plugin_shell::{ShellExt, process::CommandChild};
use tauri_plugin_opener::OpenerExt;
use tauri_plugin_notification::NotificationExt;

mod updates;

struct Backend { child: Mutex<Option<CommandChild>>, token: String, tray_enabled: Arc<AtomicBool> }
fn client() -> reqwest::blocking::Client {
    reqwest::blocking::Client::builder().timeout(Duration::from_secs(3)).build().expect("HTTP client")
}
fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app,_,_| {
            if let Some(window)=app.get_webview_window("main") { let _=window.show(); let _=window.set_focus(); }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .setup(|app| {
            let token=uuid::Uuid::new_v4().to_string();
            let tray_enabled=Arc::new(AtomicBool::new(false));
            let (mut events, child)=app.shell().sidecar("xea-backend")?
                .env("XEA_DESKTOP_TOKEN",&token).args(["--port","8787"]).spawn()?;
            // Drain sidecar output; never forward it to web content or write credentials to logs.
            tauri::async_runtime::spawn(async move { while events.recv().await.is_some() {} });
            app.manage(Backend{child:Mutex::new(Some(child)),token:token.clone(),tray_enabled:tray_enabled.clone()});
            let handle=app.handle().clone();
            let nav_handle=handle.clone();
            WebviewWindowBuilder::new(app,"main",WebviewUrl::App("index.html".into()))
                .initialization_script("window.__XEA_DESKTOP__ = true;")
                .title("Social Engagement Command Center").inner_size(1280.0,860.0).min_inner_size(760.0,600.0)
                .on_navigation(move |url| {
                    let local=url.host_str()==Some("127.0.0.1") && url.port()==Some(8787);
                    let internal=url.scheme()=="tauri" || url.host_str()==Some("tauri.localhost");
                    let external=matches!(url.scheme(),"http"|"https") && ((!local && !internal) || url.path()=="/auth/login");
                    if external { let _=nav_handle.opener().open_url(url.as_str(),None::<&str>); return false; }
                    local || internal
                })
                .on_download(|webview,event| {
                    match event {
                        tauri::webview::DownloadEvent::Requested{url,destination} => {
                            if url.host_str()!=Some("127.0.0.1") || url.port()!=Some(8787) { return false; }
                            let export = url.path().strip_prefix("/api/export/");
                            let media = url.path().starts_with("/api/media/") && url.path().ends_with("/file");
                            let filename = if let Some(kind) = export {
                                if !["settings","drafts","history","database"].contains(&kind) { return false; }
                                format!("social-{}.{}", kind, if kind=="database" {"sqlite3"} else {"json"})
                            } else if media {
                                destination.file_name().and_then(|n|n.to_str()).unwrap_or("media").chars()
                                    .filter(|c| !c.is_control() && !r#"<>:"/\\|?*"#.contains(*c)).take(150).collect::<String>()
                            } else { return false; };
                            if let Ok(folder)=webview.app_handle().path().download_dir() {
                                *destination=folder.join(format!("{}-{}",uuid::Uuid::new_v4(),filename));
                            } else { return false; }
                        },
                        tauri::webview::DownloadEvent::Finished{success,..} => {
                            let message=if success {"Export saved to your Downloads folder."} else {"Export download failed. Please try again."};
                            let script=format!("if(typeof toast==='function')toast({});",serde_json::to_string(message).unwrap());
                            let _=webview.eval(&script);
                        },
                        _=>{}
                    }
                    true
                })
                .on_new_window({
                    let app=handle.clone();
                    move |url,_features| {
                        if matches!(url.scheme(),"http"|"https") {
                            let _=app.opener().open_url(url.as_str(),None::<&str>);
                        }
                        tauri::webview::NewWindowResponse::Deny
                    }
                }).build()?;
            let open=MenuItem::with_id(app,"open","Open dashboard",true,None::<&str>)?;
            let pause=MenuItem::with_id(app,"pause","Pause monitoring",true,None::<&str>)?;
            let resume=MenuItem::with_id(app,"resume","Resume monitoring",true,None::<&str>)?;
            let quit=MenuItem::with_id(app,"quit","Quit (stops scheduling)",true,None::<&str>)?;
            let menu=Menu::with_items(app,&[&open,&pause,&resume,&quit])?;
            let tray=TrayIconBuilder::with_id("workspace").icon(app.default_window_icon().unwrap().clone())
                .tooltip("Social Engagement Command Center - monitoring paused").menu(&menu)
                .on_menu_event(|app,event| {
                    match event.id.as_ref() {
                        "open" => {if let Some(w)=app.get_webview_window("main"){let _=w.show();let _=w.set_focus();}},
                        "pause"|"resume" => {
                            let token=app.state::<Backend>().token.clone();
                            let enabled=event.id.as_ref()=="resume";
                            std::thread::spawn(move || {let _=client().post(format!("http://127.0.0.1:8787/desktop/monitoring/{enabled}")).header("X-Desktop-Token",token).send();});
                        },
                        "quit" => app.exit(0),
                        _=>{}
                    }
                }).build(app)?;
            tray.set_visible(false)?;
            std::thread::spawn(move || {
                let http=client();
                let mut ready=false;
                for _ in 0..120 {
                    if http.get("http://127.0.0.1:8787/desktop/state").header("X-Desktop-Token",&token).send().map(|r|r.status().is_success()).unwrap_or(false) {
                        ready=true;break;
                    }
                    std::thread::sleep(Duration::from_millis(500));
                }
                if !ready { return; }
                if let Some(w)=handle.get_webview_window("main") {let _=w.navigate("http://127.0.0.1:8787/".parse().unwrap());}
                loop {
                    if let Ok(r)=http.get("http://127.0.0.1:8787/desktop/state").header("X-Desktop-Token",&token).send() {
                        if let Ok(state)=r.json::<serde_json::Value>() {
                            let enabled=state["tray_enabled"].as_bool().unwrap_or(false);
                            tray_enabled.store(enabled,Ordering::SeqCst);
                            if let Some(t)=handle.tray_by_id("workspace") {
                                let _=t.set_visible(enabled);
                                let label=if state["monitoring"].as_bool().unwrap_or(false) {"Social Engagement Command Center - monitoring enabled"} else {"Social Engagement Command Center - monitoring paused"};
                                let _=t.set_tooltip(Some(label));
                            }
                        }
                    }
                    if let Ok(r)=http.get("http://127.0.0.1:8787/desktop/events").header("X-Desktop-Token",&token).send() {
                        if let Ok(events)=r.json::<Vec<serde_json::Value>>() {
                            for event in events {
                                if let Some(title)=event["title"].as_str() {let _=handle.notification().builder().title("Social Engagement Command Center").body(title).show();}
                            }
                        }
                    }
                    if let Ok(response)=http.get("http://127.0.0.1:8787/desktop/update-request").header("X-Desktop-Token",&token).send() {
                        if let Ok(job)=response.json::<serde_json::Value>() {
                            if job["state"].as_str()==Some("downloading") { updates::run(handle.clone(),token.clone(),job); }
                        }
                    }
                    std::thread::sleep(Duration::from_secs(10));
                }
            });
            Ok(())
        })
        .on_window_event(|window,event| {
            if let WindowEvent::CloseRequested{api,..}=event {
                let state=window.state::<Backend>();
                if state.tray_enabled.load(Ordering::SeqCst) {api.prevent_close();let _=window.hide();}
            }
        })
        .build(tauri::generate_context!()).expect("Could not start Social Engagement Command Center");
    app.run(|handle,event| {
        if let RunEvent::Exit=event {
            let state=handle.state::<Backend>();
            let _=client().post("http://127.0.0.1:8787/desktop/shutdown").header("X-Desktop-Token",&state.token).send();
            std::thread::sleep(Duration::from_millis(700));
            let child = state.child.lock().unwrap().take();
            if let Some(child) = child { let _ = child.kill(); }
        }
    });
}
