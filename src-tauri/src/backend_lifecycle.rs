//! Stop the owned sidecar tree before replacing its executable.
use std::{path::Path, sync::atomic::{AtomicBool, Ordering}, time::{Duration, Instant}};
use tauri::{AppHandle, Manager};
use crate::Backend;

fn wait_until(timeout: Duration, mut ready: impl FnMut() -> bool) -> bool {
    let start=Instant::now();
    loop {
        if ready() { return true; }
        if start.elapsed() >= timeout { return false; }
        std::thread::sleep(Duration::from_millis(100));
    }
}

fn released(path: &Path) -> bool {
    #[cfg(windows)] {
        use std::os::windows::fs::OpenOptionsExt;
        // A closed HTTP listener does not mean the PyInstaller process has exited.
        std::fs::OpenOptions::new().read(true).share_mode(0).open(path).is_ok()
    }
    #[cfg(not(windows))] { let _=path; true }
}

#[cfg(windows)]
fn stop_tree(pid: u32) -> Result<(), String> {
    use std::os::windows::process::CommandExt;
    let system=std::env::var_os("SystemRoot").ok_or("Windows system directory is unavailable.")?;
    let status=std::process::Command::new(Path::new(&system).join("System32/taskkill.exe"))
        .args(["/PID", &pid.to_string(), "/T", "/F"])
        .creation_flags(0x08000000).stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null()).status()
        .map_err(|_| "Could not stop the owned backend process tree.")?;
    if status.success() { Ok(()) } else { Err("The backend could not be stopped. Close the app and retry the installer.".into()) }
}

pub fn stop(app: &AppHandle) -> Result<(), String> {
    let state=app.state::<Backend>();
    let mut owned=state.child.lock().map_err(|_| "Backend ownership is unavailable.")?;
    let Some(child)=owned.as_ref() else { return Ok(()); };
    let exited: &AtomicBool=&state.exited;
    if !wait_until(Duration::from_secs(15), || exited.load(Ordering::SeqCst)) {
        #[cfg(windows)] {
            // Keep the launcher alive until its descendants are stopped; kill() alone orphans them.
            let result=stop_tree(child.pid());
            if result.is_err() && !exited.load(Ordering::SeqCst) { return result; }
        }
        #[cfg(not(windows))] { let _=child; if let Some(child)=owned.take() { child.kill().map_err(|_| "Could not stop the backend.")?; } }
    }
    if !wait_until(Duration::from_secs(10), || exited.load(Ordering::SeqCst)) {
        return Err("The backend has not exited. Installation was stopped to protect the workspace.".into());
    }
    let executable=std::env::current_exe().map_err(|_| "Could not locate the installed app.")?
        .with_file_name(if cfg!(windows) { "xea-backend.exe" } else { "xea-backend" });
    if !wait_until(Duration::from_secs(5), || released(&executable)) {
        return Err("The backend file is still in use. Installation was stopped; close the app and retry.".into());
    }
    owned.take();
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn waits_for_exit_and_refuses_unreleased_backend() {
        let mut polls=0;
        assert!(wait_until(Duration::from_secs(1), || { polls+=1; polls>=3 }));
        assert!(!wait_until(Duration::from_millis(50), || false));
    }
    #[cfg(windows)]
    #[test]
    fn locked_backend_is_not_ready_for_replacement() {
        use std::os::windows::fs::OpenOptionsExt;
        let path=std::env::temp_dir().join(format!("xea-lock-{}",uuid::Uuid::new_v4()));
        let handle=std::fs::OpenOptions::new().create_new(true).write(true).share_mode(0).open(&path).unwrap();
        assert!(!released(&path));
        drop(handle);
        assert!(released(&path));
        std::fs::remove_file(path).unwrap();
    }
    #[cfg(windows)]
    #[test]
    #[ignore = "subprocess fixture only"]
    fn process_fixture() {
        use std::os::windows::fs::OpenOptionsExt;
        let path=std::env::var_os("XEA_LIFECYCLE_FIXTURE").expect("fixture path");
        if std::env::var_os("XEA_LIFECYCLE_LEAF").is_some() {
            let _file=std::fs::OpenOptions::new().write(true).create_new(true).share_mode(0).open(path).unwrap();
            std::thread::sleep(Duration::from_secs(30));
        } else {
            let mut child=std::process::Command::new(std::env::current_exe().unwrap())
                .args(["--ignored","--exact","backend_lifecycle::tests::process_fixture"])
                .env("XEA_LIFECYCLE_LEAF","1").spawn().unwrap();
            let _=child.wait();
        }
    }
    #[cfg(windows)]
    #[test]
    fn stopping_owned_tree_releases_descendant_file_lock() {
        let path=std::env::temp_dir().join(format!("xea-tree-{}",uuid::Uuid::new_v4()));
        let mut parent=std::process::Command::new(std::env::current_exe().unwrap())
            .args(["--ignored","--exact","backend_lifecycle::tests::process_fixture"])
            .env("XEA_LIFECYCLE_FIXTURE",&path).stdout(std::process::Stdio::null()).spawn().unwrap();
        let ready=wait_until(Duration::from_secs(10), || path.exists());
        let result=stop_tree(parent.id());
        let _=parent.wait();
        assert!(ready,"fixture did not acquire lock");
        assert!(result.is_ok());
        assert!(wait_until(Duration::from_secs(5), || released(&path)),"orphaned descendant still owns the backend file");
        std::fs::remove_file(path).unwrap();
    }
}
