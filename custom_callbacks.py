import asyncio
import json
import os
import threading
from datetime import datetime
from typing import Any, Optional

from langfuse import Langfuse, propagate_attributes

from litellm._logging import verbose_logger
from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.spend_tracking.spend_tracking_utils import get_logging_payload


class ClaudeCodeObservabilityHandler(CustomLogger):
    def __init__(self) -> None:
        super().__init__()
        self._langfuse_client: Optional[Langfuse] = None
        self._langfuse_init_attempted = False
        self._langfuse_lock = threading.Lock()

    async def async_log_success_event(
        self,
        kwargs: dict,
        response_obj: Any,
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        payload = get_logging_payload(
            kwargs=kwargs,
            response_obj=response_obj,
            start_time=start_time,
            end_time=end_time,
        )

        await asyncio.to_thread(
            self._log_to_langfuse,
            kwargs,
            payload,
        )

    def _log_to_langfuse(self, kwargs: dict, payload: dict) -> None:
        langfuse_client = self._get_langfuse_client()
        if langfuse_client is None:
            return

        metadata = self._trace_metadata(kwargs=kwargs, payload=payload)
        observation_metadata = self._observation_metadata(payload=payload)
        usage_details = self._usage_details(payload=payload)
        cost_details = self._cost_details(kwargs=kwargs, payload=payload)
        model_parameters = self._model_parameters(kwargs=kwargs)

        try:
            with propagate_attributes(
                user_id=self._user_id(payload=payload),
                session_id=payload.get("session_id"),
                tags=self._request_tags(payload=payload),
                metadata=metadata,
                trace_name=self._trace_name(payload=payload),
            ):
                with langfuse_client.start_as_current_observation(
                    name="litellm_request",
                    as_type="generation",
                    input=self._normalize_for_langfuse(payload.get("messages")),
                    output=self._normalize_for_langfuse(payload.get("response")),
                    metadata=observation_metadata,
                    completion_start_time=self._parse_datetime(
                        payload.get("completionStartTime")
                    ),
                    model=payload.get("model_group") or payload.get("model"),
                    model_parameters=model_parameters,
                    usage_details=usage_details,
                    cost_details=cost_details,
                ):
                    pass

            langfuse_client.flush()
        except Exception as exc:
            verbose_logger.exception(
                "ClaudeCodeObservabilityHandler: failed to write Langfuse trace - %s",
                exc,
            )

    def _get_langfuse_client(self) -> Optional[Langfuse]:
        if self._langfuse_client is not None:
            return self._langfuse_client
        if self._langfuse_init_attempted:
            return None

        with self._langfuse_lock:
            if self._langfuse_client is not None:
                return self._langfuse_client
            if self._langfuse_init_attempted:
                return None

            self._langfuse_init_attempted = True
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            base_url = (
                os.getenv("LANGFUSE_BASE_URL")
                or os.getenv("LANGFUSE_HOST")
                or os.getenv("LANGFUSE_OTEL_HOST")
            )

            if not public_key or not secret_key or not base_url:
                verbose_logger.warning(
                    "ClaudeCodeObservabilityHandler: Langfuse env is incomplete; skipping custom Langfuse tracing"
                )
                return None

            try:
                self._langfuse_client = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    base_url=base_url,
                    flush_at=1,
                    flush_interval=1,
                )
            except Exception as exc:
                verbose_logger.exception(
                    "ClaudeCodeObservabilityHandler: failed to initialize Langfuse client - %s",
                    exc,
                )
                self._langfuse_client = None

        return self._langfuse_client

    def _trace_name(self, payload: dict) -> str:
        route = self._metadata_field(payload=payload, key="user_api_key_request_route")
        model_group = payload.get("model_group") or payload.get("model")
        if route and model_group:
            return f"{route} {model_group}"
        if route:
            return route
        if model_group:
            return str(model_group)
        return "litellm_request"

    def _trace_metadata(self, kwargs: dict, payload: dict) -> dict:
        standard_logging_object = kwargs.get("standard_logging_object") or {}
        metadata = standard_logging_object.get("metadata") or {}

        trace_metadata = {
            "request_id": payload.get("request_id"),
            "call_type": payload.get("call_type"),
            "status": payload.get("status"),
            "model": payload.get("model"),
            "model_group": payload.get("model_group"),
            "custom_llm_provider": payload.get("custom_llm_provider"),
            "api_base": payload.get("api_base"),
            "cache_hit": payload.get("cache_hit"),
            "request_duration_ms": payload.get("request_duration_ms"),
            "user_api_key_alias": metadata.get("user_api_key_alias"),
            "user_api_key_hash": metadata.get("user_api_key_hash"),
            "user_api_key_user_id": metadata.get("user_api_key_user_id"),
            "user_api_key_request_route": metadata.get("user_api_key_request_route"),
            "requester_metadata": metadata.get("requester_metadata"),
        }
        return self._drop_none(trace_metadata)

    def _observation_metadata(self, payload: dict) -> dict:
        observation_metadata = {
            "request_id": payload.get("request_id"),
            "status": payload.get("status"),
            "api_key": payload.get("api_key"),
            "session_id": payload.get("session_id"),
            "team_id": payload.get("team_id"),
            "organization_id": payload.get("organization_id"),
            "end_user": payload.get("end_user"),
            "requester_ip_address": payload.get("requester_ip_address"),
            "model_id": payload.get("model_id"),
            "cache_key": payload.get("cache_key"),
            "metadata": payload.get("metadata"),
            "proxy_server_request": payload.get("proxy_server_request"),
        }
        return self._drop_none(observation_metadata)

    def _usage_details(self, payload: dict) -> dict:
        prompt_tokens = int(payload.get("prompt_tokens") or 0)
        completion_tokens = int(payload.get("completion_tokens") or 0)
        total_tokens = int(payload.get("total_tokens") or 0)
        return {
            "input": prompt_tokens,
            "output": completion_tokens,
            "total": total_tokens,
        }

    def _cost_details(self, kwargs: dict, payload: dict) -> dict:
        standard_logging_object = kwargs.get("standard_logging_object") or {}
        cost_breakdown = standard_logging_object.get("response_cost_breakdown") or {}

        input_cost = self._as_float(
            cost_breakdown.get("input_cost") or cost_breakdown.get("input_cost_per_token")
        )
        output_cost = self._as_float(
            cost_breakdown.get("output_cost") or cost_breakdown.get("output_cost_per_token")
        )
        total_cost = self._as_float(
            cost_breakdown.get("total_cost") or payload.get("spend")
        )

        # When LiteLLM only exposes the aggregate spend, keep the total populated.
        if total_cost and input_cost == 0.0 and output_cost == 0.0:
            return {"total": total_cost, "total_cost": total_cost}

        return {
            "input": input_cost,
            "output": output_cost,
            "total": total_cost,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }

    def _model_parameters(self, kwargs: dict) -> dict:
        model_parameters = {
            "temperature": kwargs.get("temperature"),
            "top_p": kwargs.get("top_p"),
            "max_tokens": kwargs.get("max_tokens"),
            "stream": kwargs.get("stream"),
        }
        return self._drop_none(model_parameters)

    def _user_id(self, payload: dict) -> Optional[str]:
        return self._metadata_field(payload=payload, key="user_api_key_user_id")

    def _request_tags(self, payload: dict) -> Optional[list[str]]:
        request_tags = payload.get("request_tags")
        if isinstance(request_tags, list):
            return [str(tag) for tag in request_tags]
        return None

    def _metadata_field(self, payload: dict, key: str) -> Any:
        metadata = payload.get("metadata") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                return None
        return metadata.get(key)

    @staticmethod
    def _normalize_for_langfuse(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    @staticmethod
    def _drop_none(value: dict) -> dict:
        return {k: v for k, v in value.items() if v is not None}

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0


proxy_handler_instance = ClaudeCodeObservabilityHandler()
