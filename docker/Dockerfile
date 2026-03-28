# MotionTrack データ分析 - ダッシュボード
FROM python:3.11-slim

WORKDIR /app

# 依存パッケージ
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# プロジェクト一式をコピー（ビルドコンテキストはプロジェクトルート）
COPY . .

# ダッシュボード用データ（06_direction_detection/output）が含まれる前提
# データがない場合は起動時にエラー。事前に python run.py --dashboard で生成するか、
# ボリュームマウントで 06_direction_detection/output を渡すこと

EXPOSE 8050

ENV DASH_HOST=0.0.0.0
ENV DASH_DEBUG=false

CMD ["python", "09_dashboard/app.py"]
