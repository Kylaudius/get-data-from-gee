# 代码使用说明（v1.0）

本文件说明每个脚本在哪里运行、按什么顺序运行、每一步得到什么。你不需要读懂代码，按顺序复制命令即可。所有命令都在 Mac 的“终端 Terminal”中输入（启动台 → 其他 → 终端，或 Spotlight 搜索 Terminal）。

## 一、一次性准备（约 30 分钟）

### 1. 安装 Python 环境（Miniforge）

在浏览器打开 https://github.com/conda-forge/miniforge ，下载 macOS 版本（Apple 芯片选 arm64，Intel 芯片选 x86_64）。在终端中运行下载好的安装脚本，一路回车并输入 yes：

```bash
# 目的：安装 conda（Python 环境管理器）。只需运行一次。
# 结果：终端重新打开后，提示符前出现 (base)。
bash ~/Downloads/Miniforge3-MacOSX-arm64.sh
```

关闭并重新打开终端，然后创建本项目专用环境：

```bash
# 目的：新建名为 fiscal 的独立 Python 3.11 环境，避免与电脑上其他软件冲突。只需运行一次。
# 结果：环境创建成功，出现 “To activate this environment” 提示。
conda create -n fiscal python=3.11 -y
```

### 2. 安装依赖包

```bash
# 目的：进入本迭代的代码文件夹并安装全部依赖。<你的路径> 换成仓库在你电脑上的位置，
#       可以把 代码 文件夹直接拖进终端窗口自动填入路径。
# 结果：最后一行出现 Successfully installed ...
conda activate fiscal
cd <你的路径>/county_city_fiscal_dual_track/v1/v1.0/代码
pip install -r requirements.txt
```

### 3. 注册并授权 Google Earth Engine

1. 用 Google 账号登录 https://code.earthengine.google.com ，按提示注册非商业（研究）用途。
2. 在 https://console.cloud.google.com 新建一个 Cloud 项目（例如 `fiscal-gee-2026`），在该项目中启用 Earth Engine API。自 2024 年起，调用 GEE 必须指定 Cloud 项目。
3. 把项目 ID 填入 `外部参数/config.yaml` 的 `gee.project`。
4. 在终端授权：

```bash
# 目的：在浏览器中完成 GEE 登录授权，授权信息保存在本机，以后不用重复。
#       auth_mode="localhost" 会自动打开浏览器，授权后跳回本机端口，适合在自己的 Mac 上运行。
# 结果：浏览器提示授权成功，终端显示 Successfully saved authorization token。
conda activate fiscal
python -c "import ee; ee.Authenticate(auth_mode='localhost')"
```

### 4. 检查代码能否运行（不需要任何真实数据）

```bash
# 目的：用合成数据把 00–05 全部脚本跑一遍，检查环境是否装好。合成数据不是研究结果，运行完自动删除。
# 结果：每行显示 OK，最后显示“全部通过”。
python tests/run_smoke_test.py
```

## 二、数据准备

按 `../数据/README.md` 下载或整理原始数据，放入 `数据/原始/` 下对应文件夹，列名与 `数据/模板/` 中的模板一致。最少需要：县级边界、七普分县常住人口、县域与城市统计年鉴的财政收支。

## 三、正式运行顺序

| 步骤 | 命令 | 目的 | 结果 |
|---|---|---|---|
| 0 | `python 00_prepare_units.py` | 把县级边界整理为分析单元（市辖区按城市合并，县与县级市单列） | `数据/中间/units/` |
| 1a | `python 01_gee_extract_rs.py --preflight` | 检查 GEE 授权与各数据集是否可用 | 终端逐项显示 OK |
| 1b | `python 01_gee_extract_rs.py --province 44 --limit 20` | 试跑广东前 20 个单元，检查结果是否合理 | `数据/中间/gee/chunks/test_*` |
| 1c | `python 01_gee_extract_rs.py` | 全国提取遥感指标；可随时 Ctrl+C 中断，重新运行自动续跑 | `数据/中间/gee/gee_unit_metrics.csv` |
| 2 | `python 02_build_fiscal_census.py` | 统一行政区划代码，汇总财政与普查到分析单元 | `数据/中间/panel/`（含 `qa_report.md`） |
| 3 | `python 03_build_indicators.py` | 计算全部指标，划分五类分组与四象限 | `数据/结果/unit_indicators.csv` |
| 4 | `python 04_describe_and_map.py` | 描述统计表与全国地图 | `数据/结果/table*.md`、`图表/fig1–4` |
| 5 | `python 05_models.py` | 基准回归 | `数据/结果/models_*`、`图表/fig5` |

全国运行 01 的耗时取决于 GEE 排队情况，约 2 200 个单元、每批 10 个，预计 3 至 8 小时。终端会按批次显示“第几批/共几批、本批耗时、累计完成比例、预计剩余时间”。电脑休眠或断网后，重新运行同一命令会跳过已完成的批次。

### 全国运行前建议上传分析单元（可选，更稳）

默认情况下，01 脚本每批把简化后的单元边界从本地发送给 GEE，不需要上传任何文件。全国运行时，若经常出现请求过大或超时，可以改为先上传：

1. 打开 https://code.earthengine.google.com ，左侧 Assets → NEW → Shape files，选择 `数据/中间/units/units_for_gee_shp.zip`，资产名填 `units_for_gee`，上传完成后复制资产路径（形如 `projects/你的项目ID/assets/units_for_gee`）。
2. 在 `外部参数/config.yaml` 中把 `units_source` 改为 `asset`，把 `units_asset` 改为上一步的路径。
3. 重新运行 `python 01_gee_extract_rs.py`，已完成的批次不会重复计算。

## 四、常见问题

| 现象 | 处理 |
|---|---|
| `GEE 初始化失败` | 重新运行授权命令；确认 config.yaml 中的项目 ID 与 Cloud 控制台一致 |
| `User memory limit exceeded` | config.yaml 中 `tile_scale` 改为 8 或 16 |
| `Computation timed out` 反复出现 | `chunk_size` 改为 10；脚本也会自动把失败批次拆半重试 |
| `failures.csv` 中有单元 | 调整上面两个参数后重新运行 01，只会补跑失败与未完成部分 |
| 预检显示某数据集缺失 | 把日志发给合作者；多半是 GEE 目录更新了数据集 ID，改 config.yaml 的 `datasets` 即可 |
| 图中中文显示为方块 | Mac 自带苹方字体，一般不会出现；若出现，把日志发给合作者 |

## 五、工具脚本

| 命令 | 目的 |
|---|---|
| `python tools/export_codebook_md.py` | 修改 03 脚本中的指标说明表 CODEBOOK 后，重新生成 附录C |
| `python tools/check_manual_edits.py --record` / `--check` | 记录或检查文件指纹，防止新迭代覆盖手动修改 |
| `python tests/run_smoke_test.py` | 用合成数据检查全部脚本能否跑通 |

## 六、迭代管理

每次迭代结束运行 `python tools/check_manual_edits.py --record` 记录文件指纹；下一次迭代开始前运行 `python tools/check_manual_edits.py --check`，终端会列出你手动改过的文件，新构建不会覆盖这些修改。
