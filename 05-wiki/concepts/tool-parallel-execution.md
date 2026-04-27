---
id: tool-parallel-execution
tags: [concept, hermes, performance]
created: 2026-04-27
source: 01-学习/ai学习/Hermes Agent架构说明.md
---

# 工具并行执行

Hermes通过三个集合决定一批工具能否并行执行。

## 工具分类

| 分类 | 工具 | 说明 |
|------|------|------|
| _NEVER_PARALLEL_TOOLS | clarify | 会跟用户交互，不能并行 |
| _PARALLEL_SAFE_TOOLS | read_file, search_files, vision_analyze等 | 只读，无共享状态 |
| _PATH_SCOPED_TOOLS | read_file, write_file, patch | 需检查路径是否重叠 |

## 路径冲突判定

以下情况必须串行：
- 同一路径：`read_file(/a/b.txt)` + `write_file(/a/b.txt)`
- 父子路径：`read_file(/a)` + `read_file(/a/b.txt)`

## 并行池

最多8个工作线程同时跑。

## 效果

同样要做5次文件读取 + 2次搜索 + 3次网页抓取：
- 串行：10次API往返
- 并行：2-3次搞定
