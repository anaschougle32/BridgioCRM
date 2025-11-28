# Fly.io Deployment Guide for Bridgio CRM

## Why Fly.io is Great for Your Project

### ✅ Advantages:
1. **Free Persistent Volumes** - 3GB free (perfect for SQLite!)
2. **No Credit Card Required** - Free tier is truly free
3. **Global Deployment** - Deploy close to your users
4. **Shell Access** - Full SSH access included
5. **Easy SQLite Support** - Works perfectly with persistent volumes
6. **Docker-based** - Full control over your environment
7. **Auto-scaling** - Can scale to zero when not in use (saves credits)

### ⚠️ Considerations:
1. **Requires Docker** - Need to create a Dockerfile (already done!)
2. **CLI Required** - Need to install Fly CLI
3. **Learning Curve** - Slightly more technical than Railway
4. **Free Tier Limits**:
   - 3 shared-cpu VMs
   - 3GB persistent volumes
   - 160GB outbound data transfer

## Quick Start Guide

### Step 1: Install Fly CLI

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Or download from:** https://fly.io/docs/getting-started/installing-flyctl/

### Step 2: Sign Up & Login

```bash
fly auth signup
# Or if you already have an account:
fly auth login
```

### Step 3: Initialize Your App

```bash
cd "C:\Users\Dalvi Faiz\Downloads\BridgioCRM"
fly launch
```

This will:
- Detect your Dockerfile
- Ask for app name (or use `bridgiocrm`)
- Ask for region (choose closest to you, e.g., `iad` for US East)
- Create `fly.toml` (already exists, so it will ask to update)

### Step 4: Create Persistent Volume for Database

```bash
fly volumes create bridgiocrm_data --size 1 --region iad
```

This creates a 1GB persistent volume where your SQLite database will be stored.

### Step 5: Set Environment Variables

```bash
# Generate a secret key
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Set environment variables
fly secrets set SECRET_KEY="your-generated-secret-key"
fly secrets set DEBUG="False"
fly secrets set ALLOWED_HOSTS="bridgiocrm.fly.dev"
fly secrets set GOOGLE_MAPS_API_KEY="AIzaSyCwcFvh1vVe979dldumRkBnV01VU3msn30"
```

### Step 6: Upload Your Existing Database (Optional)

If you have an existing database:

1. **Encode your database (PowerShell):**
   ```powershell
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("db.sqlite3")) | Out-File db_base64.txt
   ```

2. **Copy the content from `db_base64.txt`**

3. **In Fly.io Shell:**
   ```bash
   fly ssh console
   cd /data
   echo "PASTE_BASE64_CONTENT_HERE" | base64 -d > db.sqlite3
   chmod 644 db.sqlite3
   exit
   ```

### Step 7: Deploy

```bash
fly deploy
```

This will:
- Build your Docker image
- Run migrations
- Collect static files
- Deploy your app

### Step 8: Run Migrations (if needed)

```bash
fly ssh console
python manage.py migrate
python manage.py create_superuser --username admin --email admin@bridgio.com --password admin123
exit
```

## Your App URL

After deployment, your app will be available at:
- `https://bridgiocrm.fly.dev` (or your custom app name)

## Managing Your App

### View Logs:
```bash
fly logs
```

### SSH into App:
```bash
fly ssh console
```

### Scale Your App:
```bash
# Scale to 1 VM (default)
fly scale count 1

# Scale to 0 (when not in use - saves credits)
fly scale count 0
```

### Restart App:
```bash
fly apps restart bridgiocrm
```

## Database Management

### Access Database:
```bash
fly ssh console
python manage.py dbshell
```

### Backup Database:
```bash
fly ssh console
cp /data/db.sqlite3 /data/db.sqlite3.backup
exit

# Download backup
fly sftp shell
get /data/db.sqlite3.backup
```

### Restore Database:
```bash
# Upload your database file
fly sftp shell
put db.sqlite3 /data/db.sqlite3
```

## Cost Breakdown

**Free Tier Includes:**
- 3 shared-cpu-1x VMs (256MB RAM each)
- 3GB persistent volumes ✅
- 160GB outbound data transfer
- Unlimited inbound data

**If you exceed free tier:**
- Shared-cpu-1x VM: ~$1.94/month
- Persistent volume: ~$0.15/GB/month
- Data transfer: $0.02/GB after 160GB

**For your CRM, free tier should be enough!**

## Troubleshooting

### App Won't Start:
```bash
fly logs
fly status
```

### Database Not Found:
```bash
fly ssh console
ls -la /data
# Check if volume is mounted
```

### Static Files Not Loading:
```bash
fly ssh console
python manage.py collectstatic --noinput
```

### Run Migrations:
```bash
fly ssh console
python manage.py migrate
```

## Advantages Over Render

1. ✅ **Free Persistent Storage** - No upgrade needed
2. ✅ **Free Shell Access** - Full SSH included
3. ✅ **Better for SQLite** - Persistent volumes work perfectly
4. ✅ **Global Deployment** - Deploy in multiple regions
5. ✅ **Auto-scaling** - Can scale to zero when idle
6. ✅ **More Control** - Docker-based, full environment control

## Next Steps

1. Install Fly CLI
2. Run `fly launch`
3. Create persistent volume
4. Set secrets
5. Deploy!

Your existing database will work perfectly on Fly.io with persistent volumes! 🚀

