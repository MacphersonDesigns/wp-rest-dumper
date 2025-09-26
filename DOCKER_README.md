# 🐳 Docker Setup for WordPress REST Dumper

Run the WordPress REST Dumper as a persistent web service using Docker Compose!

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

### Start the Service

```bash
# Clone or navigate to the repository
cd wp-rest-dumper

# Start the service (builds and runs in background)
docker-compose up -d

# Check if it's running
docker-compose ps
```

**That's it!** The web interface will be available at: **http://localhost:8080**

## 📋 Common Commands

### Service Management

```bash
# Start the service
docker-compose up -d

# Stop the service
docker-compose down

# Restart the service
docker-compose restart

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### Updates & Rebuilding

```bash
# Pull latest code and rebuild
git pull origin main
docker-compose down
docker-compose up -d --build

# Force rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

## 📁 File Storage

### Default Setup

- Scraped content is saved to `./wp_dump/` in your project directory
- This folder is automatically created and persisted between container restarts

### Custom Output Directory

To use a different output directory, edit `docker-compose.yml`:

```yaml
volumes:
  # Change this line to your preferred location:
  - /Users/yourname/Downloads/scraped_sites:/app/wp_dump
```

## 🔧 Configuration Options

### Change Port

Edit `docker-compose.yml` to use a different port:

```yaml
ports:
  - "9000:8080" # Access via http://localhost:9000
```

### Environment Variables

Available environment variables in `docker-compose.yml`:

- `FLASK_ENV`: Set to `production` or `development`
- `PYTHONUNBUFFERED`: Ensures real-time log output

## 🔍 Troubleshooting

### Service Won't Start

```bash
# Check Docker is running
docker --version
docker-compose --version

# View detailed logs
docker-compose logs wp-dumper

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Can't Access Web Interface

1. Verify service is running: `docker-compose ps`
2. Check port isn't blocked: `curl http://localhost:8080`
3. View logs: `docker-compose logs -f`

### Permission Issues with Output Directory

```bash
# Fix permissions (macOS/Linux)
sudo chown -R $USER:$USER ./wp_dump
```

## 🎯 Advantages of Docker Setup

✅ **Always Available**: Access anytime at http://localhost:8080  
✅ **No Terminal Needed**: Runs as background service  
✅ **Auto-Restart**: Survives system reboots  
✅ **Isolated Environment**: Doesn't conflict with system Python  
✅ **Easy Updates**: Just rebuild and restart  
✅ **Consistent Setup**: Works the same on any machine

## 🔄 Auto-Start on System Boot

### macOS/Windows (Docker Desktop)

Docker Desktop can be set to start automatically:

1. Open Docker Desktop Settings
2. General → "Start Docker Desktop when you login"
3. Your wp-dumper service will auto-start with the system

### Linux (systemd)

```bash
# Enable Docker service
sudo systemctl enable docker

# Create auto-start script
sudo nano /etc/systemd/system/wp-dumper.service
```

## 📊 Monitoring

### Health Checks

The container includes built-in health monitoring:

```bash
# Check container health
docker-compose ps
# Look for "healthy" status

# Manual health check
curl -f http://localhost:8080/ && echo "Service is healthy"
```

### Resource Usage

```bash
# Monitor resource usage
docker stats wp-rest-dumper
```

## 🛑 Stopping the Service

### Temporary Stop (keeps data)

```bash
docker-compose down
```

### Complete Cleanup (removes everything)

```bash
docker-compose down -v --rmi all
rm -rf wp_dump/  # Only if you want to delete scraped data
```

---

**Happy Scraping!** 🎉 Your WordPress REST Dumper is now running as a persistent web service.
