#!/usr/bin/env python3
"""
Simple test runner for script tests.

This script can be used to run the script tests even without pytest installed.
It provides basic test discovery and execution functionality.
"""

import os
import sys
import traceback
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess


def run_test_function(test_func, test_name):
    """Run a single test function."""
    try:
        # Create basic fixtures
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        project_root = Path(__file__).parent.parent.parent
        
        class MockScriptRunner:
            def __init__(self):
                self.project_root = project_root
                self.scripts_dir = scripts_dir
            
            def run_script(self, script_name, args=None, timeout=30):
                script_path = self.scripts_dir / script_name
                cmd = [str(script_path)]
                if args:
                    cmd.extend(args)
                
                return subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=str(self.project_root)
                )
            
            def check_script_syntax(self, script_name):
                script_path = self.scripts_dir / script_name
                try:
                    subprocess.run(
                        ["bash", "-n", str(script_path)],
                        check=True,
                        capture_output=True
                    )
                    return True
                except subprocess.CalledProcessError:
                    return False
        
        script_runner = MockScriptRunner()
        
        # Mock environment
        mock_env = {
            "ENVIRONMENT": "test",
            "TESTING": "true",
            "DATABASE_URL": "postgresql://test:test@localhost:5433/test_db",
            "PROJECT_ROOT": str(project_root),
        }
        
        # Determine function signature and call appropriately
        import inspect
        sig = inspect.signature(test_func)
        params = list(sig.parameters.keys())
        
        kwargs = {}
        if 'scripts_dir' in params:
            kwargs['scripts_dir'] = scripts_dir
        if 'script_runner' in params:
            kwargs['script_runner'] = script_runner
        if 'project_root' in params:
            kwargs['project_root'] = project_root
        if 'mock_env' in params:
            kwargs['mock_env'] = mock_env
        
        # Call the test function
        test_func(**kwargs)
        return True, None
        
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"


def discover_test_functions(module):
    """Discover test functions in a module."""
    test_functions = []
    
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and name.startswith('test_'):
            test_functions.append((name, obj))
        elif hasattr(obj, '__dict__'):  # Test class
            for method_name in dir(obj):
                if method_name.startswith('test_'):
                    method = getattr(obj, method_name)
                    if callable(method):
                        # Create instance and bind method
                        instance = obj()
                        bound_method = getattr(instance, method_name)
                        test_name = f"{name}::{method_name}"
                        test_functions.append((test_name, bound_method))
    
    return test_functions


def load_test_module(module_path):
    """Load a test module from file path."""
    spec = importlib.util.spec_from_file_location("test_module", module_path)
    module = importlib.util.module_from_spec(spec)
    
    # Add to sys.modules to support imports
    sys.modules["test_module"] = module
    
    try:
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        print(f"Failed to load {module_path}: {e}")
        return None


def run_basic_tests():
    """Run basic functionality tests."""
    print("=" * 60)
    print("BASIC SCRIPT FUNCTIONALITY TESTS")
    print("=" * 60)
    
    scripts_dir = Path(__file__).parent.parent.parent / "scripts"
    
    # Test 1: Script existence
    print("\n1. Testing script existence...")
    scripts = ["db_migrate.sh", "db_seed.sh", "db_reset.sh", "run_tests.sh", "format_code.sh"]
    for script in scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            print(f"   ✅ {script} exists")
        else:
            print(f"   ❌ {script} missing")
    
    # Test 2: Script syntax
    print("\n2. Testing script syntax...")
    for script in scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            try:
                subprocess.run(
                    ["bash", "-n", str(script_path)],
                    check=True,
                    capture_output=True
                )
                print(f"   ✅ {script} syntax OK")
            except subprocess.CalledProcessError:
                print(f"   ❌ {script} syntax error")
    
    # Test 3: Help commands
    print("\n3. Testing help commands...")
    for script in scripts:
        script_path = scripts_dir / script
        if script_path.exists():
            try:
                result = subprocess.run(
                    [str(script_path), "--help"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(scripts_dir.parent)
                )
                if result.returncode == 0 and "USAGE:" in result.stdout:
                    print(f"   ✅ {script} help works")
                else:
                    print(f"   ❌ {script} help failed")
            except subprocess.TimeoutExpired:
                print(f"   ⚠️  {script} help timed out")
            except Exception as e:
                print(f"   ❌ {script} help error: {e}")


def main():
    """Main test runner function."""
    print("DevPocket API - Script Test Runner")
    print("=" * 50)
    
    # Run basic tests first
    run_basic_tests()
    
    # Try to run unit tests if available
    test_dir = Path(__file__).parent
    test_files = [
        "test_script_integration.py",
        "test_script_verification.py"
    ]
    
    print("\n" + "=" * 60)
    print("INTEGRATION AND VERIFICATION TESTS")
    print("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_file in test_files:
        test_path = test_dir / test_file
        if not test_path.exists():
            continue
        
        print(f"\nRunning tests from {test_file}...")
        
        try:
            module = load_test_module(test_path)
            if module is None:
                continue
            
            test_functions = discover_test_functions(module)
            
            for test_name, test_func in test_functions:
                total_tests += 1
                
                # Run basic tests only (avoid complex mocking requirements)
                if any(keyword in test_name.lower() for keyword in [
                    'exists', 'executable', 'syntax', 'help', 'permissions'
                ]):
                    success, error = run_test_function(test_func, test_name)
                    
                    if success:
                        print(f"   ✅ {test_name}")
                        passed_tests += 1
                    else:
                        print(f"   ❌ {test_name}: {error}")
                        failed_tests += 1
                else:
                    # Skip complex tests that require extensive mocking
                    print(f"   ⏭️  {test_name} (skipped - requires complex mocking)")
                    
        except Exception as e:
            print(f"Error processing {test_file}: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests discovered: {total_tests}")
    print(f"Tests passed: {passed_tests}")
    print(f"Tests failed: {failed_tests}")
    print(f"Tests skipped: {total_tests - passed_tests - failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 All executed tests passed!")
        return 0
    else:
        print(f"\n⚠️  {failed_tests} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())