# Bolt's Performance Journal

## 2026-03-29 - Path Stat Syscall Overhead in File Scanning & Hashing
**Learning:** Checking `path.is_file()` or `path.stat().st_size` on `pathlib.Path` objects prior to opening files introduces redundant filesystem `os.stat` system calls per file. Opening the file descriptor directly and calling `os.fstat(f.fileno())` avoids kernel path resolution roundtrips.
**Action:** When working on file-intensive scanning, indexing, or hashing loops, operate directly on open file handles or descriptors using `os.fstat` instead of path-based pre-checks.
