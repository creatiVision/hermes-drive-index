# Bolt's Performance Journal

## 2026-03-30 - Eager List Comprehensions in Rule Engines Cause Redundant Work
**Learning:** In rule evaluation engines, constructing condition results with eager list comprehensions `[eval(c) for c in conds]` forces evaluation of all downstream conditions (such as expensive text string/regex matching on document contents) even when the rule fails on the first condition. Using generator expressions with `all()` or `any()` enables short-circuiting. Furthermore, in keyword matching, lazy evaluation of document content search prevents unnecessary string lowercasing/scanning when scope is `filename` or when `both` matches on filename first.
**Action:** When designing condition matching or rule engines, use generator expressions (`all(...)`/`any(...)`) for short-circuit evaluation and order/lazy-evaluate expensive properties (like extracted document text).

## 2026-03-29 - Path Stat Syscall Overhead in File Scanning & Hashing
**Learning:** Checking `path.is_file()` or `path.stat().st_size` on `pathlib.Path` objects prior to opening files introduces redundant filesystem `os.stat` system calls per file. Opening the file descriptor directly and calling `os.fstat(f.fileno())` avoids kernel path resolution roundtrips.
**Action:** When working on file-intensive scanning, indexing, or hashing loops, operate directly on open file handles or descriptors using `os.fstat` instead of path-based pre-checks.
