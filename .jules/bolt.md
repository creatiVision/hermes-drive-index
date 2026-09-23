# Bolt's Performance Journal

## 2026-03-29 - Path Stat Syscall Overhead in File Scanning & Hashing
**Learning:** Checking `path.is_file()` or `path.stat().st_size` on `pathlib.Path` objects prior to opening files introduces redundant filesystem `os.stat` system calls per file. Opening the file descriptor directly and calling `os.fstat(f.fileno())` avoids kernel path resolution roundtrips.
**Action:** When working on file-intensive scanning, indexing, or hashing loops, operate directly on open file handles or descriptors using `os.fstat` instead of path-based pre-checks.

## 2026-03-30 - Path Instantiation & Uncompiled Regex in Duplicate Detector Loops
**Learning:** Repeatedly creating `pathlib.Path` objects and passing uncompiled regex strings to `re.search` / `re.sub` inside file list iteration loops (such as `detect_duplicates` and `normalize_stem`) creates massive GC and re-compilation overhead, slowing execution down by up to 4x.
**Action:** Pre-compile patterns at module level using `re.compile(..., re.IGNORECASE)` and use `os.path.splitext` / `os.path.basename` inside hot scanning loops.

## 2026-03-31 - Path Instantiations and Unconditional Variable Formatting in Rule Engines
**Learning:** Instantiating `pathlib.Path` objects (`Path().parent`, `Path().stem`, `Path().suffix`) and performing unconditional `strftime` date formatting inside rule condition and template resolution loops per file slows evaluation down by 2-5x. Using `os.path.dirname`, `os.path.splitext`, and checking placeholder existence before formatting eliminates object allocation and unnecessary string manipulation.
**Action:** In condition evaluation and template resolution loops, rely on `os.path` functions and check placeholder presence (`if "{year}" in template:`) before invoking string formatting.

## 2026-04-01 - Path Instantiation & Redundant Stat in Subtree Profiling
**Learning:** Instantiating `pathlib.Path` objects for file extension extraction (`Path(entry.name).suffix`) and child directory recursion (`Path(entry.path)`), along with redundant `node_path.exists()`/`node_path.is_dir()` checks before `os.scandir`, slows recursive subtree profiling down by ~42% (1.73x overhead). Using `os.path.splitext(entry_name)[1]`, string paths, and relying on `os.scandir`'s exception handling eliminates GC pressure and stat syscalls.
**Action:** Use string paths and `os.path` utilities in directory traversal and profiling loops rather than `pathlib.Path` wrapper objects.
