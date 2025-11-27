# 🖼️ Image Scale Hub

A professional, self-hosted image processing tool with live previews, batch processing, and a powerful admin panel. Fully customizable branding - make it your own!

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## ✨ Features

### Image Tools
- 🖼️ **Frame Tool** - Add blurred backgrounds with custom sizes
- 📦 **Compress** - Reduce file size with quality control & live preview
- 📏 **Resize** - Percentage or custom dimensions with live size display
- 🔄 **Convert** - Change formats (JPG, PNG, WebP, GIF, BMP) with estimated file size

### Admin Panel
- 👥 User management with storage limits per user
- 🎨 Full branding customization (logo, colors, login text)
- 📐 Size presets & packs management
- 🗄️ Database support (SQLite, MySQL, PostgreSQL)
- 🔒 SSL & custom domain configuration
- 💾 Backup & restore tools

### Technical
- 🐳 Docker ready with one-command deploy
- 📱 Responsive design for mobile
- 🔐 Secure authentication with rate limiting
- 📧 Email support (SMTP, SendGrid, Mailgun)

## 🚀 Quick Start

### 🌟 No-Code Install (Easiest!)

**[📖 View Easy Setup Guide](installer/setup.html)** - Step-by-step instructions for beginners!

[![Deploy to Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/YOUR_USERNAME/image-resizer-pro)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/YOUR_USERNAME/image-resizer-pro)

### Option 1: One-Line Install (VPS)
```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/image-resizer-pro/main/install.sh | sudo bash
```
The installer asks for your app name, domain, and admin credentials - no coding needed!

### Option 2: Docker
```bash
git clone https://github.com/YOUR_USERNAME/image-resizer-pro.git
cd image-resizer-pro
docker build -t image-resizer .
docker run -d -p 5000:5000 -v ./data:/app/data image-resizer
```

### Option 3: Manual Installation
```bash
git clone https://github.com/YOUR_USERNAME/image-resizer-pro.git
cd image-resizer-pro
pip install -r requirements.txt
python app.py
```

**Default Login:** `admin` / `admin123`

## 📋 Requirements

- Python 3.9+
- Docker (optional but recommended)
- 512MB RAM minimum
- SQLite (default) or MySQL/PostgreSQL

## 🔧 Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Database (choose one)
DATABASE_URL=sqlite:////app/data/users.db
DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/scorpio_db
DATABASE_URL=postgresql://user:pass@localhost:5432/scorpio_db

# Email (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Security
SECRET_KEY=your-random-secret-key
```

## 🗄️ Database Setup

### SQLite (Default)
No setup needed! Database file created automatically.

### MySQL
```sql
CREATE DATABASE image_resizer;
CREATE USER 'imguser'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON image_resizer.* TO 'imguser'@'localhost';
```

### PostgreSQL
```sql
CREATE DATABASE image_resizer;
CREATE USER imguser WITH ENCRYPTED PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE image_resizer TO imguser;
```

## 🔒 SSL Setup

```bash
# Install Certbot
apt install certbot python3-certbot-nginx

# Get certificate
certbot --nginx -d yourdomain.com
```

## 📸 Screenshots

| Main App | Admin Panel |
|----------|-------------|
| ![Main](docs/screenshot-main.png) | ![Admin](docs/screenshot-admin.png) |

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Ways to Contribute
- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Submit pull requests

### Development Setup
```bash
git clone https://github.com/YOUR_USERNAME/scorpio-image-resizer.git
cd scorpio-image-resizer
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies
python app.py
```

## 📜 License

MIT License - see [LICENSE](LICENSE) file.

## 🙏 Credits

- Built with [Flask](https://flask.palletsprojects.com/)
- UI inspired by modern design principles
- Icons from emoji standards

## 📞 Support

- 📖 [Documentation](https://github.com/YOUR_USERNAME/image-resizer-pro/wiki)
- 🐛 [Issue Tracker](https://github.com/YOUR_USERNAME/image-resizer-pro/issues)
- 💬 [Discussions](https://github.com/YOUR_USERNAME/image-resizer-pro/discussions)
