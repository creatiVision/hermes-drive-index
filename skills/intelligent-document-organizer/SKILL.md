---
name: intelligent-document-organizer
description: Build a clean 4-6 top-level folder structure for messy Documents folders based on real content analysis.
---

# Intelligent Document Organizer

Tackles dense Documents directories with years of files. Analyzes content and filename patterns to propose 4-6 top-level categories:

1. `01-Projects`
2. `02-Finances`
3. `03-Personal`
4. `04-Reference`
5. `05-Archive`
6. `06-Inbox-Unsorted`

Generates consistent naming conventions (`{date}_{category}_{title}{ext}`) and requires explicit user approval before executing any file moves.

## Usage
- Run: `hermes-drive-index organize-documents <folder>` or tool `intelligent_document_organizer`.
