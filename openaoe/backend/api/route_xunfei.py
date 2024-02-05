from fastapi import APIRouter

from openaoe.backend.model.xunfei import XunfeiSparkChatBody
from openaoe.backend.service.service_xunfei import spark_chat_svc

router = APIRouter()


@router.post("/v1/spark/chat", tags=["Spark"])
async def spark_chat(body: XunfeiSparkChatBody):
    """
    chat api for XunFei Spark model
    """
    ret = spark_chat_svc(body)
    return ret
