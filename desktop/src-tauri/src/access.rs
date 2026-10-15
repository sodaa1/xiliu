use tauri::{ipc::CapabilityBuilder, Manager};

fn capabilities(port: u16) -> [CapabilityBuilder; 3] {
    // WebView2 reports the IPC source as an origin. Page paths are enforced
    // by each window navigation guard; command permissions stay role-specific.
    let origin = format!("http://127.0.0.1:{port}");
    [
        CapabilityBuilder::new("owned-main")
            .local(false)
            .window("main")
            .remote(format!("{origin}/*"))
            .permission("main-commands")
            .permission("core:event:default")
            .permission("core:window:allow-minimize")
            .permission("core:window:allow-toggle-maximize")
            .permission("core:window:allow-close"),
        CapabilityBuilder::new("owned-companion")
            .local(false)
            .window("companion")
            .remote(format!("{origin}/*"))
            .permission("companion-commands")
            .permission("core:event:allow-listen")
            .permission("core:event:allow-unlisten"),
        CapabilityBuilder::new("owned-capture")
            .local(false)
            .window("capture")
            .remote(format!("{origin}/*"))
            .permission("capture-commands")
            .permission("core:event:allow-listen")
            .permission("core:event:allow-unlisten"),
    ]
}

pub fn install(app: &tauri::AppHandle, port: u16) -> tauri::Result<()> {
    // Called only after the child proves readiness using our per-launch secret.
    // No capability is granted to another localhost service or another window.
    for capability in capabilities(port) {
        app.add_capability(capability)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tauri::ipc::RuntimeCapability;

    #[test]
    fn remote_access_is_bound_to_owned_port_and_window_role() {
        let policies: Vec<_> = capabilities(49152)
            .into_iter()
            .map(|capability| match capability.build() {
                tauri::utils::acl::capability::CapabilityFile::Capability(value) => {
                    serde_json::to_value(value).unwrap()
                }
                _ => panic!("expected a single capability"),
            })
            .collect();
        for (index, (window, path, group)) in [
            ("main", "/*", "main-commands"),
            ("companion", "/*", "companion-commands"),
            ("capture", "/*", "capture-commands"),
        ]
        .into_iter()
        .enumerate()
        {
            let policy = &policies[index];
            assert_eq!(policy["local"], false);
            assert_eq!(policy["windows"], serde_json::json!([window]));
            assert_eq!(
                policy["remote"]["urls"],
                serde_json::json!([format!("http://127.0.0.1:49152{path}")])
            );
            let permissions = policy["permissions"].as_array().unwrap();
            assert!(permissions.contains(&serde_json::json!(group)));
            assert_eq!(
                permissions
                    .iter()
                    .filter(|p| p.as_str().unwrap().ends_with("-commands"))
                    .count(),
                1
            );
        }
    }
}
