#!/usr/bin/env python3
"""
Test script to debug why connection name is not being logged
"""

import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..'))

def analyze_manager_init():
    """Analyze EbicsManager initialization"""
    print("Analyzing EbicsManager initialization...")
    
    manager_path = os.path.join(os.path.dirname(__file__), '../../ebics_manager.py')
    
    with open(manager_path, 'r') as f:
        lines = f.readlines()
    
    # Find __init__ method
    in_init = False
    init_lines = []
    for i, line in enumerate(lines, 1):
        if 'def __init__(self' in line:
            in_init = True
        elif in_init and line.strip() and not line.startswith(' '):
            break
        elif in_init:
            init_lines.append(f"  Line {i}: {line.rstrip()}")
    
    print("  __init__ method:")
    for line in init_lines[:10]:  # Show first 10 lines
        print(line)
    
    # Check if connection_name is stored
    content = ''.join(lines)
    if 'self.connection_name = connection_name' in content:
        print("  ✅ connection_name is stored in __init__")
    else:
        print("  ❌ connection_name is NOT stored in __init__")

def analyze_execute_ebics_order():
    """Analyze execute_ebics_order function"""
    print("\nAnalyzing execute_ebics_order function...")
    
    manager_path = os.path.join(os.path.dirname(__file__), '../../ebics_manager.py')
    
    with open(manager_path, 'r') as f:
        lines = f.readlines()
    
    # Find execute_ebics_order
    in_func = False
    func_lines = []
    for i, line in enumerate(lines, 1):
        if 'def execute_ebics_order(' in line:
            in_func = True
        elif in_func and line.strip() and not line.startswith(' '):
            break
        elif in_func:
            func_lines.append(f"  Line {i}: {line.rstrip()}")
    
    print("  execute_ebics_order function:")
    for line in func_lines[:15]:  # Show first 15 lines
        print(line)
    
    # Check if EbicsManager is created with connection name
    func_content = ''.join([l.split(': ', 1)[1] for l in func_lines if ': ' in l])
    if 'EbicsManager(connection)' in func_content:
        print("  ✅ EbicsManager created with connection name")
    else:
        print("  ❌ EbicsManager NOT created with connection name")

def analyze_log_operation():
    """Analyze _log_operation method"""
    print("\nAnalyzing _log_operation method...")
    
    manager_path = os.path.join(os.path.dirname(__file__), '../../ebics_manager.py')
    
    with open(manager_path, 'r') as f:
        lines = f.readlines()
    
    # Find _log_operation
    in_func = False
    func_lines = []
    for i, line in enumerate(lines, 1):
        if 'def _log_operation(' in line:
            in_func = True
        elif in_func and line.strip() and not line.startswith(' ') and not line.startswith('    def'):
            break
        elif in_func:
            func_lines.append(f"  Line {i}: {line.rstrip()}")
    
    print("  _log_operation method (key lines):")
    for line in func_lines:
        if 'connection_name' in line.lower() or 'connection' in line.lower():
            print(line)
    
    # Check how connection_name is retrieved
    func_content = ''.join([l.split(': ', 1)[1] if ': ' in l else l for l in func_lines])
    if 'connection_name = self.connection_name' in func_content:
        print("  ✅ connection_name retrieved from self.connection_name")
    else:
        print("  ❌ connection_name NOT properly retrieved")

def check_control_panel_calls():
    """Check how control panel calls the manager"""
    print("\nAnalyzing control panel calls...")
    
    js_path = os.path.join(os.path.dirname(__file__), '../../page/ebics_control_panel/ebics_control_panel.js')
    
    with open(js_path, 'r') as f:
        content = f.read()
    
    # Find execute_action
    import re
    pattern = r'execute_action.*?\{.*?frappe\.call.*?\}.*?\}'
    matches = re.findall(pattern, content, re.DOTALL)
    
    if matches:
        for match in matches[:1]:  # Show first match
            if 'connection:' in match:
                # Extract the connection line
                lines = match.split('\n')
                for line in lines:
                    if 'connection:' in line:
                        print(f"  Found: {line.strip()}")
                        if 'this.connection.name' in line:
                            print("  ✅ Passing this.connection.name")
                        else:
                            print("  ❌ Not passing correct connection name")
                        break

def simulate_call_chain():
    """Simulate the call chain to identify where connection is lost"""
    print("\nSimulating call chain:")
    print("  1. Control Panel: execute_action('generate_keys')")
    print("     → args = { connection: this.connection.name }")
    print("  2. Server: execute_ebics_order(connection='test', action='GENERATE_KEYS')")
    print("     → manager = EbicsManager(connection)")
    print("  3. EbicsManager.__init__(connection_name='test')")
    print("     → self.connection_name = connection_name")
    print("  4. EbicsManager.execute_order('GENERATE_KEYS')")
    print("     → self._log_operation(action, result)")
    print("  5. EbicsManager._log_operation()")
    print("     → connection_name = self.connection_name")
    print("     → log['connection'] = connection_name")
    
    print("\n  Checking if 'this.connection' is set...")
    
    js_path = os.path.join(os.path.dirname(__file__), '../../page/ebics_control_panel/ebics_control_panel.js')
    with open(js_path, 'r') as f:
        content = f.read()
    
    # Check if connection is loaded
    if 'this.connection = r.message;' in content:
        print("  ✅ this.connection is set from frappe.client.get")
    else:
        print("  ❌ this.connection might not be set")
    
    # Check if there's a guard
    if '!this.connection || !this.connection.name' in content:
        print("  ✅ Guard clause to check connection exists")
    else:
        print("  ⚠️  No guard clause for missing connection")

def main():
    """Run all analyses"""
    print("=" * 60)
    print("EBICS Connection Name Logging Debug")
    print("=" * 60)
    
    analyze_manager_init()
    analyze_execute_ebics_order()
    analyze_log_operation()
    check_control_panel_calls()
    simulate_call_chain()
    
    print("\n" + "=" * 60)
    print("Hypothesis: The connection might not be selected when")
    print("actions are executed from the control panel.")
    print("=" * 60)

if __name__ == "__main__":
    main()