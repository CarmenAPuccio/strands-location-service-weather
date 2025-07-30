# Development Guidelines

## Code Style and Formatting

This project enforces consistent code style using automated tools:

### Required Tools
- **Black**: Uncompromising code formatter
- **Ruff**: Fast Python linter and import sorter
- **Python 3.10+**: Minimum version required by dependencies

### Pre-Commit Workflow

**Always run before committing:**
```bash
uv run black .
uv run ruff check --fix .
```

### Configuration Details

- **Line length**: 88 characters (Black default)
- **Import organization**: Automatic via Ruff
- **Modern Python patterns**: Enforced by Ruff (e.g., `str | int` instead of `Union[str, int]`)
- **Unused imports/variables**: Automatically removed by Ruff

### Code Quality Rules

1. **No manual formatting decisions** - Let Black handle all formatting
2. **Fix Ruff issues immediately** - Don't commit with linting errors
3. **Use type hints** - Especially for function parameters and returns
4. **Follow PEP 8 naming conventions**:
   - Functions/variables: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`

### Corporate Environment Notes

- Git hook managers prevent pre-commit hook installation
- Manual formatting before commits is required
- All formatting tools work normally, just run them manually before each commit

### IDE Integration

Configure your editor to:
- Format with Black on save
- Show Ruff linting errors in real-time
- Use the project's Python version (3.10+)