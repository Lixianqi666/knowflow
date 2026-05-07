"""插件基类与注册管理"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

_registry: dict[str, type["BasePlugin"]] = {}


class BasePlugin(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    async def on_load(self):
        """插件加载时调用，在此注册事件钩子"""
        ...

    async def on_unload(self):
        """插件卸载时调用，在此移除事件钩子"""
        ...


def register_plugin(cls: type[BasePlugin]) -> type[BasePlugin]:
    """装饰器：注册插件类"""
    name = cls.name or cls.__name__
    _registry[name] = cls
    logger.info(f"plugin class registered: {name}")
    return cls


async def load_plugin(name: str) -> BasePlugin | None:
    """加载单个插件实例"""
    cls = _registry.get(name)
    if not cls:
        logger.warning(f"plugin not found: {name}")
        return None
    inst = cls()
    try:
        await inst.on_load()
        logger.info(f"plugin loaded: {name}")
        return inst
    except Exception as e:
        logger.error(f"plugin load failed: {name} - {e}")
        return None


async def load_all():
    """加载所有已注册的插件"""
    loaded = []
    for name in list(_registry.keys()):
        inst = await load_plugin(name)
        if inst:
            loaded.append(inst)
    return loaded


def list_plugins() -> list[dict]:
    return [{"name": cls.name or n, "description": cls.description} for n, cls in _registry.items()]
