# Contributing

Thanks for your interest in improving this project! Here's how you can help.

## 🎯 Good First Contributions

- **Add example carousels** — Create new themed HTML carousel files (tech, food, travel, etc.)
- **Improve error messages** — Make failures friendlier for first-time users
- **Add export formats** — Support WebP or JPEG output alongside PNG
- **Batch export** — Process multiple HTML files in one command
- **Documentation** — Fix typos, improve clarity, add usage examples

## 🚦 Before Opening a PR

1. **Test locally** — Run the script with at least one sample HTML file
2. **Keep it simple** — This project values simplicity and readability
3. **Don't commit generated files** — `slides_output/` is git-ignored for a reason
4. **Update the README** — If your change affects usage, update the docs

## 🏗️ Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/html-to-Instagram-carousel.git
cd html-to-Instagram-carousel

# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run with the example file
python main.py matrix_minimal_carousel.html
```

## 📝 Code Style

- Keep functions small and focused
- Use type hints where practical
- Prefer descriptive variable names over abbreviations
- Add docstrings to new functions

## 🐛 Reporting Issues

When reporting a bug, please include:

1. Your Python version (`python --version`)
2. Your operating system
3. The command you ran
4. The HTML file you used (or a minimal reproduction)
5. The full error message / traceback

## 📜 License

By contributing, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
