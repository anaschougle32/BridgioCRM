@echo off
echo ========================================
echo Applying Leads App Migrations
echo ========================================
echo.

echo Step 1: Checking migration status...
python manage.py showmigrations leads
echo.

echo Step 2: Fixing database schema manually (if needed)...
python fix_migrations.py
echo.

echo Step 3: Applying migrations...
python manage.py migrate leads
echo.

echo Step 4: Checking for any remaining model changes...
python manage.py makemigrations --dry-run
echo.

echo Step 5: Running system check...
python manage.py check
echo.

echo ========================================
echo Done! If no errors, server should be ready.
echo ========================================
pause

