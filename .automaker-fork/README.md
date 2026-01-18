# AutoMaker Fork Tracking

This directory contains the infrastructure for tracking upstream changes and managing feature adoption.

## Structure

```
.automaker-fork/
├── config.json          # Fork configuration and tracking state
├── reports/             # Generated upstream analysis reports
│   └── YYYY-MM-DD.md   # Daily/weekly reports
├── changelog/           # Parsed upstream changelogs
└── adopted/
    └── manifest.json    # Record of adopted/rejected/deferred features
```

## Usage

Run the `/upstream-check` skill in Claude Code to:
1. Fetch latest upstream changes
2. Analyze new commits since last check
3. Generate a markdown report with recommendations

## Configuration

Edit `config.json` to customize:
- `tracking.checkFrequencyDays`: How often to check (default: 3)
- `analysis.skipPatterns`: Commit types to skip analysis
- `analysis.priorityPatterns`: Commit types to prioritize
- `analysis.watchPaths`: Directories you care most about

## Branch Strategy

- `main`: Your modified version
- `upstream`: Clean mirror of original repo (never modify directly)

## Adopting Features

1. Run `/upstream-check` to see what's new
2. Review the report in `reports/`
3. Cherry-pick or reimplement features you want
4. Record adoption in `adopted/manifest.json`
