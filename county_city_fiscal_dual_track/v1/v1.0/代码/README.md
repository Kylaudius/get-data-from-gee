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

按 `../数据/README.md` 下载或整理原始数据，放入 `数据/原始/` 下对应文件夹，列名与 `数据/模板/` 中的模板一致。最少需要县级边界、县和市政府驻地点、2010 与 2020 年分县常住人口、2017 至 2019 年县域与城市统计年鉴的财政收支，以及七普城区人口表。其他文件都是可选的，缺了对应指标和模型会自动跳过。

以下三个工具帮助整理数据，都在 `代码/` 文件夹下运行。

```bash
# 目的：把 EPS、CNKI 等数据库导出的 Excel 或 CSV 宽表，按 外部参数/column_map.yaml 的映射转成模板格式。
#       先用 --inspect 看表头能否对上，再正式转换；已转换且未改动的文件会跳过（断点续跑）。
# 结果：数据/原始/ 下出现模板格式的 CSV；未匹配的代码与数值冲突另存为清单。
python tools/convert_yearbook_excel.py --inspect 数据库导出表.xlsx --job eps_county_fiscal
python tools/convert_yearbook_excel.py
```

```bash
# 目的：运行 02 之前体检全部原始数据，包括列名、6 位代码、重复行、年份是否齐全、比例是否在 0 至 1、
#       元与万元是否混用、驻地点坐标是否写反。
# 结果：数据/中间/qa/raw_data_check.md（中文报告，列出 Excel 行号）；有问题时终端最后一行提示问题数。
python tools/validate_raw_data.py
```

```bash
# 目的：高德、腾讯（GCJ-02）或百度（BD-09）坐标的点位与多边形转成 WGS-84，之后才能与遥感影像叠加。
#       本研究的边界、驻地点、公园和设施点位一律使用 WGS-84。
# 结果：输出文件中全部顶点完成转换，表格会另存原坐标列；--selftest 打印往返误差（应小于 0.5 米）。
python tools/coord_gcj02_to_wgs84.py --from gcj02 高德公园.geojson 公园_wgs84.gpkg
python tools/coord_gcj02_to_wgs84.py --selftest
```

## 三、正式运行顺序

| 步骤 | 命令 | 目的 | 结果 |
|---|---|---|---|
| 0 | `python 00_prepare_units.py` | 把县级边界整理为分析单元（市辖区按城市合并，县与县级市单列），同时输出不合并市辖区的准实验单元层 | `数据/中间/units/`（含 `units_did_*` 与 `seats_did.geojson`） |
| 1a | `python 01_gee_extract_rs.py --preflight` | 检查 GEE 授权与各数据集是否可用 | 终端逐项显示 OK |
| 1b | `python 01_gee_extract_rs.py --province 44 --limit 20` | 试跑广东前 20 个单元，检查结果是否合理 | `数据/中间/gee/chunks/test_*` |
| 1c | `python tools/export_cores_kml.py --province 44` | 把试跑得到的中心建成区导出为 KML，在 Google Earth 中目视核对 | `数据/中间/qa/cores_kml/` 下的 KML 与核对表 CSV |
| 1d | `python 01_gee_extract_rs.py` | 全国提取遥感指标；可随时 Ctrl+C 中断，重新运行自动续跑 | `数据/中间/gee/gee_unit_metrics.csv`、`core_polygons_2020.geojson` |
| 1e | `python 01_gee_extract_rs.py --export-failed` | 交互计算仍失败的单元（多为西部面积很大的县或超大城市）逐个提交为批处理任务，导出到 Google Drive，每分钟汇报一次状态 | Drive 的 `fdt_gee_exports` 文件夹；`数据/中间/gee/export_tasks.json` |
| 1f | `python 01_gee_extract_rs.py --merge-exports <下载的文件夹>` | 把从 Drive 下载的导出文件并入结果总表 | 更新后的 `gee_unit_metrics.csv` 与 `failures.csv` |
| 1g | `python 01_gee_extract_rs.py --annual` | 在固定的 2020 年中心建成区与单元内逐年提取 GAIA 不透水面、VIIRS 夜光与 Dynamic World 绿度，供准实验使用（须先完成 1d） | `数据/中间/gee/annual/annual_long.csv` |
| 1h | `python 01_gee_extract_rs.py --units did`（可再加 `--annual`） | 对每个 2020 年县级行政区单独提取，供准实验使用 | `数据/中间/gee/did/` |
| 2 | `python 02_build_fiscal_census.py` | 统一行政区划代码，汇总财政、普查、土地、债务与开发区数据到分析单元 | `数据/中间/panel/`（含 `qa_report.md`，列出成员覆盖率与口径提示） |
| 3 | `python 03_build_indicators.py` | 计算全部指标，划分分组与四象限 | `数据/结果/unit_indicators.csv` |
| 4 | `python 04_describe_and_map.py` | 描述统计表、全国地图与中心建成区质控图 | `数据/结果/table1` 至 `table4`；图写到 `数据/结果/图表/`（图2 至 图5、图S1） |
| 5 | `python 05_models.py` | 基准回归，每个模型注明检验的假设与预期符号 | `数据/结果/models_coef.csv`、`models_summary.md`；图6 |

脚本生成的图先写到 `数据/结果/图表/`，挑选满意的再手动复制到 `图表/`。这样下一次迭代检查手动修改时，不会把脚本输出误判为你的修改。

全国运行 01 的耗时取决于 GEE 排队情况，约 2 200 个单元、每批 10 个，预计 3 至 8 小时。终端会按批次显示“第几批/共几批、本批耗时、累计完成比例、预计剩余时间”。电脑休眠或断网后，重新运行同一命令会跳过已完成的批次。面积超过 2 万平方公里的单元会单独成批，排在最后。

### 全国运行前建议上传分析单元（可选，更稳）

默认情况下，01 脚本每批把简化后的单元边界从本地发送给 GEE，不需要上传任何文件。全国运行时，若经常出现请求过大或超时，可以改为先上传：

1. 打开 https://code.earthengine.google.com ，左侧 Assets → NEW → Shape files，选择 `数据/中间/units/units_for_gee_shp.zip`，资产名填 `units_for_gee`，上传完成后复制资产路径（形如 `projects/你的项目ID/assets/units_for_gee`）。
2. 在 `外部参数/config.yaml` 中把 `units_source` 改为 `asset`，把 `units_asset` 改为上一步的路径。
3. 重新运行 `python 01_gee_extract_rs.py`，已完成的批次不会重复计算。

### 公园、绿道与设施矢量（可选）

遥感只能测树木覆盖、大型树木斑块和线性绿地。公园和绿道两个词只用于矢量数据，需要另外准备并上传。

```bash
# 目的：从 Geofabrik 下载中国 OSM 数据（GB 级文件，断点续传，每 20 MB 汇报一次进度），
#       提取公园面、绿道线与河道面，并按省打包成可上传 GEE 的压缩包。已打包的省份会跳过。
#       提取需要 osmium-tool（在终端运行 brew install osmium-tool）或 pip install osmium，二选一。
# 结果：数据/中间/osm/osm_parks_greenways.gpkg 与 gee_upload/<省>_<图层>.zip。
python tools/build_osm_parks_greenways.py --province 44
```

把 `gee_upload/` 中的压缩包按上文“上传分析单元”的方法上传为 GEE 资产，再把资产路径填入 config.yaml 的 `park_asset`、`greenway_asset` 或 `river_asset`。学校、医院、养老机构的 POI 若来自高德或百度，先用坐标工具转换，再上传并填入 `poi_assets`。

## 四、常见问题

| 现象 | 处理 |
|---|---|
| `GEE 初始化失败` | 重新运行授权命令；确认 config.yaml 中的项目 ID 与 Cloud 控制台一致 |
| 00 提示缺少驻地点表 | 按 `数据/README.md` 整理驻地点；确实无法取得时把 config.yaml 的 `require_seats` 改为 false（不推荐） |
| `User memory limit exceeded` | config.yaml 中 `tile_scale` 改为 8 或 16 |
| `Computation timed out` 反复出现 | `chunk_size` 改为 5；脚本也会自动把失败批次拆半重试 |
| `failures.csv` 中有单元 | 先调整上面两个参数后重新运行 01；仍失败的用步骤 1e、1f 的批处理导出 |
| 预检显示某数据集缺失 | 把日志发给合作者；多半是 GEE 目录更新了数据集 ID，改 config.yaml 的 `datasets` 即可 |
| 大量城市标为“市辖区（规模未知）” | 缺少七普城区人口表 `city_urban_pop_2020.csv`，补齐后重新运行 03 |
| 图中中文显示为方块 | Mac 自带苹方字体，一般不会出现；若出现，把日志发给合作者 |

## 五、工具脚本

| 命令 | 目的 |
|---|---|
| `python tools/convert_yearbook_excel.py` | 数据库导出表转模板格式（见第二部分） |
| `python tools/validate_raw_data.py` | 原始数据体检（见第二部分） |
| `python tools/coord_gcj02_to_wgs84.py` | 高德、百度坐标转 WGS-84（见第二部分） |
| `python tools/build_osm_parks_greenways.py` | OSM 公园、绿道、河道下载与提取（见第三部分） |
| `python tools/export_cores_kml.py` | 中心建成区导出 KML 与目视核对表 |
| `python tools/export_codebook_md.py` | 修改 03 脚本中的指标说明表 CODEBOOK 后，重新生成 附录C |
| `python tools/check_manual_edits.py --record` / `--check` | 记录或检查文件指纹，防止新迭代覆盖手动修改 |
| `python tests/run_smoke_test.py` | 用合成数据检查全部脚本能否跑通 |

## 六、结果怎么读

每个研究假设对应的指标、模型编号、输出文件、预期符号与实现版本，见研究设计报告 9.8 节表 3。运行 05 后，先打开 `数据/结果/models_summary.md` 开头的模型总表，它列出每个模型检验的假设、预期符号，以及是否运行成功或因缺少哪些数据而跳过。回归结果是条件相关，不是因果效应；因果识别（省直管县、撤县设区、连片特困地区）在 v1.1 以后实现。

几个容易误读的指标：
- `net_inflow_pc_k`（人均净流入，千元）与 `own_rev_pc`（人均本级收入）以 2010 年常住人口为分母，是回归的核心财政变量；`fss` 与 `gap_ratio` 只作描述。
- `core_pop` 为中心建成区人口，主口径是官方城区与县城人口（config 中 `core_pop_source`），`core_pop_ghs` 为格网人口口径，二者之比 `core_pop_ratio_official_ghs` 用于检查。
- 大型树木斑块（`greenpatch_*`）、滨水线性绿地（`riparian_green_pc`）与道路绿带（`roadside_green_pc`）是遥感代理，不等于公园与绿道。
- 中心建成区识别失败的单元（`core_fallback` 为真）不计算任何中心建成区指标。

## 七、迭代管理

每次迭代结束运行 `python tools/check_manual_edits.py --record` 记录文件指纹；下一次迭代开始前运行 `python tools/check_manual_edits.py --check`，终端会列出你手动改过的文件，新构建不会覆盖这些修改。
