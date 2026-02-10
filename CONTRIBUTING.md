# Contributing

We welcome contributions to both the framework content and the assessment agent.

## Framework Content

Framework content lives in `framework/` and is licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

- Write in a declarative, concrete style. No hyperbole.
- Requirements state what must be true about the data, not how to achieve it.
- The framework is vendor-agnostic. Never name a specific product as a requirement.
- Factor content should define requirements at all three workload levels (L1, L2, L3).

## Assessment Agent

Agent code lives in `agent/` and is licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

### Adding a New Platform Suite

1. Create `agent/suites/<platform>.py`
2. Extend `CommonSuite` -- call `super()` to inherit ANSI SQL tests
3. Override `database_tests()`, `table_tests()`, and `column_tests()` with platform-native tests
4. Register the suite in `agent/suites/__init__.py`
5. Add connection logic in `agent/discover.py`
6. Add the driver to `agent/pyproject.toml` optional dependencies
7. Submit a PR

### Adding Tests to an Existing Suite

1. Add `Test()` entries in the appropriate method (`database_tests`, `table_tests`, or `column_tests`)
2. Add default thresholds to `agent/schema/thresholds-default.json` if the test introduces a new requirement
3. Add test coverage

### Development

```bash
make dev            # Set up dev environment
make test           # Run tests
make lint           # Lint with ruff
```

## Code of Conduct

Be respectful. Be constructive. Focus on the work.

## Submitting Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

Before submitting, run `make lint` and `make test`.
