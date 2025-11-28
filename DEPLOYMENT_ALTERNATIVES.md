# Deployment Alternatives to Render

Since Render requires an upgrade for Shell and Persistent Disks, here are better free alternatives for Django + SQLite:

## 🚀 Option 1: Railway (Recommended - Best Free Tier)

**Why Railway is Great:**
- ✅ **Free tier includes persistent storage** (no upgrade needed!)
- ✅ **Free PostgreSQL database** included
- ✅ **Easy deployment** from GitHub
- ✅ **Automatic HTTPS**
- ✅ **No credit card required** for free tier
- ✅ **Shell access** on free tier

### Setup Steps:

1. **Sign up at [railway.app](https://railway.app)**

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect your repository

3. **Add PostgreSQL Database (Free):**
   - Click "New" → "Database" → "PostgreSQL"
   - Railway automatically provides `DATABASE_URL`

4. **Update `requirements.txt`:**
   ```
   psycopg2-binary==2.9.9
   dj-database-url==2.1.0
   ```

5. **Update `bridgio/settings.py`:**
   ```python
   import dj_database_url
   import os
   
   # Use PostgreSQL from Railway if available, otherwise SQLite
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

6. **Create `railway.json` (optional):**
   ```json
   {
     "$schema": "https://railway.app/railway.schema.json",
     "build": {
       "builder": "NIXPACKS"
     },
     "deploy": {
       "startCommand": "gunicorn bridgio.wsgi:application",
       "restartPolicyType": "ON_FAILURE",
       "restartPolicyMaxRetries": 10
     }
   }
   ```

7. **Environment Variables (set in Railway dashboard):**
   - `SECRET_KEY` (generate one)
   - `DEBUG=False`
   - `ALLOWED_HOSTS=your-app.railway.app`
   - `GOOGLE_MAPS_API_KEY=AIzaSyCwcFvh1vVe979dldumRkBnV01VU3msn30`
   - `DATABASE_URL` (automatically set by Railway)

8. **Deploy:**
   - Railway auto-detects Django and deploys
   - Database migrations run automatically

**Free Tier Limits:**
- $5 credit/month (usually enough for small apps)
- 500 hours of usage
- Persistent storage included ✅

---

## 🚀 Option 2: Fly.io (Great for SQLite with Volumes)

**Why Fly.io is Great:**
- ✅ **Free persistent volumes** (no upgrade needed!)
- ✅ **Free tier available**
- ✅ **Works great with SQLite**
- ✅ **Global deployment**

### Setup Steps:

1. **Install Fly CLI:**
   ```bash
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Sign up at [fly.io](https://fly.io)**

3. **Create `fly.toml`:**
   ```toml
   app = "bridgiocrm"
   primary_region = "iad"
   
   [build]
   
   [http_service]
     internal_port = 8000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0
     processes = ["app"]
   
   [[services]]
     http_checks = []
     internal_port = 8000
     processes = ["app"]
     protocol = "tcp"
     script_checks = []
   
   [env]
     PORT = "8000"
     PYTHON_VERSION = "3.11.0"
   
   [[mounts]]
     source = "bridgiocrm_data"
     destination = "/data"
   ```

4. **Update `bridgio/settings.py`:**
   ```python
   # Use /data volume if it exists (Fly.io), otherwise project directory
   if os.path.exists('/data'):
       db_path = '/data/db.sqlite3'
   else:
       db_path = BASE_DIR / 'db.sqlite3'
   
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.sqlite3',
           'NAME': str(db_path),
       }
   }
   ```

5. **Create `Dockerfile`:**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   RUN python manage.py collectstatic --noinput
   RUN python manage.py migrate --noinput
   
   CMD gunicorn bridgio.wsgi:application --bind 0.0.0.0:8000
   ```

6. **Deploy:**
   ```bash
   fly launch
   fly volumes create bridgiocrm_data --size 1
   fly deploy
   ```

**Free Tier:**
- 3 shared-cpu VMs
- 3GB persistent volumes ✅
- 160GB outbound data transfer

---

## 🚀 Option 3: PythonAnywhere (Easiest for Beginners)

**Why PythonAnywhere:**
- ✅ **Free tier available**
- ✅ **Built for Python/Django**
- ✅ **Persistent storage included**
- ✅ **No Docker/containers needed**
- ✅ **Web-based console**

### Setup Steps:

1. **Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)**

2. **Upload your code:**
   - Use Files tab to upload your project
   - Or use Git: `git clone https://github.com/anaschougle32/BridgioCRM.git`

3. **Create Web App:**
   - Go to Web tab
   - Click "Add a new web app"
   - Select Django
   - Choose Python 3.11
   - Point to your project directory

4. **Configure:**
   - Set WSGI file path
   - Set static files path
   - Set environment variables

5. **Database:**
   - SQLite works perfectly (persistent)
   - Or use MySQL (free tier includes MySQL)

**Free Tier:**
- 1 web app
- Persistent storage ✅
- MySQL database included
- Limited CPU time

---

## 🚀 Option 4: DigitalOcean App Platform

**Why DigitalOcean:**
- ✅ **$200 free credit** for new users
- ✅ **PostgreSQL included**
- ✅ **Easy deployment**

### Setup Steps:

1. **Sign up at [digitalocean.com](https://www.digitalocean.com)** (get $200 credit)

2. **Create App:**
   - Connect GitHub repo
   - Auto-detects Django
   - Add PostgreSQL database

3. **Configure:**
   - Set environment variables
   - Deploy

**Free Credit:**
- $200 credit (lasts months for small apps)
- PostgreSQL database included ✅

---

## 🚀 Option 5: Heroku (Alternative)

**Note:** Heroku removed free tier, but has low-cost options ($5-7/month)

**Why Heroku:**
- ✅ **PostgreSQL included** (even on paid plans)
- ✅ **Very easy deployment**
- ✅ **Great documentation**

### Setup Steps:

1. **Sign up at [heroku.com](https://www.heroku.com)**

2. **Install Heroku CLI:**
   ```bash
   # Windows
   # Download from https://devcenter.heroku.com/articles/heroku-cli
   ```

3. **Create `Procfile`:**
   ```
   web: gunicorn bridgio.wsgi:application
   ```

4. **Deploy:**
   ```bash
   heroku create bridgiocrm
   heroku addons:create heroku-postgresql:mini
   git push heroku main
   ```

**Cost:**
- Eco Dyno: $5/month
- Mini PostgreSQL: $5/month
- Total: ~$10/month

---

## 📊 Comparison Table

| Platform | Free Tier | Persistent Storage | PostgreSQL | Shell Access | Best For |
|----------|-----------|-------------------|------------|--------------|----------|
| **Railway** | ✅ $5 credit/month | ✅ Yes | ✅ Free | ✅ Yes | **Best overall** |
| **Fly.io** | ✅ 3 VMs | ✅ Volumes | ❌ No | ✅ Yes | SQLite with volumes |
| **PythonAnywhere** | ✅ Limited | ✅ Yes | ✅ MySQL | ✅ Yes | Beginners |
| **DigitalOcean** | ✅ $200 credit | ✅ Yes | ✅ Yes | ✅ Yes | Production-ready |
| **Heroku** | ❌ Paid | ✅ Yes | ✅ Yes | ✅ Yes | Easy deployment |
| **Render** | ✅ Limited | ❌ Upgrade needed | ✅ Yes | ❌ Upgrade needed | Current choice |

---

## 🎯 My Recommendation

**For your use case, I recommend Railway because:**
1. ✅ Free tier includes persistent storage
2. ✅ Free PostgreSQL (better than SQLite for production)
3. ✅ Shell access on free tier
4. ✅ Easy deployment from GitHub
5. ✅ No credit card required
6. ✅ $5 credit/month (usually enough)

**Would you like me to:**
1. Set up Railway deployment configuration?
2. Set up Fly.io deployment configuration?
3. Help you migrate your existing database to PostgreSQL?

Let me know which platform you prefer!

