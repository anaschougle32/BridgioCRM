# Commands to Apply Leads Migrations

## Step-by-Step Commands (Run in Order):

### Step 1: Fix Database Schema Manually
```powershell
python fix_all_migrations.py
```
This will:
- Rename `called_by_id` to `user_id` in call_logs table
- Ensure `duration_minutes` exists (already correct)
- Ensure `call_date` exists
- Create missing indexes

### Step 2: Fake Migration 0009 (if it's causing index errors)
```powershell
python manage.py migrate leads 0009 --fake
```

### Step 3: Apply All Migrations
```powershell
python manage.py migrate
```

### Step 4: Check for Remaining Changes
```powershell
python manage.py makemigrations --dry-run
```

### Step 5: If makemigrations shows changes, create and apply them
```powershell
python manage.py makemigrations
python manage.py migrate
```

### Step 6: Final System Check
```powershell
python manage.py check
```

### Step 7: Start Server
```powershell
python manage.py runserver
```

## Quick All-in-One Command:
```powershell
python fix_all_migrations.py && python manage.py migrate && python manage.py check
```

## If You Get Index Errors:
If you see "no such index" errors, run:
```powershell
python manage.py migrate leads 0009 --fake
python manage.py migrate
```

## If You Get Column Errors:
The `fix_all_migrations.py` script should handle all column renames automatically.

