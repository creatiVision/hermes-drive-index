# Bolt's Performance Journal

## 2026-03-29 - Path Stat Syscall Overhead in File Scanning & Hashing
**Learning:** Checking `path.is_file()` or `path.stat().st_size` on `pathlib.Path` objects prior to opening files introduces redundant filesystem `os.stat` system calls per file. Opening the file descriptor directly and calling `os.fstat(f.fileno())` avoids kernel path resolution roundtrips.
**Action:** When working on file-intensive scanning, indexing, or hashing loops, operate directly on open file handles or descriptors using `os.fstat` instead of path-based pre-checks.

## 2026-03-30 - High Call Overhead from Path.resolve() & Path Instantiation in Directories
**Learning:** Calling `Path.resolve()` per file inside scanning loops executes `realpath` syscalls for every parent component in the file path. In addition, using `Path` objects in `os.walk` loops generates hundreds of thousands of temporary object allocations (`Path._parse_path`, `Path.__init__`). Using `os.scandir` with `os.DirEntry` cached `stat()`, resolving `base_path` once, and computing relative paths via string slicing reduces scan runtime by >80% and call overhead by >90%.
**Action:** For directory traversal hot paths, use `os.scandir` with string paths, resolve root directories once, and use string slicing rather than calling `Path.resolve()` and `Path.relative_to()` inside loops.
