#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module for quick TEMP cleanup for hotkey F8
"""

import os

def clean_all_temp():
    """
    Quick cleanup of temporary files.
    Returns tuple (freed_bytes, files_deleted)
    """
    total_freed = 0
    total_files = 0
    
    # Get paths to temp folders
    temp_dirs = get_temp_dirs()
    
    for directory in temp_dirs:
        if not os.path.exists(directory):
            continue
            
        try:
            freed, files = clean_directory(directory)
            total_freed += freed
            total_files += files
        except Exception as e:
            print("Cleanup error {}: {}".format(directory, e))
    
    return total_freed, total_files


def get_temp_dirs():
    """Returns list of folders to clean."""
    dirs = []
    
    # User TEMP
    user_temp = os.environ.get('TEMP', '')
    if user_temp and os.path.exists(user_temp):
        dirs.append(user_temp)
    
    # System TEMP
    system_root = os.environ.get('SystemRoot', 'C:\\Windows')
    system_temp = os.path.join(system_root, 'Temp')
    if os.path.exists(system_temp):
        dirs.append(system_temp)
    
    # Prefetch
    prefetch = os.path.join(system_root, 'Prefetch')
    if os.path.exists(prefetch):
        dirs.append(prefetch)
    
    return dirs


def clean_directory(directory):
    """Clean folder from temporary files."""
    freed_bytes = 0
    files_deleted = 0
    
    try:
        for root, dirs, files in os.walk(directory, topdown=False):
            # Delete files
            for filename in files:
                try:
                    file_path = os.path.join(root, filename)
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        try:
                            os.chmod(file_path, 0o777)
                        except:
                            pass
                        os.remove(file_path)
                        freed_bytes += size
                        files_deleted += 1
                except:
                    pass
            
            # Try to remove empty folders
            for d in dirs:
                try:
                    dir_path = os.path.join(root, d)
                    if os.path.exists(dir_path):
                        os.rmdir(dir_path)
                except:
                    pass
    except:
        pass
    
    return freed_bytes, files_deleted


def format_size(bytes_count):
    """Format size to readable view."""
    if bytes_count >= 1024**3:
        return "{:.2f} GB".format(bytes_count / (1024**3))
    else:
        return "{:.1f} MB".format(bytes_count / (1024**2))


if __name__ == "__main__":
    # Test run
    print("Starting TEMP cleanup...")
    freed, files = clean_all_temp()
    print("Freed: {}, files: {}".format(format_size(freed), files))
