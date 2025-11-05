# Contributing to ARIA

Thank you for your interest in contributing to ARIA (Adaptive Responsive Intelligence Assistant)! We welcome contributions from developers of all skill levels.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Docker and Docker Compose (for database services)
- Git
- Basic knowledge of FastAPI, SQLAlchemy, and async Python

### Development Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/your-username/aria_ai.git
   cd aria_ai
   ```

2. **Set Up Python Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # For local development
   python3 switch_config.py local
   
   # For Docker development
   python3 switch_config.py docker
   docker-compose up -d
   ```

4. **Initialize Database**
   ```bash
   alembic upgrade head
   ```

5. **Initialize Bible RAG (Optional)**
   ```bash
   python3 initialize_bible_embeddings.py
   ```

6. **Run Tests**
   ```bash
   python3 test_bible_rag.py
   python3 test_ai_bible_integration.py
   ```

## 🛠️ Development Workflow

### Branch Naming Convention

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test improvements

### Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(bible-rag): add semantic search for Bible verses
fix(ai-service): resolve circular import issue
docs(readme): update installation instructions
```

## 📝 Code Standards

### Python Code Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints where possible
- Write docstrings for all public functions and classes
- Keep functions focused and small
- Use meaningful variable and function names

### Code Quality

- Write tests for new features
- Ensure all tests pass before submitting PR
- Add logging for important operations
- Handle exceptions gracefully
- Follow existing patterns in the codebase

### Example Code Structure

```python
"""
Module docstring describing the purpose.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ExampleService:
    """Service for handling example functionality."""
    
    def __init__(self):
        self.initialized = False
    
    async def process_data(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Process the provided data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Processed result or None if processing fails
        """
        try:
            # Implementation here
            logger.info(f"Processing data: {data}")
            return "processed_result"
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            return None
```

## 🧪 Testing

### Running Tests

```bash
# Test Bible RAG functionality
python3 test_bible_rag.py

# Test AI service integration
python3 test_ai_bible_integration.py

# Test Docker connections
python3 test_docker_connections.py
```

### Writing Tests

- Write tests for new features and bug fixes
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies when appropriate

## 📚 Documentation

### Code Documentation

- Write clear docstrings for all public APIs
- Include type hints
- Document complex algorithms or business logic
- Update README.md for significant changes

### API Documentation

- FastAPI automatically generates API docs
- Ensure all endpoints have proper descriptions
- Include example requests/responses where helpful

## 🔄 Pull Request Process

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**
   - Follow code standards
   - Add tests
   - Update documentation

3. **Test Your Changes**
   ```bash
   python3 test_bible_rag.py
   python3 test_ai_bible_integration.py
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Use a descriptive title
   - Explain what changes you made and why
   - Reference any related issues
   - Include screenshots for UI changes

### PR Review Process

- All PRs require at least one review
- Address reviewer feedback promptly
- Keep PRs focused and reasonably sized
- Ensure CI checks pass

## 🐛 Bug Reports

When reporting bugs, please include:

- **Description**: Clear description of the issue
- **Steps to Reproduce**: Detailed steps to reproduce the bug
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: OS, Python version, etc.
- **Logs**: Relevant error messages or logs

## 💡 Feature Requests

For feature requests, please include:

- **Problem**: What problem does this solve?
- **Solution**: Proposed solution or approach
- **Alternatives**: Alternative solutions considered
- **Use Cases**: How would this feature be used?

## 🏗️ Architecture Overview

### Core Components

- **AI Service**: Main conversation handling with Ollama integration
- **Bible RAG Service**: Retrieval-Augmented Generation for Bible queries
- **Vector Service**: Semantic search using ChromaDB and sentence transformers
- **Context Memory Service**: Conversation memory and user context
- **API Routes**: FastAPI endpoints for all functionality

### Database Schema

- **Sessions**: User session tracking
- **Conversations**: Chat history storage
- **User Context**: User preferences and context
- **System Events**: System activity logging

## 🤝 Community

### Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Code Review**: Learn from PR feedback

### Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- Special recognition for major features

## 📄 License

By contributing to ARIA, you agree that your contributions will be licensed under the same license as the project.

## 💡 Credits

**Project Idea & Initial Development:**
- @Temples-Dev 
- Open Source Ghana Contributors

**Special Thanks:**
- All contributors who help improve ARIA
- The open source community for tools and libraries
- Beta testers and early adopters

---

Thank you for contributing to ARIA! Your efforts help make this project better for everyone. 🎉
