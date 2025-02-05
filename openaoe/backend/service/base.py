#!/usr/bin/env python3
"""
 Common Request
 TODO: all request use base_request or base_stream
"""
import json
import sys
import traceback
from io import StringIO
from typing import Callable

import httpx
from fastapi.encoders import jsonable_encoder
from jsonstreamer import ObjectStreamer

from openaoe.backend.config.constant import DEFAULT_TIMEOUT_SECONDS
from openaoe.backend.model.aoe_response import AOEResponse, StreamResponse
from openaoe.backend.util.log import log

logger = log(__name__)


async def base_request(provider: str, url: str, method: str, headers: dict, body=None,
                       timeout=DEFAULT_TIMEOUT_SECONDS,
                       params=None,
                       files=None) -> AOEResponse:
    """
    common request function for http
    Args:
        provider: use for log
        url: complete url
        method: request method
        headers: request headers, excluding user-agent, host and ip.
        body: json body only
        timeout: seconds
        params: request params
        files: request file

    Returns:
        AOEResponse
    """
    response = AOEResponse()

    headers_pure = {}
    for k, v in headers:
        k = k.lower()
        if k == "user-agent" or k == "host" or "ip" in k:
            continue
        headers_pure[k] = v

    body_str = body
    if "content-type" in headers and "multipart/form-data" in headers["content-type"]:
        body_str = "image"
    if len(body_str) > 200:
        body_str = body_str[:200]

    try:
        async with httpx.AsyncClient() as client:
            proxy = await client.request(method, url, headers=headers, json=body, timeout=timeout,
                                         params=params, files=files)
        response.data = proxy.content
        try:
            response.data = json.loads(response.data)
        except Exception:
            response.data = proxy.content

    except Exception as e:
        response.msg = str(e)
        logger.error(
            f"[{provider}] url: {url}, method: {method}, headers: {jsonable_encoder(headers)}, "
            f"body: {body_str} failed, response: {jsonable_encoder(response)}")
    return response


async def base_stream(provider: str, url: str, method: str, headers: dict,
                      stream_callback: Callable, body=None,
                      timeout=DEFAULT_TIMEOUT_SECONDS,
                      params=None,
                      files=None):
    """
    common stream request
    Args:
        stream_callback:
        provider: use for log
        url: complete url
        method: request method
        headers: request headers, excluding user-agent, host and ip.
        stream_callback: use ObjectStream to stream parse json, this method will be executed while
                         any stream received, use print to output(we have redirected stdout to
                         response stream)
        body: json body only
        timeout: seconds
        params: request params
        files: request file

    Returns:
        SSE response with StreamResponse json string
    """
    headers_pure = {
        "Content-Type": "application/json"
    }
    for k, v in headers:
        k = k.lower()
        if k == "user-agent" or k == "host" or "ip" in k:
            continue
        headers_pure[k] = v

    body_str = jsonable_encoder(body)
    if "content-type" in headers and "multipart/form-data" in headers["content-type"]:
        body_str = "image"
    if len(body_str) > 200:
        body_str = body_str[:200]

    try:
        with httpx.stream(method, url, json=body, params=params, files=files, headers=headers_pure,
                          timeout=timeout) as res:
            if res.status_code != 200:
                raise ValueError(f"request failed, model status code: {res.status_code}")

            # stream parser
            streamer = ObjectStreamer()
            sys.stdout = mystdout = StringIO()
            streamer.add_catch_all_listener(stream_callback)

            for text in res.iter_text():
                streamer.consume(text)
                res = mystdout.getvalue()
                stream_res = json.dumps(jsonable_encoder(StreamResponse(msg=res)))
                # format res
                yield stream_res
                # clear printed string
                sys.stdout.seek(0)
                sys.stdout.truncate()

    except Exception as e:
        print(traceback.format_exc())
        res = json.dumps(jsonable_encoder(StreamResponse(
            success=False,
            msg=str(e)
        )))
        logger.error(
            f"[{provider}] url: {url}, method: {method}, headers: {jsonable_encoder(headers_pure)},"
            f" body: {body_str} failed, response: {res}")
        yield res
