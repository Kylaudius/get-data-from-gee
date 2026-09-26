# 附录C 指标定义与计算公式（v1.0）

本附录由 `代码/tools/export_codebook_md.py` 根据 `代码/03_build_indicators.py` 中的 CODEBOOK 自动生成，与代码计算口径一致。

财政金额统一换算为元。主分析期为 2017 至 2019 年三年均值，是营改增后第一个完整年度到疫情前的时段，只在收入与支出都有数的年份上平均。稳健性年份为 2018、2019、2021 年，2010 期为 2009 至 2011 年，2000 期为 1999 至 2001 年。财政水平量以 2010 年普查常住人口为分母，这一分母先于主分析期确定。人口来自第五、六、七次人口普查分县资料，统一到 2020 年行政区划边界。遥感指标除特别说明外为 2020 年，统计范围为 2020 年中心建成区。中心建成区退化为几何中心 1 km 缓冲的单元，全部中心建成区指标记为缺失。表中 P2020、P2010、P2000 为普查常住人口，core_pop 为中心建成区人口主口径。

| 变量名 | 中文名 | 英文术语 | 公式 | 单位 |
|---|---|---|---|---|
| `fss` | 财政自给率（描述） | fiscal self-sufficiency ratio | 一般公共预算收入 / 一般公共预算支出，主分析期均值；只作描述，不进入回归 | 比值 |
| `gap_ratio` | 转移支付依赖度（描述） | transfer dependence ratio | = 1 − fss，仅作描述 | 比值 |
| `net_inflow_pc` | 人均净流入 | net fiscal inflow per capita | (一般公共预算支出 − 一般公共预算收入) / P2010。分母取 2010 年人口，不受此后人口变化影响；净缺口含转移支付、债务收入、调入资金与上年结转 | 元/人 |
| `net_inflow_pc_k` | 人均净流入（千元） | net fiscal inflow per capita, thousand yuan | net_inflow_pc / 1000；回归的核心财政变量，缩尾后以线性形式进入模型 | 千元/人 |
| `own_rev_pc` | 人均本级收入 | own-source revenue per capita | 一般公共预算收入 / P2010；回归中取对数 | 元/人 |
| `exp_pc_2010base` | 人均支出（2010 年人口为分母） | expenditure per capita, 2010 population base | 一般公共预算支出 / P2010 | 元/人 |
| `net_inflow_pc_rob` | 人均净流入（稳健性年份） | net fiscal inflow per capita, robustness years | 同 net_inflow_pc，财政取 fiscal_years_robust（默认 2018、2019、2021）均值 | 元/人 |
| `net_inflow_pc_k_rob` | 人均净流入（稳健性年份，千元） | net fiscal inflow per capita, robustness years, thousand yuan | net_inflow_pc_rob / 1000 | 千元/人 |
| `own_rev_pc_rob` | 人均本级收入（稳健性年份） | own-source revenue per capita, robustness years | 稳健性年份一般公共预算收入 / P2010 | 元/人 |
| `exp_pc_2010base_rob` | 人均支出（稳健性年份） | expenditure per capita, robustness years | 稳健性年份一般公共预算支出 / P2010 | 元/人 |
| `exp_pc_res` | 人均财政支出（常住口径） | expenditure per resident | 一般公共预算支出 / P2020 | 元/人 |
| `exp_pc_hukou` | 人均财政支出（户籍口径） | expenditure per registered resident | 一般公共预算支出 / 户籍人口 | 元/人 |
| `gap_pc_res` | 人均财政缺口（常住口径） | fiscal gap per resident | (支出 − 收入) / P2020 | 元/人 |
| `rev_pc_res` | 人均本级收入（常住口径） | own-source revenue per resident | 一般公共预算收入 / P2020 | 元/人 |
| `tax_share` | 税收收入占比 | tax share of own revenue | 税收收入 / 一般公共预算收入 | 比值 |
| `transfer_obs_pc` | 人均转移支付（观测值） | observed transfers per capita | 转移支付合计 / P2010；只在录入了转移支付的单元计算（2009 年《全国地市县财政统计资料》或试点省决算） | 元/人 |
| `specific_share` | 专项转移支付占比 | specific-purpose share of transfers | 专项转移支付 / (一般性转移支付 + 专项转移支付) | 比值 |
| `tax_rebate_share` | 税收返还占比 | tax rebate share of transfers | 税收返还 / 转移支付合计；合计缺失时分母取 税收返还 + 一般性转移支付 + 专项转移支付 | 比值 |
| `fss_2010` | 财政自给率（2010 期） | fiscal self-sufficiency, 2009–2011 | 2009–2011 年均收入 / 年均支出 | 比值 |
| `net_inflow_pc_2010` | 人均净流入（2010 期） | net fiscal inflow per capita, 2009–2011 | (2009–2011 年均支出 − 年均收入) / P2010；与 transfer_obs_pc_2010 对照，检验净缺口代理 | 元/人 |
| `transfer_obs_pc_2010` | 人均转移支付（2010 期观测值） | observed transfers per capita, 2009–2011 | 2009–2011 年有数年份的转移支付合计均值 / P2010；通常只有 2009 年《全国地市县财政统计资料》一年 | 元/人 |
| `specific_share_2010` | 专项转移支付占比（2010 期） | specific-purpose share of transfers, 2009–2011 | 专项转移支付 / (一般性转移支付 + 专项转移支付)，2010 期 | 比值 |
| `gap_ratio_2000` | 转移支付依赖度（2000 期） | transfer dependence ratio, 1999–2001 | (1999–2001 年均支出 − 年均收入) / 年均支出 | 比值 |
| `transfer_pc_2000_k` | 人均转移支付（2000 期，预先确定） | predetermined transfers per capita, 1999–2001 | 有转移支付观测值时取 1999–2001 年均转移支付合计 / P2000，否则取年均净流入 / P2000，再除以 1000；来源见 transfer_2000_src；长差分的处理变量 | 千元/人 |
| `transfer_2000_src` | 2000 期转移支付来源 | source of the 2000 transfer measure | observed 为转移支付观测值，net_inflow 为净缺口代理 | 类别 |
| `exp_edu_share` | 教育支出占比 | education share of expenditure | 教育支出 / 一般公共预算支出 | 比值 |
| `exp_health_share` | 卫生健康支出占比 | health share of expenditure | 卫生健康支出 / 一般公共预算支出 | 比值 |
| `exp_community_share` | 城乡社区支出占比 | urban and rural community affairs share of expenditure | 城乡社区支出 / 一般公共预算支出；公园与市政维护最直接的预算科目 | 比值 |
| `exp_personnel_share` | 工资福利支出占比 | personnel share of expenditure | 工资福利支出（经济分类）/ 一般公共预算支出；检验对立假说 R1 | 比值 |
| `exp_genpub_share` | 一般公共服务支出占比 | general public services share of expenditure | 一般公共服务支出 / 一般公共预算支出；检验对立假说 R1 | 比值 |
| `land_conv_pc` | 人均土地出让价款 | land conveyance revenue per capita | 中国土地市场网出让价款（主分析期年均）/ P2010 | 元/人 |
| `land_dep` | 土地出让依赖度 | land-conveyance dependence | 土地出让价款 / 一般公共预算收入，主分析期均值；全部单元用土地市场网汇总，缺失时用财政表中的土地出让收入 | 比值 |
| `lgfv_debt_pc` | 人均城投有息债务 | LGFV interest-bearing debt per capita | 城投平台有息债务（主分析期年末均值，按平台所属行政单位归并）/ P2010 | 元/人 |
| `special_bond_pc` | 人均新增专项债 | new special-purpose bonds per capita | 文件所列各年新增专项债合计 / P2010 | 元/人 |
| `special_bond_green_pc` | 人均市政与绿化类专项债 | municipal, greening and ecological special bonds per capita | 市政、园林绿化、生态环保三类新增专项债合计 / P2010 | 元/人 |
| `devzone_share` | 开发区核准面积比 | development-zone approved area relative to core | (国家级 + 省级开发区核准面积) / 中心建成区面积；开发区可位于中心建成区外，比值可大于 1 | 比值 |
| `admin_rank` | 行政等级 | administrative rank | 4 直辖市，3 副省级城市，2 其他省会城市，1 其他地级市（市辖区单元；外围市辖区取所属城市），0 县级市与县；来自 外部参数/admin_rank.csv | 序数 |
| `pop_chg_1020` | 常住人口对数变化 2010–2020 | log change of resident population | ln(P2020 / P2010)，普查常住人口；任一期人口为 0 或缺失时不计算 | 对数差 |
| `pop_chg_0010` | 常住人口对数变化 2000–2010 | log change of resident population | ln(P2010 / P2000) | 对数差 |
| `res_hukou_ratio` | 常住与户籍人口之比 | resident-to-registered ratio | P2020 / 户籍人口；小于 1 表示人口净流出 | 比值 |
| `urb_rate_2020` | 城镇化率 2020 | urbanization rate | 城镇人口 / 常住人口 | 比值 |
| `share_hukou_elsewhere` | 人户分离人口比例 2020 | share of residents registered elsewhere | 七普表3“户口登记地在外乡镇街道的人口” / 常住人口；含县内跨乡镇迁移，只作流动强度的近似 | 比值 |
| `conv_pop_share_2020` | 撤县设区人口占比 | population share of converted districts | 市辖区单元 2020 年常住人口中，2000 年后撤县（市）设区的区所占比例 | 比值 |
| `share_rent_market` | 市场租赁户比例 2020 | share of households renting on the market | 租赁廉租住房、公租房以外住房的家庭户 / 家庭户（七普长表，按户数合并到单元） | 比值 |
| `share_rent_public` | 公租房租赁户比例 2020 | share of households renting public housing | 租赁廉租住房或公租房的家庭户 / 家庭户 | 比值 |
| `share_commodity` | 商品房户比例 2020 | share of households in purchased commodity housing | 购买新建商品房与二手房的家庭户 / 家庭户 | 比值 |
| `share_self_built` | 自建房户比例 2020 | share of households in self-built housing | 自建住房的家庭户 / 家庭户 | 比值 |
| `housing_area_pc` | 人均住房建筑面积 2020 | housing floor area per household member | 家庭户住房建筑面积 / 家庭户人口（按家庭户人口合并到单元） | m²/人 |
| `collective_share` | 集体户人口比例 2020 | share of population in collective households | 集体户人口 / P2020；刻画宿舍劳动体制 (dormitory labour regime) | 比值 |
| `housing_slack_ratio` | 住房余量比 | housing slack ratio | 单元 GHSL 住宅建筑面积 ((u_bv_2020 − u_bvn_2020) / 层高) / (人均住房建筑面积 × 家庭户人口 2020)；大于 1 表示空置或季节性居住，小于 1 表示拥挤 | 比值 |
| `core_pop` | 中心建成区人口（主口径） | core population, main source | 按 analysis.core_pop_source 取 core_pop_official 或 core_pop_ghs，缺失时改用另一种，来源见 core_pop_src；低于 analysis.min_core_pop 记为缺失 | 人 |
| `core_pop_src` | 中心建成区人口来源 | source of core population | official 或 ghs | 类别 |
| `core_pop_ghs` | 中心建成区人口（GHS-POP 重标定） | core population, census-rescaled GHS-POP | GHS-POP 2020 中心建成区求和 × (P2020 / GHS-POP 单元求和)；普查缺失时用未重标定值。GHS-POP 按建筑体量分配人口，隐含各处入住率相同 | 人 |
| `core_pop_official` | 中心建成区人口（官方统计） | core population, official statistics | 市辖区与县级市取七普城区常住人口（city_urban_pop_file）；县取住建部《县城建设统计年鉴》mohurd_stock_year 年县城人口加暂住人口；前者缺失时用住建部同口径数 | 人 |
| `core_pop_ratio_official_ghs` | 官方与遥感中心人口之比 | official-to-GHS core population ratio | core_pop_official / core_pop_ghs；中心建成区识别的质控指标 | 比值 |
| `core_pop_2010_ghs` | 中心建成区人口 2010（GHS-POP 重标定） | core population 2010, census-rescaled | c_pop_ghs_2010 × P2010 / u_pop_ghs_2010，范围固定为 2020 年中心建成区 | 人 |
| `core_pop_chg_1020` | 中心建成区人口对数变化 2010–2020 | log change of core population | ln(core_pop_ghs / core_pop_2010_ghs)；两期各按当年普查重标定 | 对数差 |
| `core_share_2020` | 中心建成区人口占单元比例 2020 | core share of unit population | core_pop_ghs / P2020，等于 c_pop_ghs_2020 / u_pop_ghs_2020 | 比值 |
| `core_share_chg_1020` | 中心建成区人口占比变化 2010–2020 | change in core share of unit population | core_share_2020 − core_pop_2010_ghs / P2010 | 比值差 |
| `quadrant_town` | 单元与中心人口变化四象限 | unit versus core population-change quadrant | 按 pop_chg_1020 与 core_pop_chg_1020 的正负分为 县域收缩-县城增长、县域收缩-县城收缩、县域增长-县城增长、县域增长-县城收缩；市辖区单元的县域指单元，县城指中心城区 | 类别 |
| `core_pop_cf2010` | 反事实中心建成区人口 | counterfactual core population | P2010 × c_pop_ghs_2020 / u_pop_ghs_2020，即 2020 年中心占比不变、单元人口停留在 2010 年时的中心人口 | 人 |
| `denom_effect_core` | 分母效应 | denominator effect | ln(core_pop_cf2010 / core_pop)，等于任一中心人均指标的 ln(实际值) − ln(反事实值)，树木、绿地、大型树木斑块与建成面积四项按构造相同；主口径为 ghs 时等于 −pop_chg_1020 | 对数差 |
| `tree_pc_unit` | 人均树木覆盖（单元常住口径） | core tree cover per unit resident | 中心建成区树木面积 / P2020 | m²/人 |
| `tree_pc_hukou` | 人均树木覆盖（户籍口径） | core tree cover per registered resident | 中心建成区树木面积 / 户籍人口 | m²/人 |
| `tree_pc_core_cf2010` | 人均树木覆盖（反事实分母） | core tree cover per counterfactual core resident | 中心建成区树木面积 / core_pop_cf2010 | m²/人 |
| `tree_pc_core_ghs` | 人均树木覆盖（GHS-POP 分母，稳健性） | tree cover per capita, GHS-POP denominator | 中心建成区树木面积 / core_pop_ghs；低于 min_core_pop 不计算 | m²/人 |
| `green_pc_unit` | 人均绿地（单元常住口径） | core green space per unit resident | 中心建成区树木 + 灌木 + 草地面积 / P2020 | m²/人 |
| `green_pc_hukou` | 人均绿地（户籍口径） | core green space per registered resident | 同上 / 户籍人口 | m²/人 |
| `green_pc_core_cf2010` | 人均绿地（反事实分母） | core green space per counterfactual core resident | 同上 / core_pop_cf2010 | m²/人 |
| `greenpatch_pc_unit` | 人均大型树木斑块（单元常住口径） | large tree patch area per unit resident | c_greenpatch_m2_2020 / P2020 | m²/人 |
| `greenpatch_pc_hukou` | 人均大型树木斑块（户籍口径） | large tree patch area per registered resident | c_greenpatch_m2_2020 / 户籍人口 | m²/人 |
| `greenpatch_pc_core_cf2010` | 人均大型树木斑块（反事实分母） | large tree patch area per counterfactual core resident | c_greenpatch_m2_2020 / core_pop_cf2010 | m²/人 |
| `builtup_pc_unit` | 人均建成面积（单元常住口径） | core built-up surface per unit resident | c_bs_2020 / P2020 | m²/人 |
| `builtup_pc_hukou` | 人均建成面积（户籍口径） | core built-up surface per registered resident | c_bs_2020 / 户籍人口 | m²/人 |
| `builtup_pc_core_cf2010` | 人均建成面积（反事实分母） | core built-up surface per counterfactual core resident | c_bs_2020 / core_pop_cf2010 | m²/人 |
| `dlnS_builtup_1020` | 建成面积对数变化 2010–2020 | log change of built-up surface in the fixed core | ln(c_bs_2020 / c_bs_2010) | 对数差 |
| `dlnS_volume_1020` | 建筑体量对数变化 2010–2020 | log change of building volume in the fixed core | ln(c_bv_2020 / c_bv_2010) | 对数差 |
| `dlnS_imp_1018` | 不透水面对数变化 2010–2018（分解表用） | log change of impervious surface, 2010–2018 | ln(c_gaia_imp_m2_2018 / c_gaia_imp_m2_2010)，与 imp_growth_1018_core 相同 | 对数差 |
| `dlnS_imp_0010` | 不透水面对数变化 2000–2010（分解表用） | log change of impervious surface, 2000–2010 | ln(c_gaia_imp_m2_2010 / c_gaia_imp_m2_2000)，与 imp_growth_0010_core 相同 | 对数差 |
| `dlnP_core_1020` | 中心人口对数变化（分解表用） | log change of core population | = core_pop_chg_1020 | 对数差 |
| `dln_builtup_pc_1020` | 人均建成面积对数变化 2010–2020 | log change of built-up surface per core resident | dlnS_builtup_1020 − dlnP_core_1020 | 对数差 |
| `core_area_km2` | 中心建成区面积 | core built-up area | GHSL 2020 建成栅格经闭运算、填洞后含驻地点的斑块（无驻地点时取最大斑块）面积 | km² |
| `core_fallback` | 中心建成区为几何中心缓冲 | core fell back to a centroid buffer | core_method 为 fallback_centroid_1km 时为 1；这类单元的全部中心建成区指标记为缺失 | 0/1 |
| `core_builtcell_share` | 中心建成区建成栅格比例 | share of core in built cells before closing | c_builtcell_m2_2020 / core_area_m2；闭运算与填洞前已达建成阈值的 GHSL 栅格占比，越低表示并入的河流、山体与湖泊越多 | 比值 |
| `smod_share_core` | 中心建成区中城镇簇比例 | share of core in GHS-SMOD urban clusters | c_smod_ucl_m2_2020 / core_area_m2；SMOD 代码 22、23、30 | 比值 |
| `core_mohurd_ratio` | 遥感与住建部建成区面积之比 | remote-sensing to MOHURD built-up area ratio | core_area_km2 / 住建部建成区面积（mohurd_stock_year） | 比值 |
| `builtup_pc_core` | 人均建成面积（中心建成区） | built-up surface per capita | GHSL 建成面积 / core_pop | m²/人 |
| `tree_area_m2_core` | 中心建成区树木面积 | tree cover area in core | WorldCover 树木 (10) 与红树林 (95) 面积之和 | m² |
| `tree_share_core` | 树木覆盖占比（中心建成区，主口径） | tree cover share | 树木面积 / 各地类面积之和；WorldCover 草地类精度低，故以树木为主口径 | 比值 |
| `tree_pc_core` | 人均树木覆盖面积（主口径） | tree cover per capita | 树木面积 / core_pop | m²/人 |
| `tree_stock_pc_core` | 人均存量树木 | pre-existing tree cover per capita | c_tree_stock_m2_2020 / core_pop；存量指 Hansen 2000 年树冠覆盖度 ≥ gee.baseline_tree_cover_pct 的 2020 年树木像元 | m²/人 |
| `tree_new_pc_core` | 人均新增树木 | new tree cover per capita | c_tree_new_m2_2020 / core_pop | m²/人 |
| `tree_new_share` | 新增树木占比 | share of new tree cover | c_tree_new_m2_2020 / (c_tree_stock_m2_2020 + c_tree_new_m2_2020) | 比值 |
| `tree_flat_share` | 平缓地树木占比 | share of tree cover on gentle slopes | c_tree_flat_m2_2020 / 树木面积；坡度 ≤ gee.slope_mask_deg，用于排除山体残林的敏感性检验 | 比值 |
| `green_share_core` | 绿地占比（稳健性口径） | green share | 树木 + 灌木 + 草地面积 / 各地类面积之和 | 比值 |
| `green_pc_core` | 人均绿地面积（稳健性口径） | green space per capita | 树木 + 灌木 + 草地面积 / core_pop | m²/人 |
| `expo_tree_core` | 人口加权树木暴露（主口径） | population-weighted tree-cover exposure | Σ(格网人口 × 格网周围 500 m 树木覆盖比例) / Σ格网人口（Chen et al. 2022） | 比值 |
| `expo_green_core` | 人口加权绿地暴露（稳健性口径） | population-weighted greenspace exposure | 同上，绿地为树木、灌木与草地 | 比值 |
| `ndvi_core` | 中心建成区 NDVI | mean NDVI (Sentinel-2) | 2020 年 5–9 月 Sentinel-2 中值合成 NDVI 均值，剔除水面 | 无量纲 |
| `ndvi_ring` | 自然植被本底 | background NDVI (MODIS, 5 km ring) | 中心建成区外 5 km 环带非建成栅格 MODIS NDVI 均值，剔除水面 | 无量纲 |
| `ndvi_gap` | 城区相对本底的绿度差 | core-minus-background NDVI | ndvi_core − ndvi_ring | 无量纲 |
| `greenpatch_pc_core` | 人均大型树木斑块 | large tree patch area per capita | 中心建成区内面积 ≥ gee.green_patch_min_m2 的连通树木斑块面积 / core_pop；地类由 gee.green_patch_class 设定（默认只用树木），连通计数前先截断于中心建成区。遥感代理不称公园，公园一词只用于矢量数据 | m²/人 |
| `greenpatch_access_share` | 大型树木斑块 500 m 可达人口比例 | share of population within 500 m of a large tree patch | 斑块 500 m 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口 | 比值 |
| `riparian_green_pc` | 人均滨水线性绿地 | riparian linear green space per capita | 近永久水体外扩 gee.riparian_buffer_m 内的绿地面积 / core_pop；水体为 JRC 出现频率 ≥ gee.riparian_water_occurrence 且连通水面 ≥ gee.riparian_min_water_m2，或 gee.river_asset；绿地地类同大型树木斑块 | m²/人 |
| `roadside_green_pc` | 人均道路绿带（行道树代理，辅助指标） | roadside green per capita, street-tree proxy | GHSL 2018 道路面外扩 gee.road_buffer_m 内的绿地面积 / core_pop | m²/人 |
| `greenway_len_per_10k` | 每万人绿道长度 | greenway length per 10,000 core residents | c_greenway_len_m / (core_pop / 10000)；需提供 gee.greenway_asset 矢量 | m/万人 |
| `greenway_access_share` | 绿道可达人口比例 | share of population near a greenway | 绿道 gee.greenway_access_distance_m 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口 | 比值 |
| `openveg_share_2018` | 聚落内植被开放空间占比（2018） | vegetated open space share (GHS-BUILT-C) | GHSL 2018 聚落特征 1–3 类面积 / 各地类面积之和 | 比值 |
| `road_share_2018` | 道路面占比（2018） | road surface share (GHS-BUILT-C) | GHSL 2018 聚落特征 5 类面积 / 各地类面积之和 | 比值 |
| `park_pc_core` | 人均公园面积（可选） | park area per capita | 公园多边形面积 / core_pop（需提供公园矢量） | m²/人 |
| `park_access_share` | 公园步行可达人口比例（可选） | share of population within walking distance of a park | 公园 500 m 缓冲区内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口 | 比值 |
| `floor_res_pc_core` | 人均住宅建筑面积（遥感估算） | residential floor area per capita (GHSL volume) | (总建筑体量 − 非住宅体量) / 层高 / core_pop | m²/人 |
| `floor_res_pc_unit` | 人均住宅建筑面积（单元，遥感估算） | residential floor area per resident | 单元内 (总体量 − 非住宅体量) / 层高 / P2020 | m²/人 |
| `ntl_per_built` | 单位建成面积夜间灯光 | night-light radiance per km² built-up | VIIRS 2020 average_masked 求和 / 中心建成区建成面积（km²）；受路灯影响，只作辅助指标 | nW/cm²/sr per km² |
| `ntl_per_volume` | 单位建筑体量夜间灯光 | night-light radiance per building volume | 中心建成区 VIIRS 2020 求和 / 建筑体量（百万 m³） | nW/cm²/sr per 10⁶ m³ |
| `ntl_pc` | 人均夜间灯光 | night-light radiance per resident | 单元 VIIRS 2020 求和 / P2020 | nW/cm²/sr per 人 |
| `core_growth_1020` | 中心建成区面积对数变化 | log change of core area | ln(2020 动态核心面积 / 2010 动态核心面积) | 对数差 |
| `lcrpgr` | 土地消耗率与人口增长率之比 (SDG 11.3.1) | land consumption rate to population growth rate ratio | ln(A2020/A2010) / ln(P2020/P2010)，P 为单元常住人口；人口变化接近 0 时不计算 | 比值 |
| `land_pop_diverge` | 扩张与收缩背离 | built-up expansion under population decline | 中心建成区面积增长且常住人口下降 = 1 | 0/1 |
| `imp_growth_0010_core` | 不透水面对数变化 2000–2010（中心建成区） | log change of impervious surface in core, 2000–2010 | ln(c_gaia_imp_m2_2010 / c_gaia_imp_m2_2000)，范围固定为 2020 年中心建成区；GAIA | 对数差 |
| `imp_growth_1018_core` | 不透水面对数变化 2010–2018（中心建成区） | log change of impervious surface in core, 2010–2018 | ln(c_gaia_imp_m2_2018 / c_gaia_imp_m2_2010) | 对数差 |
| `imp_growth_0010_unit` | 不透水面对数变化 2000–2010（单元） | log change of impervious surface in unit, 2000–2010 | ln(u_gaia_imp_m2_2010 / u_gaia_imp_m2_2000) | 对数差 |
| `imp_growth_1018_unit` | 不透水面对数变化 2010–2018（单元） | log change of impervious surface in unit, 2010–2018 | ln(u_gaia_imp_m2_2018 / u_gaia_imp_m2_2010) | 对数差 |
| `forest_share_clcd_YYYY` | CLCD 森林占比（可选） | CLCD forest share of core | c_clcdYYYY_forest_m2 / 当年各 CLCD 地类面积之和，YYYY 取 gee.clcd_years；需配置 gee.clcd_asset_template | 比值 |
| `green_new_clcd_share` | CLCD 新增绿地占比（可选） | share of CLCD green that is new since the baseline year | c_green_new_clcd_m2_2020 / 2020 年 CLCD 森林、灌木与草地面积；新增指 gee.clcd_baseline_year 时不属这三类 | 比值 |
| `beds_per_1k_res` | 每千常住人口床位 | hospital beds per 1,000 residents | 医疗卫生机构床位（主分析期均值）/ P2020 × 1000 | 张/千人 |
| `beds_per_1k_hukou` | 每千户籍人口床位 | hospital beds per 1,000 registered residents | 床位 / 户籍人口 × 1000 | 张/千人 |
| `beds_res_hukou_ratio` | 床位常住与户籍口径之比 | resident-to-registered ratio of bed provision | beds_per_1k_res / beds_per_1k_hukou；代数上等于 户籍人口 / P2020，只在有床位数的单元计算，用来对照同一供给在两种口径下的差距 | 比值 |
| `students_per_child` | 在校生与 0–14 岁人口之比 | enrolled students per child aged 0–14 | (小学 + 普通中学在校生) / (share_0_14 × P2020)；学龄与 0–14 岁并不对应，只是近似 | 比值 |
| `welfare_beds_per_1k_65` | 每千名 65 岁以上老人养老床位 | welfare beds per 1,000 residents aged 65+ | 社会福利收养性单位床位 / (share_65plus × P2020) × 1000 | 张/千人 |
| `teachers_per_100_students` | 每百名学生专任教师 | full-time teachers per 100 students | 专任教师 / (小学 + 普通中学在校生) × 100 | 人/百人 |
| `school_access_share` | 学校可达人口比例（可选） | share of core population near a school | 学校点位 gee.poi_access_distance_m.school 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口；需提供 gee.poi_assets.school | 比值 |
| `hospital_access_share` | 医院可达人口比例（可选） | share of core population near a hospital | 医院点位 gee.poi_access_distance_m.hospital 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口；需提供 gee.poi_assets.hospital | 比值 |
| `elderly_access_share` | 养老机构可达人口比例（可选） | share of core population near a care home | 养老机构点位 gee.poi_access_distance_m.elderly 范围内的 GHS-POP 人口 / 中心建成区 GHS-POP 人口；需提供 gee.poi_assets.elderly | 比值 |
| `school_per_10k` | 每万人学校数（可选） | schools per 10,000 core residents | 中心建成区内学校点位数 / core_pop × 10000 | 个/万人 |
| `hospital_per_10k` | 每万人医院数（可选） | hospitals per 10,000 core residents | 中心建成区内医院点位数 / core_pop × 10000 | 个/万人 |
| `elderly_per_10k` | 每万人养老机构数（可选） | care homes per 10,000 core residents | 中心建成区内养老机构点位数 / core_pop × 10000 | 个/万人 |
| `park_count` | 公园个数（住建部） | number of parks (MOHURD) | mohurd_stock_year 年鉴报告值 | 个 |
| `park_area_pc_mohurd` | 人均公园面积（住建部，中心人口分母） | park area per core resident (MOHURD) | 公园面积（公顷）× 10000 / core_pop；县的 core_pop 主口径取自住建部县城人口加暂住人口，与年鉴分母同源，core_pop_source 设为 ghs 时改用普查重标定人口 | m²/人 |
| `road_area_pc_mohurd` | 人均道路面积（住建部，中心人口分母） | road area per core resident (MOHURD) | 道路面积（万 m²）× 10000 / core_pop | m²/人 |
| `park_green_pc_m2` | 人均公园绿地面积（住建部报告值） | park green space per capita as reported | 年鉴报告值，分母为城区（县城）人口加暂住人口 | m²/人 |
| `mohurd_builtup_area_km2` | 建成区面积（住建部） | built-up area (MOHURD) | mohurd_stock_year 年鉴报告值 | km² |
| `muni_invest_pc` | 人均市政公用设施投资 | municipal infrastructure investment per core resident | mohurd_years_main 年均市政公用设施建设固定资产投资 / core_pop | 元/人 |
| `muni_invest_green_pc` | 人均园林绿化投资 | landscaping investment per core resident | 年均园林绿化投资 / core_pop | 元/人 |
| `muni_invest_road_pc` | 人均道路桥梁投资 | road and bridge investment per core resident | 年均道路桥梁投资 / core_pop | 元/人 |
| `fund_fiscal_share` | 财政拨款占资金来源比例 | fiscal appropriation share of funding | (中央财政拨款 + 地方财政拨款) / 资金来源合计，mohurd_years_main 各年加总后相除 | 比值 |
| `fund_debt_share` | 债券与贷款占资金来源比例 | bond and loan share of funding | (债券 + 国内贷款) / 资金来源合计 | 比值 |
| `fund_self_share` | 自筹资金占资金来源比例 | self-raised share of funding | 自筹资金 / 资金来源合计 | 比值 |
| `maint_subsidy_share` | 维护建设资金中上级补助比例 | upper-level subsidy share of maintenance funds | 上级补助 / 城市（县城）维护建设资金收入合计 | 比值 |
| `maint_land_share` | 维护建设资金中土地出让转入比例 | land-revenue share of maintenance funds | 土地出让转入 / 维护建设资金收入合计 | 比值 |
| `green_official_ratio` | 官方与遥感人均绿地之比（可选） | official-to-remote-sensing green ratio | 住建部人均公园绿地面积 / 遥感人均绿地面积 | 比值 |
| `green_official_gap` | 官方与遥感绿地对数差 | log gap between official and remote-sensing green | ln(park_green_pc_m2) − ln(greenpatch_pc_core) | 对数差 |
| `city_size_class` | 城市规模等级（市辖区） | city size class (State Council 2014) | 按城区常住人口（万人）套用国发〔2014〕51号标准；超大特大按七普名单 | 类别 |
| `size_class_all` | 城市规模等级（全部单元） | size class for all units | 同一标准推广到全部单元：市辖区取 city_size_class，县级市取七普城区人口，县取住建部县城人口加暂住人口 | 类别 |
| `admin_size_group` | 行政类型与规模交叉分组 | administrative type by size class | 单元类型 × size_class_all，如 县级市｜Ⅱ型小城市；用于在同一规模档内比较不同行政类型 | 类别 |
| `large_county_city` | 大县级市 | large county-level city | 县级市且城区人口达到Ⅱ型大城市标准（≥ 100 万）为 1 | 0/1 |
| `group5` | 五类分组 | five-group typology | 超大特大城市市辖区 / 大城市市辖区 / 中小城市市辖区 / 县级市 / 县；另有 外围市辖区，以及城区人口缺失、无法分级的 市辖区（规模未知） | 类别 |
| `quadrant` | 财政与人口四象限 | fiscal–demographic quadrant | 财政自给率是否 ≥ 阈值 × 常住人口是否增长 | 类别 |
| `excluded` | 排除单元 | excluded unit | 代码以 units.exclude_code_prefixes 或 analysis.exclude_code_prefixes 开头（默认兵团城市 6590xx）；保留在地图中，不进入表格与回归 | 0/1 |

## 原始遥感字段命名规则

`01_gee_extract_rs.py` 输出的原始字段以前缀区分统计范围。`u_` 为整个分析单元，`c_` 为中心建成区（2020 年边界），`r_` 为中心建成区外 5 km 环带，后缀为年份。例如 `c_bs_2010` 是 2020 年中心建成区范围内 2010 年的 GHSL 建成面积（m²），`core2010_area_m2` 是按 2010 年 GHSL 单独识别的中心建成区面积。

`--annual` 模式另写 `数据/中间/gee/annual/annual_long.csv`，每个单元每年一行，字段为 c_gaia_imp_m2、u_gaia_imp_m2、c_ntl_viirs、u_ntl_viirs、c_dw_trees 与 c_dw_grass。`--units did` 模式对县级单元层（每个 2020 年县级行政区一个单元）做同样的提取，结果在 `数据/中间/gee/did/`。

| 字段 | 含义 | 来源（GEE asset） |
|---|---|---|
| `core_method` / `core_closing_m` / `core_area_m2` | 中心建成区识别方法 / 闭运算半径（m）/ 面积（m²） | JRC/GHSL/P2023A/GHS_BUILT_S |
| `c_builtcell_m2_2020` | 闭运算与填洞前已达建成阈值、位于最终中心建成区内的栅格面积（m²） | JRC/GHSL/P2023A/GHS_BUILT_S |
| `*_bs_YYYY` / `*_bsn_YYYY` | 建成面积 / 非住宅建成面积（m²） | JRC/GHSL/P2023A/GHS_BUILT_S |
| `*_bv_YYYY` / `*_bvn_YYYY` | 建筑总体量 / 非住宅体量（m³） | JRC/GHSL/P2023A/GHS_BUILT_V |
| `*_pop_ghs_YYYY` | 人口 | JRC/GHSL/P2023A/GHS_POP |
| `*_pop_wp_YYYY` | 人口（稳健性） | WorldPop/GP/100m/pop |
| `*_ntl_viirs_YYYY` / `*_ntl_ccnl_YYYY` | 夜间灯光辐亮度求和 | NOAA/VIIRS/DNB/ANNUAL_V21（2013 至 2021 年）、ANNUAL_V22（2022 年起），average_masked；BNU/FGS/CCNL/v1 |
| `c_wc_<类>_m2` | 各地类面积（m²），11 类；树木指标把树木 (10) 与红树林 (95) 合计 | ESA/WorldCover/v100 |
| `c_tree_stock_m2_2020` / `c_tree_new_m2_2020` | 2020 年树木中 2000 年树冠覆盖度达到 / 未达到 gee.baseline_tree_cover_pct 的面积 | ESA/WorldCover/v100 × UMD/hansen/global_forest_change_2025_v1_13（treecover2000） |
| `c_tree_flat_m2_2020` | 坡度不超过 gee.slope_mask_deg 的树木面积 | ESA/WorldCover/v100 × NASA/NASADEM_HGT/001 |
| `c_pw_tree_YYYY` / `c_pw_green_YYYY` / `c_pop_expo_YYYY` | 人口 × 邻域树木（绿地）比例之和 / 人口之和 | WorldCover × GHS-POP |
| `c_greenpatch_m2_YYYY` / `c_pop_greenpatch500_YYYY` | 大型树木斑块面积（先截断于中心建成区再做连通计数）/ 其 500 m 内人口 | WorldCover × GHS-POP |
| `c_riparian_green_m2_YYYY` | 近永久水体外扩带内的绿地面积（滨水线性绿地） | WorldCover × JRC/GSW1_4/GlobalSurfaceWater |
| `c_roadside_green_m2_YYYY` | 道路面外扩带内的绿地面积（行道树代理） | WorldCover × JRC/GHSL/P2023A/GHS_BUILT_C |
| `c_openveg_m2_2018` / `c_road_m2_2018` | 聚落内植被开放空间 / 道路面面积 | JRC/GHSL/P2023A/GHS_BUILT_C |
| `c_gaia_imp_m2_YYYY` / `u_gaia_imp_m2_YYYY` | 固定的 2020 年中心建成区 / 单元内的不透水面面积（2000、2010、2018 年） | Tsinghua/FROM-GLC/GAIA/v10 |
| `u_smod_ucl_m2_2020` / `u_smod_uc_m2_2020` / `c_smod_ucl_m2_2020` | 城镇簇（代码 22、23、30）/ 城市中心（代码 30）面积 | JRC/GHSL/P2023A/GHS_SMOD_V2-0 |
| `c_clcdYYYY_<类>_m2` / `c_green_new_clcd_m2_2020` | CLCD 各地类面积 / 基准年后新增的森林、灌木与草地面积（可选） | CLCD 30 m 年度地类（gee.clcd_asset_template） |
| `c_ndvi_s2_YYYY` | 生长季 NDVI 均值，剔除水面 | COPERNICUS/S2_SR_HARMONIZED |
| `c_dw_trees_YYYY` / `c_dw_grass_YYYY` | 树木 / 草地概率均值 | GOOGLE/DYNAMICWORLD/V1 |
| `r_ndvi_modis_YYYY` | 环带非建成栅格 NDVI 均值，剔除水面 | MODIS/061/MOD13Q1 |
| `*_elev` / `*_slope` | 高程、坡度均值；坡度在 30 m 原生网格上计算 | NASA/NASADEM_HGT/001 |
| `u_t2m_c_YYYY` / `u_prcp_mm_YYYY` | 年均气温（°C）/ 年降水（mm） | ECMWF/ERA5_LAND/MONTHLY_AGGR |
| `u_access_min` | 到最近城市的出行时间均值（分钟，2015） | projects/malariaatlasproject/assets/accessibility/accessibility_to_cities/2015_v1_0 |
| `c_park_m2_YYYY` / `c_pop_park500_YYYY` | 公园面积 / 公园 500 m 内人口（可选） | 用户上传的公园多边形 |
| `c_greenway_len_m` / `c_pop_greenway<距离>_2020` | 绿道长度（m）/ 绿道可达范围内人口（可选） | 用户上传的绿道线要素 |
| `c_n_poi_<类>` / `c_pop_poi_<类><距离>_2020` | 学校、医院、养老机构点位数 / 可达范围内人口（可选） | 用户上传的设施点位 |
