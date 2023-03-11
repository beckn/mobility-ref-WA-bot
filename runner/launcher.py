
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from FalconUtils.mongo.mongoutils import MongoDB
from utils.fileutils import FileUtils

from .router.dashboard import router as dashboard

mongodb = FileUtils.get_config('config.yaml', 'mongodb')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def connect_database():
    MongoDB.mongodb_connect(host=mongodb['host'],
                            port=mongodb['port'], password=mongodb['password'], user=mongodb['user'])


@app.on_event('shutdown')
def close_db_connection():
    MongoDB.mongodb_disconnect()


app.include_router(dashboard)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app)
