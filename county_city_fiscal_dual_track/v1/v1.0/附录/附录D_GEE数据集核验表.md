# 附录D GEE 数据集核验表（v1.0）

核验日期 2026-09-26。官方数据集的 asset ID、类型、波段、类别代码、分辨率与时间范围，均直接读取 Google Earth Engine 官方 STAC 目录（`https://storage.googleapis.com/earthengine-stac/catalog/...`）的 JSON 记录核对。社区目录（awesome-gee-community-catalog）的资产路径无法在本环境打开，一律标为待核验，使用前须在 GEE 中用 `ee.data.listAssets()` 或 `ee.data.getAsset()` 确认。`01_gee_extract_rs.py --preflight` 会在运行时再逐项检查一次。

## 1 本版代码实际使用的数据集

| 用途 | asset ID | 类型 | 波段与类别 | 分辨率 | 时间 | 注意事项 |
|---|---|---|---|---|---|---|
| 建成面积、识别中心建成区 | `JRC/GHSL/P2023A/GHS_BUILT_S` | ImageCollection | `built_surface`、`built_surface_nres`（m²/格） | 100 m | 1975 至 2030 年，每 5 年一期 | 2010、2020 年为多期观测的插值结果；原生投影为 Mollweide，求和必须在原生网格上进行 |
| 建筑体量、住宅面积估算 | `JRC/GHSL/P2023A/GHS_BUILT_V` | ImageCollection | `built_volume_total`、`built_volume_nres`（m³/格） | 100 m | 同上 | 高度只观测于 2018 年，体量的时间变化主要反映占地变化，2010 至 2020 年体量变化只作参考 |
| 人口（主分母，普查重标定） | `JRC/GHSL/P2023A/GHS_POP` | ImageCollection | `population_count` | 100 m | 1975 至 2020 年实测，2025、2030 年为预测 | 由 GPWv4.11 分配，中国县级总量不等于普查，必须按普查常住人口重标定 |
| 人口（稳健性） | `WorldPop/GP/100m/pop` | ImageCollection | `population`；属性 `country`（CHN）、`year` | 约 93 m | 2000 至 2020 年 | 同样需要按普查重标定 |
| 聚落内部特征（开放空间、道路面） | `JRC/GHSL/P2023A/GHS_BUILT_C` | ImageCollection | `built_characteristics`：1 至 3 植被开放空间，4 水面，5 道路面，11 至 15 住宅建筑（按高度），21 至 25 非住宅建筑 | 10 m | 仅 2018 年 | 单期，不能做变化；县城道路面识别精度未经中国验证 |
| 土地覆盖（树木、绿地） | `ESA/WorldCover/v100` | ImageCollection | `Map`：10 树木，20 灌木，30 草地，40 耕地，50 建设用地，60 裸地，70 冰雪，80 水体，90 草本湿地，95 红树林，100 苔藓地衣 | 10 m | 2020 年 | 草地类精度低（Venter et al., 2022），以树木为主口径；v100 与 v200 算法不同，不能相减得到变化 |
| 土地覆盖（2021，交叉验证） | `ESA/WorldCover/v200` | ImageCollection | 同上 | 10 m | 2021 年 | 同上 |
| 树木与草地概率 | `GOOGLE/DYNAMICWORLD/V1` | ImageCollection | `trees`、`grass` 等 9 个概率波段与 `label` | 10 m | 2015 年 6 月至今 | 只对云量不高于 35% 的景生成；华南多云地区观测少 |
| 生长季 NDVI | `COPERNICUS/S2_SR_HARMONIZED` | ImageCollection | `B4`、`B8`、`SCL`（3 云影，8 至 10 云与卷云，11 冰雪） | 10 m | 2017 年 3 月至今 | 2022 年 1 月至 2024 年 2 月 QA60 被掩膜，本代码用 SCL 去云；v1.1 可改用 Cloud Score+（`GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED`） |
| 自然植被本底 | `MODIS/061/MOD13Q1` | ImageCollection | `NDVI`（比例系数 0.0001） | 250 m | 2000 年 2 月至今 | 只用于中心建成区外 5 km 环带的非建成栅格 |
| 夜间灯光（2013 至 2021 年） | `NOAA/VIIRS/DNB/ANNUAL_V21` | ImageCollection | `average_masked`（nW/cm²/sr） | 约 464 m | 2012 年 4 月至 2021 年 | 2020 年固定用 V21 |
| 夜间灯光（2022 年起） | `NOAA/VIIRS/DNB/ANNUAL_V22` | ImageCollection | 同上 | 约 464 m | STAC 时间范围至 2025 年，说明文字只写 2022 年 | 使用前核实实际包含的年份 |
| 夜间灯光（2010 年） | `BNU/FGS/CCNL/v1` | ImageCollection | `b1` | 1 km | 1992 至 2013 年 | DMSP 校正序列，不能与 VIIRS 直接拼接 |
| 水体（滨水绿带） | `JRC/GSW1_4/GlobalSurfaceWater` | Image | `occurrence`（%） | 30 m | 1984 至 2021 年 | 从未出现水体的像元为掩膜，代码中置 0 |
| 高程、坡度 | `NASA/NASADEM_HGT/001` | Image | `elevation` | 30 m | 2000 年 | 不要用 Copernicus DEM（为含建筑的表面模型） |
| 气温、降水 | `ECMWF/ERA5_LAND/MONTHLY_AGGR` | ImageCollection | `temperature_2m`（K）、`total_precipitation_sum`（m） | 约 11 km | 1950 年至今 | 只作单元级控制变量 |
| 到最近城市的出行时间 | `projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0` | Image | `accessibility`（分钟） | 约 1 km | 2015 年 | 区位控制变量；旧 ID `Oxford/MAP/...` 已弃用 |

## 2 可用于稳健性检验或后续迭代的数据集

| 用途 | asset ID | 说明 |
|---|---|---|
| 逐年不透水面（2010 至 2018 年变化） | `Tsinghua/FROM-GLC/GAIA/v10` | 单幅影像，波段 `change_year_index`，1 = 2018 年，34 = 1985 年；某年 Y 的不透水面为 `change_year_index ≥ 2019 − Y`（2010 年即 ≥ 9）；单调，不含拆除 |
| 城镇化度（1 km） | `JRC/GHSL/P2023A/GHS_SMOD_V2-0` | `smod_code`：30 城市中心，21 至 23 城镇簇；旧 ID `GHS_SMOD` 已弃用 |
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
| OSM 公园、绿道 | 不在 GEE 目录 | 本地整理为多边形或线要素；公园多边形上传后填入 `config.yaml` 的 `park_asset` |

## 4 平台限制与代码中的应对

| 限制 | 说明 | 代码中的应对 |
|---|---|---|
| 必须指定 Cloud 项目 | earthengine-api 1.x 的 `ee.Initialize()` 无项目时报错；非商业用途需注册 | `config.yaml` 的 `gee.project` |
| 交互请求约 5 分钟超时 | `getInfo` 超时报 Computation timed out | 每批默认 10 个单元，失败自动拆半重试，单个单元仍失败记入 `failures.csv` |
| 内存不足 | User memory limit exceeded | `tile_scale` 默认 4，可调到 8 或 16 |
| 集合元素上限约 5 000 | 超过即报错 | 按批次取回，每批远小于上限 |
| 请求体约 10 MB 上限 | 客户端几何过大时请求失败 | 默认发送简化几何（约 100 m 容差）；全国运行可改为 `units_source: asset`，先上传 `units_for_gee_shp.zip` |
| 计数型栅格的重采样 | 在非原生网格上求和会改变总量 | 人口、面积、体量、灯光均在原生投影与分辨率上求和 |
