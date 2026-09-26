# 附录C 指标定义与计算公式（v1.0）

本附录由 `代码/tools/export_codebook_md.py` 根据 `代码/03_build_indicators.py` 中的 CODEBOOK 自动生成，与代码计算口径一致。

财政金额统一换算为元。主分析期为 2018、2019、2021 三年均值，避开 2020 年抗疫特别国债与新增赤字经特殊转移支付直达市县造成的异常；2010 期为 2009 至 2011 年三年均值。人口来自第五、六、七次人口普查分县资料，统一到 2020 年行政区划边界。遥感指标除特别说明外为 2020 年，统计范围为 2020 年中心建成区。

| 变量名 | 中文名 | 英文术语 | 公式 | 单位 |
|---|---|---|---|---|
| `fss` | 财政自给率 | fiscal self-sufficiency ratio | 一般公共预算收入 / 一般公共预算支出（主分析期三年均值） | 比值 |
| `gap_ratio` | 转移支付依赖度 | transfer dependence (fiscal gap ratio) | (支出 − 收入) / 支出 | 比值 |
| `exp_pc_res` | 人均财政支出（常住口径） | expenditure per resident | 一般公共预算支出 / 2020 年常住人口 | 元/人 |
| `exp_pc_hukou` | 人均财政支出（户籍口径） | expenditure per registered resident | 一般公共预算支出 / 户籍人口 | 元/人 |
| `gap_pc_res` | 人均财政缺口（常住口径） | fiscal gap per resident | (支出 − 收入) / 2020 年常住人口 | 元/人 |
| `rev_pc_res` | 人均本级收入（常住口径） | own-source revenue per resident | 一般公共预算收入 / 2020 年常住人口 | 元/人 |
| `tax_share` | 税收收入占比 | tax share of own revenue | 税收收入 / 一般公共预算收入 | 比值 |
| `land_dep` | 土地出让依赖度 | land-conveyance dependence | 国有土地使用权出让收入 / 一般公共预算收入（仅市辖区单元，可选） | 比值 |
| `fss_2010` | 财政自给率（2010 期） | fiscal self-sufficiency, 2009–2011 | 2009–2011 年均收入 / 年均支出 | 比值 |
| `pop_chg_1020` | 常住人口对数变化 2010–2020 | log change of resident population | ln(P2020 / P2010)，普查常住人口 | 对数差 |
| `pop_chg_0010` | 常住人口对数变化 2000–2010 | log change of resident population | ln(P2010 / P2000) | 对数差 |
| `res_hukou_ratio` | 常住/户籍人口比 | resident-to-registered ratio | 2020 常住人口 / 户籍人口；<1 表示人口净流出 | 比值 |
| `urb_rate_2020` | 城镇化率 2020 | urbanization rate | 城镇人口 / 常住人口 | 比值 |
| `share_hukou_elsewhere` | 人户分离人口比例 2020 | share of residents registered elsewhere | 七普表3“户口登记地在外乡镇街道的人口” / 常住人口；含县内跨乡镇迁移，只作流动强度的近似 | 比值 |
| `core_area_km2` | 中心建成区面积 | core built-up area | GHSL 2020 建成栅格最大连通斑块（或含驻地斑块）面积 | km² |
| `core_pop` | 中心建成区人口（普查重标定） | core population, census-rescaled | GHS-POP 2020 中心建成区求和 × (2020 普查常住人口 / GHS-POP 单元求和)；普查缺失时用未重标定值 | 人 |
| `builtup_pc_core` | 人均建成面积（中心建成区） | built-up surface per capita | GHSL 建成面积 / 中心建成区人口 | m²/人 |
| `tree_share_core` | 树木覆盖占比（中心建成区，主口径） | tree cover share | WorldCover 树木面积 / 各地类面积之和；WorldCover 草地类精度低，故以树木为主口径 | 比值 |
| `tree_pc_core` | 人均树木覆盖面积（主口径） | tree cover per capita | WorldCover 树木面积 / 中心建成区人口 | m²/人 |
| `green_share_core` | 绿地占比（树木+灌木+草地，稳健性口径） | green share | WorldCover 树木+灌木+草地面积 / 各地类面积之和 | 比值 |
| `green_pc_core` | 人均绿地面积（稳健性口径） | green space per capita | WorldCover 树木+灌木+草地面积 / 中心建成区人口 | m²/人 |
| `expo_tree_core` | 人口加权树木暴露（主口径） | population-weighted tree-cover exposure | Σ(格网人口 × 格网周围 500 m 树木覆盖比例) / Σ格网人口（Chen et al. 2022） | 比值 |
| `expo_green_core` | 人口加权绿地暴露（稳健性口径） | population-weighted greenspace exposure | 同上，绿地 = 树木+灌木+草地 | 比值 |
| `ndvi_core` | 中心建成区 NDVI | mean NDVI (Sentinel-2) | 2020 年 5–9 月 Sentinel-2 中值合成 NDVI 均值 | 无量纲 |
| `ndvi_ring` | 自然植被本底 | background NDVI (MODIS, 5 km ring) | 中心建成区外 5 km 环带非建成栅格 MODIS NDVI 均值 | 无量纲 |
| `ndvi_gap` | 城区相对本底的绿度差 | core-minus-background NDVI | ndvi_core − ndvi_ring | 无量纲 |
| `greenpatch_pc_core` | 人均连片绿地（公园代理） | park proxy per capita | 中心建成区内面积 ≥ 1 公顷的连片绿地（WorldCover 树木+灌木+草地）面积 / 中心建成区人口 | m²/人 |
| `greenpatch_access_share` | 连片绿地 500 m 可达人口比例（公园可达代理） | share of population within 500 m of a ≥1 ha green patch | 斑块 500 m 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口 | 比值 |
| `riparian_green_pc` | 人均滨水绿带（绿道代理） | riparian green per capita | 水体（JRC 出现频率 ≥ 50%）外扩 50 m 内的绿地面积 / 中心建成区人口 | m²/人 |
| `roadside_green_pc` | 人均道路两侧绿带（绿道代理） | roadside green per capita | GHSL 2018 道路面外扩 20 m 内的绿地面积 / 中心建成区人口 | m²/人 |
| `openveg_share_2018` | 聚落内植被开放空间占比（2018） | vegetated open space share (GHS-BUILT-C) | GHSL 2018 聚落特征 1–3 类面积 / 各地类面积之和 | 比值 |
| `road_share_2018` | 道路面占比（2018） | road surface share (GHS-BUILT-C) | GHSL 2018 聚落特征 5 类面积 / 各地类面积之和 | 比值 |
| `park_pc_core` | 人均公园面积（可选） | park area per capita | 公园多边形面积 / 中心建成区人口（需提供公园数据） | m²/人 |
| `park_access_share` | 公园步行可达人口比例（可选） | share of population within walking distance of a park | 公园 500 m 缓冲区内人口 / 中心建成区人口 | 比值 |
| `floor_res_pc_core` | 人均住宅建筑面积（遥感估算） | residential floor area per capita (GHSL volume) | (总建筑体量 − 非住宅体量) / 层高 / 中心建成区人口 | m²/人 |
| `floor_res_pc_unit` | 人均住宅建筑面积（单元，遥感估算） | residential floor area per resident | 单元内 (总体量 − 非住宅体量) / 层高 / 2020 常住人口 | m²/人 |
| `ntl_per_built` | 单位建成面积夜间灯光 | night-light radiance per km² built-up | VIIRS 2020 average_masked 求和 / 中心建成区建成面积（km²）；越低表示建成空间利用强度越低 | nW/cm²/sr per km² |
| `ntl_per_volume` | 单位建筑体量夜间灯光 | night-light radiance per building volume | 中心建成区 VIIRS 2020 求和 / 建筑体量（百万 m³）；识别“高供给、低活力” | nW/cm²/sr per 10⁶ m³ |
| `ntl_pc` | 人均夜间灯光 | night-light radiance per resident | 单元 VIIRS 2020 求和 / 2020 常住人口 | nW/cm²/sr per 人 |
| `core_growth_1020` | 中心建成区面积对数变化 | log change of core area | ln(2020 动态核心面积 / 2010 动态核心面积) | 对数差 |
| `lcrpgr` | 土地消耗率/人口增长率之比 (SDG 11.3.1) | land consumption rate to population growth rate ratio | ln(A2020/A2010) / ln(P2020/P2010)，P 为单元常住人口；人口变化接近 0 时不计算 | 比值 |
| `land_pop_diverge` | 扩张—收缩背离 | built-up expansion under population decline | 中心建成区面积增长且常住人口下降 = 1 | 0/1 |
| `green_official_ratio` | 官方/遥感人均绿地比（可选） | official-to-remote-sensing green ratio | 住建部人均公园绿地面积 / 遥感人均绿地面积 | 比值 |
| `city_size_class` | 城市规模等级 | city size class (State Council 2014) | 按城区常住人口（万人）套用国发〔2014〕51号标准；超大特大按七普名单 | 类别 |
| `group5` | 五类分组 | five-group typology | 超大特大城市市辖区 / 大城市市辖区 / 中小城市市辖区 / 县级市 / 县 | 类别 |
| `quadrant` | 财政—人口四象限 | fiscal–demographic quadrant | 财政自给率是否 ≥ 阈值 × 常住人口是否增长 | 类别 |

## 原始遥感字段命名规则

`01_gee_extract_rs.py` 输出的原始字段以前缀区分统计范围。`u_` 为整个分析单元，`c_` 为中心建成区（2020 年边界），`r_` 为中心建成区外 5 km 环带，后缀为年份。例如 `c_bs_2010` 是 2020 年中心建成区范围内 2010 年的 GHSL 建成面积（m²），`core2010_area_m2` 是按 2010 年 GHSL 单独识别的中心建成区面积。

| 字段 | 含义 | 来源（GEE asset） |
|---|---|---|
| `*_bs_YYYY` / `*_bsn_YYYY` | 建成面积 / 非住宅建成面积（m²） | JRC/GHSL/P2023A/GHS_BUILT_S |
| `*_bv_YYYY` / `*_bvn_YYYY` | 建筑总体量 / 非住宅体量（m³） | JRC/GHSL/P2023A/GHS_BUILT_V |
| `*_pop_ghs_YYYY` | 人口 | JRC/GHSL/P2023A/GHS_POP |
| `*_pop_wp_YYYY` | 人口（稳健性） | WorldPop/GP/100m/pop |
| `*_ntl_viirs_YYYY` / `*_ntl_ccnl_YYYY` | 夜间灯光辐亮度求和 | NOAA/VIIRS/DNB/ANNUAL_V21（2013 至 2021 年）、ANNUAL_V22（2022 年起），average_masked；BNU/FGS/CCNL/v1 |
| `c_wc_<类>_m2` | 各地类面积（m²） | ESA/WorldCover/v100 |
| `c_pw_tree_YYYY` / `c_pw_green_YYYY` / `c_pop_expo_YYYY` | 人口 × 邻域树木（绿地）比例之和 / 人口之和 | WorldCover × GHS-POP |
| `c_greenpatch_m2_YYYY` / `c_pop_greenpatch500_YYYY` | ≥1 公顷连片绿地面积 / 其 500 m 内人口 | WorldCover × GHS-POP |
| `c_riparian_green_m2_YYYY` / `c_roadside_green_m2_YYYY` | 滨水绿带 / 道路两侧绿带面积 | WorldCover × JRC/GSW1_4 / GHS_BUILT_C |
| `c_openveg_m2_2018` / `c_road_m2_2018` | 聚落内植被开放空间 / 道路面面积 | JRC/GHSL/P2023A/GHS_BUILT_C |
| `c_ndvi_s2_YYYY` | 生长季 NDVI 均值 | COPERNICUS/S2_SR_HARMONIZED |
| `c_dw_trees_YYYY` / `c_dw_grass_YYYY` | 树木 / 草地概率均值 | GOOGLE/DYNAMICWORLD/V1 |
| `r_ndvi_modis_YYYY` | 环带非建成栅格 NDVI 均值 | MODIS/061/MOD13Q1 |
| `*_elev` / `*_slope` | 高程、坡度均值 | NASA/NASADEM_HGT/001 |
| `u_t2m_c_YYYY` / `u_prcp_mm_YYYY` | 年均气温（°C）/ 年降水（mm） | ECMWF/ERA5_LAND/MONTHLY_AGGR |
| `u_access_min` | 到最近城市的出行时间均值（分钟，2015） | projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0 |
| `c_park_m2_YYYY` / `c_pop_park500_YYYY` | 公园面积 / 公园 500 m 内人口（可选） | 用户上传的公园多边形 |
