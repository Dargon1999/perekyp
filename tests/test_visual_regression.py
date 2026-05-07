import unittest
from gui.styles import StyleManager

class TestVisualRegression(unittest.TestCase):
    """
    Regression tests to ensure the visual style (theme colors, fonts) 
    matches the reference design specification.
    """

    def test_dark_theme_palette_integrity(self):
        """
        Verify that the DARK_THEME palette contains the exact hex values 
        defined in the reference design.
        """
        theme = StyleManager.DARK_THEME
        
        # Reference Specification (Midnight Modern - Restored Dark Blue)
        expected_values = {
            "bg_main": "#0f172a",       # Slate 900
            "bg_secondary": "#1e293b",  # Slate 800
            "bg_card": "#1e293b",
            "accent": "#3b82f6",        # Blue 500
            "input_bg": "#020617",      # Slate 950
            "border": "#334155",        # Slate 700
            "text_main": "#f1f5f9",     # Slate 100
            "text_secondary": "#94a3b8",# Slate 400
            "success": "#10b981",       # Emerald 500
            "danger": "#ef4444",        # Red 500
            "warning": "#f59e0b"        # Amber 500
        }

        for key, expected_hex in expected_values.items():
            self.assertIn(key, theme, f"Missing key in DARK_THEME: {key}")
            self.assertEqual(theme[key].lower(), expected_hex.lower(), 
                             f"Color mismatch for '{key}'. Expected {expected_hex}, got {theme[key]}")

    def test_theme_completeness(self):
        """
        Ensure all required semantic color keys are present.
        """
        required_keys = [
            "bg_main", "bg_secondary", "bg_tertiary", "bg_card",
            "accent", "accent_hover", "accent_pressed",
            "text_main", "text_secondary",
            "border", "input_bg", "scrollbar_handle",
            "success", "danger", "warning"
        ]
        
        theme = StyleManager.DARK_THEME
        for key in required_keys:
            self.assertIn(key, theme, f"DARK_THEME is missing required key: {key}")

    def test_generated_qss_contains_theme_values(self):
        """
        Verify that the QSS generator actually uses the theme values.
        """
        qss = StyleManager.get_qss("dark")
        theme = StyleManager.DARK_THEME
        
        # Check if the main background color is present in the generated QSS
        self.assertIn(theme['bg_main'], qss, "QSS should contain bg_main color")
        self.assertIn(theme['text_main'], qss, "QSS should contain text_main color")
        
        # Check for font family
        self.assertIn("Segoe UI", qss, "QSS should define standard font family")

if __name__ == '__main__':
    unittest.main()
