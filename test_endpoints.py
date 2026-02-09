#!/usr/bin/env python3
"""
Test if contact management endpoints are working
"""

import requests
import json

BASE_URL = "http://localhost:8080"

print("\n" + "="*70)
print("CONTACT MANAGEMENT ENDPOINT CHECKER")
print("="*70 + "\n")

endpoints = [
    ('GET', '/api/contacts/list', 'List contacts'),
    ('GET', '/api/contacts/1', 'Get contact detail'),
    ('POST', '/api/contacts', 'Create contact'),
    ('PUT', '/api/contacts/1', 'Update contact'),
    ('DELETE', '/api/contacts/1', 'Delete contact'),
    ('GET', '/api/contacts/duplicates', 'Find duplicates'),
]

print("Testing endpoints...\n")

for method, path, description in endpoints:
    url = BASE_URL + path
    
    try:
        if method == 'GET':
            response = requests.get(url, timeout=2)
        elif method == 'POST':
            response = requests.post(url, json={}, timeout=2)
        elif method == 'PUT':
            response = requests.put(url, json={}, timeout=2)
        elif method == 'DELETE':
            response = requests.delete(url, timeout=2)
        
        status = "✓" if response.status_code != 404 else "✗"
        print(f"{status} {method:6} {path:30} {description:20} [{response.status_code}]")
        
    except requests.exceptions.ConnectionError:
        print(f"✗ {method:6} {path:30} {description:20} [Server not running]")
    except Exception as e:
        print(f"✗ {method:6} {path:30} {description:20} [Error: {e}]")

print("\n" + "="*70)
print("If you see 404 errors, the endpoints aren't added to Flask app")
print("Run: cat /mnt/user-data/outputs/contact_management_integration.py")
print("And add to team_dashboard_app.py before 'if __name__'")
print("="*70 + "\n")
