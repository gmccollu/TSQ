#!/bin/bash
# Cleanup script to remove development/internal files from public repo

set -e

echo "=========================================="
echo "TSQ Repository Cleanup"
echo "=========================================="
echo ""
echo "This will remove internal development files from the repository."
echo "Files will be deleted from git but kept locally (moved to .cleanup/)."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Create backup directory
mkdir -p .cleanup
echo "Creating backup in .cleanup/..."

# Remove entire archive directory
echo "Removing archive/..."
git rm -r archive/
mv archive/ .cleanup/ 2>/dev/null || true

# Remove internal documentation
echo "Removing internal documentation..."
git rm -f BENCHMARK_RESULTS.md
git rm -f BENCHMARK_SUMMARY_VISUAL.txt
git rm -f DOCUMENTATION_INDEX.md
git rm -f FILE_NAMING_CONVENTION.md
git rm -f FINAL_COMPARISON.txt
git rm -f FINAL_NTP_WG_REPORT.md
git rm -f FINAL_TEST_RESULTS.md
git rm -f SLEW_THRESHOLD_UPDATE.md
git rm -f TSQ_CLOCK_SYNC_COMPLETE.md

# Move to backup
mv BENCHMARK_RESULTS.md .cleanup/ 2>/dev/null || true
mv BENCHMARK_SUMMARY_VISUAL.txt .cleanup/ 2>/dev/null || true
mv DOCUMENTATION_INDEX.md .cleanup/ 2>/dev/null || true
mv FILE_NAMING_CONVENTION.md .cleanup/ 2>/dev/null || true
mv FINAL_COMPARISON.txt .cleanup/ 2>/dev/null || true
mv FINAL_NTP_WG_REPORT.md .cleanup/ 2>/dev/null || true
mv FINAL_TEST_RESULTS.md .cleanup/ 2>/dev/null || true
mv SLEW_THRESHOLD_UPDATE.md .cleanup/ 2>/dev/null || true
mv TSQ_CLOCK_SYNC_COMPLETE.md .cleanup/ 2>/dev/null || true

# Remove old test/deployment scripts
echo "Removing old test scripts..."
git rm -f test_adjtime.py
git rm -f test_ntp_sync.py
git rm -f test_nts_sync.py
git rm -f test_runner_requirements.txt
git rm -f deploy_adjtime_dg.py
git rm -f setup_nts_servers.py
git rm -f validate_accuracy.py
git rm -f cleanup.sh
git rm -f install_quiche.sh
git rm -f tsq_client.py

mv test_adjtime.py .cleanup/ 2>/dev/null || true
mv test_ntp_sync.py .cleanup/ 2>/dev/null || true
mv test_nts_sync.py .cleanup/ 2>/dev/null || true
mv test_runner_requirements.txt .cleanup/ 2>/dev/null || true
mv deploy_adjtime_dg.py .cleanup/ 2>/dev/null || true
mv setup_nts_servers.py .cleanup/ 2>/dev/null || true
mv validate_accuracy.py .cleanup/ 2>/dev/null || true
mv cleanup.sh .cleanup/ 2>/dev/null || true
mv install_quiche.sh .cleanup/ 2>/dev/null || true
mv tsq_client.py .cleanup/ 2>/dev/null || true

# Remove old IETF drafts (keep only latest -01)
echo "Removing old IETF drafts..."
git rm -f draft-mccollum-ntp-tsq-00.html
git rm -f draft-mccollum-ntp-tsq-00.txt
git rm -f draft-mccollum-ntp-tsq-00.xml
git rm -rf draft-mccollum-tsq/

mv draft-mccollum-ntp-tsq-00.* .cleanup/ 2>/dev/null || true
mv draft-mccollum-tsq/ .cleanup/ 2>/dev/null || true

# Update .gitignore to prevent re-adding
echo "Updating .gitignore..."
cat >> .gitignore << 'EOF'

# Cleanup directory
.cleanup/

# Additional internal files
DOCUMENTATION_INDEX.md
*_COMPARISON.txt
*_WG_REPORT.md
EOF

echo ""
echo "=========================================="
echo "Cleanup Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  - Removed archive/ directory"
echo "  - Removed internal documentation"
echo "  - Removed old test scripts"
echo "  - Removed old IETF draft versions"
echo "  - Kept only essential files"
echo ""
echo "Backup created in .cleanup/"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit: git commit -m 'Clean up repository for public release'"
echo "  3. Push: git push origin main"
echo ""
