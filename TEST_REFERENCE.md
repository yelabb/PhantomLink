# PhantomLink Test Quick Reference

## Quick Commands

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest test_models.py -v

# Run tests matching pattern
pytest -k "test_spike" -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Run last failed tests
pytest --lf
```

## Windows Batch Files

```bash
# Run all tests
test.bat

# Run unit tests only
test.bat unit

# Run integration tests
test.bat integration

# Run with coverage
test.bat coverage

# Run fast tests
test.bat fast
```

## Test Files Overview

| File | Purpose | Type |
|------|---------|------|
| `test_models.py` | Pydantic model validation | Unit |
| `test_data_loader.py` | NWB data loading | Unit |
| `test_playback_engine.py` | 40Hz streaming engine | Unit |
| `test_session_manager.py` | Multi-session management | Unit |
| `test_server.py` | FastAPI endpoints & WebSocket | Integration |

## Common Test Scenarios

### Test a Specific Function
```bash
pytest test_models.py::TestSpikeData::test_valid_spike_data -v
```

### Test with Detailed Output
```bash
pytest test_models.py -vv -s
```

### Test with Failures Detail
```bash
pytest --tb=long
```

### Parallel Execution
```bash
pip install pytest-xdist
pytest -n auto
```

## Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Skip slow tests
pytest -m "not slow"
```

## Coverage Analysis

```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Show missing lines in terminal
pytest --cov=. --cov-report=term-missing

# Coverage for specific module
pytest --cov=models --cov-report=term
```

## Debugging Tests

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger at start
pytest --trace

# Show local variables on failure
pytest -l

# Verbose traceback
pytest --tb=long
```

## CI/CD

Tests run automatically on:
- Push to `main` or `develop`
- Pull requests
- See `.github/workflows/tests.yml`

## Writing New Tests

1. Create test file: `test_<module>.py`
2. Import module and pytest
3. Create test class: `TestClassName`
4. Write test functions: `def test_something()`
5. Use fixtures for setup: `@pytest.fixture`
6. Mark async tests: `@pytest.mark.asyncio`

Example:
```python
import pytest
from my_module import MyClass

@pytest.fixture
def instance():
    return MyClass()

class TestMyClass:
    def test_basic(self, instance):
        assert instance.method() == expected_value
    
    @pytest.mark.asyncio
    async def test_async(self, instance):
        result = await instance.async_method()
        assert result is not None
```

## Performance Testing

Check 40Hz timing:
```python
@pytest.mark.asyncio
async def test_40hz_timing(engine):
    await engine.start()
    
    times = []
    async for packet in engine.stream():
        times.append(time.time())
        if len(times) >= 40:
            break
    
    intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
    avg = sum(intervals) / len(intervals)
    
    assert abs(avg - 0.025) < 0.010  # 25ms ± 10ms
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | `pip install -r requirements.txt` |
| Data not found | Download mc_maze.nwb to data/ folder |
| Port in use | Kill process on port 8000 |
| Async timeout | Increase timeout in `wait_for()` |
| Fixture not found | Check conftest.py |

## Resources

- Full guide: See [TESTING.md](TESTING.md)
- pytest docs: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
