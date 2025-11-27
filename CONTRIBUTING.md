# Contributing to Image Scale Hub

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## 🌟 Ways to Contribute

### 1. Report Bugs
- Check if the bug is already reported in [Issues](https://github.com/YOUR_USERNAME/image-resizer-pro/issues)
- If not, create a new issue with:
  - Clear title and description
  - Steps to reproduce
  - Expected vs actual behavior
  - Screenshots if applicable
  - Your environment (OS, browser, Docker version)

### 2. Suggest Features
- Open a [Discussion](https://github.com/YOUR_USERNAME/image-resizer-pro/discussions) first
- Describe the feature and its use case
- If approved, create an issue to track it

### 3. Improve Documentation
- Fix typos, clarify instructions
- Add examples and screenshots
- Translate to other languages

### 4. Submit Code
- Bug fixes
- New features
- Performance improvements
- Test coverage

## 🔧 Development Setup

### Prerequisites
- Python 3.9+
- Git
- Docker (optional)

### Local Setup
```bash
# Fork and clone the repo
git clone https://github.com/YOUR_USERNAME/image-resizer-pro.git
cd image-resizer-pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run the app
python app.py
```

### Running Tests
```bash
pytest tests/
```

### Code Style
We use:
- **Black** for Python formatting
- **Flake8** for linting
- **isort** for import sorting

```bash
# Format code
black .
isort .

# Check linting
flake8
```

## 📝 Pull Request Process

### 1. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Changes
- Write clear, commented code
- Follow existing code style
- Add tests for new features
- Update documentation if needed

### 3. Commit Messages
Use clear, descriptive commit messages:
```
feat: Add WebP support to convert tool
fix: Resolve login redirect issue
docs: Update MySQL setup instructions
style: Format admin templates
test: Add compress tool tests
```

### 4. Submit PR
- Push your branch
- Create a Pull Request
- Fill out the PR template
- Link related issues

### 5. Code Review
- Address reviewer feedback
- Keep PR focused and small
- Be patient and respectful

## 🏗️ Project Structure

```
image-resizer-pro/
├── app.py              # Main Flask application
├── config.py           # Configuration settings
├── models.py           # Database models
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── routes/
│   ├── auth.py         # Authentication routes
│   ├── admin.py        # Admin panel routes
│   └── images.py       # Image processing routes
├── templates/
│   ├── base.html       # Base template
│   ├── index.html      # Main app template
│   ├── login.html      # Login page
│   └── admin/          # Admin templates
├── static/
│   └── uploads/        # User uploads
├── utils/
│   ├── security.py     # Security utilities
│   ├── email_sender.py # Email functionality
│   └── logger.py       # Logging utilities
└── tests/              # Test files
```

## 🎯 Priority Areas

We especially welcome contributions in:

### High Priority
- [ ] Unit tests for all routes
- [ ] API documentation
- [ ] Docker Compose for MySQL/PostgreSQL
- [ ] Internationalization (i18n)

### Medium Priority
- [ ] Batch processing improvements
- [ ] Image optimization algorithms
- [ ] Mobile app (React Native)
- [ ] CLI tool

### Nice to Have
- [ ] Plugin system
- [ ] Webhook integrations
- [ ] Cloud storage (S3, GCS)
- [ ] AI-powered features

## 💬 Communication

- **Issues**: Bug reports and feature requests
- **Discussions**: Questions and ideas
- **Pull Requests**: Code contributions

## 📜 Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- No harassment or discrimination

## 🙏 Recognition

Contributors will be:
- Listed in README.md
- Mentioned in release notes
- Given credit in commit messages

## ❓ Questions?

- Open a [Discussion](https://github.com/YOUR_USERNAME/image-resizer-pro/discussions)
- Check existing issues and discussions first

---

Thank you for contributing! 🖼️
