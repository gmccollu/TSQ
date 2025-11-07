#!/bin/bash
# TSQ Log Analysis Script
# Analyzes systemd journal logs for TSQ server usage statistics

echo "=========================================="
echo "TSQ Server Usage Statistics"
echo "=========================================="
echo ""

# Check if running on server
if ! command -v journalctl &> /dev/null; then
    echo "Error: journalctl not found. This script must run on the server."
    exit 1
fi

# Get logs from both services
LOGS=$(sudo journalctl -u tsq-datagram -u tsq-stream --since "7 days ago" | grep "\[TSQ-LOG\]")

if [ -z "$LOGS" ]; then
    echo "No TSQ logs found in the last 7 days."
    exit 0
fi

echo "=== Overall Statistics (Last 7 Days) ==="
echo ""

# Total requests
TOTAL=$(echo "$LOGS" | wc -l)
echo "Total Requests: $TOTAL"

# Success vs Failure
SUCCESS=$(echo "$LOGS" | grep "status=SUCCESS" | wc -l)
FAILED=$(echo "$LOGS" | grep "status=FAILED" | wc -l)
SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($SUCCESS/$TOTAL)*100}")

echo "Successful: $SUCCESS ($SUCCESS_RATE%)"
echo "Failed: $FAILED"
echo ""

# By Protocol
DATAGRAM=$(echo "$LOGS" | grep "protocol=datagram" | wc -l)
STREAM=$(echo "$LOGS" | grep "protocol=stream" | wc -l)

echo "=== By Protocol ==="
echo "Datagrams: $DATAGRAM"
echo "Streams: $STREAM"
echo ""

# Unique clients
UNIQUE_IPS=$(echo "$LOGS" | grep -oP 'client=\K[0-9.]+' | sort -u | wc -l)
echo "=== Unique Clients ==="
echo "Unique IP Addresses: $UNIQUE_IPS"
echo ""

# Top 10 clients
echo "=== Top 10 Clients ==="
echo "$LOGS" | grep -oP 'client=\K[0-9.]+' | sort | uniq -c | sort -rn | head -10 | \
    awk '{printf "  %s: %d requests\n", $2, $1}'
echo ""

# Average processing time
echo "=== Performance ==="
AVG_PROCESSING=$(echo "$LOGS" | grep -oP 'processing_time=\K[0-9.]+' | \
    awk '{sum+=$1; count++} END {if(count>0) printf "%.3f", sum/count; else print "N/A"}')
echo "Average Processing Time: ${AVG_PROCESSING}ms"
echo ""

# Requests per day
echo "=== Daily Activity ==="
echo "$LOGS" | grep -oP '^\w+ \d+ \d+:\d+:\d+' | \
    awk '{print $1, $2}' | sort | uniq -c | \
    awk '{printf "  %s %2d: %d requests\n", $2, $3, $1}'
echo ""

# Common errors
ERRORS=$(echo "$LOGS" | grep "status=FAILED" | grep -oP 'error="\K[^"]+' | sort | uniq -c | sort -rn)
if [ ! -z "$ERRORS" ]; then
    echo "=== Common Errors ==="
    echo "$ERRORS" | awk '{printf "  %s (%d occurrences)\n", substr($0, index($0,$2)), $1}'
    echo ""
fi

echo "=========================================="
echo "Analysis Complete"
echo "=========================================="
