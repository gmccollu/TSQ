#!/bin/bash
# Clean up TSQ directory - move non-essential files to archive

cd "$(dirname "$0")"

echo "Cleaning up TSQ directory..."
echo

# Create archive directory
mkdir -p archive

# === KEEP THESE (Essential Production Files) ===
# Core implementations
# - tsq_server.py (Streams server)
# - tsq_client.py (Streams client)
# - rust/ (Datagrams implementation)
# - compare_all.py (Main comparison script)
# - tsq_test_runner.py (Test automation)
# - kill_servers.py (Utility)
# - check_status.py (Utility)

# === MOVE TO ARCHIVE (Intermediate/Debug files) ===

echo "Moving intermediate files to archive/..."

# Old comparison scripts (superseded by compare_all.py)
mv compare_ntp_tsq.py archive/ 2>/dev/null
mv compare_all_three.py archive/ 2>/dev/null
mv compare_final.py archive/ 2>/dev/null
mv compare_three_ways.py archive/ 2>/dev/null
mv compare_on_client.sh archive/ 2>/dev/null

# Old datagram test scripts (superseded by compare_all.py)
mv run_datagram_test.py archive/ 2>/dev/null
mv test_datagrams_local.sh archive/ 2>/dev/null

# Deployment/build scripts (one-time use)
mv build_and_deploy_linux.py archive/ 2>/dev/null
mv build_on_linux.sh archive/ 2>/dev/null
mv build_quiche_tsq.sh archive/ 2>/dev/null
mv deploy_datagrams.sh archive/ 2>/dev/null
mv copy_client_binary.py archive/ 2>/dev/null
mv fix_client_binary.py archive/ 2>/dev/null

# Setup scripts (one-time use)
mv setup_ntp_servers.py archive/ 2>/dev/null
mv setup_passwordless_sudo.py archive/ 2>/dev/null
mv fix_ntp_servers.py archive/ 2>/dev/null
mv install_chrony_client.py archive/ 2>/dev/null
mv start_stream_servers.py archive/ 2>/dev/null

# Test/debug scripts
mv test_minimal.py archive/ 2>/dev/null
mv test_ntp_only.py archive/ 2>/dev/null
mv test_queries.py archive/ 2>/dev/null
mv test_tsq_client.py archive/ 2>/dev/null
mv analyze_measurements.py archive/ 2>/dev/null
mv measure_quic_overhead.py archive/ 2>/dev/null
mv check_ntp_service.py archive/ 2>/dev/null
mv check_ntp_status.py archive/ 2>/dev/null

# Datagram attempts with aioquic (didn't work)
mv tsq_server_datagram.py archive/ 2>/dev/null
mv tsq_client_datagram.py archive/ 2>/dev/null
mv tsq_client_datagram_fixed.py archive/ 2>/dev/null
mv tsq_client_datagram_v2.py archive/ 2>/dev/null

# Incomplete quiche Python wrapper attempt
mv tsq_server_quiche.py archive/ 2>/dev/null
mv quiche_wrapper.py archive/ 2>/dev/null

# Intermediate documentation (superseded by final docs)
mv DATAGRAM_STATUS.md archive/ 2>/dev/null
mv QUICHE_IMPLEMENTATION_PLAN.md archive/ 2>/dev/null
mv QUICHE_SETUP.md archive/ 2>/dev/null
mv README_QUICHE.md archive/ 2>/dev/null
mv BUILD_LINUX_INSTRUCTIONS.md archive/ 2>/dev/null
mv BUILD_ON_SERVER.sh archive/ 2>/dev/null
mv QUICK_BUILD_GUIDE.md archive/ 2>/dev/null
mv COMPARISON_GUIDE.md archive/ 2>/dev/null
mv HOW_TO_RUN_DATAGRAMS.md archive/ 2>/dev/null
mv TSQ_DATAGRAMS_READY.md archive/ 2>/dev/null
mv TROUBLESHOOTING.md archive/ 2>/dev/null
mv FINAL_COMPARISON.md archive/ 2>/dev/null
mv FINAL_RESULTS.md archive/ 2>/dev/null
mv TSQ_FINAL_STATUS.md archive/ 2>/dev/null

# Build script (keep install_quiche.sh for reference)

echo
echo "✓ Cleanup complete!"
echo
echo "=== KEPT (Essential Files) ==="
echo "Core Implementation:"
echo "  - tsq_server.py (Streams server)"
echo "  - tsq_client.py (Streams client)"
echo "  - rust/ (Datagrams implementation)"
echo
echo "Testing & Utilities:"
echo "  - compare_all.py (Complete comparison: NTP vs Streams vs Datagrams)"
echo "  - tsq_test_runner.py (Test automation)"
echo "  - kill_servers.py (Server cleanup)"
echo "  - check_status.py (Status checker)"
echo
echo "Documentation:"
echo "  - FINAL_SUMMARY.md (Complete summary)"
echo "  - draft-mccollum-ntp-tsq-*.xml/txt/html (IETF drafts)"
echo
echo "Setup:"
echo "  - install_quiche.sh (Quiche installation)"
echo "  - rust/build.sh (Build script)"
echo
echo "=== ARCHIVED ==="
echo "  - archive/ (intermediate files, old scripts, debug tools)"
echo
