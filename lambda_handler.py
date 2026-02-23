from main import app
from mangum import Mangum

# API Gateway HTTP API/Lambda Proxy v2
handler = Mangum(app, lifespan="off")
