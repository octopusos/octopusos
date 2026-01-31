# Task #16: Quick Commands Reference

## One-Line Commands

### Run Full Verification
```bash
./scripts/verify_mode_100_completion.sh
```

### View Latest Report
```bash
cat outputs/mode_system_100_verification/reports/MODE_SYSTEM_100_VERIFICATION_REPORT_*.txt | tail -100
```

### Check Pass/Fail Only
```bash
./scripts/verify_mode_100_completion.sh 2>&1 | grep -E "(Total|Passed|Failed|Pass Rate)"
```

### Run Silently (Exit Code Only)
```bash
./scripts/verify_mode_100_completion.sh > /dev/null 2>&1 && echo "✅ PASS" || echo "❌ FAIL"
```

## Individual Components

### Run Unit Tests Only
```bash
pytest tests/unit/mode/test_mode_policy.py -v     # 41 tests
pytest tests/unit/mode/test_mode_alerts.py -v     # 24 tests
```

### Run Gates Only
```bash
python3 scripts/gates/gm1_mode_non_impl_diff_denied.py
python3 scripts/gates/gm2_mode_impl_requires_diff.py
python3 scripts/gates/gm3_mode_policy_enforcement.py
python3 scripts/gates/gm4_mode_alert_integration.py
```

### Run All Gates
```bash
for gate in scripts/gates/gm*.py; do python3 "$gate" || exit 1; done
```

## File Checks

### Check Core Files Exist
```bash
ls -lh agentos/core/mode/mode_policy.py
ls -lh agentos/core/mode/mode_alerts.py
ls -lh agentos/webui/api/mode_monitoring.py
```

### Check Config Files
```bash
ls -lh configs/mode/*.json
```

### Validate JSON Configs
```bash
for f in configs/mode/*.json; do python3 -m json.tool "$f" > /dev/null && echo "✅ $f" || echo "❌ $f"; done
```

## Test Verification

### Count Tests
```bash
pytest tests/unit/mode/test_mode_policy.py --collect-only -q | grep -E "^tests" | wc -l
pytest tests/unit/mode/test_mode_alerts.py --collect-only -q | grep -E "^tests" | wc -l
```

### Run Tests with Coverage
```bash
pytest tests/unit/mode/ --cov=agentos.core.mode --cov-report=term-missing
```

### Run Tests Verbosely
```bash
pytest tests/unit/mode/ -vv -s
```

## Import Tests

### Test Python Imports
```bash
python3 -c "from agentos.core.mode.mode_policy import ModePolicy; print('✅ mode_policy')"
python3 -c "from agentos.core.mode.mode_alerts import get_alert_aggregator; print('✅ mode_alerts')"
python3 -c "from agentos.webui.api import mode_monitoring; print('✅ mode_monitoring')"
```

### Test Mode Functions
```bash
python3 -c "from agentos.core.mode import get_mode; m = get_mode('implementation'); print(f'✅ allows_commit={m.allows_commit()}')"
```

## Report Management

### List All Reports
```bash
ls -lht outputs/mode_system_100_verification/reports/
```

### View Specific Report Section
```bash
cat outputs/mode_system_100_verification/reports/MODE_SYSTEM_100_VERIFICATION_REPORT_*.txt | grep -A 20 "Phase 1"
```

### Count Passed Checks
```bash
cat outputs/mode_system_100_verification/reports/MODE_SYSTEM_100_VERIFICATION_REPORT_*.txt | grep -c "PASS"
```

### Clean Old Reports
```bash
rm outputs/mode_system_100_verification/reports/*.txt
```

## Debugging

### Run Script with Debug Output
```bash
bash -x scripts/verify_mode_100_completion.sh 2>&1 | tee debug.log
```

### Check Script Syntax
```bash
bash -n scripts/verify_mode_100_completion.sh && echo "✅ Syntax OK"
```

### Test Individual Check
```bash
python3 -c "
import sys
sys.path.insert(0, '.')
from agentos.core.mode.mode_policy import ModePolicy
policy = ModePolicy()
impl = policy.get_permissions('implementation')
print(f'implementation.allows_commit = {impl.allows_commit}')
print(f'implementation.allows_diff = {impl.allows_diff}')
"
```

## CI/CD Integration

### GitHub Actions Snippet
```yaml
- name: Verify Mode System
  run: ./scripts/verify_mode_100_completion.sh
```

### GitLab CI Snippet
```yaml
verify_mode:
  script:
    - ./scripts/verify_mode_100_completion.sh
  artifacts:
    when: always
    paths:
      - outputs/mode_system_100_verification/reports/
```

### Jenkins Snippet
```groovy
stage('Verify Mode System') {
    steps {
        sh './scripts/verify_mode_100_completion.sh'
    }
}
```

## Performance

### Time Script Execution
```bash
time ./scripts/verify_mode_100_completion.sh
```

### Profile Test Execution
```bash
pytest tests/unit/mode/ --durations=10
```

## Statistics

### Count Lines of Code
```bash
wc -l scripts/verify_mode_100_completion.sh
wc -l agentos/core/mode/*.py
wc -l tests/unit/mode/*.py
```

### Count Files Verified
```bash
grep -c "exists" outputs/mode_system_100_verification/reports/MODE_SYSTEM_100_VERIFICATION_REPORT_*.txt
```

### Show Verification Summary
```bash
./scripts/verify_mode_100_completion.sh 2>&1 | tail -30
```

## Documentation

### View All Docs
```bash
ls -lh TASK16_*.md
```

### Quick Start Guide
```bash
cat TASK16_快速参考.md
```

### Full Documentation
```bash
cat TASK16_MODE_100_VERIFICATION_GUIDE.md
```

### Deliverables List
```bash
cat TASK16_DELIVERABLES_MANIFEST.md
```

## Common Workflows

### Daily Verification
```bash
# Quick daily check
./scripts/verify_mode_100_completion.sh && echo "✅ Daily check passed"
```

### Pre-Commit Check
```bash
# Before committing changes
./scripts/verify_mode_100_completion.sh || { echo "❌ Fix issues before commit"; exit 1; }
```

### Pre-Merge Verification
```bash
# Before merging PR
./scripts/verify_mode_100_completion.sh 2>&1 | tee pre-merge-verification.log
```

### Full System Check
```bash
# Complete verification with all details
./scripts/verify_mode_100_completion.sh 2>&1 | tee full-verification-$(date +%Y%m%d).log
cat full-verification-*.log | tail -50
```

## Troubleshooting Commands

### Check Prerequisites
```bash
which python3 && echo "✅ python3"
which pytest && echo "✅ pytest"
which git && echo "✅ git"
```

### Check Python Version
```bash
python3 --version
```

### Check Pytest Installation
```bash
pytest --version
```

### Check Repository Status
```bash
git status
git log --oneline -5
```

### Verify File Permissions
```bash
ls -l scripts/verify_mode_100_completion.sh | grep -q "x" && echo "✅ Executable" || echo "❌ Not executable"
```

### Fix Permissions
```bash
chmod +x scripts/verify_mode_100_completion.sh
```

## Emergency Commands

### Quick Fix Script
```bash
# If script not executable
chmod +x scripts/verify_mode_100_completion.sh

# If reports directory missing
mkdir -p outputs/mode_system_100_verification/reports

# If Python path issues
export PYTHONPATH="$(pwd):$PYTHONPATH"
```

### Force Clean and Retry
```bash
rm -rf outputs/mode_system_100_verification/
./scripts/verify_mode_100_completion.sh
```

## Useful Aliases

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Quick verification
alias verify-mode='./scripts/verify_mode_100_completion.sh'

# View latest report
alias mode-report='cat outputs/mode_system_100_verification/reports/MODE_SYSTEM_100_VERIFICATION_REPORT_*.txt | tail -100'

# Run mode tests
alias mode-tests='pytest tests/unit/mode/ -v'

# Run mode gates
alias mode-gates='for gate in scripts/gates/gm*.py; do python3 "$gate"; done'
```

## Quick Status Check

One command to rule them all:

```bash
echo "=== Mode System Status ===" && \
./scripts/verify_mode_100_completion.sh 2>&1 | grep -E "(Total|Passed|Failed|Pass Rate|Overall|Status)" && \
echo "=== Latest Report ===" && \
ls -lh outputs/mode_system_100_verification/reports/ | tail -1
```

---

**Last Updated**: 2026-01-30
**Version**: 1.0.0
**Status**: ✅ Ready to Use
