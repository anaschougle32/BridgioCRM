# Deploying Bridgio CRM on Render

## Quick Setup Guide

### Option 1: Using Render Dashboard (Recommended)

1. **Go to Render Dashboard**: https://dashboard.render.com
2. **Create New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `anaschougle32/BridgioCRM`
   - Branch: `main`

3. **Configure the Service**:
   - **Name**: `BridgioCRM`
   - **Region**: `Virginia (US East)` or your preferred region
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```bash
     pip install -r requirements.txt && python manage.py collectstatic --noinput
     ```
   - **Start Command**: 
     ```bash
     gunicorn bridgio.wsgi:application
     ```

4. **Set Environment Variables**:
   In your Web Service settings, add these environment variables:
   
   ```
   SECRET_KEY=<generate a secure random key>
   DEBUG=False
   ALLOWED_HOSTS=bridgiocrm.onrender.com
   GOOGLE_MAPS_API_KEY=AIzaSyCwcFvh1vVe979dldumRkBnV01VU3msn30
   PYTHON_VERSION=3.11.0
   ```
   
   **Note**: We're using SQLite (no separate database service needed)
   
   **To generate SECRET_KEY**:
   ```python
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

6. **Deploy**:
   - Click "Create Web Service"
   - Render will automatically build and deploy your app
   - Wait for the build to complete (usually 5-10 minutes)

7. **Run Initial Setup**:
   Once deployed, you need to:
   - Create a superuser: Use Render's Shell feature or run:
     ```bash
     python manage.py createsuperuser
     ```
   - Or use the management command:
     ```bash
     python manage.py set_super_admin
     ```

### Option 2: Using render.yaml (Infrastructure as Code)

1. The `render.yaml` file is already in the repository
2. In Render Dashboard:
   - Go to "Blueprints"
   - Click "New Blueprint"
   - Connect your repository
   - Render will automatically detect and use `render.yaml`
   - Review and apply the blueprint

### Post-Deployment Steps

1. **Create Super Admin**:
   - Use Render's Shell feature (SSH into your service)
   - Run: `python manage.py createsuperuser`
   - Or use: `python manage.py set_super_admin`

2. **Create Test Data** (Optional):
   ```bash
   python manage.py create_test_users
   python manage.py create_projects_and_leads
   ```

3. **Access Your App**:
   - Your app will be available at: `https://bridgiocrm.onrender.com`
   - Admin panel: `https://bridgiocrm.onrender.com/admin/`

### Important Notes

- **Free Tier Limitations**:
  - Services spin down after 15 minutes of inactivity
  - First request after spin-down takes ~30 seconds
  - Consider upgrading to paid plan for production use

- **SQLite Database**:
  - ⚠️ **IMPORTANT**: SQLite database file is stored in the filesystem
  - On Render's free tier, the filesystem is **ephemeral** (data may be lost on redeploy)
  - For production with persistent data, consider:
    - Upgrading to a paid plan with persistent disk
    - Or switching to PostgreSQL (recommended for production)
  - For development/testing, SQLite works fine

- **Static Files**:
  - WhiteNoise is configured to serve static files
  - No need for separate static file service

- **Media Files**:
  - For production, consider using AWS S3 or similar for media storage
  - Current setup stores media locally (may be lost on redeploy)

### Troubleshooting

1. **Build Fails**:
   - Check build logs in Render dashboard
   - Ensure all dependencies are in `requirements.txt`

2. **Database Issues**:
   - SQLite database is created automatically on first migration
   - If data is lost, it's because filesystem is ephemeral on free tier
   - Consider upgrading to paid plan or using PostgreSQL for persistent data

3. **Static Files Not Loading**:
   - Run `python manage.py collectstatic` manually
   - Check `STATIC_ROOT` setting

4. **500 Errors**:
   - Check application logs in Render dashboard
   - Ensure `DEBUG=False` in production
   - Check `ALLOWED_HOSTS` includes your domain

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | (auto-generated) |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed hostnames | `bridgiocrm.onrender.com` |
| `GOOGLE_MAPS_API_KEY` | Google Maps API key | `AIzaSyCwcFvh1vVe979dldumRkBnV01VU3msn30` |
| `PYTHON_VERSION` | Python version | `3.11.0` |

**Note**: No `DATABASE_URL` needed - using SQLite

### Updating Your Deployment

1. Push changes to `main` branch
2. Render automatically detects and redeploys
3. Or manually trigger redeploy from dashboard

### Monitoring

- View logs: Render Dashboard → Your Service → Logs
- View metrics: Render Dashboard → Your Service → Metrics
- Set up alerts: Render Dashboard → Your Service → Alerts

