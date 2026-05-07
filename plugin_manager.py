import os
import json
import importlib.util
import sys
import logging
from PyQt6.QtWidgets import QWidget
from event_bus import EventBus

class Plugin:
    def __init__(self, plugin_id, metadata, module, ui_module=None):
        self.id = plugin_id
        self.metadata = metadata
        self.module = module
        self.ui_module = ui_module
        self.instance = None

    def initialize(self, app_context):
        if hasattr(self.module, "initialize"):
            self.instance = self.module.initialize(app_context)
            logging.info(f"Plugin {self.id} initialized")

    def get_ui(self, parent=None):
        if self.ui_module and hasattr(self.ui_module, "create_ui"):
            return self.ui_module.create_ui(parent)
        return None

class PluginManager:
    def __init__(self, plugins_dir="plugins", app_context=None):
        self.plugins_dir = plugins_dir
        self.app_context = app_context
        self.plugins = {}
        self.event_bus = EventBus.get_instance()

    def discover_plugins(self):
        if not os.path.exists(self.plugins_dir):
            return

        for plugin_name in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, plugin_name)
            if os.path.isdir(plugin_path):
                metadata_path = os.path.join(plugin_path, "plugin.json")
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                        
                        plugin_id = metadata.get("id", plugin_name)
                        main_py = os.path.join(plugin_path, "main.py")
                        ui_py = os.path.join(plugin_path, "ui.py")

                        # Load main module
                        spec = importlib.util.spec_from_file_location(f"{plugin_id}.main", main_py)
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[f"{plugin_id}.main"] = module
                        spec.loader.exec_module(module)

                        # Load UI module if exists
                        ui_module = None
                        if os.path.exists(ui_py):
                            ui_spec = importlib.util.spec_from_file_location(f"{plugin_id}.ui", ui_py)
                            ui_module = importlib.util.module_from_spec(ui_spec)
                            sys.modules[f"{plugin_id}.ui"] = ui_module
                            ui_spec.loader.exec_module(ui_module)

                        plugin = Plugin(plugin_id, metadata, module, ui_module)
                        self.plugins[plugin_id] = plugin
                        logging.info(f"Plugin {plugin_id} discovered")
                        
                    except Exception as e:
                        logging.error(f"Failed to load plugin {plugin_name}: {e}")

    def initialize_plugins(self):
        for plugin in self.plugins.values():
            try:
                plugin.initialize(self.app_context)
            except Exception as e:
                logging.error(f"Error initializing plugin {plugin.id}: {e}")

    def get_plugin_tabs(self):
        tabs = []
        for plugin in self.plugins.values():
            ui = plugin.get_ui()
            if ui:
                tabs.append((plugin.metadata.get("name", plugin.id), ui, plugin.metadata.get("icon", "🔌")))
        return tabs
