# pounding-ozon 首发包使用说明

## 这是什么

这是 `pounding-ozon` 的轻量首发包。  
目标是让用户直接在本地运行：

- 1688 找货
- 1688 → Ozon 单商品上架
- 批量铺货
- Ozon 商品翻新
- 上架状态查询

首发包默认：

- **不附带本地缓存**
- **不附带测试文件**
- **不附带运行产物**
- **不附带你的本地配置**

---

## 包内包含

- `AGENTS.md`
- `SKILL.md`
- `cli.py`
- `run.sh`
- `requirements.txt`
- `scripts/`
- `release_bundle.py`

---

## 环境要求

- Python 3.10+
- 能访问：
  - 1688
  - Ozon API
  - `https://api.mxou.cn`

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

---

## 首次使用先做什么

先执行：

```bash
python3 cli.py configure guide
```

它会告诉你当前缺什么配置。

---

## 必须配置的内容

用户必须自行配置：

### 1. 1688 AK

```bash
python3 cli.py configure 1688 --ak "<YOUR_AK>"
```

### 2. Ozon 店铺

```bash
python3 cli.py configure ozon --client-id "<ID>" --api-key "<KEY>"
```

如果你明确知道店铺合同币种，也可以一起写：

```bash
python3 cli.py configure ozon --client-id "<ID>" --api-key "<KEY>" --currency CNY
```

### 3. mxou token

需要先去：

```text
https://api.mxou.cn
```

注册并获取 token，然后执行：

```bash
python3 cli.py configure mxou --token "<TOKEN>"
```

---

## 先检查配置状态

```bash
python3 cli.py configure status
```

---

## 最常用命令

### 1. 文字找货并完整上架

```bash
python3 cli.py publish_flow --query "保温杯" --poll-status
```

### 2. 先 dry-run

```bash
python3 cli.py publish_flow --query "保温杯" --dry-run
```

### 3. 用 draft 文件继续发布

```bash
python3 cli.py publish_flow --draft-file draft_xxx.json --poll-status
```

### 4. 批量铺货

```bash
python3 cli.py publish_flow --drafts-file drafts.json --poll-status
```

### 5. 查询状态

```bash
python3 cli.py status --task-id "<TASK_ID>"
```

---

## 批量队列规则

批量上传时程序会自动形成队列。

默认并发策略：

- 1 个商品：串行
- 2~3 个商品：2 并发
- 4 个及以上：3 并发

也就是说：

- 用户一次上传 20 个商品时，不会 20 个一起跑
- 会按队列自动调度
- 默认最多 3 并发

如果手动传 `--max-workers`，当前版本也会自动限制到最大 `3`。

---

## 当前版本边界

首发版程序本身：

- 会优先使用 1688 真实重量/尺寸
- 会做文本解析与本地规则补充
- **不会内置调用 LLM 估算重量/尺寸**

如果仍然缺少可靠重量/尺寸，程序会返回：

- `metric_gaps`

由外部 agent 自己决定如何评估。

---

## 运行产物

运行后，程序会在本地生成自己的运行目录和缓存目录。  
这些属于本地运行数据，不属于发布包内容。

---

## 如果预检失败

优先执行：

```bash
python3 cli.py configure guide
python3 cli.py configure status
```

如果仍失败，重点检查：

- 1688 AK 是否有效
- Ozon `client_id / api_key` 是否正确
- mxou token 是否可用
- 当前网络是否能访问 Ozon / mxou

---

## 当前版本建议定位

这版适合作为：

- 首发版
- 内测版
- 小范围真实用户试用版

如果要进入大规模正式商用，建议先再做一轮：

- release 包态真实上架 smoke
- 批量 3~5 商品真实冒烟

---

## 构建命令

如果你在源码仓库里重新打包：

```bash
python3 release_bundle.py
```

输出文件在：

```text
dist/pounding-ozon-v0.1.0-lite.zip
```
