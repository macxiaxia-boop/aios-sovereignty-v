FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY src/aios_kernel ./aios_kernel
RUN pip install --no-cache-dir -e .
EXPOSE 9000
ENV AIOS_KERNEL_OFFLINE=1
ENV AIOS_KERNEL_NO_EXTERNAL_APIS=1
CMD ["python", "-m", "aios_kernel.cli"]
