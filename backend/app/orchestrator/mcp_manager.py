import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from app.orchestrator.errors import (
    MCPServerConnectionError,
    MCPTimeoutError,
    MCPToolExecutionError,
)
from app.orchestrator.schemas import (
    MCPHealthResponse,
    ServerHealthInfo,
    ServerStatus,
    ToolCallLog,
)
from app.orchestrator.server_registry import registry

logger = logging.getLogger("webtruth.orchestrator.mcp_manager")


class MCPManager:
    """Manages real stdio MCP client subprocesses and tool execution using official MCP SDK."""

    def __init__(self) -> None:
        self.registry = registry

    @asynccontextmanager
    async def open_session(
        self,
        server_name: str,
        timeout_seconds: Optional[float] = None,
    ) -> AsyncGenerator[ClientSession, None]:
        """Launch an independent stdio MCP subprocess, initialize session, and yield the client session."""
        server_def = self.registry.get(server_name)
        if not server_def:
            raise MCPServerConnectionError(f"Server '{server_name}' is not registered in ServerRegistry.")

        init_timeout = timeout_seconds or server_def.timeout_seconds
        params = server_def.build_stdio_parameters()

        logger.info(
            "Launching MCP subprocess for '%s' (module=%s, init_timeout=%ss)",
            server_name,
            server_def.module_name,
            init_timeout,
        )

        try:
            async with stdio_client(params) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    async with asyncio.timeout(init_timeout):
                        init_result = await session.initialize()
                    logger.debug(
                        "MCP server '%s' initialized (serverInfo: %s)",
                        server_name,
                        getattr(init_result, "server_info", None),
                    )
                    yield session
        except TimeoutError as ex:
            logger.error("Connection or initialization timed out for '%s' after %ss", server_name, init_timeout)
            raise MCPTimeoutError(f"Server '{server_name}' timed out after {init_timeout}s") from ex
        except (MCPTimeoutError, MCPToolExecutionError):
            raise
        except BaseExceptionGroup as eg:
            # AnyIO TaskGroup wraps TimeoutError / MCPTimeoutError inside ExceptionGroup
            if eg.subgroup(TimeoutError) or eg.subgroup(MCPTimeoutError):
                logger.error("Connection or tool execution timed out for '%s' (%ss)", server_name, init_timeout)
                raise MCPTimeoutError(f"Server '{server_name}' timed out after {init_timeout}s") from eg
            if eg.subgroup(MCPToolExecutionError):
                raise eg.subgroup(MCPToolExecutionError).exceptions[0] from eg
            logger.error("TaskGroup error with MCP server '%s': %s", server_name, eg)
            raise MCPServerConnectionError(f"Failed to connect to MCP server '{server_name}': {eg}") from eg
        except Exception as ex:
            logger.error("Failed to connect or maintain session with MCP server '%s': %s", server_name, ex)
            raise MCPServerConnectionError(f"Failed to connect to MCP server '{server_name}': {ex}") from ex

    async def call_tool_on_session(
        self,
        session: ClientSession,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 30.0,
    ) -> tuple[Any, ToolCallLog]:
        """Execute a tool on an open MCP session, validating response and producing a structured log."""
        call_id = f"call_{uuid.uuid4().hex[:10]}"
        args = arguments or {}
        start_time = time.perf_counter()

        logger.info("Executing MCP tool call [%s]: %s.%s", call_id, server_name, tool_name)
        try:
            async with asyncio.timeout(timeout_seconds):
                result = await session.call_tool(tool_name, arguments=args)
                elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

                # Check if result indicates error
                is_err = getattr(result, "is_error", False)
                if is_err:
                    err_msg = "Tool execution reported error"
                    if getattr(result, "content", None):
                        err_msg = getattr(result.content[0], "text", err_msg)
                    log_item = ToolCallLog(
                        call_id=call_id,
                        server_name=server_name,
                        tool_name=tool_name,
                        arguments=args,
                        status="failed",
                        execution_time_ms=elapsed_ms,
                        error=err_msg,
                    )
                    logger.warning("Tool call [%s] failed on server '%s': %s", call_id, server_name, err_msg)
                    raise MCPToolExecutionError(f"Tool '{tool_name}' failed on server '{server_name}': {err_msg}")

                # Parse JSON output from content
                parsed_data = None
                if getattr(result, "content", None) and len(result.content) > 0:
                    text_content = getattr(result.content[0], "text", "")
                    if text_content:
                        try:
                            parsed_data = json.loads(text_content)
                        except Exception:
                            parsed_data = text_content
                    else:
                        parsed_data = text_content
                else:
                    parsed_data = {}

                log_item = ToolCallLog(
                    call_id=call_id,
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=args,
                    status="success",
                    execution_time_ms=elapsed_ms,
                )
                logger.debug("Tool call [%s] succeeded in %sms", call_id, elapsed_ms)
                return parsed_data, log_item

        except TimeoutError as ex:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            log_item = ToolCallLog(
                call_id=call_id,
                server_name=server_name,
                tool_name=tool_name,
                arguments=args,
                status="failed",
                execution_time_ms=elapsed_ms,
                error=f"Timed out after {timeout_seconds}s",
            )
            raise MCPTimeoutError(f"Tool call '{tool_name}' timed out after {timeout_seconds}s") from ex
        except MCPToolExecutionError:
            raise
        except Exception as ex:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            log_item = ToolCallLog(
                call_id=call_id,
                server_name=server_name,
                tool_name=tool_name,
                arguments=args,
                status="failed",
                execution_time_ms=elapsed_ms,
                error=str(ex),
            )
            raise MCPToolExecutionError(f"Tool call '{tool_name}' encountered exception: {ex}") from ex

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> tuple[Any, ToolCallLog]:
        """Convenience wrapper: opens a dedicated stdio session and executes a single tool call."""
        async with self.open_session(server_name, timeout_seconds=timeout_seconds) as session:
            s_def = self.registry.get(server_name)
            timeout = timeout_seconds or (s_def.timeout_seconds if s_def else 30.0)
            return await self.call_tool_on_session(
                session=session,
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
                timeout_seconds=timeout,
            )

    async def list_tools(
        self,
        server_name: str,
        timeout_seconds: Optional[float] = None,
    ) -> List[str]:
        """Discover tools exposed by a specific MCP server over stdio."""
        async with self.open_session(server_name, timeout_seconds=timeout_seconds) as session:
            tools_res = await session.list_tools()
            return [t.name for t in tools_res.tools]

    async def check_server_health(self, server_name: str) -> ServerHealthInfo:
        """Ping server over stdio and report discovered tools and response latency."""
        server_def = self.registry.get(server_name)
        if not server_def:
            return ServerHealthInfo(
                server_name=server_name,
                module_name="unknown",
                status=ServerStatus.ERROR,
                error=f"Server '{server_name}' is not registered.",
            )

        start_time = time.perf_counter()
        try:
            async with self.open_session(server_name, timeout_seconds=server_def.timeout_seconds) as session:
                tools_res = await session.list_tools()
                latency = round((time.perf_counter() - start_time) * 1000.0, 2)
                tools = [t.name for t in tools_res.tools]
                return ServerHealthInfo(
                    server_name=server_name,
                    module_name=server_def.module_name,
                    status=ServerStatus.CONNECTED,
                    discovered_tools=tools,
                    tool_count=len(tools),
                    latency_ms=latency,
                )
        except Exception as ex:
            latency = round((time.perf_counter() - start_time) * 1000.0, 2)
            return ServerHealthInfo(
                server_name=server_name,
                module_name=server_def.module_name,
                status=ServerStatus.ERROR,
                discovered_tools=[],
                tool_count=0,
                latency_ms=latency,
                error=str(ex),
            )

    async def check_all_health(self) -> MCPHealthResponse:
        """Audit health and availability across all registered servers in parallel."""
        servers = self.registry.list_servers()
        tasks = [self.check_server_health(s.name) for s in servers]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        server_map: Dict[str, ServerHealthInfo] = {}
        total_tools = 0
        error_count = 0

        for info in results:
            server_map[info.server_name] = info
            total_tools += info.tool_count
            if info.status != ServerStatus.CONNECTED:
                error_count += 1

        if error_count == 0 and len(servers) > 0:
            status = "healthy"
        elif error_count < len(servers):
            status = "degraded"
        else:
            status = "unhealthy"

        return MCPHealthResponse(
            status=status,
            total_tools_count=total_tools,
            servers=server_map,
        )


mcp_manager = MCPManager()
