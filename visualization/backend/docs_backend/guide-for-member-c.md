# dPolyWatch 成员 C 完全指导手册

> 最后更新：2026-03-27
> 适用对象：成员 C（核心算法工程师 / Quant）以及需要对接的其他成员
> 写给完全零基础的小白，每一步都有详细解释

---

## 目录

- [第一部分：搭建成员 B 的环境](#第一部分搭建成员-b-的环境)
- [第二部分：验证成员 C 的工作成果](#第二部分验证成员-c-的工作成果)
- [第三部分：成员 C 接下来要做的事](#第三部分成员-c-接下来要做的事)
- [第四部分：成员 E 前端接入指南](#第四部分成员-e-前端接入指南)

---

# 第一部分：搭建成员 B 的环境

> 成员 B 建了一套数据采集管道：用 Docker 运行 TimescaleDB（一种数据库）+ Python 采集器（每 5 分钟从 Polymarket 抓价格）。我们的算法需要这个数据库才能运行"真实分析"。

## 前置条件：你的电脑需要装什么

### 1. 安装 Docker Desktop

Docker 是一个"容器化"工具——你可以把它理解为一个"虚拟机轻量版"，它能在你电脑上运行数据库，不需要你手动安装配置 PostgreSQL。

**Mac 用户：**
```bash
# 方法一：去官网下载安装包（推荐）
# 打开浏览器访问 https://www.docker.com/products/docker-desktop/
# 点击 "Download for Mac" -> 选择你的芯片类型（M1/M2/M3 选 Apple Silicon，老 Mac 选 Intel）
# 下载后双击 .dmg 文件，把 Docker 图标拖到 Applications 文件夹

# 方法二：用 Homebrew 安装（如果你已经有 brew）
brew install --cask docker
```

**安装完成后：**
1. 打开"启动台"（Launchpad），找到 Docker 图标，双击打开
2. 第一次启动会要求授权，点"允许"
3. 等菜单栏出现一个鲸鱼图标（小鲸鱼），说明 Docker 已经在运行了

**验证安装成功：**
```bash
# 打开终端（Terminal），输入以下命令
docker --version
# 应该输出类似：Docker version 27.x.x, build xxxxxxx

docker compose version
# 应该输出类似：Docker Compose version v2.x.x
```

> 如果提示 `command not found`，说明 Docker 没装好或者没启动。请确认菜单栏有鲸鱼图标。

### 2. 确认 Python 3.10+

```bash
python3 --version
# 应该输出 Python 3.10 或更高版本
# 我们项目使用 Python 3.14（虚拟环境已建好）
```

### 3. 确认 Git

```bash
git --version
# 应该输出 git version 2.x.x
```

---

## 第一步：进入项目目录

```bash
# 假设你的项目在这里（请替换成你的实际路径）
cd ~/6290
```

> 如何确认你在正确的位置？输入 `ls`，应该能看到 `core_analysis/`、`data_pipeline/`、`requirements.txt` 等文件。

---

## 第二步：启动 Docker 数据库

```bash
# 1. 进入数据管道目录
cd data_pipeline

# 2. 启动所有服务（-d 表示后台运行）
docker compose up -d
```

> **第一次运行**会比较慢（需要下载 TimescaleDB 镜像，约 500MB），之后就很快了。

你会看到类似这样的输出：
```
[+] Running 3/3
 ✔ Network data_pipeline_default          Created
 ✔ Container data_pipeline-timescaledb-1  Started
 ✔ Container data_pipeline-collector-1    Started
```

**验证数据库是否启动成功：**
```bash
# 查看容器状态
docker compose ps
```

你应该看到类似：
```
NAME                           STATUS         PORTS
data_pipeline-timescaledb-1    Up (healthy)   0.0.0.0:5433->5432/tcp
data_pipeline-collector-1      Up             
```

> **关键点：** `timescaledb` 的状态必须是 `Up (healthy)`。如果显示 `starting` 或 `unhealthy`，等 10-20 秒再检查。

---

## 第三步：导入历史数据（种子数据）

> 这一步很重要！数据库刚启动时是空的。我们需要导入 2024 年美国大选的 7,356 条历史价格数据，这是成员 C 算法回测的核心数据。

```bash
# 确保你在 data_pipeline/ 目录下
# 如果不确定，运行：
cd ~/6290/data_pipeline

# 1. 把种子 CSV 文件拷贝到数据库容器内
docker cp db/price_history_seed.csv data_pipeline-timescaledb-1:/tmp/seed.csv
```

> 如果报错说找不到 `data_pipeline-timescaledb-1`，可能你的容器名不同。
> 运行 `docker compose ps` 查看实际的容器名，替换掉命令中的名字。

```bash
# 2. 插入市场元数据（告诉数据库有哪些市场）
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
INSERT INTO markets (token_id, slug, question) VALUES
  ('21742633143463906290569050155826241533067272736897614950488156847949938836455',
   'presidential-election-winner-2024',
   'Will Donald Trump win the 2024 US Presidential Election?'),
  ('46553455570564517989191023458705371521436514261892866503067981558938998232024',
   'fed-decision-in-march-885',
   'Will the Fed decrease interest rates by 50+ bps after the March 2026 meeting?'),
  ('67028631656597977031363620447645908995417871899828777750494099295092202422178',
   'presidential-election-winner-2028',
   'Will Eric Trump win the 2028 US Presidential Election?'),
  ('60590045489347122735554346200880179420435533609307820342798544098823516727807',
   'democratic-presidential-nominee-2028',
   'Will Stephen A. Smith win the 2028 Democratic presidential nomination?'),
  ('8501497159083948713316135768103773293754490207922884688769443031624417212426',
   'what-will-happen-before-gta-vi',
   'Russia-Ukraine Ceasefire before GTA VI?'),
  ('5161623255678193352839985156330393796378434470119114669671615782853260939535',
   'will-trump-acquire-greenland-before-2027',
   'Will Trump acquire Greenland before 2027?')
ON CONFLICT (token_id) DO NOTHING;
"
```

> 这条命令很长，请完整复制粘贴。如果终端显示 `INSERT 0 6` 或 `INSERT 0 0`（已存在），都是正常的。

```bash
# 3. 导入价格历史数据
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
CREATE TEMP TABLE price_history_import (
    slug  TEXT,
    time  TIMESTAMPTZ,
    price NUMERIC(6,4)
);
COPY price_history_import FROM '/tmp/seed.csv' CSV HEADER;
INSERT INTO price_history (time, token_id, price)
SELECT i.time, m.token_id, i.price
FROM price_history_import i
JOIN markets m USING (slug)
ON CONFLICT (time, token_id) DO NOTHING;
"
```

**验证数据导入成功：**
```bash
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
SELECT m.slug, COUNT(*) AS 行数
FROM price_history ph
JOIN markets m USING (token_id)
GROUP BY m.slug
ORDER BY 行数 DESC;
"
```

你应该看到类似：
```
                   slug                    | 行数
-------------------------------------------+------
 presidential-election-winner-2024         | 7356
 what-will-happen-before-gta-vi            |  724
 will-trump-acquire-greenland-before-2027  |  712
```

> 如果 `presidential-election-winner-2024` 显示 7356 行，恭喜！数据导入成功。

---

## 第四步：确认 collector 正常运行

```bash
# 查看采集器实时日志
docker compose logs -f collector
```

你应该看到类似输出：
```
[collector] PolyWatch collector starting. Poll interval: 300s
[collector] Starting collection pass at 2026-03-27T...
[collector] presidential-election-winner-2024: already up to date.
[collector] what-will-happen-before-gta-vi: fetched 12 points, inserted 12 new rows.
[collector] will-trump-acquire-greenland-before-2027: fetched 12 points, inserted 12 new rows.
[collector] Pass complete.
```

> 按 `Ctrl+C` 退出日志查看。

---

## 第五步：回到项目根目录

```bash
cd ~/6290
```

---

## 常见问题

### Q: Docker 启动报错 "port 5433 is already in use"
说明端口被占用。运行：
```bash
# 查看谁占了 5433 端口
lsof -i :5433
# 关掉那个进程，或者修改 docker-compose.yml 中的端口映射
```

### Q: 怎么关闭数据库？
```bash
cd ~/6290/data_pipeline

# 关闭（保留数据，下次可以重新启动）
docker compose stop

# 重新启动
docker compose start

# 彻底删除（会丢失所有数据！）
docker compose down -v
```

### Q: 怎么确认数据库能从 Python 访问？
```bash
cd ~/6290
./venv/bin/python -c "
import psycopg2
conn = psycopg2.connect('postgresql://polywatch:polywatch@localhost:5433/polywatch')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM price_history')
print(f'数据库中共有 {cur.fetchone()[0]} 条价格记录')
conn.close()
"
```

---

# 第二部分：验证成员 C 的工作成果

> 这一部分教你怎么验证成员 C（也就是你自己）写的所有代码是否正确运行。

## 成员 C 的交付物清单

在开始验证之前，先了解我们做了什么：

### 核心算法模块

| 文件 | 功能 | 行数 |
|------|------|------|
| `core_analysis/zscore_detector.py` | Z-Score 异常检测算法 | ~313 |
| `core_analysis/benford_detector.py` | Benford 定律检测算法 | ~431 |
| `core_analysis/whale_alert.py` | 鲸鱼警报算法 | ~432 |
| `core_analysis/backtester.py` | 回测系统 | ~450 |
| `core_analysis/run_analysis.py` | 统一运行入口 (CLI) | ~382 |
| `core_analysis/api_server.py` | REST API 服务器（供成员 E 前端调用，7 个接口） | ~220 |

### 单元测试（共 83 个，全部通过）

| 文件 | 测试数 |
|------|--------|
| `tests/core_analysis/test_zscore_detector.py` | 15 |
| `tests/core_analysis/test_benford_detector.py` | 24 |
| `tests/core_analysis/test_whale_alert.py` | 18 |
| `tests/core_analysis/test_backtester.py` | 23 |
| 不含成员 B 的测试（23 个）和 E2E 测试（5 个，需要 DB）| - |

### Jupyter Notebooks

| 文件 | 内容 |
|------|------|
| `notebooks/01_zscore_analysis.ipynb` | Z-Score 分析 Notebook |
| `notebooks/02_benford_analysis.ipynb` | Benford 分析 Notebook |
| `notebooks/03_whale_alert_analysis.ipynb` | Whale Alert 分析 Notebook |
| `notebooks/04_backtest_report.ipynb` | 回测报告 Notebook |

### 文档与配置

| 文件 | 内容 |
|------|------|
| `docs/algorithm-accuracy-report.md` | 算法准确率报告 |
| `docs/guide-for-member-c.md` | 本指导手册 |
| `requirements.txt` | 已更新：添加 scipy, matplotlib, jupyter, pytest, flask, flask-cors |

### 已安装到虚拟环境的额外依赖

| 包 | 用途 |
|-----|------|
| `scipy` | Benford 卡方检验、KS 检验 |
| `matplotlib` | Notebook 图表 |
| `jupyter` | Notebook 运行 |
| `pytest` | 单元测试 |
| `flask` | REST API 服务器 |
| `flask-cors` | 允许前端跨域调用 API |

---

## 验证步骤 1：确认虚拟环境可用

### 这一步在干什么？为什么要做？

> **虚拟环境 (venv)** 是 Python 的一种隔离机制。你可以把它想象成一个"独立的 Python 小房间"——在这个房间里安装的所有库（numpy、pandas、flask 等）不会影响你电脑系统自带的 Python，反过来也一样。
>
> 我们的项目依赖很多第三方库（scipy、flask、pandas 等），全部安装在 `venv/` 这个文件夹中。如果这个文件夹不存在或者里面的东西损坏了，后面所有步骤都会失败。
>
> **所以这一步的目的是：确认 venv 文件夹存在，里面的 Python 可以用。**

### 具体操作

**第 1 步：打开终端（Terminal）**

- **Mac 用户：** 按 `Command + 空格`，输入 `Terminal`，回车打开
- **或者：** 在 Finder 中找到"应用程序" → "实用工具" → "终端"
- **如果你用 VSCode：** 按 `Ctrl + ~`（键盘左上角波浪线那个键）打开内置终端

**第 2 步：进入项目目录**

```bash
cd ~/6290
```

> **解释：** `cd` 是 "change directory"（切换目录）的缩写。`~/6290` 的意思是"我的家目录下面的 6290 文件夹"。`~` 代表你的家目录（比如 `/Users/你的用户名/`）。执行完这个命令后，你就"站在"了项目根目录里。

**第 3 步：检查虚拟环境是否存在**

```bash
ls venv/bin/python
```

> **解释：** `ls` 是 "list"（列出）的缩写，用来查看文件是否存在。这个命令的意思是"列出 `venv/bin/python` 这个文件"。
>
> - **如果你看到输出 `venv/bin/python`** → 说明虚拟环境存在，你可以继续下一步
> - **如果你看到 `No such file or directory`（没有这个文件或目录）** → 说明虚拟环境不存在，需要重新创建

**第 4 步（可选）：验证虚拟环境里的 Python 版本**

```bash
./venv/bin/python --version
```

> **解释：** `./venv/bin/python` 是指"用虚拟环境里的 Python 来执行"（而不是你电脑系统自带的 Python）。`--version` 是让它打印版本号。你应该看到类似 `Python 3.14.x` 的输出。
>
> **为什么前面要加 `./` ？** 因为我们要明确告诉系统"用当前目录下的 venv 里的 python"，而不是系统自带的 python。这是最重要的一点——后续所有命令都用 `./venv/bin/python` 或 `./venv/bin/pytest`，不要用裸的 `python` 或 `pytest`。

**第 5 步（可选）：检查关键依赖是否已安装**

```bash
./venv/bin/pip list | grep -i flask
```

> **解释：**
> - `./venv/bin/pip list` = 列出虚拟环境中已安装的所有包
> - `|` = "管道"符号，把上一个命令的输出传给下一个命令
> - `grep -i flask` = 从输出中筛选包含"flask"的行（`-i` 是忽略大小写）
>
> 你应该看到类似：
> ```
> Flask                    3.x.x
> flask-cors               5.x.x
> ```
> 这说明 Flask 已经装好了。

### 如果虚拟环境不存在怎么办？

如果第 3 步显示 `No such file or directory`，需要手动重新创建：

```bash
# 第一步：创建虚拟环境
python3 -m venv venv
```

> **解释：** `python3 -m venv venv` 的意思是"用 python3 运行 venv 模块，创建一个名叫 venv 的虚拟环境文件夹"。`-m` 是 "module"（模块）的缩写。第一个 `venv` 是模块名，第二个 `venv` 是你给文件夹起的名字。

```bash
# 第二步：在虚拟环境中安装所有项目依赖
./venv/bin/pip install -r requirements.txt
```

> **解释：**
> - `./venv/bin/pip` = 用虚拟环境里的 pip（Python 包管理器）
> - `install` = 安装
> - `-r requirements.txt` = 从 `requirements.txt` 文件中读取需要安装的包列表（`-r` 是 "requirements" 的缩写）
>
> 这个文件里列了项目需要的所有库（numpy、pandas、scipy、flask 等），pip 会自动全部下载安装。安装过程可能需要 1-3 分钟，取决于你的网速。

### 这一步可能遇到的问题

| 现象 | 原因 | 解决方法 |
|------|------|---------|
| `python3: command not found` | 你的电脑没有安装 Python 3 | 去 https://www.python.org/downloads/ 下载安装 |
| `pip install` 报网络错误 | 网络问题或被墙 | 试试加镜像源：`./venv/bin/pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| 装包时报 `gcc` 或编译错误 | 缺少 C 编译器（少见） | Mac 运行 `xcode-select --install` 安装开发工具 |

---

## 验证步骤 2：运行单元测试（不需要数据库）

### 这一步在干什么？为什么要做？

> **单元测试 (Unit Test)** 是软件工程中的一种验证方法。每个"测试"是一小段代码，它会调用我们写的函数，然后检查返回结果是否正确。就像数学考试的"对答案"——我们提前知道正确答案应该是什么，然后看代码算出来的结果是不是对的。
>
> **为什么这一步最重要？** 因为单元测试使用的是**合成数据**（代码自己造的假数据），不需要连接数据库，不需要 Docker，不需要网络。如果这 83 个测试全部通过，就能证明我们的算法代码**逻辑上是正确的**。
>
> **pytest 是什么？** `pytest` 是 Python 世界最流行的测试框架。你只要运行 `pytest` 命令，它会自动找到项目里所有以 `test_` 开头的文件，运行里面所有以 `test_` 开头的函数，然后告诉你哪些通过了、哪些失败了。

### 我们有哪些测试？每个测试在验证什么？

| 测试文件 | 测试数量 | 在验证什么 |
|----------|---------|-----------|
| `test_zscore_detector.py` | 15 个 | Z-Score 算法能否正确检测价格突变（比如：喂给它一段有明显尖刺的价格数据，看它能不能发现那个尖刺） |
| `test_benford_detector.py` | 24 个 | Benford 定律检测能否正确判断数据是否符合 Benford 分布（比如：给它一组符合 Benford 的数据，看它是否返回"正常"；给它一组造假数据，看它是否返回"异常"） |
| `test_whale_alert.py` | 18 个 | 鲸鱼警报能否正确识别大额交易（比如：在一堆小额交易中混入一笔巨额交易，看它能不能标记出来） |
| `test_backtester.py` | 23 个 | 回测系统能否正确计算准确率指标（比如：给它一组已知答案的数据，看它算出的 Precision/Recall 是否正确） |

### 具体操作

**第 1 步：确保你在项目根目录**

```bash
cd ~/6290
```

> 如果你已经在这个目录了（上一步已经 cd 过了），可以跳过。你可以输入 `pwd`（print working directory，打印当前目录）来确认你在哪。

**第 2 步：运行所有 83 个测试**

```bash
./venv/bin/pytest tests/core_analysis/test_zscore_detector.py \
                  tests/core_analysis/test_benford_detector.py \
                  tests/core_analysis/test_whale_alert.py \
                  tests/core_analysis/test_backtester.py \
                  -v
```

> **逐字解释这条命令：**
> - `./venv/bin/pytest` = 用虚拟环境里的 pytest 来运行测试
> - 后面跟的 4 个文件路径 = 告诉 pytest "只运行这 4 个文件里的测试"（不包含成员 B 的测试和需要数据库的 e2e 测试）
> - `\` = 续行符，意思是"这个命令还没写完，下一行继续"。这只是为了排版好看，你也可以把所有内容写在一行
> - `-v` = "verbose"（详细模式），让 pytest 显示每一个测试的名字和结果，而不只是一个总结
>
> **你也可以复制下面这个单行版本**（效果完全一样）：
> ```bash
> ./venv/bin/pytest tests/core_analysis/test_zscore_detector.py tests/core_analysis/test_benford_detector.py tests/core_analysis/test_whale_alert.py tests/core_analysis/test_backtester.py -v
> ```

**第 3 步：看懂输出结果**

运行后，屏幕上会滚动大量信息。这是正常的。关键是看**最后几行**。

**情况 A：全部通过（这是你应该看到的）**

```
tests/core_analysis/test_zscore_detector.py::TestZScoreDetector::test_detect_returns_dataframe PASSED
tests/core_analysis/test_zscore_detector.py::TestZScoreDetector::test_spike_detected PASSED
...
（中间省略很多行，每行都是一个测试）
...
tests/core_analysis/test_backtester.py::TestElectionEvents::test_at_least_5_events PASSED

============================== 83 passed in XX.XXs ==============================
```

> **怎么看这个输出：**
> - 每一行的格式是 `文件名::测试类名::测试函数名 PASSED`
>   - `PASSED` = 通过（绿色），说明这个测试点验证成功
>   - 如果有 `FAILED` = 失败（红色），说明有问题
> - **最后一行是总结**：`83 passed` 表示 83 个测试全部通过
> - `XX.XXs` 是运行耗时（通常在 5-20 秒之间）
>
> **你只需要确认：最后一行显示 `83 passed`，没有 `failed`，就说明代码全部正确。**

**情况 B：有测试失败（不应该发生）**

如果你看到类似：
```
============================== 2 failed, 81 passed in XX.XXs ==============================
```

那说明有 2 个测试没通过。屏幕上会有红色的错误信息，告诉你哪个测试失败了以及为什么。这种情况**正常情况下不会出现**，但如果出现了，可能原因是：
- 虚拟环境的包没有正确安装（解决：重新运行 `./venv/bin/pip install -r requirements.txt`）
- 文件被意外修改了（解决：用 `git status` 检查哪些文件被改过）

### 可选：分开运行每个文件的测试

如果你想一个一个文件地测（这样更容易看出哪个算法有问题）：

```bash
# 只测 Z-Score（预期：15 passed）
./venv/bin/pytest tests/core_analysis/test_zscore_detector.py -v

# 只测 Benford（预期：24 passed）
./venv/bin/pytest tests/core_analysis/test_benford_detector.py -v

# 只测 Whale Alert（预期：18 passed）
./venv/bin/pytest tests/core_analysis/test_whale_alert.py -v

# 只测回测系统（预期：23 passed）
./venv/bin/pytest tests/core_analysis/test_backtester.py -v
```

> **为什么要分开测？** 这 4 个文件对应 4 个模块。如果全部一起跑出了 FAILED，你很难知道是哪个模块的问题。分开跑就能精确定位。

### 可选：简洁模式

```bash
# 不加 -v，pytest 只显示一个总结（不列出每个测试名字）
./venv/bin/pytest tests/core_analysis/test_zscore_detector.py \
                  tests/core_analysis/test_benford_detector.py \
                  tests/core_analysis/test_whale_alert.py \
                  tests/core_analysis/test_backtester.py
```

> 输出会更短，类似 `83 passed in XX.XXs`，适合你已经确认没问题、只想快速跑一遍的情况。

---

## 验证步骤 3：运行真实数据分析（需要数据库）

### 这一步在干什么？为什么要做？

> 上一步（单元测试）验证的是算法逻辑是否正确，用的是"假数据"。这一步要用**真实数据**来运行算法——也就是从成员 B 搭建的 TimescaleDB 数据库中读取真实的 Polymarket 价格数据，然后用我们的三个检测器（Z-Score、Benford、Whale Alert）去分析。
>
> **这一步能证明什么？** 能证明我们的代码不仅逻辑正确，还能在真实环境中跑起来、产生有意义的结果。这对课程答辩和报告非常重要——你需要展示真实数据的分析结果截图。
>
> **`run_analysis.py` 是什么？** 这是我们写的一个"统一运行入口"。它会连接数据库、读取价格数据、运行三个检测器、输出结果。可以把它理解为一个"一键分析"工具。

### 前提条件

> **你必须先完成第一部分（搭建成员 B 的环境），确保：**
> 1. Docker Desktop 正在运行（菜单栏有小鲸鱼图标）
> 2. 数据库容器已启动（`docker compose up -d` 已执行）
> 3. 历史数据已导入（`price_history_seed.csv` 已导入）
>
> **如果你还没做第一部分，请先跳回去做。这一步没有数据库是跑不了的。**

### 具体操作

**第 1 步：确认数据库在运行**

```bash
cd ~/6290/data_pipeline
docker compose ps
```

> **解释：** `docker compose ps` 会列出所有正在运行的 Docker 容器。你应该看到 `timescaledb` 和 `collector` 两个容器的状态是 `Up`（运行中）。
>
> 如果状态是 `Exit` 或者根本没有输出，说明数据库没在运行，需要先启动：
> ```bash
> docker compose up -d
> ```
> （`-d` 表示在后台运行，不会占着你的终端窗口。）

**第 2 步：回到项目根目录**

```bash
cd ~/6290
```

**第 3 步：用 dry-run 模式运行分析**

```bash
./venv/bin/python -m core_analysis.run_analysis --dry-run
```

> **逐字解释这条命令：**
> - `./venv/bin/python` = 用虚拟环境的 Python
> - `-m core_analysis.run_analysis` = 把 `core_analysis/run_analysis.py` 当作模块来运行。`-m` 表示 "module"（模块），Python 会自动找到 `core_analysis` 文件夹下的 `run_analysis.py` 来执行
> - `--dry-run` = "干跑"模式。**这是一个非常重要的参数！** 它的意思是"运行分析但**不把结果写入数据库**"。只是在屏幕上打印结果，不修改任何数据。第一次运行时建议永远先用 dry-run，确认没问题再正式跑。
>
> **为什么用 `-m` 而不是直接 `python core_analysis/run_analysis.py`？** 因为用 `-m` 可以让 Python 正确处理模块之间的导入关系（比如 `run_analysis.py` 需要导入 `db_interface.py`）。如果用直接路径运行，可能会报 `ModuleNotFoundError`（找不到模块）的错误。

**第 4 步：看懂输出结果**

运行后你应该看到类似这样的输出（具体数字可能不同）：

```
╔══════════════════════════════════════════════════════════════╗
║   PolyWatch Anomaly Detection Engine v1.0                    ║
║   Member C — Core Algorithm Module                           ║
╚══════════════════════════════════════════════════════════════╝

Found 3 active markets
```

> **解释：** 程序连接了数据库，发现有 3 个市场有数据：
> 1. `presidential-election-winner-2024`（2024 美国大选）
> 2. `what-will-happen-before-gta-vi`（GTA6 相关）
> 3. `will-trump-acquire-greenland-before-2027`（格陵兰相关）

```
============================================================
  Market: presidential-election-winner-2024
============================================================
  Data points: 7356
  Time range: 2024-01-05 ... ~ 2024-11-06 ...
```

> **解释：** 正在分析第一个市场。`Data points: 7356` 表示这个市场有 7356 条价格记录。`Time range` 是数据的时间范围（2024 年 1 月到 11 月）。

```
  [Z-Score] Running...
  [Z-Score] Anomalies: XX (X.X%)
```

> **解释：** Z-Score 检测器运行完毕。`Anomalies: XX` 表示检测到 XX 个异常点。`(X.X%)` 是异常率——即异常点占总数据点的百分比。一般来说异常率在 1%-5% 是合理的。

```
  [Benford] Running...
  [Benford] Overall conforming: True/False
  [Benford] Anomaly windows: X
```

> **解释：**
> - `Overall conforming: True` = 整体来看，价格变化的首位数字分布**符合** Benford 定律（说明没有大规模造假）
> - `Overall conforming: False` = 整体**不符合** Benford 定律（可能有异常）
> - `Anomaly windows: X` = 在滑动窗口分析中，有 X 个时间窗口不符合 Benford 定律

```
  [Whale Alert] Running...
  [Whale Alert] Whale trades: X
```

> **解释：** 鲸鱼警报检测到 X 笔可疑的大额交易。注意，由于我们没有真实的交易量数据，这里用的是从价格变化模拟出来的交易数据（详见 `findings.md`）。

> **看到这些输出就说明分析成功了。** 程序没有报错，三个检测器都正常运行，产生了有意义的结果。

### 其他运行方式

```bash
# 只分析某一个市场（用 --market 参数指定市场 slug）
./venv/bin/python -m core_analysis.run_analysis \
    --market presidential-election-winner-2024 \
    --dry-run
```

> **解释：** `--market` 后面跟的是市场的"slug"（唯一标识符）。如果不指定，默认分析所有市场。

```bash
# 只运行某一个检测器（用 --detector 参数指定）
./venv/bin/python -m core_analysis.run_analysis \
    --detector zscore \
    --dry-run
```

> **解释：** `--detector` 可以是 `zscore`、`benford` 或 `whale`。如果不指定，默认三个全跑。

```bash
# 把结果保存到 JSON 文件（方便之后分析或交给前端）
./venv/bin/python -m core_analysis.run_analysis \
    --dry-run \
    --output results.json
```

> **解释：** `--output results.json` 让程序把结果写入一个叫 `results.json` 的文件。JSON 是一种数据格式，你可以用 VSCode 打开查看。

```bash
# 正式运行（结果会写入 anomaly_events 数据库表）
./venv/bin/python -m core_analysis.run_analysis
```

> **注意：** 不加 `--dry-run` 就是正式模式，检测到的异常会被写入数据库的 `anomaly_events` 表。这样成员 E 的前端就能通过 API 查询到这些异常了。**建议先跑一次 dry-run 确认没问题，再跑正式的。**

### 这一步可能遇到的问题

| 现象 | 原因 | 解决方法 |
|------|------|---------|
| `Connection refused` 或 `could not connect to server` | 数据库没在运行 | `cd ~/6290/data_pipeline && docker compose up -d` |
| `Found 0 active markets` | 数据库在运行但没有数据 | 需要导入种子数据，参见第一部分 |
| `ModuleNotFoundError: No module named 'xxx'` | 虚拟环境缺少某个包 | `./venv/bin/pip install -r requirements.txt` |

---

## 验证步骤 4：运行回测（需要数据库）

### 这一步在干什么？为什么要做？

> **回测 (Backtesting)** 是量化交易/金融工程中的核心概念。简单说就是：**用历史数据来检验算法到底有多准。**
>
> 具体来说：
> 1. 我们知道 2024 年美国大选期间发生了哪些重大事件（Trump 被枪击、Biden 退选等），这些事件导致了真实的价格剧烈波动
> 2. 我们把这些"已知会导致异常的时间点"标记出来，作为**标准答案**（ground truth）
> 3. 然后让算法"假装不知道答案"去分析这些历史数据
> 4. 最后对比算法的检测结果和标准答案，算出准确率
>
> **计算的指标是什么意思？**
> - **Precision（精确率）**：算法说"这是异常"的时候，有多大比例真的是异常？Precision = 0.8 表示算法标记的异常中 80% 确实是真异常，20% 是误报
> - **Recall（召回率）**：所有真实异常中，算法找到了多大比例？Recall = 0.7 表示真实异常中有 70% 被算法找到了，30% 被漏掉了
> - **F1 Score**：Precision 和 Recall 的调和平均数，综合评分。F1 越接近 1 越好
> - **TP（True Positive）**：真异常，算法也说异常 → 正确检测
> - **FP（False Positive）**：不是异常，但算法说是异常 → 误报
> - **FN（False Negative）**：真异常，但算法没检测到 → 漏报
> - **TN（True Negative）**：不是异常，算法也说不是 → 正确忽略

### 前提条件

> 跟验证步骤 3 一样：需要 Docker 数据库在运行，并且有 2024 大选的历史数据（`presidential-election-winner-2024` 市场的 7356 条价格记录）。

### 具体操作

**第 1 步：确保你在项目根目录且数据库在运行**

```bash
cd ~/6290

# 快速检查数据库状态
cd data_pipeline && docker compose ps && cd ..
```

> 确认 `timescaledb` 状态是 `Up`。

**第 2 步：运行回测**

```bash
./venv/bin/python -m core_analysis.run_analysis --backtest
```

> **解释：** `--backtest` 参数告诉程序进入"回测模式"。程序会：
> 1. 读取 `presidential-election-winner-2024` 市场的全部 7356 条历史价格数据
> 2. 根据 2024 年的重大事件时间线，标记哪些时间点**应该**被检测为异常（这就是标准答案）
> 3. 运行三个检测器
> 4. 将检测结果与标准答案逐一对比
> 5. 计算 Precision / Recall / F1 / TP / FP / FN / TN
> 6. 额外检查：每个已知事件（如 Trump 枪击）是否被检测到

**第 3 步：看懂输出结果**

```
============================================================
  BACKTEST MODE: presidential-election-winner-2024
============================================================
  Data points: 7356
  Ground truth positives: XXX / 7356
```

> **解释：**
> - `Data points: 7356` = 用于回测的数据点总数
> - `Ground truth positives: XXX / 7356` = 标准答案中有 XXX 个时间点被标记为"应该检测到异常"（其余的是正常时间点）

```
  Running all detectors...

  ──────────────────────────────────────────────
  RESULTS:
  ──────────────────────────────────────────────

  ZSCORE:
    Precision: 0.XXXX
    Recall:    0.XXXX
    F1:        0.XXXX
    TP=XX, FP=XX, FN=XX, TN=XXXX
```

> **怎么解读这些数字：**
> - `Precision: 0.65` → Z-Score 报告的异常中，65% 确实是真异常
> - `Recall: 0.80` → 真实异常中，80% 被 Z-Score 找到了
> - `F1: 0.72` → 综合评分 0.72（满分 1.0）
> - `TP=40` → 40 个异常被正确检测到
> - `FP=22` → 22 个误报（其实不是异常，但算法说是）
> - `FN=10` → 10 个漏报（真异常但没检测到）
> - `TN=7284` → 7284 个正常点被正确忽略
>
> **这些数值没有"标准答案"——因为异常检测本身就是模糊的。** 一般来说，F1 > 0.5 就算可以用了。课程报告中解释为什么某些事件被检测到、某些没有，比数字本身更重要。

```
  Event Detection:
    [DETECTED] Trump Shooting (2024-07-13) peak_z=X.XX
    [DETECTED] Biden Dropout (2024-07-21) peak_z=X.XX
    [MISSED]   Iowa Caucus (2024-01-15)
    ...
```

> **解释：** 这部分逐一检查已知历史事件：
> - `[DETECTED]` = 该事件被算法检测到了，`peak_z=X.XX` 是该事件附近的最大 Z-Score 值（越大说明异常越明显）
> - `[MISSED]` = 该事件没被检测到
>
> **Trump Shooting 和 Biden Dropout 几乎一定会被检测到**（因为这两个事件导致了巨大的价格波动）。Iowa Caucus 这种影响较小的事件可能会被漏掉，这是正常的。

> **看到了 Precision/Recall/F1 数值和事件检测结果，就说明回测成功了。** 截个图保存，课程答辩会用到。

---

## 验证步骤 5：运行 Jupyter Notebooks

### 这一步在干什么？为什么要做？

> **Jupyter Notebook** 是一种交互式编程环境，可以在浏览器里一格一格地运行代码，还能显示图表、表格等可视化内容。在学术界和数据科学中非常流行。
>
> 我们写了 4 个 Notebook，每个对应一个算法模块。它们的作用是：
> 1. **生成可视化图表**（价格走势图、异常标记图、Benford 分布图等）——课程报告和答辩 PPT 可以直接用
> 2. **提供交互式分析环境**——你可以修改参数重新运行，探索不同阈值的效果
> 3. **作为算法说明文档**——每个 Notebook 里有详细的文字解释

### 具体操作

**第 1 步：确保你在项目根目录**

```bash
cd ~/6290
```

**第 2 步：启动 Jupyter Notebook 服务**

```bash
./venv/bin/jupyter notebook notebooks/
```

> **逐字解释这条命令：**
> - `./venv/bin/jupyter` = 用虚拟环境里的 jupyter
> - `notebook` = 启动 Notebook 服务（不是 JupyterLab）
> - `notebooks/` = 让 Jupyter 以 `notebooks/` 文件夹作为根目录打开
>
> 运行后，终端会输出类似：
> ```
> [I 2026-03-27 15:00:00.000 ServerApp] Jupyter Server is running at:
> [I 2026-03-27 15:00:00.000 ServerApp]     http://localhost:8888/tree?token=abc123...
> ```
> **同时，你的默认浏览器应该会自动打开一个新标签页**，显示 Jupyter 的文件列表界面。
>
> 如果浏览器没有自动打开，手动复制终端中那个 `http://localhost:8888/tree?token=...` 链接，粘贴到浏览器地址栏打开。

**第 3 步：依次打开并运行每个 Notebook**

在浏览器中你会看到 4 个 `.ipynb` 文件：

| 文件名 | 内容 | 是否需要数据库 |
|--------|------|---------------|
| `01_zscore_analysis.ipynb` | Z-Score 算法的可视化分析：价格走势图 + 异常标记 | 有数据库更好，但有合成数据回退方案 |
| `02_benford_analysis.ipynb` | Benford 定律分析：首位数字分布柱状图 | 同上 |
| `03_whale_alert_analysis.ipynb` | 鲸鱼警报分析：大额交易检测 | 同上 |
| `04_backtest_report.ipynb` | 回测结果报告：P/R/F1 汇总 | 需要数据库 |

**对每个 Notebook 做以下操作：**

1. **点击文件名** → 打开 Notebook
2. **点击顶部菜单 `Cell` → `Run All`** → 一次性运行所有代码格
   - 或者用快捷键：`Shift + Enter` 可以逐格运行（按一次运行一格，再按运行下一格）
3. **等待运行完成**（可能需要几秒到几十秒）
4. **检查结果：**
   - 代码格下方应该出现输出（文字、表格或图表）
   - **绿色/无色** = 正常运行
   - **红色文字** = 出了错误。如果是 `ConnectionRefused` 类错误，说明数据库没开；其他错误请截图
5. **查看图表**：如果一切正常，你应该能看到漂亮的价格走势图、异常标记点、柱状图等

**第 4 步：关闭 Jupyter**

在终端中按 `Ctrl + C`（同时按 Control 键和 C 键），然后输入 `y` 回车确认关闭。

> **注意：** Jupyter 运行时会占着你的终端窗口。如果你想同时做其他事，可以打开一个新的终端窗口/标签页。

### 这一步可能遇到的问题

| 现象 | 原因 | 解决方法 |
|------|------|---------|
| `jupyter: command not found` | jupyter 没安装在虚拟环境中 | `./venv/bin/pip install jupyter` |
| Notebook 报 `ConnectionRefused` | 数据库没启动 | 启动 Docker：`cd ~/6290/data_pipeline && docker compose up -d` |
| 图表没显示 | matplotlib 可能没装 | `./venv/bin/pip install matplotlib` |
| 浏览器没自动打开 | 系统设置问题 | 手动复制终端中的 URL 到浏览器打开 |

---

## 验证步骤 6：查看文档

### 这一步在干什么？为什么要做？

> 除了代码之外，课程项目还需要文档说明。我们写了一份**算法准确率报告**（`docs/algorithm-accuracy-report.md`），里面详细解释了每个算法的原理、参数选择理由、在真实数据上的表现、已知限制等。
>
> 这份文档可以直接用在你的课程报告中（复制粘贴或引用均可）。

### 具体操作

**方法一：用 VSCode 打开（推荐，Markdown 渲染效果好）**

```bash
code docs/algorithm-accuracy-report.md
```

> **解释：** `code` 是 VSCode 的命令行工具。如果你安装了 VSCode，这个命令会直接在 VSCode 中打开文件。VSCode 支持 Markdown 预览——打开文件后，按 `Ctrl+Shift+V`（Mac 用 `Cmd+Shift+V`）可以看到渲染后的效果（标题、表格、粗体等）。
>
> 如果提示 `code: command not found`，说明 VSCode 的命令行工具没有安装。在 VSCode 里按 `Cmd+Shift+P`（Mac）或 `Ctrl+Shift+P`（Windows），输入 `Shell Command: Install`，选择"Install 'code' command in PATH"即可。

**方法二：用 cat 在终端查看（不推荐，没有渲染效果）**

```bash
cat docs/algorithm-accuracy-report.md
```

> **解释：** `cat` = "concatenate"（连接），用来把文件内容打印到终端。缺点是 Markdown 的格式标记（`#`、`**`、`|` 等）不会被渲染，直接以纯文本显示，可读性差。

**方法三：用浏览器打开（如果你装了 Markdown 预览插件）**

在 Finder 中找到 `~/6290/docs/algorithm-accuracy-report.md`，双击用支持 Markdown 的应用打开。

**你应该看到的内容：**

报告包含以下几个部分：
1. 三个算法（Z-Score、Benford、Whale Alert）的原理简述
2. 参数选择和阈值设置的理由
3. 在 2024 大选数据上的表现（准确率指标）
4. 已知限制和改进方向

> **确认文件存在且内容完整即可。** 内容不需要修改。

---

## 验证总结

以下是所有验证步骤的速查表。**建议从上到下依次执行。** "需要 DB" 列标注了哪些步骤需要 Docker 数据库在运行——如果你还没搭好数据库环境，可以先只做不需要 DB 的步骤（步骤 1、2、6）。

| 步骤 | 验证项 | 命令 | 预期结果 | 需要 DB？ |
|------|--------|------|---------|-----------|
| 1 | 虚拟环境 | `ls venv/bin/python` | 文件存在 | 不需要 |
| 2 | 单元测试 | `./venv/bin/pytest tests/core_analysis/test_zscore_detector.py tests/core_analysis/test_benford_detector.py tests/core_analysis/test_whale_alert.py tests/core_analysis/test_backtester.py -v` | 83 passed, 0 failed | 不需要 |
| 3 | 真实数据分析 | `./venv/bin/python -m core_analysis.run_analysis --dry-run` | 3 个市场有分析输出 | 需要 |
| 4 | 回测 | `./venv/bin/python -m core_analysis.run_analysis --backtest` | 有 P/R/F1 数值和事件检测结果 | 需要 |
| 5 | Notebooks | `./venv/bin/jupyter notebook notebooks/` | 4 个 Notebook 可运行，图表正常 | 部分需要 |
| 6 | 文档 | 打开 `docs/algorithm-accuracy-report.md` | 内容完整（算法原理 + 准确率 + 限制） | 不需要 |

> **最低验证标准（不需要数据库就能完成）：** 步骤 1 + 步骤 2 + 步骤 6。如果这三步都通过了，就能证明代码是正确的。
>
> **完整验证标准（需要数据库）：** 全部 6 步都通过。这能证明代码不仅正确，还能在真实环境中运行并产生有意义的结果。

---

# 第三部分：成员 C 接下来要做的事

> 核心代码已全部完成。以下是建议的后续工作，按优先级排列。

## 任务 1：用真实数据运行完整分析并截图（高优先级）

> 为什么：课程答辩/报告需要真实数据的运行结果作为证据。

**步骤：**

```bash
# 1. 确保 Docker 数据库在运行
cd ~/6290/data_pipeline
docker compose ps
# 如果没运行，执行 docker compose up -d

# 2. 回到项目根目录
cd ~/6290

# 3. 运行完整分析，结果写入数据库
./venv/bin/python -m core_analysis.run_analysis

# 4. 运行回测，结果保存到 JSON
./venv/bin/python -m core_analysis.run_analysis --backtest --output backtest_results.json

# 5. 确认异常事件已写入数据库
cd ~/6290/data_pipeline
docker compose exec timescaledb psql -U polywatch -d polywatch -c "
SELECT event_type, severity, COUNT(*)
FROM anomaly_events
GROUP BY event_type, severity
ORDER BY event_type, severity;
"
```

> 截图保存终端输出，特别是回测的 Precision/Recall/F1 结果和事件检测结果。

---

## 任务 2：运行 Notebooks 生成可视化图表（高优先级）

> 为什么：图表是报告/答辩的核心素材。

```bash
cd ~/6290

# 启动 Jupyter
./venv/bin/jupyter notebook notebooks/
```

在每个 Notebook 中运行所有 Cell，截图/导出以下图表：
- **01_zscore**: 价格曲线 + Z-Score 异常标记图
- **02_benford**: 第一位数字分布 vs Benford 理论分布的柱状图
- **03_whale_alert**: 大额交易标记图
- **04_backtest**: 回测 Precision/Recall 报告、事件检测表格

---

## 任务 3：调优算法参数（中优先级）

> 为什么：回测结果可能显示某些参数不够理想（比如 F1 偏低），需要调参。

回测系统支持参数网格搜索。可以在回测结果的 JSON 文件中查看 `grid_search_top5` 字段，找到最优参数组合：

```bash
# 查看回测结果中的最优参数
cd ~/6290
./venv/bin/python -c "
import json
with open('backtest_results.json') as f:
    data = json.load(f)
top5 = data.get('backtest', {}).get('grid_search_top5', [])
for i, cfg in enumerate(top5):
    print(f'#{i+1}: z_threshold={cfg.get(\"z_threshold\")}, '
          f'short_window={cfg.get(\"short_window\")}, '
          f'F1={cfg.get(\"f1\", \"N/A\")}')
"
```

如果想用更优的参数，修改 `core_analysis/zscore_detector.py` 中 `ZScoreConfig` 的默认值：

```python
@dataclass
class ZScoreConfig:
    z_threshold: float = 2.5       # ← 改这里
    short_window: int = 6          # ← 改这里（单位：数据点数）
    medium_window: int = 24
    long_window: int = 72
```

---

## 任务 4：撰写最终报告中的算法部分（高优先级）

> 为什么：课程作业需要提交书面报告。

你需要在报告中包含：

1. **算法原理说明**（每个算法 1-2 段）
   - Z-Score: 基于统计学的异常检测，计算价格偏离均值的标准差数
   - Benford 定律: 自然产生的数据的首位数字遵循特定分布，偏离说明数据被人为操纵
   - Whale Alert: 检测大额交易和短时间内的异常交易量集中

2. **数据说明**
   - 数据来源：Polymarket CLOB API
   - 数据量：3 个市场，共约 8,800+ 条价格记录
   - 数据缺口：无交易量数据，Benford 和 Whale 使用代理方案

3. **回测结果**（用 backtest_results.json 中的数据填表）

4. **图表**（来自 Notebooks）

> 参考 `docs/algorithm-accuracy-report.md`，里面已经有一份完整的框架。

---

## 任务 5：为成员 E 准备 API 接口（已完成 ✅）

> `core_analysis/api_server.py` 已创建，包含 7 个 REST API 接口。详见第四部分了解如何启动和测试。

---

## 任务 6：添加更多监控市场（低优先级）

如果想让系统监控更多市场：

```bash
# 1. 编辑 data_pipeline/collector/main.py
# 在 TRACKED_MARKETS 列表中添加新的 slug

# 2. 重建 collector 容器
cd ~/6290/data_pipeline
docker compose up -d --build collector
```

---

## 任务 7：考虑获取真实交易量数据（低优先级）

目前 Benford 定律和 Whale Alert 使用的是**代理数据**（用价格变化模拟交易）。如果能获取真实交易量数据，算法精度会更高。可以：

1. 联系成员 B，看是否能在采集器中增加 Polymarket Order Book API 的对接
2. 或者使用 Polymarket 的 WebSocket API 实时监听成交数据

> 这不是必须的——当前的代理方案已经能工作，但在报告中应该诚实说明这个限制。

---

# 第四部分：成员 E 前端接入指南

> 成员 E 负责前端可视化。这一部分解释 E 需要什么数据、现有系统提供了什么、还缺什么、以及如何补齐。

## 现有系统能提供什么

成员 B 的 `core_analysis/db_interface.py` 已经提供了 E 需要的所有核心数据查询函数：

| 函数 | 返回 | E 的用途 |
|------|------|---------|
| `get_markets_df()` | 所有市场列表 + 最新/前一天价格 | 市场列表页 |
| `get_price_series(slug)` | 某市场全部价格历史 | 价格走势图 |
| `query_anomalies(slug)` | 某市场的异常事件列表 | 异常事件标记 / 列表 |
| `get_active_slugs()` | 有数据的市场 slug 列表 | 市场筛选 |
| `get_market_stats()` | 每个市场的统计信息 | 仪表盘数据 |

## E 的前端大概需要哪些页面

1. **市场列表页** — 显示所有监控中的市场，当前价格，24h 涨跌幅
2. **市场详情页** — 某个市场的价格走势图 + 异常事件标记
3. **异常事件列表页** — 所有检测到的异常事件，可按类型/严重程度筛选
4. **回测报告页**（可选）— 展示算法准确率指标

## REST API 层（已完成）

> **好消息：** `core_analysis/api_server.py` 已经创建完成，包含 7 个 REST API 接口，把现有的数据库查询函数包装成了 HTTP API，供前端直接调用。

### 解决的核心问题

所有数据查询函数都是 Python 函数，直接连数据库。前端（JavaScript/React/Vue）不能直接调 Python 函数，所以我们创建了 Flask HTTP API 作为中间层。

---

## API 服务器使用方法

### 步骤 1：确认依赖已安装

`flask` 和 `flask-cors` 已在 `requirements.txt` 中。如果虚拟环境是新建的，只需运行：

```bash
cd ~/6290
./venv/bin/pip install -r requirements.txt
```

### 步骤 2：查看 API 服务器文件

文件已存在于 `core_analysis/api_server.py`（约 260 行），无需手动创建。

该文件包含 7 个 REST API 接口，所有接口都有 `try/except` 错误处理：

| 接口 | 方法 | 路径 | 功能 |
|------|------|------|------|
| 健康检查 | GET | `/api/health` | 返回服务状态 |
| 市场列表 | GET | `/api/markets` | 所有市场 + 最新/前一天价格 |
| 价格历史 | GET | `/api/markets/<slug>/prices` | 某市场价格历史（可选 `?since=`） |
| 市场统计 | GET | `/api/markets/<slug>/stats` | 行数、时间范围、均价 |
| 数据缺口 | GET | `/api/markets/<slug>/gaps` | 数据采集缺口 |
| 异常事件 | GET | `/api/anomalies` | 检测到的异常（可选 `?slug=` `?severity=`） |
| 实时分析 | POST | `/api/analyze/<slug>` | 按需运行检测器 |

> 如果你想查看完整代码，直接打开 `core_analysis/api_server.py` 即可。

### 步骤 3：启动 API 服务器

```bash
cd ~/6290

# 确保数据库在运行
cd data_pipeline && docker compose ps && cd ..

# 启动 API
./venv/bin/python -m core_analysis.api_server
```

你会看到：
```
==================================================
  PolyWatch API Server
  http://localhost:5000
==================================================

可用接口：
  GET  /api/health                - 健康检查
  GET  /api/markets               - 市场列表
  GET  /api/markets/<slug>/prices  - 价格历史
  GET  /api/markets/<slug>/stats   - 市场统计
  GET  /api/markets/<slug>/gaps    - 数据缺口
  GET  /api/anomalies              - 异常事件列表
  POST /api/analyze/<slug>         - 实时分析
```

### 步骤 4：测试 API 是否工作

打开另一个终端窗口，运行：

```bash
# 测试健康检查
curl http://localhost:5000/api/health | python3 -m json.tool

# 测试市场列表
curl http://localhost:5000/api/markets | python3 -m json.tool

# 测试价格历史（只取最近 7 天）
curl "http://localhost:5000/api/markets/presidential-election-winner-2024/prices?since=2024-11-01" | python3 -m json.tool

# 测试异常事件
curl http://localhost:5000/api/anomalies | python3 -m json.tool

# 测试实时分析（POST 请求）
curl -X POST http://localhost:5000/api/analyze/presidential-election-winner-2024 \
     -H "Content-Type: application/json" \
     -d '{"detectors": ["zscore"]}' | python3 -m json.tool
```

---

## 给成员 E 的接口文档

> 把以下内容发给成员 E，这就是他需要知道的全部。

### 基础信息

- **API 地址：** `http://localhost:5000`（开发环境）
- **格式：** 所有接口返回 JSON
- **跨域：** 已启用 CORS，前端可以直接调用
- **认证：** 无（内网开发环境）

### 接口列表

#### 0. `GET /api/health` — 健康检查

**请求：** 无参数

**响应示例：**
```json
{
  "status": "ok",
  "service": "polywatch-api"
}
```

**前端用途：** 检测后端是否在线，可在页面顶部显示连接状态指示灯。

---

#### 1. `GET /api/markets` — 获取市场列表

**请求：** 无参数

**响应示例：**
```json
[
  {
    "slug": "presidential-election-winner-2024",
    "question": "Will Donald Trump win the 2024 US Presidential Election?",
    "active": true,
    "lastPrice": 0.9500,
    "prevPrice": 0.9300
  }
]
```

**前端用途：** 渲染市场卡片列表，显示名称、当前价格、24h 涨跌幅（`lastPrice - prevPrice`）。

---

#### 2. `GET /api/markets/<slug>/prices` — 获取价格历史

**请求参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `since` | string | 否 | ISO 日期，如 `2024-10-01`，只返回该日期之后的数据 |

**请求示例：**
```
GET /api/markets/presidential-election-winner-2024/prices?since=2024-10-01
```

**响应示例：**
```json
[
  {"time": "2024-10-01T00:00:03+00:00", "price": 0.5200},
  {"time": "2024-10-01T01:00:01+00:00", "price": 0.5210},
  ...
]
```

**前端用途：** 绘制价格走势折线图（X 轴 = time，Y 轴 = price）。

---

#### 3. `GET /api/markets/<slug>/stats` — 获取市场统计

**响应示例：**
```json
{
  "slug": "presidential-election-winner-2024",
  "question": "Will Donald Trump win...",
  "rowCount": 7356,
  "firstTime": "2024-01-05T00:00:03+00:00",
  "lastTime": "2024-11-06T04:00:01+00:00",
  "avgPrice": 0.527
}
```

**前端用途：** 市场详情页的元信息展示。

---

#### 4. `GET /api/markets/<slug>/gaps` — 获取数据缺口

**响应示例：**
```json
[
  {
    "start": "2024-03-15T12:00:00+00:00",
    "end": "2024-03-15T18:00:00+00:00",
    "duration_hours": 6.0
  }
]
```

**前端用途：** 在价格走势图上标记数据缺口区域（灰色虚线区域），提示用户该段时间无采集数据。

---

#### 5. `GET /api/anomalies` — 获取异常事件列表

**请求参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `slug` | string | 否 | 按市场筛选 |
| `severity` | string | 否 | 按严重程度筛选：`low` / `medium` / `high` |

**请求示例：**
```
GET /api/anomalies?slug=presidential-election-winner-2024&severity=high
```

**响应示例：**
```json
[
  {
    "id": 42,
    "marketSlug": "presidential-election-winner-2024",
    "detectedAt": "2024-07-13T18:00:00+00:00",
    "eventType": "zscore_spike",
    "severity": "high",
    "detail": {
      "zscore": 4.2,
      "price": 0.87,
      "description": "Price spike detected"
    }
  }
]
```

**前端用途：**
- 在价格走势图上用红点/标记显示异常位置
- 渲染异常事件列表/表格
- 按严重程度显示不同颜色（high=红, medium=橙, low=黄）

**eventType 可能的值：**
| eventType | 含义 |
|-----------|------|
| `zscore_spike` | Z-Score 检测到价格突变 |
| `benford_anomaly` | Benford 定律检测到数据异常 |
| `whale_trade` | 检测到大额交易/鲸鱼活动 |
| `price_return_spike` | 价格收益率突变 |
| `cumulative_volume_spike` | 交易量累积突变 |

**severity 可能的值：**
| severity | 含义 |
|----------|------|
| `low` | 轻微异常，可能是正常波动 |
| `medium` | 中等异常，值得关注 |
| `high` | 严重异常，强烈疑似操纵 |

---

#### 6. `POST /api/analyze/<slug>` — 按需实时分析

> 这个接口触发对指定市场的实时异常检测分析，不会写入数据库。

**请求体：**
```json
{
  "detectors": ["zscore", "benford", "whale"]
}
```

> `detectors` 是可选的，默认运行全部三个。

**响应示例：**
```json
{
  "zscore": {
    "anomalyCount": 156,
    "anomalyRate": 2.1,
    "events": [
      {
        "timestamp": "2024-07-13T18:00:00+00:00",
        "event_type": "zscore_spike",
        "severity": "high",
        "detail": {"zscore": 4.2, "price": 0.87}
      }
    ]
  },
  "benford": {
    "overallConforming": true,
    "anomalyWindows": 3,
    "summary": {...}
  },
  "whale": {
    "whaleTradeCount": 12,
    "totalTrades": 500,
    "events": [...]
  }
}
```

**前端用途：** "分析"按钮——用户点击后触发实时分析，显示结果。

---

## 前端 JavaScript 调用示例

E 在前端中可以这样调用（以 React/fetch 为例）：

```javascript
// 获取市场列表
const markets = await fetch("http://localhost:5000/api/markets")
  .then(res => res.json());

// 获取某市场最近30天的价格
const prices = await fetch(
  "http://localhost:5000/api/markets/presidential-election-winner-2024/prices?since=2024-10-01"
).then(res => res.json());

// 获取所有高严重度异常事件
const anomalies = await fetch(
  "http://localhost:5000/api/anomalies?severity=high"
).then(res => res.json());

// 触发实时分析
const analysis = await fetch(
  "http://localhost:5000/api/analyze/presidential-election-winner-2024",
  {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({detectors: ["zscore"]})
  }
).then(res => res.json());
```

---

## 启动完整系统的步骤（给 E 的一键指南）

```bash
# 第一步：启动数据库
cd ~/6290/data_pipeline
docker compose up -d

# 第二步：等待数据库就绪（约 10 秒）
docker compose ps
# 确认 timescaledb 状态为 "Up (healthy)"

# 第三步：运行一次异常检测，把结果写入数据库
cd ~/6290
./venv/bin/python -m core_analysis.run_analysis

# 第四步：启动 API 服务器
./venv/bin/python -m core_analysis.api_server

# API 现在运行在 http://localhost:5000
# 前端可以开始开发了
```

---

## 附录：完整项目文件结构

```
~/6290/
├── core_analysis/                  # 核心分析模块
│   ├── __init__.py
│   ├── db_interface.py             # [成员B] 共享数据库接口
│   ├── data_quality.py             # [成员B] 数据质量报告
│   ├── run_quality_report.py       # [成员B] 质量报告 CLI
│   ├── zscore_detector.py          # [成员C] Z-Score 异常检测
│   ├── benford_detector.py         # [成员C] Benford 定律检测
│   ├── whale_alert.py              # [成员C] 鲸鱼警报
│   ├── backtester.py               # [成员C] 回测系统
│   ├── run_analysis.py             # [成员C] 统一运行入口 CLI
│   └── api_server.py               # [成员C] REST API 服务器（已创建，7 个接口）
│
├── data_pipeline/                  # [成员B] 数据采集管道
│   ├── docker-compose.yml          # Docker 服务编排
│   ├── db/
│   │   ├── init.sql                # 数据库表结构
│   │   └── price_history_seed.csv  # 历史数据种子
│   ├── collector/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                 # 采集器主程序
│   │   ├── fetcher.py              # API 请求
│   │   └── db.py                   # 数据库写入
│   └── README.md
│
├── tests/                          # 测试
│   ├── core_analysis/
│   │   ├── test_zscore_detector.py # [成员C] 15 个测试
│   │   ├── test_benford_detector.py# [成员C] 24 个测试
│   │   ├── test_whale_alert.py     # [成员C] 18 个测试
│   │   ├── test_backtester.py      # [成员C] 23 个测试
│   │   ├── test_data_quality.py    # [成员B] 8 个测试
│   │   ├── test_db_interface.py    # [成员B] 15 个测试
│   │   └── test_e2e.py             # [成员B] 5 个集成测试（需要 DB）
│   └── data_pipeline/
│       ├── test_fetcher.py         # [成员B] 6 个测试
│       └── test_db.py              # [成员B] 7 个测试
│
├── notebooks/                      # [成员C] Jupyter Notebooks
│   ├── 01_zscore_analysis.ipynb
│   ├── 02_benford_analysis.ipynb
│   ├── 03_whale_alert_analysis.ipynb
│   └── 04_backtest_report.ipynb
│
├── docs/                           # 文档
│   ├── algorithm-accuracy-report.md# [成员C] 算法准确率报告
│   ├── data-pipeline-guide.md      # [成员B] 数据管道指南
│   └── guide-for-member-c.md       # [成员C] 本文件
│
├── requirements.txt                # Python 依赖
├── venv/                           # Python 虚拟环境
├── task_plan.md                    # 任务计划
├── findings.md                     # 研究发现
└── progress.md                     # 进度日志
```

---

## 附录：数据库连接信息速查

| 项目 | 值 |
|------|-----|
| 主机 | `localhost` |
| 端口 | `5433`（注意不是默认的 5432） |
| 数据库名 | `polywatch` |
| 用户名 | `polywatch` |
| 密码 | `polywatch` |
| 连接字符串 | `postgresql://polywatch:polywatch@localhost:5433/polywatch` |

---

## 附录：常用命令速查表

| 目的 | 命令 |
|------|------|
| 启动数据库 | `cd ~/6290/data_pipeline && docker compose up -d` |
| 关闭数据库 | `cd ~/6290/data_pipeline && docker compose stop` |
| 查看数据库状态 | `cd ~/6290/data_pipeline && docker compose ps` |
| 运行单元测试 | `cd ~/6290 && ./venv/bin/pytest tests/core_analysis/test_zscore_detector.py tests/core_analysis/test_benford_detector.py tests/core_analysis/test_whale_alert.py tests/core_analysis/test_backtester.py -v` |
| 运行分析（干跑） | `cd ~/6290 && ./venv/bin/python -m core_analysis.run_analysis --dry-run` |
| 运行分析（写入DB） | `cd ~/6290 && ./venv/bin/python -m core_analysis.run_analysis` |
| 运行回测 | `cd ~/6290 && ./venv/bin/python -m core_analysis.run_analysis --backtest` |
| 启动 API 服务器 | `cd ~/6290 && ./venv/bin/python -m core_analysis.api_server` |
| 测试 API 健康检查 | `curl http://localhost:5000/api/health` |
| 启动 Jupyter | `cd ~/6290 && ./venv/bin/jupyter notebook notebooks/` |
| 查看异常事件数据库 | `cd ~/6290/data_pipeline && docker compose exec timescaledb psql -U polywatch -d polywatch -c "SELECT * FROM anomaly_events LIMIT 10;"` |
