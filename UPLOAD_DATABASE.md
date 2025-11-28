# How to Use Your Existing Database on Render

## Option 1: Use Persistent Disk (Recommended - Same as Your Other Project!)

If your other Django project on Render uses SQLite without issues, you're likely using a **Persistent Disk**. This is the proper way to use SQLite on Render.

### Step 1: Add Persistent Disk in Render Dashboard
1. Go to Render Dashboard → Your Service → **Disks** tab
2. Click **Add Disk**
3. Set:
   - **Mount Path**: `/var/data` (or any path you prefer)
   - **Size**: 1GB (or more if needed)
4. Save and wait for the disk to be attached

### Step 2: Update Settings (Already Done!)
The settings are already configured to use `/var/data` if it exists. The database will automatically be stored on the persistent disk.

### Step 3: Upload Your Existing Database
1. Go to Render Dashboard → Your Service → **Shell**
2. Navigate to the persistent disk:
   ```bash
   cd /var/data
   ```
3. Upload your database using one of these methods:

   **Method A: Using Base64 (easiest)**
   
   On your local machine (PowerShell):
   ```powershell
   cd "C:\Users\Dalvi Faiz\Downloads\BridgioCRM"
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("db.sqlite3")) | Out-File db_base64.txt
   ```
   - Open `db_base64.txt` and copy all the content
   
   In Render Shell:
   ```bash
   cd /var/data
   # Paste the base64 content between quotes
   echo "PASTE_BASE64_CONTENT_HERE" | base64 -d > db.sqlite3
   chmod 644 db.sqlite3
   ```

   **Method B: Using SCP (if you have SSH access)**
   ```bash
   # From your local machine
   scp db.sqlite3 render:/var/data/db.sqlite3
   ```

### Step 4: Restart Service
- Go to Render Dashboard → Your Service → **Manual Deploy** → **Clear build cache & deploy**

**✅ With Persistent Disk, your database will persist across redeploys!**

## Option 2: Upload Database via Render Shell (Without Persistent Disk)

### Step 1: Prepare Your Database File
1. Make sure your `db.sqlite3` file is up to date with all migrations
2. Compress it (optional but recommended):
   ```bash
   # On Windows (PowerShell)
   Compress-Archive -Path db.sqlite3 -DestinationPath db.sqlite3.zip
   ```

### Step 2: Upload to Render
1. Go to your Render Dashboard → Your Service → **Shell**
2. Navigate to the project directory:
   ```bash
   cd /opt/render/project/src
   ```
3. Upload your database file using one of these methods:

   **Method A: Using Render's File Upload (if available)**
   - Use the file upload feature in Render Shell
   
   **Method B: Using SCP/SFTP (if you have SSH access)**
   ```bash
   # From your local machine
   scp db.sqlite3 render:/opt/render/project/src/
   ```
   
   **Method C: Using Base64 (for small databases)**
   - On your local machine, encode the database:
     ```bash
     # Windows PowerShell
     [Convert]::ToBase64String([IO.File]::ReadAllBytes("db.sqlite3")) | Out-File db_base64.txt
     ```
   - Copy the content of `db_base64.txt`
   - In Render Shell, decode it:
     ```bash
     echo "PASTE_BASE64_CONTENT_HERE" | base64 -d > db.sqlite3
     ```

### Step 3: Set Permissions
```bash
chmod 644 db.sqlite3
```

### Step 4: Restart Service
- Go to Render Dashboard → Your Service → **Manual Deploy** → **Clear build cache & deploy**

## Option 3: Include Database in Git (NOT RECOMMENDED for Production)

⚠️ **Warning**: This will commit your database to version control, which is not secure for production.

1. Add `db.sqlite3` to your repository (temporarily)
2. Push to GitHub
3. Render will use it on next deploy

**Then immediately remove it from Git:**
```bash
git rm --cached db.sqlite3
echo "db.sqlite3" >> .gitignore
git commit -m "Remove database from version control"
git push
```

## Option 4: Use PostgreSQL (Alternative for Production)

For persistent storage, consider switching to PostgreSQL:

1. **Add PostgreSQL Database in Render:**
   - Go to Render Dashboard → **New** → **PostgreSQL**
   - Create a new database
   - Copy the `DATABASE_URL`

2. **Update `requirements.txt`:**
   ```
   psycopg2-binary==2.9.9
   dj-database-url==2.1.0
   ```

3. **Update `bridgio/settings.py`:**
   ```python
   import dj_database_url
   
   # Use PostgreSQL if DATABASE_URL is set, otherwise SQLite
   if os.environ.get('DATABASE_URL'):
       DATABASES = {
           'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
       }
   else:
       DATABASES = {
           'default': {
               'ENGINE': 'django.db.backends.sqlite3',
               'NAME': BASE_DIR / 'db.sqlite3',
           }
       }
   ```

4. **Update `render.yaml`:**
   ```yaml
   services:
     - type: web
       name: bridgiocrm
       env: python
       plan: free
       buildCommand: pip install -r requirements.txt && python manage.py migrate --noinput && python manage.py collectstatic --noinput
       startCommand: gunicorn bridgio.wsgi:application
       envVars:
         - key: DATABASE_URL
           fromDatabase:
             name: bridgiocrm-db
             property: connectionString
   ```

5. **Migrate your SQLite data to PostgreSQL:**
   ```bash
   # Use django-dbbackup or manual export/import
   python manage.py dumpdata > data.json
   # Then import to PostgreSQL
   python manage.py loaddata data.json
   ```

## Important Notes

### ⚠️ SQLite on Render:
- **Without Persistent Disk**: Database will be **lost on every redeploy** (ephemeral filesystem)
- **With Persistent Disk**: Database **persists across redeploys** ✅ (recommended)
- **Single Process**: SQLite doesn't work well with multiple workers (use 1 worker for SQLite)

### ✅ Recommended Solution:
For production use, **switch to PostgreSQL** (Option 3) which provides:
- Persistent storage
- Better performance
- Multi-process support
- Automatic backups

## Quick Commands Reference

### Check if database exists:
```bash
ls -la db.sqlite3
```

### Backup your database:
```bash
cp db.sqlite3 db.sqlite3.backup
```

### Verify database:
```bash
python manage.py dbshell
sqlite> .tables
sqlite> .quit
```

