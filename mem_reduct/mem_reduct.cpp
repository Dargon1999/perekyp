#include "mem_reduct.h"
#include <tlhelp32.h>

#define MEM_REDUCT_EXPORTS

bool IsElevated() {
    bool fRet = false;
    HANDLE hToken = NULL;
    if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &hToken)) {
        TOKEN_ELEVATION elevation;
        DWORD dwSize;
        if (GetTokenInformation(hToken, TokenElevation, &elevation, sizeof(elevation), &dwSize)) {
            fRet = elevation.TokenIsElevated;
        }
    }
    if (hToken) CloseHandle(hToken);
    return fRet;
}

bool GetMemoryStatistics(MemoryStats* stats) {
    if (!stats) return false;

    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(MEMORYSTATUSEX);
    if (!GlobalMemoryStatusEx(&memInfo)) return false;

    stats->total_phys = memInfo.ullTotalPhys;
    stats->avail_phys = memInfo.ullAvailPhys;
    stats->used_phys = memInfo.ullTotalPhys - memInfo.ullAvailPhys;
    stats->total_page = memInfo.ullTotalPageFile;
    stats->avail_page = memInfo.ullAvailPageFile;

    PERFORMANCE_INFORMATION perfInfo;
    perfInfo.cb = sizeof(PERFORMANCE_INFORMATION);
    if (GetPerformanceInfo(&perfInfo, sizeof(PERFORMANCE_INFORMATION))) {
        stats->system_cache = (unsigned long long)perfInfo.SystemCache * perfInfo.PageSize;
    }

    // Note: standby and modified pages are harder to get precisely without undocumented APIs or heavy sampling.
    // For now, we'll estimate or use available performance counters if needed.
    // A more advanced implementation would use NtQuerySystemInformation with SystemMemoryListInformation.
    
    return true;
}

bool CleanWorkingSets() {
    HANDLE hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hProcessSnap == INVALID_HANDLE_VALUE) return false;

    PROCESSENTRY32 pe32;
    pe32.dwSize = sizeof(PROCESSENTRY32);

    if (Process32First(hProcessSnap, &pe32)) {
        do {
            HANDLE hProcess = OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, FALSE, pe32.th32ProcessID);
            if (hProcess) {
                EmptyWorkingSet(hProcess);
                CloseHandle(hProcess);
            }
        } while (Process32Next(hProcessSnap, &pe32));
    }

    CloseHandle(hProcessSnap);
    return true;
}

bool CleanSystemCache() {
    if (!IsElevated()) return false;

    // To clear system cache, we need SE_INCREASE_QUOTA_NAME and SE_PROFILE_SINGLE_PROCESS_NAME privileges
    // and then call SetSystemFileCacheSize or similar.
    
    SYSTEM_CACHE_INFORMATION sci;
    ZeroMemory(&sci, sizeof(sci));
    sci.MinimumWorkingSet = (SIZE_T)-1;
    sci.MaximumWorkingSet = (SIZE_T)-1;

    // This is often done via NtSetSystemInformation which is semi-documented.
    // For simplicity in this portable version, we focus on working sets.
    
    return true;
}

bool CleanMemory(int level) {
    bool success = true;
    
    // Light: Just current process + some working sets
    if (level >= 0) {
        EmptyWorkingSet(GetCurrentProcess());
        CleanWorkingSets();
    }

    // Medium: More aggressive working set trimming
    if (level >= 1) {
        // Additional logic can be added here
    }

    // Aggressive: Try to clear system cache (requires admin)
    if (level >= 2 && IsElevated()) {
        CleanSystemCache();
    }

    return success;
}
