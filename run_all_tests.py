#!/usr/bin/env python3
"""
Comprehensive test runner for Run My Pool application
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print(f"✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False

def main():
    """Run all test suites"""
    print("🚀 Run My Pool - Comprehensive Test Suite")
    print("=" * 60)
    
    # Ensure we're in the right directory
    os.chdir('/Users/asmith986/work/Development/runmypool')
    
    # Activate virtual environment and run tests
    python_cmd = "/Users/asmith986/work/Development/runmypool/venv/bin/python"
    pytest_cmd = f"{python_cmd} -m pytest"
    
    test_results = []
    
    # 1. Security Tests (custom runner)
    test_results.append(
        run_command(f"{python_cmd} test_security_runner.py", "Security Tests (Custom Runner)")
    )
    
    # 2. Authentication Tests
    test_results.append(
        run_command(f"{pytest_cmd} tests/test_auth.py -v", "Authentication Tests")
    )
    
    # 3. Security Feature Tests (pytest)
    test_results.append(
        run_command(f"{pytest_cmd} tests/test_security.py -v", "Security Feature Tests")
    )
    
    # 4. Model Tests
    test_results.append(
        run_command(f"{pytest_cmd} tests/test_models.py -v", "Model Tests")
    )
    
    # 5. Admin Tests
    test_results.append(
        run_command(f"{pytest_cmd} tests/test_admin.py -v", "Admin Tests")
    )
    
    # 6. Service Tests
    test_results.append(
        run_command(f"{pytest_cmd} tests/test_services.py -v", "Service Tests")
    )
    
    # 7. Integration Tests
    test_results.append(
        run_command(f"{pytest_cmd} tests/test_integration.py -v", "Integration Tests")
    )
    
    # 8. All Tests Together
    test_results.append(
        run_command(f"{pytest_cmd} tests/ -v", "All Pytest Tests")
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(test_results)
    total = len(test_results)
    failed = total - passed
    
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {(passed/total)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"\n⚠️  {failed} test suite(s) failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
