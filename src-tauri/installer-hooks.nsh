!macro NSIS_HOOK_POSTUNINSTALL
  IfSilent xea_keep_data
  MessageBox MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2 "Also remove your local X Engagement Assistant workspace and saved credentials? This permanently deletes your drafts, history, and encrypted keys. Choose No to keep them for a reinstall." IDNO xea_keep_data
  RMDir /r "$LOCALAPPDATA\XEngagementAssistant"
  xea_keep_data:
!macroend
