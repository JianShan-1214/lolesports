# LOL 比賽通知系統 Docker 配置
FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安裝 uv
RUN pip install uv

# 複製專案檔案
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY config/ ./config/
COPY main.py ./

# 建立必要目錄
RUN mkdir -p data logs

# 安裝 Python 依賴
RUN uv sync --frozen

# 暴露 Streamlit 預設埠
EXPOSE 8501

# 設定健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 執行應用程式
CMD ["uv", "run", "streamlit", "run", "main.py", "--server.address", "0.0.0.0", "--server.port", "8501"]