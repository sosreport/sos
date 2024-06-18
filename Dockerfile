# Base stage
FROM python:3.10-slim AS base
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Build stage 
FROM base AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential
RUN python -m venv $VIRTUAL_ENV
COPY requirements.txt .
RUN pip install -r requirements.txt

# Final stage
FROM base AS final 
WORKDIR /app
COPY --from=build $VIRTUAL_ENV $VIRTUAL_ENV
COPY . .
CMD ["python3", "bin/sos", "report", "--batch"]
