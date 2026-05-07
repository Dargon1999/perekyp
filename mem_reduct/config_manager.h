#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <string>
#include <windows.h>

class ConfigManager {
public:
    static std::string GetConfigPath() {
        char buffer[MAX_PATH];
        GetModuleFileNameA(NULL, buffer, MAX_PATH);
        std::string path(buffer);
        size_t pos = path.find_last_of("\\/");
        return path.substr(0, pos) + "\\mem_reduct\\config.ini";
    }

    static void SaveSetting(const std::string& section, const std::string& key, const std::string& value) {
        WritePrivateProfileStringA(section.c_str(), key.c_str(), value.c_str(), GetConfigPath().c_str());
    }

    static std::string LoadSetting(const std::string& section, const std::string& key, const std::string& defaultValue) {
        char buffer[256];
        GetPrivateProfileStringA(section.c_str(), key.c_str(), defaultValue.c_str(), buffer, 256, GetConfigPath().c_str());
        return std::string(buffer);
    }
};

#endif // CONFIG_MANAGER_H
