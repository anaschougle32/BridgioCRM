#!/usr/bin/env python
"""
Check actual table names in database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%call%' OR name LIKE '%lead%'")
    tables = cursor.fetchall()
    print("Tables related to leads/calls:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check call_logs specifically
    print("\n" + "="*60)
    print("Checking 'call_logs' table:")
    print("="*60)
    try:
        cursor.execute("PRAGMA table_info(call_logs)")
        cols = cursor.fetchall()
        if cols:
            print(f"✅ Table 'call_logs' exists with {len(cols)} columns:")
            for col in cols:
                print(f"  - {col[1]} ({col[2]})")
        else:
            print("❌ Table 'call_logs' is empty or doesn't exist")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Check leads_calllog
    print("\n" + "="*60)
    print("Checking 'leads_calllog' table:")
    print("="*60)
    try:
        cursor.execute("PRAGMA table_info(leads_calllog)")
        cols = cursor.fetchall()
        if cols:
            print(f"✅ Table 'leads_calllog' exists with {len(cols)} columns:")
            for col in cols:
                print(f"  - {col[1]} ({col[2]})")
        else:
            print("❌ Table 'leads_calllog' doesn't exist")
    except Exception as e:
        print(f"❌ Error: {e}")

