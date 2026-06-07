# Server Tasks

定时任务模块，基于 asyncio 实现周期性后台任务。

## 架构

```
server/tasks/
├── __init__.py
├── register.py          # 任务注册表与装饰器
├── setup.py             # 自动发现与管理器
├── garbage_collection.py # 垃圾回收任务
└── ...                  # 其他任务模块
```

- `register.py` 维护全局注册表 `TASKS`，提供 `@register` 装饰器
- `setup.py` 在 FastAPI lifespan 启动时自动扫描同目录下所有 `.py`，为每个注册函数创建 asyncio 周期任务
- 任务函数为同步函数，由 `asyncio.to_thread` 在线程池中执行

## 新增任务

在 `server/tasks/` 下新建 `.py` 文件，使用 `@register` 装饰即可：

```python
from server.tasks.register import register

@register("task_name", interval=3600)
def my_task():
    # 同步函数，执行实际逻辑
    pass
```

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | str | 必填 | 任务唯一标识，不可重复 |
| `interval` | int | 3600 | 执行间隔，单位秒 |

任务函数必须是**同步函数**。`setup.py` 会通过 `asyncio.to_thread` 将其提交到线程池执行，避免阻塞 FastAPI 事件循环。

## 生命周期

由 `server/main.py` 的 `lifespan` 管理：

```python
from server.tasks.setup import setup as task_setup

task_manager = task_setup()  # 发现任务并启动
yield
task_manager.stop()          # 取消所有任务
```

## 已有任务

| name | interval | 说明 |
|------|----------|------|
| `garbage_collection` | 3600s | 清理过期会话、过期垃圾消息、孤立文件、临时上传 |
