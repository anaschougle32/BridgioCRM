# Database Replication Guide

## The Smart Way: Export Database to Fixtures

Instead of uploading your database file every time, you can **export your database to JSON fixtures** and include them in your repository. This way, every deployment automatically gets your data!

## How It Works

1. **Export** your local database to JSON fixtures
2. **Commit** fixtures to Git
3. **Build process** automatically loads fixtures
4. **Every deployment** gets the same data! 🎉

## Step-by-Step Guide

### Step 1: Export Your Database

Run this command locally:

```bash
cd "C:\Users\Dalvi Faiz\Downloads\BridgioCRM"
python export_database.py
```

Or manually:

```bash
python manage.py dumpdata --exclude contenttypes --exclude auth.permission --exclude sessions --natural-foreign --natural-primary --indent 2 > fixtures/initial_data.json
```

This creates `fixtures/initial_data.json` with all your data.

### Step 2: Review the Fixture File

Check `fixtures/initial_data.json`:
- Make sure it's not too large (< 10MB is ideal)
- Remove any sensitive data if needed
- Verify all your data is there

### Step 3: Commit to Git

```bash
git add fixtures/initial_data.json
git commit -m "Add initial database fixtures"
git push
```

### Step 4: Deploy!

On the next deployment, the build process will:
1. Run migrations
2. **Automatically load your fixtures** ✅
3. Your database will be populated!

## What Gets Exported

The export includes:
- ✅ All Users (with passwords hashed)
- ✅ All Projects
- ✅ All Leads
- ✅ All Bookings
- ✅ All Payments
- ✅ All Channel Partners
- ✅ All Attendance records
- ✅ All Call Logs
- ✅ All Reminders
- ✅ All OTP Logs

**Excludes:**
- Content types (auto-generated)
- Permissions (auto-generated)
- Sessions (temporary)

## Updating Your Database

### When to Re-export:

1. **After adding new data locally**
2. **After making significant changes**
3. **Before major deployments**

### How to Re-export:

```bash
# Delete old fixture
rm fixtures/initial_data.json

# Export fresh data
python export_database.py

# Commit and push
git add fixtures/initial_data.json
git commit -m "Update database fixtures"
git push
```

## Build Process

The build command now includes:

```bash
python manage.py migrate --noinput
python manage.py load_initial_data --skip-if-exists  # ← Loads your fixtures!
python manage.py collectstatic --noinput
```

The `--skip-if-exists` flag ensures:
- ✅ First deployment: Loads fixtures
- ✅ Subsequent deployments: Skips if data exists (won't duplicate)

## Advantages

1. ✅ **No manual upload needed** - Data is in Git
2. ✅ **Consistent deployments** - Same data every time
3. ✅ **Version controlled** - Track database changes in Git
4. ✅ **Automatic** - Happens during build
5. ✅ **Works on all platforms** - Render, Fly.io, Railway, etc.

## Security Note

⚠️ **Important**: Fixtures contain user data including password hashes. 

**Options:**
1. **Keep fixtures private** - Don't share repository publicly
2. **Remove sensitive data** - Edit fixtures before committing
3. **Use environment variables** - For sensitive data

## File Size Considerations

- **Small databases** (< 1MB): Perfect for fixtures
- **Medium databases** (1-10MB): Still fine, but slower to load
- **Large databases** (> 10MB): Consider:
  - Splitting into multiple fixtures
  - Using database upload instead
  - Using PostgreSQL with direct migration

## Troubleshooting

### Fixtures won't load:
```bash
# Check if file exists
ls -la fixtures/initial_data.json

# Try loading manually
python manage.py loaddata fixtures/initial_data.json
```

### Data conflicts:
```bash
# Clear database first (CAREFUL!)
python manage.py flush

# Then load fixtures
python manage.py loaddata fixtures/initial_data.json
```

### Update specific models only:
```bash
# Export only specific apps
python manage.py dumpdata accounts projects > fixtures/users_projects.json

# Load specific fixtures
python manage.py loaddata fixtures/users_projects.json
```

## Best Practices

1. **Export regularly** - Keep fixtures up to date
2. **Test locally first** - Load fixtures locally before deploying
3. **Backup before loading** - If updating existing database
4. **Use --skip-if-exists** - Prevents duplicate data
5. **Review fixtures** - Check for sensitive data

## Quick Commands

```bash
# Export database
python export_database.py

# Or manually
python manage.py dumpdata --exclude contenttypes --exclude auth.permission --exclude sessions --natural-foreign --natural-primary --indent 2 > fixtures/initial_data.json

# Load fixtures locally (test)
python manage.py loaddata fixtures/initial_data.json

# Load fixtures (skip if exists)
python manage.py load_initial_data --skip-if-exists
```

## For Different Platforms

### Render:
- Fixtures load automatically during build ✅

### Fly.io:
- Fixtures load automatically during Docker build ✅

### Railway:
- Fixtures load automatically during build ✅

### PythonAnywhere:
- Upload fixtures manually or via Git
- Run: `python manage.py loaddata fixtures/initial_data.json`

---

**This is the smartest way to replicate your database!** 🚀

