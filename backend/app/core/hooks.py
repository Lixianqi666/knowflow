"""事件钩子系统

插件注册 → 挂载到钩子 → 核心流程触发钩子 → 插件按序执行
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_hooks: dict[str, list[tuple[str, Any]]] = {}  # event -> [(plugin_name, handler)]


def register(event: str, plugin_name: str, handler: Any):
    """注册插件到事件钩子"""
    _hooks.setdefault(event, []).append((plugin_name, handler))
    logger.debug(f"plugin registered: {plugin_name} -> {event}")


def unregister(event: str, plugin_name: str):
    """移除插件"""
    if event in _hooks:
        _hooks[event] = [(n, h) for n, h in _hooks[event] if n != plugin_name]


async def trigger(event: str, **kwargs) -> dict[str, Any]:
    """触发事件钩子，依次执行所有注册的插件

    返回值: {'results': {plugin_name: handler_result}, 'errors': {plugin_name: error_msg}}
    """
    results = {}
    errors = {}
    for plugin_name, handler in _hooks.get(event, []):
        try:
            if callable(handler):
                res = handler(**kwargs)
                if hasattr(res, "__await__"):
                    res = await res
                results[plugin_name] = res
            else:
                results[plugin_name] = handler
        except Exception as e:
            logger.warning(f"hook {event}/{plugin_name} failed: {e}")
            errors[plugin_name] = str(e)
    return {"results": results, "errors": errors}
