#include "mem_reduct.h"
#include <cassert>
#include <iostream>

void test_stats() {
    MemoryStats stats;
    bool ok = GetMemoryStatistics(&stats);
    assert(ok);
    assert(stats.total_phys > 0);
    assert(stats.used_phys > 0);
    std::cout << "test_stats passed" << std::endl;
}

void test_elevation() {
    bool elevated = IsElevated();
    std::cout << "Process is " << (elevated ? "" : "NOT ") << "elevated" << std::endl;
}

void test_clean() {
    MemoryStats before, after;
    GetMemoryStatistics(&before);
    bool ok = CleanMemory(0); // Light clean
    assert(ok);
    GetMemoryStatistics(&after);
    std::cout << "test_clean passed. Saved: " << (long long)before.used_phys - (long long)after.used_phys << " bytes" << std::endl;
}

int main() {
    std::cout << "Running tests..." << std::endl;
    test_stats();
    test_elevation();
    test_clean();
    std::cout << "All tests passed!" << std::endl;
    return 0;
}
