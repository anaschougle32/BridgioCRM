#!/usr/bin/env python
"""
Check what Django detects as missing
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bridgio.settings')
django.setup()

from django.core.management import call_command
import sys

# Capture output
old_stdout = sys.stdout
sys.stdout = open('makemigrations_output.txt', 'w')

try:
    call_command('makemigrations', 'leads', '--dry-run', verbosity=2)
finally:
    sys.stdout.close()
    sys.stdout = old_stdout

print("Output saved to makemigrations_output.txt")

