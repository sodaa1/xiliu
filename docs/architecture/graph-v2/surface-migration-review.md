# Source relocation audit

The scanner now includes the shipped docs/web/src introduction. 27 obsolete identities are preserved verbatim under archived_surfaces with their original verification and source; 27 reviewed current Intro controls are ui_only and not_run. Existing model save boundaries remain restricted. Historical failed coverage reports are retained. No verification status was upgraded. The current sources contain only navigation/anchors, local presentation state and clipboard copy; no business API mutation. UI assertions are unchanged.
