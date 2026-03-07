# Changelog

All notable changes to this project will be documented in this file.

## [9.2.3] - 2026-03-07

### Fixed
- **Capital Planning**: Improved goal formatting to display only integers without decimals or separators (e.g., "$1000" instead of "$1,000.00").
- **Fishing Tab**: Fixed build suggestion generator to use real equipment names from the active profile instead of "test line" and "test bait" placeholders.
- **Tests**: Enhanced unit tests to cover financial goal formatting and fishing equipment name localization.

## [9.2.2] - 2026-03-07

### Added
- **UI**: Dynamic visibility of the "Ad Cost" field in the Buy/Sell tab based on automation settings.
- **Capital Planning**: Flexible goal input width with support for very large numbers (billions) without truncation.
- **Fishing Tab**: Enhanced "Community Builds" cards with a grid layout to prevent text overlapping and ensure all equipment info is visible.

### Fixed
- **Capital Planning**: Fixed `NameError` related to `QSizePolicy` during tab initialization.
- **Buy/Sell Tab**: Fixed a logic bug where the ad cost field wouldn't hide correctly when disabled in settings.

## [9.2.1] - 2026-03-07

### Added
- **DataManager**: Added `get_achievements()` method to properly retrieve unlocked achievements, resolving initialization errors.
- **Settings**: Added "Show buy price in inventory" toggle for the "Buy/Sell" tab.
- **Buy/Sell Tab**: Automatic ad cost pre-filling now supports persistent state between items and immediate refresh.

### Fixed
- **General**: Fixed a critical `ImportError` on startup/interaction due to missing `QAccessible` in some PyQt6 environments (removed accessibility notifications for now to prioritize stability).
- **Capital Planning**: Fixed `AttributeError` when loading achievements during tab initialization.
- **Capital Planning**: Fixed Enter key validation in the inline balance editor to ensure immediate saving.
- **Buy/Sell Tab**: Fixed a bug where ad cost auto-filling wouldn't work even if enabled in settings.
- **Buy/Sell Tab**: Fixed reactive visibility of the buy price in the inventory list.

## [9.2.0] - 2026-03-07

### Added
- **Fishing Tab**: Added "Line" and "Bait" information to the equipment build generator and community builds cards, including durability tracking.
- **Fishing Tab**: Replaced bait icon 🐟 with 🪱 for better visual accuracy.
- **Settings**: Added global toggle "Allow manual balance edit" (allowManualBalanceEdit) in the General settings page.
- **Inline Editing**: Enabled double-click inline editing for balance labels in "Car Rental", "Capital Planning", and other standard tabs.
- **Tests**: Added comprehensive tests for release V9.2 fixes in `tests/test_v9_2_fixes.py`.

### Fixed
- **Analytics Tab**: Resolved loading errors by implementing robust data validation and error handling in `AnalyticsSubTab.refresh_data`.
- **Analytics Tab**: Improved date parsing logic to handle multiple formats (ISO, Russian) and prevent crashes on corrupted data.
- **Car Rental**: Fixed a bug where manual balance editing remained inactive even when enabled in settings (incorrect key reference).
- **Capital Planning**: Expanded input field widths (to 280px) and label widths (to 300px) to prevent truncation of large numbers (billions).
- **Capital Planning**: Implemented "Enter" key listener on the goal input field to automatically save the financial goal.
- **General UI**: Increased minimum width of statistics cards to 220px across all tabs for better readability of large financial values.

### Localized
- **Fishing Tab**: Fully translated equipment categories and sub-tab headers to Russian ("Снасти", "Леска", "Наживка", "Вопрос / Сборка").
- **Fishing Tab**: Updated build suggestion text and community cards to use Russian terminology for all gear components.
