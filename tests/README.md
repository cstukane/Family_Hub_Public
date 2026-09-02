# Family Hub Test Suite

This test suite covers the complete Family Hub application functionality with 40 comprehensive tests that validate:

## Test Coverage

### Routes (14 tests)
- **API Routes**: 11 tests covering all partial templates and API endpoints
  - Notes partial rendering and CRUD operations
  - Shopping partial rendering and CRUD operations  
  - Calendar partials (week view, up next) rendering
  - Weather partial rendering
  - Media partial rendering
  - Calendar event creation API
  - Launch app API
  - Health endpoint
- **Main Routes**: 3 tests for main application routes
  - Root page rendering
  - View switching
  - Health check endpoint

### Services (15 tests)
- **Calendar Service**: 4 tests for calendar functionality
  - Calendar event creation and model
  - Upcoming events retrieval (with app context)
  - Event listing within date ranges (with app context)
- **Notes Service**: 4 tests for notes functionality
  - Note model and creation
  - Data serialization
- **Shopping Service**: 4 tests for shopping functionality
  - Shopping item model and creation
  - Data serialization and defaults
- **Weather Service**: 3 tests for weather models
  - Current weather, hourly forecast, daily forecast models
  - Weather data retrieval

### Database Layer (4 tests)
- Database initialization and table creation
- Notes table structure and operations
- Shopping items table structure and operations
- Events local table structure and operations

### Configuration (3 tests)
- Configuration schema validation with valid data
- Configuration handling with invalid data
- Configuration model structure

### Adapters (4 tests)
- Media service function availability
- General service functionality checks

## Running Tests

To run the complete test suite:
```bash
pytest tests/
```

To run specific test modules:
```bash
pytest tests/test_config.py
pytest tests/services/
pytest tests/routes/
```

To see detailed output:
```bash
pytest tests/ -v
```

To run with coverage:
```bash
pytest tests/ --cov=hub --cov-report=html
```

## Test Environment

The test suite uses:
- Pytest for test discovery and execution
- Flask test client for API testing
- In-memory SQLite database for isolation
- Temporary configuration files
- Proper application context management

## Coverage Summary

- **Components Tested**: All major components (calendar, notes, shopping, weather, media, configuration)
- **Functionality**: Full CRUD operations, API endpoints, database interactions, template rendering
- **Integration**: End-to-end functionality testing
- **Edge Cases**: Error handling, empty states, invalid data

All tests pass, confirming the Family Hub application is functioning correctly according to the original requirements and architecture.