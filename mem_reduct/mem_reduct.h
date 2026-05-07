#ifndef MEM_REDUCT_H
#define MEM_REDUCT_H

#include <windows.h>
#include <psapi.h>
#include <iostream>
#include <vector>
#include <string>

#ifdef MEM_REDUCT_EXPORTS
#define MEM_REDUCT_API __declspec(dllexport)
#else
#define MEM_REDUCT_API __declspec(dllimport)
#endif

extern "C" {
    struct MemoryStats {
        unsigned long long total_phys;
        unsigned long long avail_phys;
        unsigned long long used_phys;
        unsigned long long total_page;
        unsigned long long avail_page;
        unsigned long long system_cache;
        unsigned long long standby;
        unsigned long long modified;
    };

    MEM_REDUCT_API bool GetMemoryStatistics(MemoryStats* stats);
    MEM_REDUCT_API bool CleanMemory(int level); // 0: light, 1: medium, 2: aggressive
    MEM_REDUCT_API bool IsElevated();
}

#endif // MEM_REDUCT_H
