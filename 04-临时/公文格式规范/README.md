# 公文格式规范 — Word 文档格式化工具

## 目录结构

```
公文格式规范/
├── format_word.exe         # 打包好的 exe（无需 Python，拖拽即用）
├── format_word.py          # 主脚本（拖拽运行 / 命令行）
├── 方正小标宋_GBK.TTF      # 标题字体
├── 黑体_GB18030.TTF        # 一级标题字体
├── 楷体_GB2312.TTF         # 二级标题字体
├── 仿宋_GB2312.TTF         # 正文 / 三四级标题字体
└── README.md               # 本文件
```

## 使用方法

### 方式一：使用 format_word.exe（推荐，无需 Python）

直接拖拽 .docx 文件到 `format_word.exe` 上，同目录生成 `输入文件_格式化.docx`。

或者命令行运行：

```
format_word.exe 输入文件.docx
format_word.exe 输入文件.docx 输出文件.docx
```

### 方式二：Python 脚本运行

1. 安装 Python 3.8+
2. 安装依赖：`pip install python-docx`
3. 拖拽 .docx 文件到 format_word.py 上，或命令行运行：
   ```
   python format_word.py 输入文件.docx
   ```
   同目录生成 `输入文件_格式化.docx`

### 方式三：自行打包 exe

在 Windows 上操作：

1. 安装 Python 3.8+（官网 https://python.org 下载）
   - 安装时勾选 "Add Python to PATH"
2. 打开命令提示符（Win+R → cmd），安装依赖和打包工具：
   ```
   pip install python-docx pyinstaller
   ```
3. 进入脚本所在目录，打包：
   ```
   cd 公文格式规范目录路径
   pyinstaller --onefile --name format_word format_word.py
   ```
4. 打包完成，exe 在 `dist/format_word.exe`
5. 把 exe 移回 `公文格式规范/` 目录（和字体文件放一起）
6. 以后直接拖拽 .docx 文件到 format_word.exe 上即可

## 层级识别规则

| 层级 | 序号格式 | 示例 |
|------|----------|------|
| 标题 | 第一个非空段落（无序号） | 关于……的报告 |
| 一级标题 | 中文数字 + 、 | 一、 二、 三、 |
| 二级标题 | （中文数字） | （一）（二）（三） |
| 三级标题 | 数字 + . + 空格 | 1. 2. 3. |
| 四级标题 | (数字) | (1) (2) (3) |
| 正文 | 以上均不匹配 | — |

## 格式一览

| 样式 | 字体 | 字号 | 其他 |
|------|------|------|------|
| 标题 | 方正小标宋_GBK | 二号（22pt） | 居中 |
| 一级标题 | 黑体 | 三号（16pt） | 加粗 |
| 二级标题 | 楷体_GB2312 | 三号（16pt） | — |
| 三级标题 | 仿宋_GB2312 | 三号（16pt） | — |
| 四级标题 | 仿宋_GB2312 | 三号（16pt） | — |
| 正文 | 仿宋_GB2312 | 三号（16pt） | 首行缩进2字符，行距固定28磅 |