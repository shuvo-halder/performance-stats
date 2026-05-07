# Testing Guide

**Server Stats Monitor v2.0.0** - Comprehensive Testing Framework

---

## Table of Contents

- [Quick Tests](#quick-tests)
- [Unit Tests](#unit-tests)
- [Integration Tests](#integration-tests)
- [Manual Testing](#manual-testing)
- [Performance Testing](#performance-testing)
- [CI/CD Setup](#cicd-setup)

---

## Quick Tests

### Basic Functionality Test

```bash
#!/bin/bash
# Run basic tests

echo "=== Quick Functionality Tests ==="

# Test 1: Script execution
echo "Test 1: Script execution..."
./server-stats.sh > /dev/null 2>&1 && echo "✓ PASS" || echo "✗ FAIL"

# Test 2: JSON output
echo "Test 2: JSON output..."
./server-stats.sh --json 2>/dev/null | grep -q "version" && echo "✓ PASS" || echo "✗ FAIL"

# Test 3: Help message
echo "Test 3: Help message..."
./server-stats.sh --help 2>/dev/null | grep -q "USAGE" && echo "✓ PASS" || echo "✗ FAIL"

# Test 4: Version check
echo "Test 4: Version check..."
./server-stats.sh --version 2>/dev/null | grep -q "2.0.0" && echo "✓ PASS" || echo "✗ FAIL"

# Test 5: Verbose mode
echo "Test 5: Verbose mode..."
./server-stats.sh --verbose 2>&1 | grep -q "DEBUG" && echo "✓ PASS" || echo "✗ FAIL"

echo "=== Quick Tests Complete ==="
```

---

## Unit Tests

### Test Script: `test-unit.sh`

```bash
#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${SCRIPT_DIR}/server-stats.sh"
TESTS_PASSED=0
TESTS_FAILED=0

# Colors
GREEN="\e[32m"
RED="\e[31m"
YELLOW="\e[33m"
RESET="\e[0m"

# Test framework
assert_command() {
    local test_name="$1"
    local cmd="$2"
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${RESET}: $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${RESET}: $test_name"
        ((TESTS_FAILED++))
    fi
}

assert_output() {
    local test_name="$1"
    local cmd="$2"
    local expected="$3"
    
    if eval "$cmd" 2>/dev/null | grep -q "$expected"; then
        echo -e "${GREEN}✓ PASS${RESET}: $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${RESET}: $test_name"
        ((TESTS_FAILED++))
    fi
}

echo "=========================================="
echo "     SERVER STATS MONITOR UNIT TESTS"
echo "=========================================="
echo ""

# Test 1: Script exists and is executable
echo "Test Group: Basic Checks"
echo "---"
assert_command "Script exists" "[ -f '$SCRIPT' ]"
assert_command "Script is executable" "[ -x '$SCRIPT' ]"
assert_command "Script is readable" "[ -r '$SCRIPT' ]"
echo ""

# Test 2: Script syntax
echo "Test Group: Syntax Validation"
echo "---"
if command -v shellcheck &> /dev/null; then
    assert_command "ShellCheck validation" "shellcheck -x '$SCRIPT'"
else
    echo -e "${YELLOW}⊘ SKIP${RESET}: ShellCheck not installed"
fi
assert_command "Bash syntax check" "bash -n '$SCRIPT'"
echo ""

# Test 3: Help and version
echo "Test Group: Help & Version"
echo "---"
assert_output "Help message shows usage" "$SCRIPT --help" "USAGE"
assert_output "Version shows correct number" "$SCRIPT --version" "2.0.0"
assert_output "Help shows options" "$SCRIPT --help" "OPTIONS"
echo ""

# Test 4: Basic execution
echo "Test Group: Basic Execution"
echo "---"
assert_command "Script runs without args" "$SCRIPT > /dev/null 2>&1"
assert_command "JSON output works" "$SCRIPT --json 2>/dev/null | grep -q version"
assert_command "Verbose mode works" "$SCRIPT --verbose 2>&1 | head -20 > /dev/null"
echo ""

# Test 5: Configuration
echo "Test Group: Configuration"
echo "---"
assert_command "Config file exists" "[ -f '$SCRIPT_DIR/server-stats.conf' ]"
assert_command "Config file is readable" "[ -r '$SCRIPT_DIR/server-stats.conf' ]"
assert_command "Config syntax is valid" "bash -n '$SCRIPT_DIR/server-stats.conf'"
echo ""

# Test 6: Command-line arguments
echo "Test Group: CLI Arguments"
echo "---"
assert_command "CPU threshold option" "$SCRIPT -c 75 > /dev/null 2>&1"
assert_command "Memory threshold option" "$SCRIPT -m 80 > /dev/null 2>&1"
assert_command "Disk threshold option" "$SCRIPT -d 85 > /dev/null 2>&1"
assert_command "Services option" "$SCRIPT -s nginx,postgres > /dev/null 2>&1"
assert_command "JSON output option" "$SCRIPT -j > /dev/null 2>&1"
echo ""

# Test 7: Metrics collection
echo "Test Group: Metrics Collection"
echo "---"
assert_output "CPU info available" "$SCRIPT" "CPU"
assert_output "Memory info available" "$SCRIPT" "Memory"
assert_output "Disk info available" "$SCRIPT" "Disk"
assert_output "Network info available" "$SCRIPT" "Network"
echo ""

# Summary
echo "=========================================="
echo "     TEST SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${RESET}"
echo -e "${RED}Failed: $TESTS_FAILED${RESET}"
echo "=========================================="

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${RESET}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${RESET}"
    exit 1
fi
```

---

## Integration Tests

### Test Script: `test-integration.sh`

```bash
#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="${SCRIPT_DIR}/server-stats.sh"
TEMP_DIR=$(mktemp -d)
TESTS_PASSED=0
TESTS_FAILED=0

GREEN="\e[32m"
RED="\e[31m"
RESET="\e[0m"

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

assert_test() {
    local test_name="$1"
    local cmd="$2"
    
    if eval "$cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${RESET} $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗${RESET} $test_name"
        ((TESTS_FAILED++))
    fi
}

echo "=========================================="
echo "     INTEGRATION TESTS"
echo "=========================================="
echo ""

# Test 1: JSON output parsing
echo "Test Group: JSON Output"
echo "---"
assert_test "JSON is valid" "$SCRIPT --json 2>/dev/null | python3 -m json.tool > /dev/null"
OUTPUT=$($SCRIPT --json 2>/dev/null)
assert_test "JSON contains timestamp" "echo '$OUTPUT' | grep -q timestamp"
assert_test "JSON contains hostname" "echo '$OUTPUT' | grep -q hostname"
assert_test "JSON contains version" "echo '$OUTPUT' | grep -q version"
assert_test "JSON contains cpu metrics" "echo '$OUTPUT' | grep -q cpu"
assert_test "JSON contains memory metrics" "echo '$OUTPUT' | grep -q memory"
echo ""

# Test 2: Output file generation
echo "Test Group: File Output"
echo "---"
OUTPUT_FILE="${TEMP_DIR}/output.txt"
assert_test "Output to file" "$SCRIPT -o '$OUTPUT_FILE' 2>/dev/null && [ -f '$OUTPUT_FILE' ]"
assert_test "Output file has content" "[ -s '$OUTPUT_FILE' ]"
assert_test "Output file contains header" "grep -q 'SERVER PERFORMANCE' '$OUTPUT_FILE'"
echo ""

# Test 3: Lock file mechanism
echo "Test Group: Lock File"
echo "---"
assert_test "Lock file created" "$SCRIPT > /dev/null 2>&1 && sleep 1"
# Note: Lock file cleanup happens after script finishes
assert_test "Lock file released" "sleep 2 && [ ! -f /tmp/server-stats.sh.lock ] 2>/dev/null || true"
echo ""

# Test 4: Threshold configuration
echo "Test Group: Thresholds"
echo "---"
OUTPUT=$($SCRIPT -c 50 -m 60 -d 70 2>/dev/null)
assert_test "Custom CPU threshold applied" "echo '$OUTPUT' | grep -q CPU"
assert_test "Custom memory threshold applied" "echo '$OUTPUT' | grep -q Memory"
assert_test "Custom disk threshold applied" "echo '$OUTPUT' | grep -q Disk"
echo ""

# Test 5: Service monitoring
echo "Test Group: Service Monitoring"
echo "---"
OUTPUT=$($SCRIPT -s nginx,docker 2>/dev/null)
assert_test "Service monitoring output present" "echo '$OUTPUT' | grep -q 'Service'"
echo ""

# Summary
echo "=========================================="
echo "     INTEGRATION TEST SUMMARY"
echo "=========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${RESET}"
echo -e "${RED}Failed: $TESTS_FAILED${RESET}"
echo "=========================================="

exit $([ $TESTS_FAILED -eq 0 ] && echo 0 || echo 1)
```

---

## Manual Testing

### Basic Functionality Checklist

- [ ] Script runs without errors: `./server-stats.sh`
- [ ] Help displays: `./server-stats.sh --help`
- [ ] Version shows: `./server-stats.sh --version`
- [ ] JSON output valid: `./server-stats.sh --json | jq .`
- [ ] Output file created: `./server-stats.sh -o test.txt && [ -f test.txt ]`
- [ ] Custom thresholds work: `./server-stats.sh -c 75 -m 80 -d 85`
- [ ] Service filtering works: `./server-stats.sh -s nginx,docker`
- [ ] Verbose output shows debug messages: `./server-stats.sh --verbose 2>&1 | grep DEBUG`

### Output Validation Checklist

- [ ] CPU information displayed
- [ ] Memory information displayed
- [ ] Disk information displayed
- [ ] Network information displayed
- [ ] Service status shown
- [ ] Top processes listed
- [ ] Security information present
- [ ] Proper color coding applied
- [ ] No error messages

### Configuration Testing

- [ ] Configuration file loaded correctly
- [ ] Thresholds from config applied
- [ ] Services list from config used
- [ ] Alert settings respected

---

## Performance Testing

### Execute and Measure

```bash
#!/bin/bash

echo "Performance Testing"
echo "===================="
echo ""

# Time the script
echo "Execution Time Test:"
time ./server-stats.sh > /dev/null

# CPU usage
echo ""
echo "CPU Usage Test:"
time -p ./server-stats.sh > /dev/null 2>&1

# Memory usage (with /usr/bin/time)
echo ""
echo "Memory Usage Test:"
/usr/bin/time -v ./server-stats.sh > /dev/null 2>&1

# JSON generation time
echo ""
echo "JSON Generation Time:"
time ./server-stats.sh --json > /dev/null

# Load testing (10 runs)
echo ""
echo "Load Test (10 sequential runs):"
for i in {1..10}; do
    echo -n "Run $i... "
    time -f "%es" ./server-stats.sh > /dev/null 2>&1
done
```

---

## CI/CD Setup

### GitHub Actions Workflow

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y shellcheck
    
    - name: ShellCheck
      run: shellcheck -x server-stats.sh
    
    - name: Bash syntax check
      run: bash -n server-stats.sh
    
    - name: Run unit tests
      run: bash test-unit.sh
    
    - name: Run integration tests
      run: bash test-integration.sh
    
    - name: Test basic execution
      run: |
        ./server-stats.sh --version
        ./server-stats.sh --help
        ./server-stats.sh > /dev/null
```

---

## Test Execution

### Run All Tests

```bash
#!/bin/bash

echo "Running all tests..."
echo ""

# Unit tests
echo "Running unit tests..."
bash test-unit.sh || exit 1

echo ""
echo "Running integration tests..."
bash test-integration.sh || exit 1

echo ""
echo "✓ All tests passed!"
```

### Test Coverage Tracking

```bash
# Identify untested code paths
bash -x server-stats.sh 2>&1 | tee coverage.log
```

---

## Expected Test Results

All tests should pass with output similar to:

```
==========================================
     SERVER STATS MONITOR UNIT TESTS
==========================================

Test Group: Basic Checks
---
✓ PASS: Script exists and is executable
✓ PASS: Script is executable
✓ PASS: Script is readable

Test Group: Syntax Validation
---
✓ PASS: ShellCheck validation
✓ PASS: Bash syntax check

Test Group: Help & Version
---
✓ PASS: Help message shows usage
✓ PASS: Version shows correct number
✓ PASS: Help shows options

... (more tests) ...

==========================================
     TEST SUMMARY
==========================================
Passed: 35
Failed: 0
==========================================
✓ All tests passed!
```

---

## Troubleshooting Tests

### Test Fails: "ShellCheck not installed"

```bash
sudo apt-get install shellcheck  # Debian/Ubuntu
sudo yum install shellcheck      # RHEL/CentOS
```

### Test Fails: "JSON parsing"

```bash
# Install Python JSON tools
sudo apt-get install python3

# Or use jq
sudo apt-get install jq
```

### Test Fails: "systemctl not available"

Tests may fail in containers. Use `--rm -v /sys:/sys:ro` when running in Docker.

---

## Contributing Tests

When adding new features:

1. Add unit tests for the function
2. Add integration tests for behavior
3. Update manual test checklist
4. Run full test suite before PR
5. Ensure CI/CD passes

---

**Last Updated:** 2026-05-07  
**Version:** 2.0.0
