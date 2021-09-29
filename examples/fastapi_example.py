from fastapi import FastAPI
import epsagon

epsagon.init(
  token='',
  metadata_only=False,
  ignored_endpoints=['/ignored'],
)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Fast API in Python"}


@app.get("/ignored")
def ignored():
    return {"message": "This Is Ignored"}
