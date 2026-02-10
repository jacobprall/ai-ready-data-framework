FROM python:3.12-slim

WORKDIR /app

# Copy project files
COPY agent/ agent/
COPY framework/ framework/
COPY tests/ tests/

# Install the agent (no database drivers -- user provides via AIRD_DRIVER)
RUN pip install --no-cache-dir ./agent

# Install driver based on build arg (default: none)
# Build with: docker build --build-arg DRIVER=snowflake -t aird/agent .
ARG DRIVER=""
RUN if [ "$DRIVER" = "snowflake" ]; then pip install --no-cache-dir snowflake-connector-python; fi && \
    if [ "$DRIVER" = "databricks" ]; then pip install --no-cache-dir databricks-sql-connector; fi && \
    if [ "$DRIVER" = "postgres" ]; then pip install --no-cache-dir psycopg2-binary; fi && \
    if [ "$DRIVER" = "duckdb" ]; then pip install --no-cache-dir duckdb; fi && \
    if [ "$DRIVER" = "all" ]; then pip install --no-cache-dir snowflake-connector-python databricks-sql-connector psycopg2-binary duckdb; fi

ENV AIRD_LOG_LEVEL=info
ENV AIRD_OUTPUT=markdown
ENV AIRD_TARGET_LEVEL=all

ENTRYPOINT ["python", "-m", "agent.cli"]
CMD ["assess"]
