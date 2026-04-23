// SPDX-License-Identifier: CC-BY-NC-SA-4.0
// Copyright (c) 2026 Sean O'Connor
//
// Test-only fixture: deliberately truncated expression on line 6
// yields an OpenSCAD parser error with a line number the error-state
// UI can render. Do not include in `models/` — this file should
// never ship to users (CI filters it by location).
width = 10;
cube(width
