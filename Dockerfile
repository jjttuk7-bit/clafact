# ClaFact MVP 데모 — Hugging Face Spaces / 임의 컨테이너 환경용
# 표준 라이브러리만 사용하므로 의존성 설치 없음
FROM python:3.12-slim
WORKDIR /app
COPY . .
ENV PORT=7860
EXPOSE 7860
CMD ["python", "scripts/demo_server.py"]
