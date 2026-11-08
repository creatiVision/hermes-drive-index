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

## 2026-04-01 - O(N^2) Path.resolve() Syscalls in Boundary Deduplication Loops
**Learning:** In candidate deduplication loops, calling `Path.resolve()` repeatedly inside inner comparison functions (like `same_path` or `is_path_inside`) generates $O(N^2)$ filesystem system calls and `Path` object allocations. Pre-normalizing paths once before the loop and using string prefix matching (`child.startswith(parent_prefix)`) speeds up path containment checks by over 400x.
**Action:** Pre-normalize filesystem paths once before entering comparison loops, and use string prefix matching for path containment checks on normalized path strings.

## 2026-04-01 - dataclasses.asdict Reflection Overhead & Datetime Parsing in Hot Sort Loops
**Learning:** Calling `dataclasses.asdict()` on thousands of items in batch operations (e.g. duplicate detection or file classification) causes significant CPU overhead due to recursive field reflection and deepcopy semantics. Implementing explicit `.to_dict()` methods on dataclasses speeds up conversion by ~5x. Furthermore, comparing ISO 8601 date strings directly in sort keys eliminates redundant `datetime.fromisoformat(...).timestamp()` calls.
**Action:** Provide explicit `.to_dict()` methods on dataclasses used in high-volume collection results, and sort ISO 8601 timestamps lexicographically directly instead of parsing them into `datetime` objects in key callbacks.
## 2026-04-01 - Path Instantiation & Redundant Stat in Subtree Profiling
**Learning:** Instantiating `pathlib.Path` objects for file extension extraction (`Path(entry.name).suffix`) and child directory recursion (`Path(entry.path)`), along with redundant `node_path.exists()`/`node_path.is_dir()` checks before `os.scandir`, slows recursive subtree profiling down by ~42% (1.73x overhead). Using `os.path.splitext(entry_name)[1]`, string paths, and relying on `os.scandir`'s exception handling eliminates GC pressure and stat syscalls.
**Action:** Use string paths and `os.path` utilities in directory traversal and profiling loops rather than `pathlib.Path` wrapper objects.

## 2026-04-01 - os.path.commonpath List Allocation Overhead in Docker Mount Subpath Checking
**Learning:** Using `os.path.commonpath([norm_parent, norm_child]) == norm_parent` inside mount translation and validation loops incurs heavy overhead from allocating temporary list objects and splitting path strings into component arrays. Fast string prefix matching on normalized absolute paths (`norm_child == norm_parent or norm_child.startswith(norm_parent + os.sep)`) accelerates path containment checks by over 3x.
**Action:** When validating path containment in high-frequency mount translation or sandboxing routines, use normalized string prefix checking rather than `os.path.commonpath`.

## 2026-04-01 - Path Allocation & Relative-To Splitting in Document Structure Planning
**Learning:** In `plan_document_structure`, invoking `Path(f.path).relative_to(base).parts` and repeated list creations (`[t[0] for t in TOP_LEVEL_STRUCTURE]`) inside directory categorization loops creates severe object allocation overhead and slows file classification by over 11x. Pre-computing top-level directory names and path mappings as string sets/dicts, and checking relative paths via fast string slicing on `f.relative_path` or `base_prefix`, dramatically cuts classification latency.
**Action:** When scanning and sorting large directory trees into target hierarchies, pre-compute directory string paths upfront and use string slicing rather than instantiating `pathlib.Path` objects and calling `.relative_to().parts`.

## 2026-04-02 - Vector L2 Norm & Set Allocation Overhead in Semantic Content Routing
**Learning:** In `AutonomousContentRouter.propose_routing`, repeatedly computing `math.sqrt(sum(x * x))` for vector norms, allocating temporary `set()` objects for document types, entities, and extensions, and running multi-pass generator expressions inside the $O(N \times M)$ folder comparison loop creates severe CPU and GC overhead. Pre-computing folder purpose norms and sets once before the file loop and using a single-pass accumulator for dot-products in `_cosine_similarity` speeds up content routing proposals by ~3.15x.
**Action:** When performing $O(N \times M)$ candidate matching across semantic embeddings or categorical metadata, pre-compute target centroid L2 norms and lookup sets outside the comparison loop and compute candidate vector norms only once per candidate.

## 2026-11-08 - Path Allocation & Redundant Folder String Join in Downloads Organization
**Learning:** In `plan_download_organization`, repeatedly constructing `base / cat / year` and `dest_dir / f.name` using `pathlib.Path` objects and string conversions in the file iteration loop introduces heavy allocation overhead. Memoizing directory strings via a local `(category, year)` cache and using `os.path.join` yields a ~10x speedup.
**Action:** In file categorization and destination planning loops, resolve the base folder string once, memoize destination directory paths by category key, and construct target paths using `os.path.join`.
