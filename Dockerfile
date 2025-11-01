FROM python:3.11-slim
WORKDIR /app
RUN python -m pip install --no-cache-dir uvicorn fastapi
EXPOSE 9000
CMD ["bash","-lc","python - << 'PY'\nfrom fastapi import FastAPI\napp=FastAPI()\n@app.get('/')\nasync def root():\n    return {'status':'ok','service':'backend'}\nimport uvicorn; uvicorn.run(app, host='0.0.0.0', port=9000)\nPY"]
