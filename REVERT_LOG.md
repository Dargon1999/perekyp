# Revert Log - 2026-02-07

## Interface Restoration
- **SettingsTab**:
  - Reverted navigation from Top Navigation Bar to **Sidebar (QListWidget)**.
  - Restored 5 distinct pages: General, Update, Tab Management, Advanced, Contact.
  - Moved "Contact/Feedback" from Advanced page to its own dedicated page (Index 4).
  - Restored button styles and layouts to match the original design.
  
- **FeedbackWidget**:
  - Restored "Topic" selection (QComboBox).
  - Restored "Attach Screenshot" button.
  - Added "Technical Data" gathering (OS, Python version).
  - Fixed initial state of "Send" button (synced with validation).

## Functional Restoration
- **Buttons**:
  - Verified `check_update_btn` is enabled and connected.
  - Verified `download_btn` and `install_btn` are disabled until update check.
  - Verified `send_btn` (Feedback) is validated against text length.
  - Verified `screen_btn` (Screenshot) is enabled.
  - Verified `admin_btn` is enabled and connected to login logic.

## Verification
- Passed `tests/test_settings_navigation.py` (Structure & Navigation).
- Passed `tests/test_buttons_interactive.py` (Button States & Interactions).
