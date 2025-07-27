# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **PDF Vocabulary Extractor** application that automatically extracts English words from PDF documents, retrieves Chinese definitions and IPA pronunciations, and generates formatted PDF vocabulary lists. The application is written in Python and uses a modular architecture with dependency injection.

## Key Components & Architecture

### Core Architecture
- **Interface-based design**: All major components implement abstract interfaces defined in `src/vocabulary_extractor/core/interfaces.py`
- **Dependency injection**: Components are injected through the main `VocabularyExtractorApp` class
- **Modular structure**: Clear separation between PDF processing, word extraction, dictionary services, and PDF generation

### Main Modules
- `core/`: Contains interfaces, models, and the main application controller
- `pdf/`: PDF processing and text extraction using pdfplumber
- `dictionary/`: Dictionary services for word definitions and pronunciations  
- `config/`: Configuration management
- `tests/`: Unit tests using Python's unittest framework

### Key Classes
- `VocabularyExtractorApp` (core/app.py): Main application controller that orchestrates the entire workflow
- `PDFProcessor` (pdf/processor.py): Handles PDF validation and text extraction using pdfplumber
- `VocabularyExtractor` (core/extractor.py): Extracts and normalizes English words from text
- `BaseDictionaryService` (dictionary/service.py): Base class for dictionary API services
- Data models in `core/models.py`: `WordInfo`, `ProcessingResult`, `APIResponse`

## Development Commands

### Running Tests
```bash
# Run all tests from project root
python -m unittest discover src/vocabulary_extractor/tests -v

# Run specific test file
python -m unittest src.vocabulary_extractor.tests.test_pdf_processor -v

# Run individual test class
python -m unittest src.vocabulary_extractor.tests.test_pdf_processor.TestPDFProcessor -v
```

### Code Quality
- No formal linting setup found - consider adding flake8 or black for code formatting
- Tests use extensive mocking for external dependencies (pdfplumber, API calls)

## Dependencies

### Required Libraries
- `pdfplumber`: PDF text extraction (core dependency)
- `requests`: HTTP client for dictionary API calls
- Standard library: `unittest`, `pathlib`, `typing`, `dataclasses`, `abc`

### Optional Dependencies
- Dictionary API services require API keys (EasyPronunciation service implemented)
- Local fallback dictionary service available for offline use

## Working with the Code

### Adding New Features
1. Define interfaces first in `core/interfaces.py` if creating new component types
2. Implement concrete classes following the existing patterns
3. Add comprehensive unit tests with mocking for external dependencies
4. Update the main `VocabularyExtractorApp` to wire new components

### Testing Strategy
- Extensive use of `unittest.mock` for external dependencies
- Test files follow naming convention `test_*.py`
- Each major component has dedicated test coverage
- Tests include error cases, edge cases, and progress tracking scenarios

### Configuration
- Configuration managed through `ConfigManager` class
- Supports API keys, file size limits, processing parameters
- Default values provided with override capability

### Error Handling
- Custom exception classes for different error types
- Graceful degradation when external services fail
- Comprehensive logging throughout the application

## Important Notes
- The application handles Chinese text output (definitions) - ensure UTF-8 encoding
- API rate limiting is implemented with retry mechanisms and delays
- PDF validation includes file size checks and format verification
- Word extraction supports advanced normalization and filtering
- Progress tracking interface allows for UI integration