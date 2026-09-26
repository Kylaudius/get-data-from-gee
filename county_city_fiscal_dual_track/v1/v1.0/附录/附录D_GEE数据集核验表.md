# 附录D GEE 数据集核验表（v1.0）

核验日期 2026-09-26。官方数据集的 asset ID、类型、波段、类别代码、分辨率与时间范围，均直接读取 Google Earth Engine 官方 STAC 目录（`https://storage.googleapis.com/earthengine-stac/catalog/...`）的 JSON 记录核对。社区目录（awesome-gee-community-catalog）的资产路径无法在本环境打开，一律标为待核验，使用前须在 GEE 中用 `ee.data.listAssets()` 或 `ee.data.getAsset()` 确认。`01_gee_extract_rs.py --preflight` 会在运行时再逐项检查一次。

## 1 本版代码实际使用的数据集

| 用途 | asset ID | 类型 | 波段与类别 | 分辨率 | 时间 | 注意事项 | 核验 |
|---|---|---|---|---|---|---|---|
| 建成面积、识别中心建成区 | `JRC/GHSL/P2023A/GHS_BUILT_S` | ImageCollection | `built_surface`、`built_surface_nres`（m²/格） | 100 m | 1975 至 2030 年，每 5 年一期 | 2010、2020 年为多期观测的插值结果；原生投影为 Mollweide，求和必须在原生网格上进行 | STAC JSON |
| 建筑体量、住宅面积估算 | `JRC/GHSL/P2023A/GHS_BUILT_V` | ImageCollection | `built_volume_total`、`built_volume_nres`（m³/格） | 100 m | 同上 | 高度只观测于 2018 年，体量的时间变化主要反映占地变化，2010 至 2020 年体量变化只作参考 | STAC JSON |
| 人口（主分母，普查重标定） | `JRC/GHSL/P2023A/GHS_POP` | ImageCollection | `population_count` | 100 m | 1975 至 2020 年实测，2025、2030 年为预测 | 由 GPWv4.11 分配，中国县级总量不等于普查，必须按普查常住人口重标定 | STAC JSON |
| 人口（稳健性） | `WorldPop/GP/100m/pop` | ImageCollection | `population`；属性 `country`（CHN）、`year` | 约 93 m | 2000 至 2020 年 | 同样需要按普查重标定 | STAC JSON |
| 城镇化程度（中心建成区识别的外部对照） | `JRC/GHSL/P2023A/GHS_SMOD_V2-0` | ImageCollection | `smod_code`：10 水体，11 至 13 农村，21 郊区，22 半密集城镇簇，23 密集城镇簇，30 城市中心 | 1 km（Mollweide） | 1975 至 2030 年，每 5 年一期 | 按年份取 2020 年一期，预检确认该年只有 1 幅；统计 22、23、30 合计与 30 单独的面积；旧 ID `GHS_SMOD` 已弃用 | STAC JSON |
| 不透水面历年变化 | `Tsinghua/FROM-GLC/GAIA/v10` | Image | `change_year_index`，值 v 表示该像元在 2019 − v 年转为不透水面（34 为 1985 年，1 为 2018 年） | 30 m | 1985 至 2018 年 | 到 Y 年为止的不透水面取 v ≥ 2019 − Y，2000、2010、2018 年分别为 ≥ 19、≥ 9、≥ 1。STAC 说明原文为 “the impervious surface in 1990 can be revealed as the pixel value greater than 29”，按同一记录的查找表 29 即 1990 年，大于 29 会漏掉 1990 年当年转化的像元，本代码按查找表取大于等于。序列单调，不含拆除 | STAC JSON |
| 2000 年树冠覆盖度（存量与新增树木） | `UMD/hansen/global_forest_change_2025_v1_13` | Image | `treecover2000`（%，0 至 100） | 30.92 m | 2000 年基准；产品版本 v1.13，时间范围 2000 至 2025 年 | 树冠指 5 m 以上植被；无数据置 0。果园与低矮的新植树会落入新增 | STAC JSON |
| 聚落内部特征（开放空间、道路面） | `JRC/GHSL/P2023A/GHS_BUILT_C` | ImageCollection | `built_characteristics`：1 至 3 植被开放空间，4 水面，5 道路面，11 至 15 住宅建筑（按高度），21 至 25 非住宅建筑 | 10 m | 仅 2018 年 | 单期，不能做变化；县城道路面识别精度未经中国验证 | STAC JSON |
| 土地覆盖（树木、绿地） | `ESA/WorldCover/v100` | ImageCollection | `Map`：10 树木，20 灌木，30 草地，40 耕地，50 建设用地，60 裸地，70 冰雪，80 水体，90 草本湿地，95 红树林，100 苔藓地衣 | 10 m | 2020 年 | 树木口径含 95 红树林；草地类精度低（Venter et al., 2022），以树木为主口径；v100 与 v200 算法不同，不能相减得到变化 | STAC JSON |
| 土地覆盖（2021，交叉验证） | `ESA/WorldCover/v200` | ImageCollection | 同上 | 10 m | 2021 年 | 同上 | STAC JSON |
| 树木与草地概率 | `GOOGLE/DYNAMICWORLD/V1` | ImageCollection | `trees`、`grass` 等 9 个概率波段与 `label` | 10 m | 2015 年 6 月至今 | 只对云量不高于 35% 的景生成，华南多云地区观测少；年度模式取 2016 至 2024 年生长季均值 | STAC JSON |
| 生长季 NDVI | `COPERNICUS/S2_SR_HARMONIZED` | ImageCollection | `B4`、`B8`、`SCL`（3 云影，8 至 10 云与卷云，11 冰雪） | 10 m | 2017 年 3 月至今 | 2022 年 1 月至 2024 年 2 月 QA60 被掩膜，本代码用 SCL 去云；v1.1 可改用 Cloud Score+（`GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`） | STAC JSON |
| 自然植被本底 | `MODIS/061/MOD13Q1` | ImageCollection | `NDVI`（比例系数 0.0001） | 250 m | 2000 年 2 月至今 | 只用于中心建成区外 5 km 环带的非建成栅格 | STAC JSON |
| 夜间灯光（2013 至 2021 年） | `NOAA/VIIRS/DNB/ANNUAL_V21` | ImageCollection | `average_masked`（nW/cm²/sr） | 约 464 m | 2012 年 4 月至 2021 年 | 2020 年固定用 V21；年度模式取 2013 至 2021 年 | STAC JSON |
| 夜间灯光（2022 年起） | `NOAA/VIIRS/DNB/ANNUAL_V22` | ImageCollection | 同上 | 约 464 m | STAC 时间范围至 2025 年，说明文字只写 2022 年 | 使用前核实实际包含的年份 | STAC JSON |
| 夜间灯光（2010 年） | `BNU/FGS/CCNL/v1` | ImageCollection | `b1` | 1 km | 1992 至 2013 年 | DMSP 校正序列，不能与 VIIRS 直接拼接 | STAC JSON |
| 水体（滨水线性绿地、NDVI 剔除水面） | `JRC/GSW1_4/GlobalSurfaceWater` | Image | `occurrence`（%）；`transition`：1 永久水体，2 新增永久水体，4 季节性水体等 11 类 | 30 m | 1984 至 2021 年 | 从未出现水体的像元为掩膜，代码中置 0。只用 `occurrence`；`transition` 本版未用，其中新增永久水体可用来识别 1984 年后开挖的养殖塘 | STAC JSON |
| 高程、坡度 | `NASA/NASADEM_HGT/001` | Image | `elevation` | 30 m | 2000 年 | 坡度在原生 30 m 网格上计算；不要用 Copernicus DEM（为含建筑的表面模型） | STAC JSON |
| 气温、降水 | `ECMWF/ERA5_LAND/MONTHLY_AGGR` | ImageCollection | `temperature_2m`（K）、`total_precipitation_sum`（m） | 约 11 km | 1950 年至今 | 只作单元级控制变量 | STAC JSON |
| 到最近城市的出行时间 | `projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0` | Image | `accessibility`（分钟） | 约 1 km | 2015 年 | 区位控制变量；旧 ID `Oxford/MAP/...` 已弃用 | STAC JSON |
| 历年地类（可选，新增管理绿地） | 社区目录路径，填入 `config.yaml` 的 `clcd_asset_template`，默认为空 | 每年一幅 Image，或一个 ImageCollection | 波段默认 `b1`；类别按 Yang 与 Huang（2021）为 1 耕地，2 林地，3 灌木，4 草地，5 水体，6 冰雪，7 裸地，8 不透水面，9 湿地 | 30 m | 论文版为 1985 年与 1990 至 2019 年逐年，更新版年份须核实 | 不在官方目录。`config.yaml` 取 2020 年，须更新版才有。波段名与类别代码须对照资产核实 | 未核验 |

## 2 可用于稳健性检验或后续迭代的数据集

| 用途 | asset ID | 说明 |
|---|---|---|
| 建筑高度（2018） | `JRC/GHSL/P2023A/GHS_BUILT_H` | `built_height`；有研究指出全球高度产品低估中国高层核心区 |
| 10 m 建成面积（2018） | `JRC/GHSL/P2023A/GHS_BUILT_S_10m` | 县城精细边界与交叉验证 |
| 2020 年受约束人口与年龄结构 | `WorldPop/GP/100m/pop_age_sex_cons_unadj` | 可计算老年人与儿童的公园可达性；是否经联合国总量调整，STAC 说明自相矛盾，需核实 |
| 跨期绿度 | `LANDSAT/LT05/C02/T1_L2`、`LANDSAT/LC08/C02/T1_L2` | 2010 至 2020 年同源比较需做跨传感器定标；不要用 `LANDSAT/COMPOSITES/.../ANNUAL_NDVI`（取最近像元） |
| 局地气候分区 | `RUB/RUBCLIM/LCZ/global_lcz_map/latest` | 2018 年单期，可描述城市形态 |

## 3 官方目录中不存在、需要自行上传的数据

| 数据 | 状态 | 处理办法 |
|---|---|---|
| 县级行政区划边界 | 官方目录中 FAO GAUL 与 geoBoundaries（`WM/geoLab/geoBoundaries/600/ADM2`）只到二级，中国二级为地级；争议地区画法不符合标准地图 | 使用天地图 2024 版行政区划（审图号 GS(2024)0650）或 1:100 万公众版基础地理信息数据，由 `00_prepare_units.py` 整理后使用 |
| 全球城市边界 GUB | 社区目录路径未核验 | 从清华大学数据站下载后上传，或以 GHSL 建成栅格识别（本代码的做法） |
| EULUC-China 2018 | 官方目录没有，社区路径未核验 | 下载后上传，只作 2018 年公园地块的截面参考 |
| CNBH-10 m（2020 年中国建筑高度） | 不在任何 GEE 目录 | 从 Zenodo 下载后上传 |
| Google Open Buildings | 官方目录有，但不覆盖中国 | 不使用 |
| OSM 公园、绿道、河道 | 不在 GEE 目录 | 本地整理后上传；公园面填入 `park_asset`，绿道线填入 `greenway_asset`，河道面或线填入 `river_asset` |
| 学校、医院、养老机构点位 | 不在 GEE 目录 | 整理为 WGS-84 点位后上传，填入 `poi_assets` 的对应键；高德、百度 POI 须先用 `tools/coord_gcj02_to_wgs84.py` 转换坐标 |

## 4 平台限制与代码中的应对

| 限制 | 说明 | 代码中的应对 |
|---|---|---|
| 必须指定 Cloud 项目 | earthengine-api 1.x 的 `ee.Initialize()` 无项目时报错；非商业用途需注册 | `config.yaml` 的 `gee.project` |
| 交互请求约 5 分钟超时 | `getInfo` 超时报 Computation timed out | 每批默认 10 个单元，失败自动拆半重试，单个单元仍失败记入 `failures.csv`；这些单元用 `--export-failed` 改为批处理任务，不受此限制 |
| 特大单元 | 西部县域面积可达 10 万至 20 万平方千米，单个单元即可超时 | 面积超过 `large_unit_km2`（默认 2 万平方千米）的单元各自成批，排在普通批次之后 |
| 内存不足 | User memory limit exceeded | `tile_scale` 默认 4，可调到 8 或 16 |
| 集合元素上限约 5 000 | 超过即报错 | 按批次取回，每批远小于上限 |
| 请求体约 10 MB 上限 | 客户端几何过大时请求失败 | 默认发送简化几何（约 100 m 容差），每批只发送本批单元的驻地点；全国运行可改为 `units_source: asset`，先上传 `units_for_gee_shp.zip` |
| 连通计数上限 | `connectedPixelCount` 最多计到 1024 个像元 | 1 公顷绿斑为 100 个像元，5 公顷水面不到 130 个像元，均在上限内；门槛调得更大时按 1024 个像元处理并在终端警告 |
| 计数型栅格的重采样 | 在非原生网格上求和会改变总量 | 人口、面积、体量、灯光、不透水面、城镇化程度均在原生投影与分辨率上求和 |

## 5 代码中的处理方法

**中心建成区的闭运算。** 矢量化之前，先在 GHSL 原生 100 m 网格上对建成掩膜做形态学闭运算（morphological closing），即先取方形邻域最大值，再取方形邻域最小值。半径取 `core.closing_radius_m`，按 100 m 换算为像元数并四舍五入。默认 200 m 即 2 个像元，宽度不超过约 400 m 的河流、道路和铁路走廊两侧的斑块会连成一片，设为 0 则不做。2010 年的动态中心建成区用同一规则。`core_closing_m` 记录实际半径，`c_builtcell_m2_2020` 记录最终中心建成区内原始达标栅格的面积。它与 `core_area_m2` 之比越低，说明闭运算与填洞并入的非建成面积越多。

**大型绿斑。** 地类由 `green_patch_class` 指定，默认只用树木，即 WorldCover 10 树木与 95 红树林。计数前先乘中心建成区掩膜，截断斑块与区外山林的连通。连通计数在 GHSL 的 Mollweide 10 m 网格上进行，每个像元恰为 100 m²，1 公顷门槛等于 100 个像元，不随纬度变化。

**滨水线性绿地的水体。** 默认用 JRC 近永久水体，即出现频率不低于 90% 且所在连通水面不小于 5 公顷。连通面积在 JRC 原生网格上计算，以连通像元数乘该处像元面积，因此门槛不随纬度变化。零散鱼塘被排除，成片养殖塘仍可能计入。提供 `river_asset` 后改用河道要素。滨水与道路两侧的线性绿地都采用大型绿斑的地类。

**NDVI 剔除水面。** `mask_water_in_ndvi` 为 true 时，中心建成区的 Sentinel-2 NDVI 与环带的 MODIS NDVI 都剔除 JRC 出现频率不低于 50% 或 WorldCover 水体的像元。水面 NDVI 为负值，不剔除时湖泊和河流会拉低滨水城镇的绿度。

**坡度。** 先在 NASADEM 原生 30 m 网格上计算坡度，再取均值。单元均值按 `terrain_unit_scale_m`（默认 90 m）抽样统计，中心建成区按 30 m 统计。原做法在 500 m 与 90 m 尺度上计算坡度，山区坡度被明显低估，单元与中心建成区之间也不可比。

**存量与新增树木。** 2020 年 WorldCover 树木像元按 Hansen 2000 年树冠覆盖度划分，不低于 `baseline_tree_cover_pct`（默认 30%）的记为存量，其余记为新增。坡度不超过 `slope_mask_deg`（默认 15°）的树木另行统计，供排除山体残林的敏感性检验使用。配置 CLCD 后，另计 2020 年绿地中基期为耕地、裸地或不透水面的面积，作为新增管理绿地。

**年度模式。** `--annual` 读取主运行合并的 `core_polygons_2020.geojson`，在固定的 2020 年中心建成区与整个单元内逐年提取 GAIA 不透水面（2000 至 2018 年）和 VIIRS 夜光总量（2013 至 2021 年），并在中心建成区内提取 Dynamic World 生长季树木与草地平均概率（2016 至 2024 年）。每类数据单独请求，Dynamic World 每次 3 年。分批、续跑、拆分与进度汇报沿用正式运行的做法。结果为长表 `annual/annual_long.csv`，一行一个单元年份。找不到中心建成区文件的单元，在服务器端按同一规则重新识别，终端给出警告。

**批处理导出。** `--export-failed` 对 `failures.csv` 中的每个单元构建与正式运行相同的计算图，把单元级与环带属性并到中心建成区要素上，以 GeoJSON 批处理导出（batch export）到 Google Drive 的 `export_folder`。任务 ID 与状态记在 `export_tasks.json`，重新运行只继续查询，不重复提交排队、运行中或已完成的任务。文件下载到本地后运行 `--merge-exports`，结果写成 `chunks/export_*`。合并时正式运行的结果优先，其次是导出结果，最后是试跑结果。

**准实验单元层。** `--units did` 对 00 输出的 `units_did_for_gee.geojson` 做同样的提取，每个 2020 年县级行政区一个单元，驻地点取 `seats_did.geojson`，结果写到 `数据/中间/gee/did/`。

## 6 局限

邻域运算所在的网格会让地面距离随纬度变形。人口加权绿地暴露与大型绿斑可达的 500 m 圆形邻域在 GHSL 的 Mollweide 网格上计算。该投影中央经线为 0°，在中国的角度变形（angular distortion）为 26° 至 54°。按变形椭圆（Tissot's indicatrix）计算，半径 500 m 的邻域在地面上是一个面积不变的椭圆，两个半轴在广州约为 400 m 与 630 m，在北京约为 340 m 与 740 m，在哈尔滨约为 300 m 与 820 m。滨水 50 m 与道路 20 m 的缓冲在 10 m 经纬度网格上计算，东西向宽度按纬度余弦缩短。50 m 缓冲的东西向宽度在广州约为 46 m，在北京约为 38 m，在哈尔滨约为 35 m。两类误差都随纬度系统变化，会与南北差异混在一起。设施点位、绿道和公园矢量的可达人口先按地面距离缓冲再画到网格上，不受影响。

后续版本可把这些邻域运算放到中国区域的 Albers 等积圆锥投影上，双标准纬线取 25°N 与 47°N，中央经线取 105°E。该投影在中国境内的角度变形不超过约 4°，尺度误差在 4% 以内。暴露度与可达范围是强度量（intensive quantity），可在该网格上算好后采样回 GHSL 网格，再与原生网格上的人口相乘求和，人口总量不受重采样影响。该投影的 WKT 定义须先在 GEE 服务器上验证。
