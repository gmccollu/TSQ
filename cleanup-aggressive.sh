#!/bin/bash
# Aggressive cleanup - keep only essential files for public release

set -e

echo "=========================================="
echo "TSQ Repository - Aggressive Cleanup"
echo "=========================================="
echo ""
echo "This will remove ALL non-essential files."
echo "Only core code, docs, and latest IETF draft will remain."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create backup
mkdir -p .cleanup-aggressive
echo "Creating backup in .cleanup-aggressive/..."

# List of files to KEEP (everything else gets removed)
KEEP_FILES=(
    ".gitignore"
    "LICENSE"
    "README.md"
    "FINAL_BENCHMARK_RESULTS.md"
    "draft-mccollum-ntp-tsq-01.txt"
    "draft-mccollum-ntp-tsq-01.html"
    "draft-mccollum-ntp-tsq-01.xml"
    "tsq-stream-server.py"
    "tsq-stream-client.py"
    "rust/Cargo.toml"
    "rust/Cargo.lock"
    "rust/README.md"
    "rust/build.sh"
    "rust/build_linux.sh"
    "rust/src/server.rs"
    "rust/src/client.rs"
    "rust/src/adjtime.rs"
    "systemd/tsq-datagram.service"
    "systemd/tsq-stream.service"
    "systemd/INSTALL.md"
    "systemd/setup-services.sh"
)

# Get all tracked files
echo "Analyzing repository..."
ALL_FILES=$(git ls-files)

# Find files to remove
FILES_TO_REMOVE=()
for file in $ALL_FILES; do
    KEEP=false
    for keep_file in "${KEEP_FILES[@]}"; do
        if [ "$file" = "$keep_file" ]; then
            KEEP=true
            break
        fi
    done
    
    if [ "$KEEP" = false ]; then
        FILES_TO_REMOVE+=("$file")
    fi
done

# Show what will be removed
echo ""
echo "Files to be removed (${#FILES_TO_REMOVE[@]} total):"
echo "---"
for file in "${FILES_TO_REMOVE[@]}"; do
    echo "  - $file"
done
echo ""

read -p "Proceed with removal? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Remove files from git and backup
echo ""
echo "Removing files..."
for file in "${FILES_TO_REMOVE[@]}"; do
    # Create backup directory structure
    backup_dir=".cleanup-aggressive/$(dirname "$file")"
    mkdir -p "$backup_dir"
    
    # Copy to backup
    cp "$file" "$backup_dir/" 2>/dev/null || true
    
    # Remove from git
    git rm -f "$file" 2>/dev/null || true
done

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Kept ${#KEEP_FILES[@]} essential files:"
echo "  ✓ Core Rust implementation (3 files)"
echo "  ✓ Python stream implementation (2 files)"
echo "  ✓ Documentation (README, LICENSE, benchmarks)"
echo "  ✓ Latest IETF draft (3 formats)"
echo "  ✓ Systemd deployment files (4 files)"
echo "  ✓ Build configuration"
echo ""
echo "Removed ${#FILES_TO_REMOVE[@]} non-essential files"
echo "Backup saved in .cleanup-aggressive/"
echo ""
echo "Next steps:"
echo "  1. Review: git status"
echo "  2. Commit: git commit -m 'Clean repository - keep only essential files'"
echo "  3. Push: git push origin main"
echo ""
