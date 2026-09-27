# 附录A 文献核验表（v1.0）

报告正文采用作者年份制引文。同姓不同人的第一作者（如 Wu、He、Li、Liu、Zhang、Chen）在正文中标注名字首字母，何深静 (Shenjing He) 写作 S. He，投稿时按目标期刊格式统一。

本表收录研究设计报告引用的全部期刊文献。每一条都按 DOI 在 Scite 中取回元数据（标题、作者、期刊、年、卷、期、页），与引用信息逐项比对；核心发现只依据 Scite 或 Consensus 实际返回的摘要、全文片段或引文片段撰写，证据原文摘录附在条目下。本环境的网络策略阻断了 doi.org 与出版社网站，无法用浏览器打开 DOI 页面，这是与研究者要求的核验方式不同之处；投稿前请在浏览器中逐条打开 DOI 复核。

核心发现的依据分四类，每条的依据类别列在条目下。全部 99 篇中，Scite 摘要 61 篇，Consensus 摘要 31 篇，仅引文片段（他文）6 篇，无摘要（仅本文全文摘录）1 篇。Scite 摘要指 Scite 返回了本文摘要；Consensus 摘要指 Scite 只有元数据，本文或同名工作论文的摘要来自 Consensus；仅引文片段指本文没有可用摘要，依据是他文引用本文的片段或他文摘要；无摘要指两处都没有摘要，也没有他文片段，依据是本文自己的全文摘录。后三类的核心发现可靠性依次降低，投稿前应优先取得全文复核。

每条的设计采用情况说明“本研究中的用途”一栏提出的做法是否进入研究设计报告，写法为已采用（所在节）、待 v1.x（版本与原因）或不采用（理由）。用途一栏保留文献代理当时的建议原文，与采用情况不一致时以采用情况为准。报告引用了证据摘录之外的细节时，条目下另列补充证据，为 Scite 返回的原文。

年份取期刊卷期的刊印年份；Scite 记录的在线优先年份与之不同时，在备注中说明。Crossref 元数据中部分中文作者的姓与名顺序颠倒，已按中文姓名习惯改正并在备注中标明，投稿前需在出版社页面确认。

## A.1 财政体制与县级转移支付

**[1]** Fan, S., Li, L., & Zhang, X. (2012). Challenges of creating cities in China: Lessons from a short-lived county-to-city upgrading policy. *Journal of Comparative Economics*, *40*(3), 476–491. https://doi.org/10.1016/j.jce.2011.12.007

- **依据类别** Consensus 摘要
- **核验途径** Scite search (metadata; no abstract in Scite); abstract via Consensus
- **核心发现** 基于覆盖全国县的面板，1980至1990年代公式化的撤县设市标准在实践中未被严格执行；1998年前升格为市的单元在经济增长和公共服务提供上并不优于仍为县的对照单元，该政策于1997年叫停。
- **证据摘录** we find that the formula was not strictly enforced in the practice. Moreover, jurisdictions that were upgraded to cities prior to 1998 do not perform better than their counterparts that remained county status in terms of both economic growth and providing public services.
- **本研究中的用途** 县级市与县可合并为县级单元但需设虚拟变量；为检验县城基建优势来自转移支付而非行政名义提供基准。
- **设计采用情况** 已采用，§2.1 与 §5，县与县级市同属一个财政层级，以行政类型与规模交叉分组区分。

**[2]** Guo, G. (2008). Vertical imbalance and local fiscal discipline in China. *Journal of East Asian Studies*, *8*(1), 61–88. https://doi.org/10.1017/s1598240800005099

- **依据类别** Scite 摘要
- **核验途径** Scite search/DOI: metadata + abstract
- **核心发现** 1994年分税制后的纵向失衡不利于地方财政自律；县级动态面板显示，一般性转移支付和调资补助每增加100万元，分别使县政府供养人员增加约15人和16人；上级补助未显著挤出地方税收努力。
- **证据摘录** A dynamic panel analysis of Chinese counties reveals that a million-yuan increase in general transfer payment and salary raise subsidies would add, respectively, fifteen and sixteen employees to the county government payroll, other things being equal.
- **本研究中的用途** 提示转移支付可能被人员经费（吃饭财政）吸收而非转化为可见基建；设计上按支出功能分类（一般公共服务 vs 城乡社区/交通运输/节能环保）与遥感基建指标对照，检验转移支付→基础设施传导链。
- **设计采用情况** 已采用，§4 的 R1 与 §9.3 以工资福利支出占比和一般公共服务支出占比检验（M15a、M15b）；县级决算在 v1.1 广东试点收集。

**[3]** Han, L., & Kung, J. K.-S. (2015). Fiscal incentives and policy choices of local governments: Evidence from China. *Journal of Development Economics*, *116*, 89–104. https://doi.org/10.1016/j.jdeveco.2015.04.003

- **依据类别** Scite 摘要
- **核验途径** Scite title lookup: metadata + abstract
- **核心发现** 利用政府间收入分享规则的外生变化（模拟工具变量），企业所得税留成率下降后，地方政府将努力从扶持工业转向城市化，即发展房地产和建筑业；新收入来源弥补了约一半的财权调整损失，并抑制了内资工业增长。
- **证据摘录** We find evidence that local governments shifted their efforts from fostering industrial growth to "urbanizing" China, i.e., to developing the real estate and construction sectors, when their retention rate of enterprise tax revenue was reduced.
- **本研究中的用途** 解释大城市市场化融资（土地出让、房地产）的制度起点；数据管线中必须把政府性基金收入（土地出让收入）与一般公共预算收入分开统计，否则会低估大城市自有财力、误判其市场依赖。
- **设计采用情况** 已采用，§2.3；土地出让与一般公共预算分开统计，作为并列资金来源进入模型（§6、§9.3 的 M16）。

**[4]** He, J. (2024). The price of losing autonomy: Assessing the economic impact of county-to-district mergers in China. *Urban Affairs Review*, *60*(6), 1839–1870. https://doi.org/10.1177/10780874241242696

- **依据类别** Scite 摘要
- **核验途径** Scite search: metadata + abstract
- **核心发现** 县改区后原县级单元经济表现总体不乐观：负面影响先体现在微观指标（尤其居民存款），随后体现在宏观长期轨迹；杭州比较案例将问题归因于行政自主权丧失，受省级保护、保留一定自主权的县改区负面影响较小。
- **证据摘录** my analysis reveals a generally less optimistic outlook for these county-turned districts following the mergers. The negative impacts are initially evident in microeconomic indicators, especially in resident deposits ... link the problem to the loss of administrative autonomy.
- **本研究中的用途** 支持县改区＝财政自主权与县级转移支付身份丧失的机制假设；比较县 vs 区时须把近年由县转区的单元单列，避免制度转换期混入市辖区组。
- **设计采用情况** 已采用，§5 记录撤县设区人口占比，作控制变量与剔除检验待 v1.1；准实验在 units_did 层单列原县。
- **备注** 作者为 Jianzi He，非何深静

**[5]** Henderson, J. V., Su, D., Zhang, Q., & Zheng, S. (2022). Political manipulation of urban land markets: Evidence from China. *Journal of Public Economics*, *214*, 104730. https://doi.org/10.1016/j.jpubeco.2022.104730

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata; no abstract in Scite); abstract via Consensus
- **核心发现** 基于地级市数据的结构一般均衡模型：地方官员操纵土地配置推高房价；反事实显示，均等化城市间资本价格、把官员考核改为居民福利导向并放松地方预算约束后，几乎所有城市房价下降，全国过度且常为形象工程的地方公共基础设施投资将减少49%。
- **证据摘录** Housing prices would decline in almost all cities; and the reforms would reduce the current excessive, often showcase investment in local public infrastructure by 49% nationally.
- **本研究中的用途** 提醒遥感测得的基建供给可能含形象工程 (showcase investment)；应将遥感绿地/道路供给与使用强度（夜光、人口格网、POI）结合区分有效供给与过度供给，并把房价/房价收入比纳入大城市压力指标。
- **设计采用情况** 已采用，§2.3；使用不足改用住房余量比检验（§8.4）；房价收入比需要房价数据，待 v2.0。

**[6]** Huang, B., & Chen, K. (2012). Are intergovernmental transfers in China equalizing? *China Economic Review*, *23*(3), 534–551. https://doi.org/10.1016/j.chieco.2012.01.001

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata); abstract via Consensus
- **核心发现** 1994年建立的转移支付体系含有均等化成分，主要源于税收返还比重的收缩机制，以及2002年后份额上升但仍偏小的规则化一般性转移支付；但规模最大的专项转移支付 (specific-purpose transfers) 呈反均等化，且非规则化、易受政治影响，导致总转移支付整体表现出显著的反均等化效应。
- **证据摘录** However, the equalization effects of the largest component of transfers, specific-purpose transfers, are anti-equalizing. They are typically not rule-based and thus subject to political influence. As a result, total transfers also exhibit significant anti-equalization effects.
- **本研究中的用途** 变量构造必须区分税收返还、一般性（均衡性）转移支付与专项转移支付；专项资金多以项目形式落地为公园、绿道、道路等可见设施，是遥感可检测的转移支付→基建主要通道。
- **设计采用情况** 已采用，§6 用 2009 年观测值拆分税收返还、一般性与专项转移支付，专项占比对应项目化供给；2017 至 2019 年的分项只在 v1.1 广东试点校验。

**[7]** Li, P., Lu, Y., & Wang, J. (2016). Does flattening government improve economic performance? Evidence from China. *Journal of Development Economics*, *123*, 18–37. https://doi.org/10.1016/j.jdeveco.2016.07.002

- **依据类别** Consensus 摘要
- **核验途径** Scite search (JDE metadata; no abstract in Scite); abstract via Consensus for the SSRN working-paper version (10.2139/ssrn.2638647, same authors and title)
- **核心发现** 利用1995至2012年政府层级重组面板，扁平化（省直管县）提高了县级收入和转移支付，但管理幅度扩大使上级难以协调和监督，导致县总支出和增长性支出下降、土地腐败增加，总体上对经济绩效有负面影响。
- **证据摘录** Delayering has led to increases in revenue and inter-governmental transfers for county governments, but the associated enlarged span of control makes it difficult for upper-level governments to coordinate and monitor local ones.
- **本研究中的用途** PMC批次是县级转移支付变化的外生来源，可作交错DID识别转移支付增加→县城基建；同时监督弱化可能带来违规建设用地扩张，可用遥感建设用地/不透水面检验。
- **设计采用情况** 已采用，§9.5 省直管县主设计（v1.1）；用地扩张以年度 GAIA 不透水面检验。
- **备注** Crossref 将第三作者记为 Jin, Wang，应为 Wang, J.；本文效应方向的表述依据同名 SSRN 工作论文摘要（10.2139/ssrn.2638647）

**[8]** Li, H., Wang, Q., Zhang, P., & Zheng, C. (2025). Interjurisdictional competition, land finance revenue, and redistributive expenditure of local governments in China. *Public Finance and Management*, *24*(1–2), 50–68. https://doi.org/10.1177/15239721251330379

- **依据类别** Scite 摘要
- **核验途径** Scite search: metadata + abstract + full-text excerpts
- **核心发现** 基于283个地级市与2862个县级单元的多层模型，辖区竞争使支出偏向发展性而非再分配性服务；以税收或转移支付衡量的财政能力与再分配支出无显著关系，而土地财政收入与再分配支出正相关；样本中县级单位平均转移支付约为本级税收的2.9倍，西部部分县尤高。
- **证据摘录** No significant relationship is observed between fiscal capacity—measured by tax revenues or intergovernmental transfers—and redistributive expenditures. ... the average intergovernmental transfers are about 2.9 times the total tax revenue of local governments.
- **补充证据**（Scite 全文摘录（描述统计与表注））Intergovernmental transfers are of vital importance for local governments, many of which rely heavily on this revenue source. This is the reason why the average intergovernmental transfers are about 2.9 times the total tax revenue of local governments. ... The average percentage of intergovernmental transfer to local tax revenue seems large since this percentage in some western counties is very high.
- **本研究中的用途** 为县拿转移支付提供量级参照（转移/税收≈2.9倍）；提示转移支付未必转化为社会基础设施 (social infrastructure)，需将教育、医疗、社保支出与遥感可见的硬基建分开检验。
- **设计采用情况** 已采用，§2.1 量级参照；教育与卫生形成的社会基础设施单独检验（§4 的 H7、§6）。
- **备注** Crossref 将第三作者记为 Ping, Zhang，应为 Zhang, P.

**[9]** Liu, Y., & Alm, J. (2016). “Province-managing-county” fiscal reform, land expansion, and urban growth in China. *Journal of Housing Economics*, *33*, 82–100. https://doi.org/10.1016/j.jhe.2016.05.002

- **依据类别** Scite 摘要
- **核验途径** Scite title lookup: metadata + abstract
- **核心发现** 基于1999至2011年263个城市的DID，PMC改革平均使城市GDP增长提高约1个百分点；该正效应源于改革后城市为寻求预算外收入而扩大土地出让，改革城市土地出让扩张速度比未改革城市高14%，且效应随时间增强。
- **证据摘录** Our results show that on average implementing the PMC fiscal reform moderately increases city GDP growth by around 1 percentage point. ... the reformed cities tend to expand land leasing at a speed that is 14 percent higher than the non-reformed cities.
- **本研究中的用途** 说明财政层级调整通过土地财政影响空间扩张；遥感建成区扩张（不透水面、土地覆盖）可作为PMC与土地财政的结果变量，与公园绿地供给形成对照。
- **设计采用情况** 已采用，§9.5，建成区扩张是省直管县准实验的结果变量之一（v1.1）。

**[10]** Liu, Y., Martínez-Vázquez, J., & Wu, A. M. (2017). Fiscal decentralization, equalization, and intra-provincial inequality in China. *International Tax and Public Finance*, *24*(2), 248–281. https://doi.org/10.1007/s10797-016-9416-1

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata; Scite abstract field was boilerplate); abstract via Consensus
- **核心发现** 基于1995至2009年全国县级面板，省以下财政分权扩大省内地区不平等，而省级政府的财政均等化努力能缓解这一负面效应；以支出侧衡量的分权效应更大。
- **证据摘录** we find that while fiscal decentralization at the sub-provincial level in China leads to larger intra-provincial inequality, fiscal equalization efforts performed by provincial governments tend to mitigate the detrimental effect of fiscal decentralization on intra-provincial inequality.
- **本研究中的用途** 支持以省内比较为主识别框架（省固定效应/省内排序）；以县级人均决算支出的省内离散度作为均等化结果变量，并与遥感人均绿地/道路的省内离散度对照。
- **设计采用情况** 已采用，§2.1 与 §9.3 的省份固定效应；以省内离散度为结果变量不采用，本研究关心人均供给水平而非均等化程度。
- **备注** Scite 记录年份为 2016（在线），卷 24 为 2017 年

**[11]** Liu, F., & Hu, Y. (2025). Can fiscal transfers achieve both equity and efficiency: Evidence from Chinese counties. *International Review of Economics & Finance*, *103*, 104586. https://doi.org/10.1016/j.iref.2025.104586

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata); abstract via Consensus
- **核心发现** 基于2016至2021年县级财政数据，转移支付分配更均等的省份县域增长更好，但省级层面存在不显著的效率损失；原因是均等化转移支付产生逆向激励，即促进小县增长、抑制大县增长，机制包括增长潜力不足、支出偏好扭曲和对转移支付的过度依赖。
- **证据摘录** the reverse incentives created by the equalization of fiscal transfers, which encourage growth in smaller counties but hinder growth in larger ones. The main mechanisms ... include insufficient growth potential, distorted fiscal spending preferences, and an over-reliance on transfer payments.
- **本研究中的用途** 提供2016年后县级转移支付的最新证据；以县人口规模为异质性维度，叠加普查人口变化，检验人口流失的小县是否凭转移支付获得更高人均基建。
- **设计采用情况** 已采用，§2.1；03 为全部单元输出规模分级与交叉分组（§5），按交叉分组的比较表待 v1.1。

**[12]** Ma, G., & Mao, J. (2018). Fiscal decentralisation and local economic growth: Evidence from a fiscal reform in China. *Fiscal Studies*, *39*(1), 159–187. https://doi.org/10.1111/j.1475-5890.2017.12148

- **依据类别** Consensus 摘要
- **核验途径** Scite search (metadata; Scite abstract empty); abstract via Consensus
- **核心发现** 基于2001至2011年县级面板，PMC改革显著提高县GDP增长率，在初始制度质量较好的地区更明显；渠道是县政府降低企业税负并增加基础设施建设支出。
- **证据摘录** we find that the reform has led to a significant increase in GDP growth rate. ... the PMC reform induced county governments to exert lower tax burdens on firms and increase spending on infrastructure construction.
- **本研究中的用途** 提供县级财政自主权→基础设施支出的直接证据，可作为遥感基建指标的外部效度参照；与Li, Lu & Wang (2016) 的负面结论构成需在报告中讨论的争议。
- **设计采用情况** 已采用，§2.1 与 §9.5 第一阶段的参照。

**[13]** Sieg, H., Yoon, C., & Zhang, J. (2023). The impact of local fiscal and migration policies on human capital accumulation and inequality in China. *International Economic Review*, *64*(1), 57–93. https://doi.org/10.1111/iere.12597

- **依据类别** Scite 摘要
- **核验途径** Scite author/term search: metadata + abstract
- **核心发现** 空间世代交叠模型估计显示，改革内部迁移政策（让流动人口获得户籍及同等公共服务）显著提高农村出生流动儿童的大学入学率、增加高技能劳动者，但需要显著加税以弥补流动人口原本提供的正向财政外部性 (positive fiscal externalities) 的减少。
- **证据摘录** We find that this policy change significantly increases the college attainment of migrant children born in rural areas and, therefore, promises to increase the number of high‐skill workers. However, it requires significant tax increases to offset the reduction of the positive fiscal externalities provided by migrants.
- **本研究中的用途** 为大城市公共品被流入人口稀释、户籍人口享受溢价提供结构模型证据；以普查常住人口与户籍人口分别作分母计算人均支出/基建，两者之差度量非户籍人口面临的服务缺口。
- **设计采用情况** 已采用，§2.3、§4 的 H5 与 H7；常住与户籍两种分母见 §7。
- **备注** Scite 记录年份为 2022（在线）

**[14]** Tang, W., & Hewings, G. J. D. (2017). Do city–county mergers in China promote local economic development? *Economics of Transition*, *25*(3), 439–469. https://doi.org/10.1111/ecot.12118

- **依据类别** Scite 摘要
- **核验途径** Scite search: metadata + abstract
- **核心发现** 利用城市、县和企业多层数据评估2000至2004年撤县设区 (che xian she qu)，合并显著促进地方经济发展，效应大小取决于与集聚力相关的地方禀赋；合并后交通基础设施改善和城市集聚经济是可能渠道。
- **证据摘录** we present evidence that the merger significantly increases local economic development, and the magnitude of the effect depends on local endowments related to agglomeration forces. ... improved transport infrastructure and urban agglomeration economies after merger are potential contributors
- **本研究中的用途** 撤县设区使原县财政身份由县变为区，需建立2000至2020年行政区划代码对照表 (crosswalk)；可用事件研究检验转换前后遥感交通与绿色基础设施的变化。
- **设计采用情况** 已采用，§5 代码对照表统一到 2020 年边界；§9.5 撤县设区改为行政身份的简化式效应（v2.0）。
- **备注** Crossref 记为 Wei, Tang，应为 Tang, W.

**[15]** Wang, J., & Yeh, A. G. O. (2020). Administrative restructuring and urban development in China: Effects of urban administrative level upgrading. *Urban Studies*, *57*(6), 1201–1223. https://doi.org/10.1177/0042098019830898

- **依据类别** Consensus 摘要
- **核验途径** Scite search (metadata); abstract via Consensus
- **核心发现** PSM-DID显示，县升格为地级市在数年内显著提高城市人口增长和财政收入（但不必然加速工业化）；县升格为县级市则无此效应，因县与县级市处于同一行政级别。
- **证据摘录** county- to prefecture-level city upgrading can positively lead to a significant increase in urban population growth and fiscal revenue in a few years after upgrading, although this may not necessarily lead to rapid industrialisation. However, the same is not true for county to county-level city upgrading.
- **本研究中的用途** 支持按行政级别（而非名称）划分样本：县与县级市视为同一财政层级，地级及以上城市的市辖区为另一层级。
- **设计采用情况** 已采用，§2.1 与 §5，按财政层级划分单元。
- **备注** Scite 记录年份为 2019（在线）

**[16]** Wong, C. (2009). Rebuilding government for the 21st century: Can China incrementally reform the public sector? *The China Quarterly*, *200*, 929–952. https://doi.org/10.1017/s0305741009990567

- **依据类别** Scite 摘要
- **核验途径** Scite title lookup: metadata + abstract
- **核心发现** 1980至1990年代被动、渐进的政府收缩叠加财政投入不足，打破了政府间财政体系，并扭曲了政府机构与事业单位 (shiye danwei) 的激励结构；不修复政府间财政体系，建设服务型政府的自上而下计划效果有限。
- **证据摘录** This article argues that the reactive, incremental retrenchment of government in the 1980s and 1990s, combined with inadequate finance, had broken the intergovernmental fiscal system and created large distortions in the incentive structure facing government agencies and public institutions
- **本研究中的用途** 作为制度背景：说明县级事权下沉与财权上收(unfunded mandates) 的结构性根源，支撑把县级支出−自有收入缺口视为制度性而非周期性现象。
- **设计采用情况** 已采用，§2.1 制度背景；净流入按制度性缺口处理（§6）。

**[17]** Yu, Y., Wang, J., & Tian, X. (2016). Identifying the flypaper effect in the presence of spatial dependence: Evidence from education in China's counties. *Growth and Change*, *47*(1), 93–110. https://doi.org/10.1111/grow.12113

- **依据类别** Scite 摘要
- **核验途径** Scite search: metadata + abstract
- **核心发现** 以2007年县级教育支出数据和空间计量模型检验，在考虑空间相互依赖、不同空间权重及教育补助内生性后，没有粘蝇纸效应的证据，反而发现反粘蝇纸效应(anti-flypaper effect)。
- **证据摘录** We find that, in the presence of spatial interdependence, there is no evidence of a "flypaper effect" when different spatial weighting schemes and the endogeneity problem of education grants are accounted for. Rather, the "anti-flypaper effect" is found.
- **本研究中的用途** 提醒转移支付对特定公共品的边际效应可能小于1甚至被替代；检验转移支付→公园/绿道时需加入空间滞后项控制邻县溢出，并处理转移支付内生性（公式化均衡性转移支付或政策冲击作工具变量）。
- **设计采用情况** 已采用，§2.1；空间滞后项不采用，空间相关在 v1.1 以 Conley 标准误处理，内生性交给 §9.5 的准实验。
- **备注** Scite 记录年份为 2015（在线），卷 47 为 2016 年

**[18]** Zhang, P., & Ren, Q. (2016). Sub-provincial fiscal conditions in China: Local fiscal autonomy and inter-jurisdictional disparities. *Public Finance and Management*, *16*(3), 228–256. https://doi.org/10.1177/152397211601600302

- **依据类别** Scite 摘要
- **核验途径** Scite search: metadata + abstract
- **核心发现** 省内视角下区县（尤其是县）的财政能力与自主性仍远不足；大部分转移支付流向县，县在转移前的自有收入差距大于市辖区，但转移后的公共支出差距反而更小；在中西部，转移支付大幅消除区与县差距，使人均支出几乎持平。
- **证据摘录** Since most inter-governmental grants go to counties, even though inter-jurisdictional disparities within provinces in own revenue before the transfers were higher for counties than for districts, after the transfers, the disparities in public expenditures were lower
- **补充证据**（Scite 摘要）The large amount of intergovernmental grants dramatically eliminates the big district-county disparities that previously existed in the interior and western regions, bringing the average public expenditures for the localities to almost the same level.
- **本研究中的用途** 直接支撑县 vs 市辖区二元财政体制的分组；计算转移前（一般公共预算收入）与转移后（决算支出）的人均值与不平等指数，并叠加普查常住人口，检验人口流出是否放大县的人均支出优势。
- **设计采用情况** 已采用，§2.1 与 §5 的县与市辖区分层；常住与户籍两种口径的人均支出见 §7。

## A.2 人口收缩、县城城镇化与过度建设

**[19]** Austin, B., Glaeser, E., & Summers, L. H. (2018). Jobs for the heartland: Place-based policies in 21st-century America. *Brookings Papers on Economic Activity*, *2018*(1), 151–255. https://doi.org/10.1353/eca.2018.0002

- **依据类别** Scite 摘要
- **核验途径** Scite DOI metadata lookup; abstract returned by Scite
- **核心发现** 美国区域收敛明显放缓，壮年男性非就业率近50年上升到约三倍。在历史上非就业率高的地区，劳动需求增加对就业的拉动更大，因此在这些就业弹性较高的地区定向补贴就业（如扩大EITC），可能降低非就业并改善经济表现。作者据此促使经济学家重新审视对地方导向政策的传统怀疑。
- **证据摘录** We document that increases in labor demand appear to have greater effects on employment in areas where not working has been historically high, suggesting that subsidizing employment in such places could reduce the rate of not working.
- **本研究中的用途** 为转移支付提供有条件支持的理论。本项目可以把转移支付分成建设型（基建、公园绿道）和民生/就业型（社保、教育），检验在收缩县里后者是否比前者更有福利上的合理性。
- **设计采用情况** 已采用，§2.2；建设型与民生型支出的比较需要功能分类决算，待 v1.1 广东试点。

**[20]** Chan, K. W. (2012). Crossing the 50 percent population Rubicon: Can China urbanize to prosperity? *Eurasian Geography and Economics*, *53*(1), 63–86. https://doi.org/10.2747/1539-7216.53.1.63

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI metadata lookup (no abstract in Scite); abstract text from Consensus search
- **核心发现** 作者用西方学者少用的户籍人口序列，分析全国与地方城镇人口。近年城镇人口（包括非农业人口）的增长，很大程度上不是农民工真正融入城市，部分只是城郊被征地农民户籍身份的名义性重分类。作者认为，只有户籍制度彻底改革或取消，城镇化带动消费的设想才现实。
- **证据摘录** Instead the trend represents partly a nominal (not substantive) redesignation of the hukou status of residents of exurban areas where some peasants' land is being expropriated for new development.
- **本研究中的用途** 提醒本项目分清常住城镇人口与户籍城镇人口。大城市市辖区常住人口多于户籍人口（人口流入，而公共服务按户籍配置，形成压力）；县城常住少于户籍（外出人口仍计入户籍）。人均财政指标应报告两种分母，并用常住/户籍比值代理公共服务压力。
- **设计采用情况** 已采用，§7 的三种分母与常住户籍之比。

**[21]** Chen, L., Li, M., & Huang, Y. (2025). From industry to education-driven urbanization: A welfare transformation of urbanization in Chinese counties. *Habitat International*, *155*, 103248. https://doi.org/10.1016/j.habitatint.2024.103248

- **依据类别** Consensus 摘要
- **核验途径** Scite title/DOI metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 县域城镇化的动力正从产业驱动转向教育驱动。农村家庭把优质教育和学区视为理性的代际投资；政府改善教育服务、放宽户籍限制，推动了向县城的教育型迁移。县城吸纳人口要靠公共服务和就业两者并重。
- **证据摘录** rural families increasingly view access to quality education and desirable school districts as rational, intergenerational investments. Government efforts to improve educational services and relax household registration restrictions have facilitated this transition
- **本研究中的用途** 说明县城可能通过教育这类社会基础设施（social infrastructure）把县域内人口吸向县城。本项目应把学校（POI/教育统计）纳入公共品清单，并检验转移支付→县城教育供给→县城人口份额（县城常住/县域常住）这条链条。
- **设计采用情况** 已采用，§4 的 H7 与 §6 的学位指标；县城人口份额见 core_share_2020（§7 表 1 的人口行）。

**[22]** Glaeser, E. L., & Gottlieb, J. D. (2008). The economics of place-making policies. *Brookings Papers on Economic Activity*, *2008*(1), 155–253. https://doi.org/10.1353/eca.0.0005

- **依据类别** 无摘要（仅本文全文摘录）
- **核验途径** Scite DOI metadata lookup; fulltextExcerpts returned by Scite (NBER w14373 version)
- **核心发现** 作者从空间均衡（spatial equilibrium）出发论证：补贴贫困地区会被更高的价格抵消，主要的实际效果是把人引向或留在低生产率地区。支持地方导向政策的理由应主要基于效率（把外部性内部化），而不是公平。实证上，衰退地区集聚经济更强这一说法缺乏支持。
- **证据摘录** Subsidies to poor places will be offset by higher prices, and the primary real effect will be to move people into economically unproductive areas. ... the case for national policy that favors specific places must depend more on efficiency-internalizing externalities-than on equity
- **本研究中的用途** 为大城市靠市场、县城靠转移支付命题提供反方论证。本项目应检验：县城人均公共品高，是否同时伴随人口持续流出（即补贴没能留住人）；大城市人均公共品被稀释，是否是获得集聚收益的代价。
- **设计采用情况** 已采用，§2.2；§4 的 H3 检验人均供给偏高是否与人口流失并存。

**[23]** Han, L., & Lu, M. (2017). Housing prices and investment: An assessment of China's inland-favoring land supply policies. *Journal of the Asia Pacific Economy*, *22*(1), 106–121. https://doi.org/10.1080/13547860.2016.1261452

- **依据类别** Consensus 摘要
- **核验途径** Scite record found via author search 'Ming Lu' (Scite author order: Ming Lü, Libin Han; Scite date 2016-12-06, print vol. 22 no. 1 = 2017; Consensus lists byline Han et al., 2017); abstract text from Consensus search
- **核心发现** 2003年起，中央把更多建设用地指标（construction land-use quotas）配给内陆省份，以缩小沿海与内陆的差距。用2001至2007年企业数据，作者发现2003年后指标减少的城市房价涨得比指标增加的城市快。房价上涨一方面通过抵押品效应增加企业投资，另一方面挤出固定资本投资，净效应为负，限制了经济增长。
- **证据摘录** Since 2003, China's central government has allocated more construction land-use quotas to inland provinces than elsewhere ... cities in which land-use quotas decreased experienced faster housing price growth than the cities in which land-use quotas increased after 2003
- **本研究中的用途** 为内陆县城过建、东部大城市住房压力提供制度机制。本项目以2003年的指标倾斜为外生冲击，检验内陆县城建成区扩张与东部大城市房价、人均住房面积（七普住房表）的分化。陆铭团队的 Liang, Lu & Zhang (2016, JHE) 可作补充。
- **设计采用情况** 已采用，§2.2 制度背景；以 2003 年用地指标倾斜为外生冲击不采用，与本研究 2010 至 2020 年的窗口不重合。
- **备注** Scite 记录年份为 2016（在线）；第二作者即陆铭 (Ming Lu)

**[24]** He, S. Y., Lee, J., Zhou, T., & Wu, D. (2017). Shrinking cities and resource-based economy: The economic restructuring in China's mining cities. *Cities*, *60*, 75–83. https://doi.org/10.1016/j.cities.2016.07.009

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI metadata lookup (no abstract in Scite); abstract text from Consensus search
- **核心发现** 文章以大庆（石油）和萍乡（煤炭）为案例，梳理中央、省、市三级针对资源型城市收缩的规划政策和经济重构实践。单一产业结构和繁荣-萧条周期是这类城市面临收缩的主因，政府用积极政策试图扭转预期中的衰退。注：作者是 Sylvia Y. He（香港中文大学），不是何深静 (Shenjing He)。
- **证据摘录** To reverse the expected decline of these cities in the future, the Chinese Government has implemented active policies at national, provincial and municipal levels. ... two case studies, a petroleum mining city (Daqing City) and a coal mining city (Pingxiang City)
- **本研究中的用途** 作为资源枯竭型收缩地区的对照组。本项目在回归中加入资源型城市虚拟变量（参照国务院资源型城市名录），把资源枯竭驱动的收缩与普通县城人口外流分开，避免把东北资源型城市的高人均基建误读为转移支付的普遍效应。
- **设计采用情况** 待 v1.2，§9.6 资源型城市异质性，全国数据到位后分析。
- **备注** 作者为 Sylvia Y. He（香港中文大学），非何深静

**[25]** Hollander, J. B., & Németh, J. (2011). The bounds of smart decline: A foundational theory for planning shrinking cities. *Housing Policy Debate*, *21*(3), 349–367. https://doi.org/10.1080/10511482.2011.585164

- **依据类别** Consensus 摘要
- **核验途径** Scite title/author search metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 针对美国城市的人口收缩，作者提出精明收缩（smart decline）的基础理论。理论以规划和政治理论中的伦理、公平与社会正义讨论为起点，并以成功的精明收缩实践为依据。Consensus 返回的作者后续文章摘要显示，原文提出了包容、协商、承认、透明、尺度适宜五项正义命题。
- **证据摘录** This paper advances a foundational theory of smart decline that takes as its starting point discussions of ethics, equity, and social justice in the planning and political theory literature, but is well grounded in observations of successful smart decline practice.
- **本研究中的用途** 为收缩县城的规划回应提供规范框架。对识别出的人均公共品过剩＋人口流失县，评估公园绿道等存量的再利用（生态修复、社区化运营）和公共服务整合是否满足五项正义命题，与研究者关注的社会基础设施和城市更新衔接。
- **设计采用情况** 已采用，§2.2 文献定位；按五项正义命题评估存量再利用不采用，超出本研究的量化设计。

**[26]** Jin, X., Long, Y., Sun, W., Lu, Y., Yang, X., & Tang, J. (2017). Evaluating cities' vitality and identifying ghost cities in China with emerging geographical data. *Cities*, *63*, 98–109. https://doi.org/10.1016/j.cities.2017.01.002

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI metadata lookup (no abstract in Scite); abstract text from Consensus search
- **核心发现** 作者用城市活力（urban vitality）理论界定鬼城。数据是2002至2013年的535523个住宅项目，结合路网交叉口、POI和位置服务（LBS）数据，测度形态、功能、社会三类活力。新城区住宅项目的平均活力只有老城区的8.8%。文章识别出30个鬼城，并用夜光影像等做了交叉验证。
- **证据摘录** we are able to profile ghost cities of China based on 535,523 recent project-level residential developments from 2002 to 2013. ... We find the average vitality of residential projects in new urban areas is only 8.8% of that in old urban areas
- **本研究中的用途** 提供新旧城区活力比指标。本项目以2000年建成区为老城，2000年后新增的不透水面/建成区（分期不透水面产品）为新城，在县城和大城市之间比较新区与老区的夜光/POI活力比，用来识别过度建设（overbuilding）。
- **设计采用情况** 不采用，新旧城区活力比依赖位置服务数据；使用不足改以住房余量比刻画（§8.4）。

**[27]** Jin, X., Sun, B., & Du, H. (2026). County-level assessment of coordinated relationship between land and population in urban China. *Ecological Indicators*, *186*, 114907. https://doi.org/10.1016/j.ecolind.2026.114907

- **依据类别** Consensus 摘要
- **核验途径** Scite title/DOI metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 作者整合卫星与统计数据，评估2000至2021年全国县级城市建设用地（UCL）与城镇人口（UP）的耦合协调度（CCD）。两者都在扩张，但UP一直滞后于UCL。县级协调度低于省级；即使在整体协调度高的省份内部，县际差异也很大。空间计量显示，GDP和政府收入通过直接效应和正向空间溢出提高协调度，产业结构和公共服务则呈负溢出。
- **证据摘录** although both UCL and UP continued to expand, UP growth has consistently lagged behind UCL expansion. ... GDP and government revenue significantly enhance CCD through both direct effects and positive spatial spillovers
- **本研究中的用途** 与本项目财政×人口×遥感县级叠加设计最接近的近期研究，可借鉴其CCD指标和空间计量设定。不同之处在于，本项目要把政府收入拆成本级税收、转移支付和土地出让收入，检验不同财源对县城地快人慢的作用是否不同。
- **设计采用情况** 已采用，§2.2；政府收入拆为本级收入、净流入、土地出让与债务（§6）；耦合协调度指标不采用，改用分子分母分解（§9.2）。

**[28]** Kajita, S. (2001). Public investment as a social policy in remote rural areas in Japan. *Geographical Review of Japan, Series B*, *74*(2), 147–158. https://doi.org/10.4157/grj1984b.74.147

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据、摘要与全文摘录（开放获取，2026-09-26 核验）
- **核心发现** 日本地方交付税按各市町村服务成本与收入能力的差异计算，分配向过疏 (kaso) 市町村倾斜。过疏市町村的人均地方税低于全体市町村平均，计入地方交付税与国家、都道府县专项拨付后差距反转；过疏市町村人均总支出为全体市町村平均的 1.88 倍，人均公共工程资本支出为 2.33 倍，公共投资是两类转移资金最偏重的领域。以岛根县为例，公共投资曾作为偏远农村的社会政策吸纳本地劳动力，随劳动力代际更替，这一作用正在终结。
- **证据摘录** Because the amount of local allocation tax for each municipality is calculated by taking into account differences in service costs and revenue potential, its allocation favors kaso munici[palities] ... In both local allocation tax and national and prefectural government special purpose disbursements, public investment is the most favored sector for kaso municipalities. ... while total expenditure per capita in kaso municipalities is 1.88 times higher than the total municipal per capita average, capital expenditure per capita in the public works sector is actually 2.33 times higher in kaso muni
- **本研究中的用途** §2.2 日本比较的第一步：转移资金向人口过疏地区倾斜，并主要形成公共投资，与县城命题平行。数据年份未出现在 Scite 返回的摘录中，正文不写具体年份。
- **设计采用情况** 已采用，§2.2 日本比较。

**[29]** Kline, P., & Moretti, E. (2014). People, places, and public policy: Some simple welfare economics of local economic development programs. *Annual Review of Economics*, *6*(1), 629–662. https://doi.org/10.1146/annurev-economics-080213-041024

- **依据类别** Scite 摘要
- **核验途径** Scite DOI metadata lookup; abstract returned by Scite
- **核心发现** 作者构建简单的空间均衡模型，评估地方导向政策（place-based policies）对地方和全国经济的福利效应。文章讨论谁从中受益、全国层面收益是否大于成本、哪类干预最有效，并据此批判性地评估这类政策的经济学理由和最新证据。
- **证据摘录** A growing class of "place based" policies attempt to address these differences through public investments and subsidies that target disadvantaged neighborhoods, cities or regions. ... Who benefits from place based interventions? Do the national benefits outweigh the costs?
- **本研究中的用途** 作为转移支付的理论框架。县城拿到的转移支付本质上是 place-based 政策。本项目要分清它的效应落在地方（基建、地价）还是人（留守居民福利），并检验收益是否被土地和住房价格资本化（capitalization）。
- **设计采用情况** 已采用，§2.2；资本化检验见 §4 的 H6（v1.1 广东可行性，v2.0 全国）。

**[30]** Li, H., & Mykhnenko, V. (2018). Urban shrinkage with Chinese characteristics. *The Geographical Journal*, *184*(4), 398–412. https://doi.org/10.1111/geoj.12266

- **依据类别** Scite 摘要
- **核验途径** Scite DOI metadata lookup (dois, no term); abstract and Smart Citation snippets returned by Scite
- **核心发现** 作者用城市地区（urban area, UA）重新界定中国的城市。收缩城市从1990年代的164个增至2000年代的281个（增加71%），2010年收缩城市净流失人口730万。文章归纳了四类成因：国家主导的再工业化与经济重构（63%）、集聚向心力导致的边缘化（34%）、国家推动的人口结构变化（26%）、国家主导的巨型收缩（mega-shrinkage，近20%）。文中还指出，用户籍数据统计城市人口，会算进已经离开的人，漏掉没有本地户口的常住者。
- **证据摘录** with the absolute number of shrinking cities rising by 71% from 164 in the 1990s to 281 in the 2000s ... (4) state‐sponsored mega‐shrinkage, responsible for urban population loss in almost 20% of all the cases
- **本研究中的用途** 提供中国式收缩的类型学。本项目可以把县和县级市的收缩分成集聚边缘化型与政策/行政驱动型，再比较两类的转移支付依赖度。文中对户籍口径偏误的讨论，也支持本项目以常住人口作为主分母。
- **设计采用情况** 已采用，§2.2 与 §7，以常住人口为主分母；收缩类型学不采用，本研究按连续变量分群（§4 的 H1）。
- **备注** Crossref 记为 He, Li；学界通常引作 Li & Mykhnenko，投稿前在出版社页面核对

**[31]** Long, Y., & Wu, K. (2016). Shrinking cities in a rapidly urbanizing China. *Environment and Planning A: Economy and Space*, *48*(2), 220–222. https://doi.org/10.1177/0308518x15621631

- **依据类别** Scite 摘要
- **核验途径** Scite DOI metadata lookup (dois, no term); abstract text returned by Scite
- **核心发现** 作者用2000、2010年普查的常住人口（residents，非户籍 hukou）估算全国乡镇街道人口。39007个乡镇街道中有19882个人口减少，面积约占国土三分之一。文章识别出180个收缩城市（1个省会乌鲁木齐、40个地级市、139个县级市），说明快速城镇化与城市收缩（urban shrinkage）同时存在。文中还指出，撤镇设街道这类行政升级会让一个地方一夜变成城市。
- **证据摘录** we estimated their population (residents not Hukou) based on the Population Censuses of China in 2000 and 2010, respectively. We found that 19 882 among all 39 007 townships were losing their population during 2000-10
- **本研究中的用途** 作为乡镇街道级普查人口变化的方法基线。本项目用2000/2010/2020三期普查常住人口，在乡镇街道尺度计算人口变化，再聚合到县城建成区（城关镇/街道）和县域其余部分。撤县设区、撤镇设街道会制造名义城镇化，所以面板要统一到2020年行政边界。
- **设计采用情况** 已采用，§2.2；乡镇街道尺度的人口变化只用于 §9.7 的街道检验（v1.2），全国县城人口用官方中心人口与 GHS-POP 重标定值。

**[32]** Meng, X., & Long, Y. (2022). Shrinking cities in China: Evidence from the latest two population censuses 2010–2020. *Environment and Planning A: Economy and Space*, *54*(3), 449–453. https://doi.org/10.1177/0308518x221076499

- **依据类别** Scite 摘要
- **核验途径** Scite search result metadata and abstract (term search, DOI record)
- **核心发现** 作者用六普、七普识别2010至2020年的人口流失。1507个区县在收缩，占2896个区县的52%，面积440万km²，约占国土46%。收缩城市有266个，比2000至2010年多86个，空间上集中在东北和中部。作者呼吁调整增长导向的规划范式。
- **证据摘录** we identified 1507 shrinking districts and counties (52% of all 2896 districts and counties in China), with a total area of 4.4 million km2, covering almost 46% of China's territory. ... Chinese shrinking cities are clustered, mainly in the northeast and central regions.
- **本研究中的用途** 作为2010至2020年区县收缩的外部校验基线。本项目用同一普查口径复算区县人口变化，核对1507个收缩区县这一数量级，再叠加财政决算（人均一般公共预算支出、转移支付依赖度）和遥感建成区/绿地变化。
- **设计采用情况** 已采用，§2.2，作为区县收缩数量的外部校验。

**[33]** Moss, T. (2008). ‘Cold spots’ of urban infrastructure: ‘Shrinking’ processes in Eastern Germany and the modern infrastructural ideal. *International Journal of Urban and Regional Research*, *32*(2), 436–451. https://doi.org/10.1111/j.1468-2427.2008.00790.x

- **依据类别** Scite 摘要
- **核验途径** Scite DOI metadata lookup; abstract returned by Scite
- **核心发现** 以原东德的供排水系统为例：人口收缩使用水量骤降，而统一后基础设施又在扩张，结果形成慢性产能过剩（overcapacity）。过剩带来技术和经济问题，加剧服务质量与价格的空间不平等，也挑战了供给导向、普遍均等的现代基础设施理想（modern infrastructural ideal）。
- **证据摘录** the serious technical and economic problems posed by overcapacity are intensifying spatial disparities in service quality and price, and -more fundamentally -are challenging the supply-driven 'modern infrastructural ideal' of universal and equitable water services
- **本研究中的用途** 为县城基建更好这一判断的另一面即维护负担提供理论依据。本项目除了算人均基础设施存量，还要估算存量道路、管网、公园绿道的年维护成本占一般公共预算支出的比重，检验高转移依赖县是否在用转移支付维持过剩基础设施的运维。
- **设计采用情况** 已采用，§2.2 与 §3 的维护负担机制；维护成本以住建部维护建设资金收支近似（§6）。

**[34]** Musha, T. (2021). How can cities be compacted? Logic and reality of the location normalization plan. *E-journal GEO*, *16*(1), 57–69. https://doi.org/10.4157/ejgeo.16.57

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据与英文摘要（正文为日文，2026-09-26 核验）
- **核心发现** 立地适正化计划是把城市功能引导到紧凑城市中心的制度框架。大都市区中福利、医疗等功能被引导迁入中心，中心区居住环境的改善成为重要议题；地方城市的公共设施则在中心区内被引导和重组。作者认为紧凑化还取决于中心区居住人口的增加。
- **证据摘录** The Location Normalization Plan was institutionalized as a framework to guide urban functions to the center of compact cities. In metropolitan areas where the plan has been implemented, ... urban functions such as welfare and medical care are being guided to relocate to city centers. On the other hand, public facilities are being guided and restructured in the centers of local cities.
- **本研究中的用途** §2.2 日本比较的第三步：政策从扩大供给转向集中，与 2022 年县城城镇化意见对人口流失县城的集中要求对照。
- **设计采用情况** 已采用，§2.2 日本比较。
- **备注** 正文为日文，英文题名与摘要取自 Scite；投稿时按目标期刊要求决定是否附日文原题

**[35]** Nishino, T. (2015). Discussion of structure and content of early adopting municipalities' public facility reorganization plans. *Journal of Architecture and Planning (Transactions of AIJ)*, *80*(714), 1775–1785. https://doi.org/10.3130/aija.80.1775

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据、英文摘要与英文摘要页的全文摘录（正文为日文，2026-09-26 核验）
- **核心发现** 日本市町村所有的公共设施的重组（包括大幅削减）已成为主要议题。截至 2013 年 9 月，全国 1 744 个市町村中只有 4.0% 完成了公共设施重组计划；2014 年 4 月总务省要求各市町村编制公共设施等综合管理计划，并设定削减目标。
- **证据摘录** The reorganization, including substantial reduction, of public facilities owned by Japan's municipalities is becoming a major issue. ... of the 1,744 municipalities nationwide, only 4.0 percent have completed formulation of a public facility reorganization plan. ... In April 2014, the Ministry of Internal Affairs and Communications (MIC) requested municipalities to formulate a "Comprehensive Management of Public Facilities and Infrastructure Plan." ... Because MIC's request asked for a reduction target amount to be set
- **本研究中的用途** §2.2 日本比较的第二步：人口减少后设施存量需要削减，对应本研究的维护负担机制与住房余量比。
- **设计采用情况** 已采用，§2.2 日本比较。
- **备注** 正文为日文，英文题名与摘要取自 Scite；投稿时按目标期刊要求决定是否附日文原题

**[36]** Yang, Z., & Dunford, M. (2018). City shrinkage in China: Scalar processes of urban and hukou population losses. *Regional Studies*, *52*(8), 1111–1121. https://doi.org/10.1080/00343404.2017.1335865

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI metadata lookup (no abstract in Scite; Scite year = online-first 2017, print vol. 52 no. 8); abstract text from Consensus search
- **核心发现** 基于2000、2010年普查，336个地级单元中有88个出现总人口、城镇人口和户籍人口不同组合的流失。广义有序logit模型显示，在中国的人口控制语境下，制造业衰退、服务业增长和人口活力相互作用。收缩可以在城乡转型完成前发生，作者因此呼吁修正增长导向的城市政策。
- **证据摘录** Analysis of the latest census data for 2000 and 2010 shows that 88 out of 336 Chinese municipalities suffered combinations of total, urban and hukou population loss. ... These findings call for a modification of China's growth-oriented urban policy.
- **本研究中的用途** 直接支撑本项目的分母设计。同时构造常住总人口、城镇常住人口、户籍人口三种口径的收缩指标和人均财政支出，比较县城与市辖区在三种口径下的排序差异（denominator sensitivity）。
- **设计采用情况** 已采用，§7 的三种分母。
- **备注** Scite 记录年份为 2017（在线）

**[37]** Zhang, Q., Wallace, J., Deng, X., & Seto, K. C. (2014). Central versus local states: Which matters more in affecting China's urban growth? *Land Use Policy*, *38*, 487–496. https://doi.org/10.1016/j.landusepol.2013.12.015

- **依据类别** Consensus 摘要
- **核验途径** Scite title metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 作者用多层模型分析城市热点县（urban hotspot counties）在1995至2000、2000至2005、2005至2008三个时期的城市增长。控制其他因素后，越依赖中央财政转移支付的县，把耕地转为城市用地越少。地方政府在经济、财政和政治激励下，对城市土地开发的影响力在增强。
- **证据摘录** Our results show that counties that are more dependent on fiscal transfers from the central government convert less cultivated land to urban use, controlling for other factors.
- **本研究中的用途** 与本项目命题形成张力的关键证据。如果高转移依赖县的城市用地扩张反而更少，县城靠转移支付搞建设就要区分转移支付的类型和时期（2008年后城投与专项债扩张）。本项目应在2010至2020年面板中重新检验转移依赖度与建成区扩张之间的符号。
- **设计采用情况** 已采用，§4 的 R1，与 H2 在同一模型中检验（§9.3）。

**[38]** Zhang, H., Chen, M., & Chen, L. (2022). Urbanization of county in China: Spatial patterns and influencing factors. *Journal of Geographical Sciences*, *32*(7), 1241–1260. https://doi.org/10.1007/s11442-022-1995-4

- **依据类别** Scite 摘要
- **核验途径** Scite title/DOI metadata with abstract; Smart Citation snippet from the paper's own text returned by Scite
- **核心发现** 作者用五普、六普和2018年人口统计分析县域城镇化。县域城镇化是全国城镇化的短板。2000至2010年城镇化水平高的县集中在东部沿海，城镇化快的县多在中西部。远离中心城市、高海拔、受教育水平低等不利禀赋是主要制约。县域新型城镇化是就近城镇化（nearby urbanization）的主要形式，高等级教育、医疗等公共服务只能在县城和中心镇提供。
- **证据摘录** The paper reveals that the urbanization level of counties is a weak area in China's overall urbanization. ... high-level public services, such as education and health care, can be delivered only in county seats and central towns that serve as service centers
- **本研究中的用途** 支持县城是县域公共服务中心这一设定。本项目在县城建成区尺度评估学校、医院、公园、绿道的供给，并把县域（而非仅县城）常住人口作为服务人口的备选分母，比较两种口径下的人均供给。
- **设计采用情况** 已采用，§2.2 县城是县域公共服务中心的设定；学校、医院可达比例在 v1.1 广东试点计算。

**[39]** Zhang, X., Zhang, Q., Zhang, X., & Gu, R. (2023). Spatial-temporal evolution pattern of multidimensional urban shrinkage in China and its impact on urban form. *Applied Geography*, *159*, 103062. https://doi.org/10.1016/j.apgeog.2023.103062

- **依据类别** Consensus 摘要
- **核验途径** Scite title/DOI metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 作者构建多维收缩评价体系，分析2000至2020年中国城市收缩。收缩趋势在加剧，收缩城市多位于增长极外围和东北，常常人口、经济、社会同步收缩。人口和经济收缩对城市形态的影响增强，使用地扩张变慢、规模变小。但部分城市出现人口流失、经济衰退与城市用地扩张并存的悖论，形成空间错配。
- **证据摘录** There is a spatial mismatch between the level of urban shrinkage and urban form indicators, particularly in some cities where a paradox of population loss, economic decline, and urban land expansion coexist.
- **本研究中的用途** 直接对应收缩县城仍在扩张的检验。本项目在县级面板中构造建成区增长率/常住人口增长率弹性（land–population elasticity），识别人口减少而建成区增加的悖论县，再检验它们与转移支付依赖度、土地出让收入的关系。
- **设计采用情况** 已采用，§7 表 1 的扩张效率与扩张收缩背离指标，对应 §4 的 H4。
- **备注** Crossref 记为 Xiao, Zhang；按中文姓名习惯判断第一作者姓 Zhang，投稿前核对

**[40]** Zhang, Y., Ding, X., Li, D., & Yu, S. (2024). Research on spatiotemporal patterns and influencing factors of county-level urban shrinkage in urbanizing China. *Sustainable Cities and Society*, *109*, 105544. https://doi.org/10.1016/j.scs.2024.105544

- **依据类别** Consensus 摘要
- **核验途径** Scite title/DOI metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 研究以2846个县级单元为对象。2000至2010年有180个收缩，2010至2020年增至1050个，重度收缩的比例上升。东北、华北、中部、西北是核心集聚区，东部在2010至2020年新出现集聚。绝对收缩成为主导类型，主要由城–城迁移和异地城镇化（off-site urbanization）驱动；城镇化水平、经济发展、老龄化是影响因素。
- **证据摘录** Taking 2846 county-level cities as research units, the results showed that 180 and 1050 county-level cities shrunk in 2000–2010 and 2010–2020, respectively. ... Absolute shrinkage became the main shrinking type significantly driven by "city–city" and "off-site urbanization" migration.
- **本研究中的用途** 县级收缩的最新全国证据。本项目参照该文的城市与城市周边二分，把县域拆成县城建成区和县域其余部分，检验县域收缩而县城不收缩是否普遍，以准确界定命题中县城人少的含义。
- **设计采用情况** 已采用，§4 的 H1 设县域收缩、县城增长一类（table4_quadrant_town）。
- **备注** Crossref 记为 Yu, Zhang；按中文姓名习惯判断第一作者姓 Zhang，投稿前在出版社页面核对

**[41]** Zheng, Q., Zeng, Y., Deng, J., Wang, K., Jiang, R., & Ye, Z. (2017). “Ghost cities” identification using multi-source remote sensing datasets: A case study in Yangtze River Delta. *Applied Geography*, *80*, 112–121. https://doi.org/10.1016/j.apgeog.2017.02.004

- **依据类别** Consensus 摘要
- **核验途径** Scite title metadata (no abstract in Scite); abstract text from Consensus search
- **核心发现** 作者用夜光影像、土地覆盖产品和人口格网，在县/区尺度构建鬼城指数（ghost city index, GCI）。三项标准是：灯光区与建成区的一致性、灯光强度、人口密度。长三角的鬼城在空间上显著集聚；县和新开发区风险更高，省会和地级市对周边有缓解作用。
- **证据摘录** comprising three criteria: consistency of lit area and built-up area, illumination intensity and population density. ... counties and new development zones have higher risk of suffering from the phenomenon, while capital cities and municipal cities have an alleviative effect for ambient regions
- **本研究中的用途** GEE管线可以直接复现的县级指标。用 VIIRS DNB 年/月合成、ESA WorldCover/Dynamic World 建成区和 WorldPop/GHS-POP 人口格网计算县级 GCI，比较县城与市辖区。该文县的风险更高的结论与县城过建命题方向一致。
- **设计采用情况** 已采用，§8.4，单位建成面积夜光作 H4 的辅助指标；完整的鬼城指数不复现。

## A.3 土地财政、住房与绅士化

**[42]** Anguelovski, I., Connolly, J. J., García-Lamarca, M., Cole, H., & Pearsall, H. (2019). New scholarly pathways on green gentrification: What does the urban ‘green turn’ mean and where is it going? *Progress in Human Geography*, *43*(6), 1064–1086. https://doi.org/10.1177/0309132518803799

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract + Smart Citation snippets returned)
- **核心发现** 梳理绿色绅士化研究议程：城市绿化干预可能形成环境特权的精英飞地（elite enclaves of environmental privilege），排斥低收入与少数群体；提出考察绿色绅士化规模、范围、表现形式与抵抗的新问题与研究设计。
- **证据摘录** urban greening interventions can create elite enclaves of environmental privilege and green gentrification, and exclude lower-income and minority residents from their benefits.
- **本研究中的用途** 为研究设计提供概念框架（why/how/where/when green gentrification takes place），可用于界定本项目中绿色绅士化的测度维度（房价、人口构成、置换）。
- **设计采用情况** 已采用，§2.4；绅士化以人口构成与置换测度（§9.7）。
- **备注** Scite 记录年份为 2018（在线）

**[43]** Fang, H., Gu, Q., Xiong, W., & Zhou, L.-A. (2016). Demystifying the Chinese housing boom. *NBER Macroeconomics Annual*, *30*(1), 105–166. https://doi.org/10.1086/685953

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata, no abstract) + Consensus abstract
- **核心发现** 基于120个城市2003至2013年新房重复销售价格指数与按揭数据：房价大幅上涨，除少数一线城市外基本伴随收入同步增长；最低收入按揭者以超过8倍的房价收入比购房，财务负担沉重，但首付比例普遍超35%。
- **证据摘录** we find enormous housing price appreciation during the decade, which was accompanied by equally impressive growth in household income, except in a few first-tier cities. While bottom-income mortgage borrowers endured severe financial burdens by using price-to-income ratios over eight to buy homes
- **本研究中的用途** 支持以房价收入比（price-to-income ratio）作为大城市压力指标，并提示一线城市与其他城市的收入-房价脱钩差异；房价需外部数据补充，不在GEE与普查中。
- **设计采用情况** 待 v2.0，房价收入比需要外部房价数据；本版以市场租赁户与集体户比例刻画住房压力（§4 的 H5）。

**[44]** Glaeser, E. L., Huang, W., Ma, Y., & Shleifer, A. (2017). A real estate boom with Chinese characteristics. *Journal of Economic Perspectives*, *31*(1), 93–116. https://doi.org/10.1257/jep.31.1.93

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned); Scite lists first three authors only
- **核心发现** 2003至2014年中国房价年均实际涨幅超过10%，达建安成本的2-10倍；同期建设了千亿平方英尺住宅，空置住房大幅增加；价格可持续性取决于政府是否大幅收缩新增供给。
- **证据摘录** Chinese housing prices rose by over 10 percent per year in real terms between 2003 and 2014 and are now between two and ten times higher than the construction cost of apartments. ... This boom has been accompanied by a large increase in the number of vacant homes
- **本研究中的用途** 为大城市住房压力与中小城市空置并存提供宏观背景；提示可用普查住房存量/常住户数与夜间灯光-建成区错配近似空置率，检验县城基建多、人少是否伴随住房空置。
- **设计采用情况** 已采用，§8.4 的住房余量比。

**[45]** He, S. (2007). State-sponsored gentrification under market transition: The case of Shanghai. *Urban Affairs Review*, *43*(2), 171–198. https://doi.org/10.1177/1078087407305175

- **依据类别** Scite 摘要
- **核验途径** Scite author+term search then metadata (abstract returned)
- **核心发现** 上海绅士化中国家强力介入：刺激并迎合绅士化者的消费需求；为资本循环创造条件，大量投资于环境美化与基础设施；动员资源解决产权碎片化。国家资助型绅士化以大规模居民置换（displacement）为代价追求经济与城市增长。
- **证据摘录** the state makes policy interventions and invests heavily in environment beautification and infrastructure construction. ... The state-sponsored gentrification under market transition is motivated by the pursuit of economic and urban growth at the cost of large-scale residential displacement.
- **本研究中的用途** 关键理论支点：大城市的环境美化与基础设施投资本身是绅士化机制，而非中性公共品供给；为绿化/基建投入-房价-人口替换链条提供机制假设。
- **设计采用情况** 已采用，§2.4 与 §9.7 的街道尺度检验。
- **备注** 何深静

**[46]** He, S., & Wu, F. (2009). China's emerging neoliberal urbanism: Perspectives from urban redevelopment. *Antipode*, *41*(2), 282–304. https://doi.org/10.1111/j.1467-8330.2009.00673.x

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned)
- **核心发现** 城市更新处于中国新自由主义化前沿；新自由主义化是对多重危机与快速发展需求的回应，充满社会抵抗与央地张力；在次国家尺度最为显著，因地方政府最能协助新自由主义实验与管理危机；关键不在国家在场与否，而在其是否使市场运作合法化。
- **证据摘录** neoliberal urbanism is more tangible at the sub-national scale, since the local state can most effectively assist neoliberal experiments and manage crises.
- **本研究中的用途** 支持以地方（市/县）为分析单元，并将市场化程度理解为地方政府促成市场运作的程度；可用于解释为何大城市与县城在同一中央体制下呈现不同供给模式。
- **设计采用情况** 已采用，§2.4；地方政府促成市场运作的判断支撑 §3 的体制修正。
- **备注** 何深静

**[47]** He, S. (2019). Three waves of state-led gentrification in China. *Tijdschrift voor Economische en Sociale Geografie*, *110*(1), 26–34. https://doi.org/10.1111/tesg.12334

- **依据类别** Scite 摘要
- **核验途径** Scite author+term search (abstract returned); Scite year 2018 (online), volume 110 (2019 issue)
- **核心发现** 提出以国家为中心的三角嵌入（state-centred triangular embedment）框架，将中国绅士化分为三波：1990年代零星绅士化、2000年代广泛绅士化、2010年后国家主导金融化下的再激活绅士化；绅士化成为现代竞争型国家通过市场运作从土地/住房再开发中汲取价值的组成部分。
- **证据摘录** the third wave of reactivated gentrification under state-led financialisation after 2010. Gentrification has become an integral part of the making of the modern competitive state in China, joining force with the state's endeavour in extracting values from land/housing redevelopment through market operation
- **本研究中的用途** 为时间分期提供依据：普查2000/2010/2020三期恰好对应第二波与第三波；可检验2010至2020年大城市中心区人口结构（教育、职业、租住比例）变化是否与土地金融化强度相关。
- **设计采用情况** 已采用，§9.7，城中村拆除作为第三波绅士化的更新处理（v1.2）。
- **备注** 何深静；Scite 记录年份为 2018（在线）

**[48]** He, S., Zhang, M., & Wei, Z. (2020). The state project of crisis management: China's shantytown redevelopment schemes under state-led financialization. *Environment and Planning A: Economy and Space*, *52*(3), 632–653. https://doi.org/10.1177/0308518x19882427

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned; author order confirmed by DOI fetch)
- **核心发现** 2008年后国家以低息、稳定、长期贷款的国家主导金融化推动全国棚户区改造（SRSs），以成都为例说明其作为危机管理国家项目，既应对经济危机也应对合法性危机，但因国家过度干预成为危机管理的危机。
- **证据摘录** Since 2008, China has introduced state-led financialization to inject low-interest, stable and long-term loans to facilitate urban redevelopment through national shantytown redevelopment schemes (SRSs). ... this model has simultaneously become a source of “crisis of crisis-management”
- **本研究中的用途** 棚改是连接土地金融化与城市更新的政策变量，且覆盖大量中小城市与县城；在比较县城与大城市时需把棚改（货币化安置）作为共同冲击，避免把棚改驱动的县城住房与基建扩张归因于转移支付。
- **设计采用情况** 待 v1.x，棚改作为共同冲击的控制变量尚无县级数据来源。
- **备注** 何深静；Scite 记录年份为 2019（在线）

**[49]** He, S., & Cai, R. (2024). Negotiating the exclusive right to public schools in China's education-featured gated communities under multiscalar and multidirectional urban entrepreneurialism. *Urban Studies*, *61*(14), 2756–2777. https://doi.org/10.1177/00420980231204714

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据与摘要（2026-09-26 核验）
- **核心发现** 教育型封闭小区把 K–12 学位打包为小区服务，使教育由公共品变为可被房价资本化的俱乐部品，成为城市企业主义的组成部分；业主通过与地方政府的密集互动争取学位的排他性权利。
- **证据摘录** By turning education from a public good into a club good that can be capitalised in the housing price and leveraged in urban (re)development, education-featured gated communities are highly sought after by homebuyers, developers, and local states
- **本研究中的用途** 支持 H5 的市场替代机制：大城市的公共服务与公共空间可被小区化并计入房价；绿地的俱乐部化可类比检验。
- **设计采用情况** 已采用，§2.4 与 §4 的 H7 大城市一侧的入学约束；小区俱乐部化的检验待 v1.1 广东试点。
- **备注** 何深静；Scite 记录年份为 2023（在线）

**[50]** He, S., He, Q., Jiang, B., Ji, R., & Gong, P. (2026). Urban development as a polyrhythmic project: Reimagining multiple urban futures in the era of slow growth. *Urban Studies*. https://doi.org/10.1177/00420980261484531

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据与摘要（2026-09-26 核验）
- **核心发现** 以山东乳山这一沿海小城市为例，用节奏分析 (rhythmanalysis) 考察慢增长时期的发展范式转变：乳山曾依靠异地投资者对低密度滨海居住的需求逐年加密住房，住房需求收缩与紧凑发展政策使其进入慢增长期，季节性投资型居民与游客带来的暂时密度 (transient density) 成为新的积累场所，却造成不完整、较慢的开发。
- **证据摘录** Rushan once witnessed annual repetition of urban growth through selective housing densification capitalising on trans-local investors' desire for lower-density coastal living, driven by the housing capital rhythm and a pro-growth coalition.
- **补充证据**（Scite 摘要）Shrinking housing demand and national strategies promoting compact development, however, ushered in a (different) slow-growth period. The rhythms of seasonal investor-residents and tourists, and the transient density they entailed, became key sites for accumulation. Yet their seasonal and fragmented urban engagement produced incomplete and slow(er) development.
- **本研究中的用途** 为县级小城市在人口与住房需求收缩后的建设空间使用不足提供质性机制，对应本研究的单位建筑体量夜光与季节性使用强度。
- **设计采用情况** 已采用，§2.2 与 §8.4，暂时密度对应住房余量比大于 1 的一端。
- **备注** 何深静；在线优先发表（2026-09），尚无卷期

**[51]** Latham, A., & Layton, J. (2019). Social infrastructure and the public life of cities: Studying urban sociality and public spaces. *Geography Compass*, *13*(7). https://doi.org/10.1111/gec3.12444

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract + Smart Citation snippets returned)
- **核心发现** 借鉴Klinenberg发展社会基础设施（social infrastructure）概念，用以研究和评价图书馆、公园、游泳池、学校等支撑城市公共生活的空间，整合基础设施、公共性与公共空间、社会交往与相遇、供给政治四条研究脉络。
- **证据摘录** this article develops the concept of “social infrastructure” as a way to research and value these kinds of spaces. ... four related strands of social scientific inquiry: work on infrastructure; publicness and public space; sociality and encounter; and the politics of provision.
- **本研究中的用途** 为研究者的社会基础设施视角提供概念锚点；提醒遥感绿量只是供给侧数量代理，需以POI补充图书馆、社区中心、学校、菜市场等设施，并将供给政治（谁出资、谁可进入）纳入指标设计。
- **设计采用情况** 已采用，§2.4 与 §3 的社会基础设施机制；学校、医院、养老机构点位在 v1.1 广东试点接入。

**[52]** Li, Z., Wu, F., & Zhang, F. (2024). A geographical approach to China's local government debt. *The Professional Geographer*, *76*(3), 318–330. https://doi.org/10.1080/00330124.2023.2300803

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned)
- **核心发现** 基于2009至2020年300余城市城投债与地方政府债数据：2015年后经济较好城市发债更多，财政集权加强；但欠发达城市债券发行/财政收入比更高、使用效率更低、金融风险更高，财政集权未能有效控制其风险。
- **证据摘录** Fiscal centralization did not effectively contain the financial risk in the less-developed cities. Motivated by the competition, the less-developed cities did not use bonds efficiently and had higher ratios of bond issuance to fiscal income, experiencing higher financial risk.
- **本研究中的用途** 直接关联县城基建更好的命题：欠发达地区的基础设施可能部分由债务而非转移支付驱动。建议在县级面板中加入债券发行额/一般公共预算收入，区分转移支付驱动与债务驱动的供给，并检验其与人口流失的错配。
- **设计采用情况** 已采用，§3 与 §6，人均城投有息债务与人均新增专项债作为并列资金来源。

**[53]** Lichtenberg, E., & Ding, C. (2009). Local officials as land developers: Urban spatial expansion in China. *Journal of Urban Economics*, *66*(1), 57–64. https://doi.org/10.1016/j.jue.2009.03.002

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (title/journal/year/abstract returned)
- **核心发现** 财政与治理改革使地方官员像土地开发商一样决策，农地转用与城市空间规模接近竞争性土地市场的结果；上海及周边省份存在显著地租梯度（rent gradient），在经济最发达地区最强、欠发达地区最弱，城市地价远高于农地价格。
- **证据摘录** These rent gradients are strongest in the most economically developed portions of the study region and weakest in the least economically developed. Urban land values exceed agricultural land values by a considerable margin
- **本研究中的用途** 为大城市靠土地市场提供激励机制的经典解释；提示土地出让收益高度依赖区位与发展水平，县级面板中须控制经济发展水平与距中心城市距离，否则会把区位差异误读为财政体制差异。
- **设计采用情况** 已采用，§2.3；区位以到城市出行时间与省份或地级市固定效应控制（§9.3）。

**[54]** Liu, Y., He, S., Wu, F., & Webster, C. (2010). Urban villages under China's rapid urbanization: Unregulated assets and transitional neighbourhoods. *Habitat International*, *34*(2), 135–144. https://doi.org/10.1016/j.habitatint.2009.08.003

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata, no abstract) + Consensus abstract
- **核心发现** 基于六个大城市11个城中村，将城中村（chengzhongcun）视为未受管制的资产与过渡性社区：模糊产权、非正规租赁市场与国家管制真空使其为失地农民提供生计、为流动人口提供低成本住房；国家主导改造将产生复杂后果。
- **证据摘录** the vacuum of state regulation in the urban village makes possible a means of subsistence for landless villagers and provides low-cost residential space for migrants. The transformation of the urban village under state regulation would produce complicated results.
- **本研究中的用途** 说明大城市流入人口的住房压力阀是非正规租赁市场；城中村拆除（可用遥感建成区形态变化识别）意味着低成本住房流失，应作为大城市住房压力的空间指标之一。何深静为第二作者。
- **设计采用情况** 已采用，§2.3；城中村拆除作为 §9.7 街道检验的更新处理（v1.2）。
- **备注** 何深静为第二作者

**[55]** Logan, J., Fang, Y., & Zhang, Z. (2009). Access to housing in urban China. *International Journal of Urban and Regional Research*, *33*(4), 914–935. https://doi.org/10.1111/j.1468-2427.2009.00848.x

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned)
- **核心发现** 利用2000年人口普查八大城市数据，发现户籍/居住身份决定住房获取路径：有城市户籍的迁移者反而具有优势，而农村流动人口无论居住多久都处于持续劣势。
- **证据摘录** Using data from the Chinese census of 2000 for eight large cities, this study shows how residence status affects access to various pathways to housing. ... persistent disadvantages for rural migrants regardless of how long they have lived in the city.
- **本研究中的用途** 方法上直接示范普查住房表×户籍身份的分析；本项目可用2000/2010/2020普查的住房来源（租赁、购买商品房、自建房）与人户分离数据，构造大城市流入人口住房压力指标。
- **设计采用情况** 已采用，§4 的 H5 与 §6，用住房来源与人户分离构造住房压力指标。

**[56]** Tao, R., Su, F., Liu, M., & Cao, G. (2010). Land leasing and local public finance in China's regional development: Evidence from prefecture-level cities. *Urban Studies*, *47*(10), 2217–2236. https://doi.org/10.1177/0042098009357961

- **依据类别** Scite 摘要
- **核验途径** Scite title/author search then DOI metadata (abstract returned); Scite lists first three authors only
- **核心发现** 1990年代中期以来，地方政府以补贴性土地与基础设施作为竞争制造业投资的关键工具；基于1999至2003年地级市面板，比较了协议出让与招拍挂（auction/tender）两类土地出让方式的财政效应，并将地方土地开发行为归因于土地制度与央地财政安排。
- **证据摘录** explores local fiscal incentives to use subsidised land and infrastructure as key instruments in regional competition for manufacturing investment ... compares the fiscal impacts of different forms of land leasing (by negotiation versus by auction/tender)
- **本研究中的用途** 支撑以土地出让收入/一般公共预算收入构造土地财政依赖指标，并区分工业用地（协议、低价）与商住用地（招拍挂）的财政含义；地级市面板方法可下沉至县级。
- **设计采用情况** 已采用，§6 与 §7 的人均土地出让价款；工业与商住用地的区分待 v1.x 视中国土地市场网字段而定。

**[57]** Wolch, J. R., Byrne, J., & Newell, J. P. (2014). Urban green space, public health, and environmental justice: The challenge of making cities ‘just green enough’. *Landscape and Urban Planning*, *125*, 234–244. https://doi.org/10.1016/j.landurbplan.2014.01.017

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata, no abstract) + Consensus abstract
- **核心发现** 综述英美文献并比较美中城市绿化：绿地分布多偏向富裕群体；中国城市国家更控制土地供给但同样存在绿化的市场激励；新增绿地在改善健康与环境的同时抬高房价与物业价值，可能引发绅士化与置换，因此提出刚好够绿（just green enough）策略。
- **证据摘录** Similar strategies are being employed in Chinese cities where there is more state control of land supply but similar market incentives for urban greening. In both contexts, however, urban green space strategies may be paradoxical ... it also can increase housing costs and property values.
- **本研究中的用途** 为绿色悖论（green space paradox）提供理论起点，并明确将中国纳入比较；可据此提出对照假说：县城因住房需求弱，绿化较少资本化，绿而不贵。
- **设计采用情况** 已采用，§2.4 与 §4 的 H6。

**[58]** Wu, F. (2018). Planning centrality, market instruments: Governing Chinese urban transformation under state entrepreneurialism. *Urban Studies*, *55*(7), 1383–1399. https://doi.org/10.1177/0042098017721828

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned)
- **核心发现** 提出国家企业家主义（state entrepreneurialism）：规划中心性（planning centrality）与市场工具（market instruments）相结合，通过三旧改造、郊区新城与乡村重建等案例说明中国不同于新自由主义增长机器（growth machine）。
- **证据摘录** This article defines the key parameters of 'state entrepreneurialism' as a governance form that combines planning centrality and market instruments ... the article details institutional configurations that make the Chinese case different from a neoliberal growth machine.
- **本研究中的用途** 用于修正核心命题中大城市靠市场的表述：大城市是国家主导+市场工具而非纯市场；理论框架应以财政体制×国家中心性而非国家vs市场二分来比较县城与大城市。
- **设计采用情况** 已采用，§2.3 与 §3，体制以四条连续投入轴界定。
- **备注** Scite 记录年份为 2017（在线）

**[59]** Wu, F. (2022). Land financialisation and the financing of urban development in China. *Land Use Policy*, *112*, 104412. https://doi.org/10.1016/j.landusepol.2019.104412

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract returned)
- **核心发现** 土地收益之外，土地金融化（land financialisation）自2008年起加速：土地抵押、地方政府融资平台（LGFVs）与城投债（Chengtou Bonds）相继成为城市开发融资渠道；财政刺激计划触发了土地金融化，最初是危机管理的发展策略。
- **证据摘录** This paper examines the land mortgage, which has accelerated since 2008, and subsequent waves of financialisation through local government financial vehicles (LGFVs) and Chengtou Bonds (urban construction and investment bonds).
- **本研究中的用途** 提示财政变量不能只用一般公共预算：需加入政府性基金预算中的土地出让收入与城投债/专项债，否则会低估大城市与部分县城的基础设施实际资金来源。
- **设计采用情况** 已采用，§6，土地出让、城投债务与专项债进入模型。

**[60]** Wu, L., & Rowe, P. G. (2022). Green space progress or paradox: Identifying green space associated gentrification in Beijing. *Landscape and Urban Planning*, *219*, 104321. https://doi.org/10.1016/j.landurbplan.2021.104321

- **依据类别** Consensus 摘要
- **核验途径** Scite title search (metadata, no abstract) + Consensus abstract
- **核心发现** 北京基于开放数据与含双重差分（DID）的特征价格模型，证实新公园通过抬高周边房价引发绅士化的绿色空间悖论；资本化程度因公园类型而异：综合公园显著正向，自然公园在最近距离不显著，开园前后效应大于开园即时。
- **证据摘录** our estimation results confirmed the “green spaces paradox” in Beijing that adding new parks can trigger gentrification by increasing nearby housing prices. ... Natural parks posed insignificant effects on housing prices at the closest distance, but comprehensive parks showed a positive sign.
- **本研究中的用途** 提供超大城市公园资本化的因果识别范式（hedonic + DID）；本项目可将新建公园时点（遥感/OSM识别）作为处理变量，在大城市与县城间比较资本化幅度。
- **设计采用情况** 待 v1.1，特征价格模型先在广东试点检验可行性（§4 的 H6）。

**[61]** Xiao, Y., Li, Z., & Webster, C. (2016). Estimating the mediating effect of privately-supplied green space on the relationship between urban public green space and property value: Evidence from Shanghai, China. *Land Use Policy*, *54*, 439–447. https://doi.org/10.1016/j.landusepol.2016.03.001

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata, no abstract) + Consensus abstract
- **核心发现** 将中国城市绿地分为公共绿地（开放公园）、私人绿地与俱乐部绿地（club green space，仅供缴费小区居民）；上海特征价格模型支持小区内私人供给绿地替代公共绿地的假说，区级公园对购房者无可测使用价值。
- **证据摘录** we test the hypothesis that the privately supplied green spaces withing club-communities substitute for publicly supplied green spaces in the public realm. We find evidence in support of this hypothesis, showing for example, that unlike other kinds of green space, public district parks have no measurable use value to Shanghai home-buyers
- **本研究中的用途** 直接回答市场供给（封闭小区绿地）vs 公共供给绿地的对比问题：大城市绿量中相当部分是开发商提供、房价内化的俱乐部品；遥感测算时必须用小区AOI掩膜区分俱乐部绿地与公共绿地，否则会高估大城市公共绿地供给。
- **设计采用情况** 待 v1.1，小区 AOI 掩膜拆分俱乐部绿地在广东试点实现（§4 的 H5）。

**[62]** Zhang, J., & Wu, L. (2025). Gentrification outcomes of greening in different urbanization stages: A longitudinal analysis of Chinese cities, 2012–2020. *Environment and Planning B: Urban Analytics and City Science*, *52*(1), 231–246. https://doi.org/10.1177/23998083241258683

- **依据类别** Scite 摘要
- **核验途径** Scite title lookup (abstract returned)
- **核心发现** 2012至2020年全国城市纵向分析：以NDVI、邻近公园距离与面积为绿地指标，以夜间灯光与住宅地价为绅士化代理；增加NDVI与新建公园均可引致绅士化，公园面积效应微弱；城镇化率较高城市受NDVI影响更大、受公园距离影响更小。
- **证据摘录** Nationwide analyses indicated that both increasing NDVI and building new parks nearby could lead to gentrification, but the park area had a marginal effect. ... Cities with higher urbanization rates were more affected by NDVI but less affected by park distance.
- **本研究中的用途** 与本项目最直接可复用的全国尺度遥感方案：NDVI（Landsat/MODIS/Sentinel-2）、VIIRS夜光可在GEE实现；可扩展到县级并按城市层级/城镇化阶段分层，检验县城与大城市绿化的资本化差异。
- **设计采用情况** 已采用，§2.4；县城与大城市的资本化比较待 v2.0。
- **备注** Scite 记录年份为 2024（在线）

**[63]** Zhu, J., He, S., & Hao, J. (2022). Growing rights consciousness of the marginalised and the reshuffling of the landlord–tenant power relationship: Examining a country park-induced displacement in Shanghai. *Population, Space and Place*, *28*(1). https://doi.org/10.1002/psp.2510

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (abstract + full-text Smart Citation snippets returned; author order confirmed)
- **核心发现** 上海郊野公园（Country Park）规划以提升生态品质为名清退非正规聚落；流动租户借助社会资本与权利意识从房东处争取到补偿，房东与政府形成临时联盟，地方政府规避正面冲突；但清退终结了流动人口聚居区的社会支持，阻碍其向上流动。
- **证据摘录** the rural settlement clearance in question is part of the Country Park plan that is aimed at improving the ecological quality of metropolitan Shanghai ... the overall situation brought an end to the social support that existed in migrant enclaves and thus hampered their upward social mobility.
- **本研究中的用途** 中国语境下绿色项目引致置换（green-induced displacement）的直接案例：提示遥感识别的绿地增加可能伴随非正规住房拆除与流动人口外迁，应将绿地变化与普查乡镇/街道层级常住人口、外来人口变化联动分析。
- **设计采用情况** 已采用，§4 的 H6a 与 §9.7（v1.2）。
- **备注** 何深静为第二作者；Scite 记录年份为 2021（在线）

## A.4 遥感测度与数据质量

**[64]** Bai, Z., Wang, J., Wang, M., & Gao, M. (2018). Accuracy assessment of multi-source gridded population distribution datasets in China. *Sustainability*, *10*(5), 1363. https://doi.org/10.3390/su10051363

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 以GIS化的2000年乡镇级普查检验GPW、GRUMP、WorldPop和CnPop四套人口网格。WorldPop精度最高，能准确估计约60%的人口；CnPop约一半；GPW只在少数平原和盆地可接受，约30%。
- **证据摘录** These datasets are assessed using a specific method based on a GIS-linked 2000 census dataset at the township level in China. The results indicate that WorldPop had the highest estimation accuracy, estimating about 60% of the total population.
- **补充证据**（Scite 全文摘录）This shows that the WorldPop dataset simulates the population distribution well for the vast majority of towns in eastern and southern China; however, there is a considerably large error level in the hilly areas such as Hengduan Mountain.
- **本研究中的用途** 支持选用WorldPop并以乡镇街道普查数据校正。同时提示：西部和山区人口稀疏县的网格误差较大，县城与大城市比较必须报告误差敏感性。
- **设计采用情况** 已采用，§2.5；01 已同时提取 WorldPop，以其重算的格网人口稳健性检验待 v1.1（§9.6 表 2）。

**[65]** Barrington-Leigh, C., & Millard-Ball, A. (2017). The world's user-generated road map is more than 80% complete. *PLOS ONE*, *12*(8), e0180698. https://doi.org/10.1371/journal.pone.0180698

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); editorial notice = correction/erratum 2019 (10.1371/journal.pone.0224742), not retraction
- **核心发现** 结合卫星影像目视评估和贡献曲线饱和估计，全球OSM道路完整度约83%，40%以上国家的街道网络已基本完整。治理较好、互联网普及的国家完整度更高；完整度与人口密度呈U形关系，人口稀疏区和稠密城市最完整。
- **证据摘录** We find (i) that globally, OSM is ∼83% complete [...] and that completeness has a U-shaped relationship with population density—both sparsely populated areas and dense cities are the best mapped
- **本研究中的用途** 县城处在人口密度的中间段，按U形关系可能恰是OSM最不完整的区间。因此县城与大城市的道路、公园比较不能直接用OSM原始数据，需要评估完整度或用其他来源校核。
- **设计采用情况** 待 v1.1，§8.3，广东试点做分层抽样核验，并按组报告精确率与召回率。
- **备注** Scite 显示该文有更正通知 (correction)，无撤稿

**[66]** Brown, C. F., Brumby, S. P., Guzder-Williams, B., Birch, T., Hyde, S. B., Mazzariello, J., Czerwinski, W., Pasquarella, V. J., Haertel, R., Ilyushchenko, S., Schwehr, K., Weisse, M., Stolle, F., Hanson, C., Guinan, O., Moore, R., & Tait, A. M. (2022). Dynamic World, near real-time global 10 m land use land cover mapping. *Scientific Data*, *9*. https://doi.org/10.1038/s41597-022-01307-4

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 用深度学习对Sentinel-2做10 m近实时土地利用/覆盖分类（Dynamic World），逐景输出各类别概率，可按任意时段合成。
- **证据摘录** We developed a new automated approach for globally consistent, high resolution, near real-time (NRT) land use land cover (LULC) classification leveraging deep learning on 10 m Sentinel-2 imagery.
- **本研究中的用途** 用GOOGLE/DYNAMICWORLD/V1按年合成2016年以后的“trees”和“grass”概率，追踪县城2016年后的绿化建设。概率波段便于做阈值敏感性分析，并可与WorldCover交叉验证。
- **设计采用情况** 已采用，§8.2 交叉验证与 §9.5 的年度结果变量。

**[67]** Chen, W. Y., & Hu, F. Z. Y. (2015). Producing nature for public: Land-based urbanization and provision of public green spaces in China. *Applied Geography*, *58*, 32–40. https://doi.org/10.1016/j.apgeog.2015.01.007

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata only) + Consensus abstract; also grounded by Smart Citation in Chung et al. 2018 (Antipode)
- **核心发现** 285个地级市2002至2009年面板显示，对土地财政（land finance）的依赖度与城市公共绿地面积负相关。东、中、西部的差异表明，两者在发展早期为正相关，随城市化和经济发展加快转为负相关，可能造成绿地可达性的社会不公。
- **证据摘录** The results reveal a negative relationship between the reliance on land finance and the amount of urban public green spaces, indicating that local governments' pursuit of maximizing land lease revenue will not be able to finance more public green spaces, and may even cause the loss of public green spaces.
- **本研究中的用途** 直接支撑本项目的财政与绿地机制：大城市走市场/土地财政路径，不必然带来更多公共绿地。应把这一面板设计复制到县级，并加入转移支付依赖度作为对照机制，把因变量从统计绿地面积换成遥感暴露指标。
- **设计采用情况** 已采用，§2.4；土地出让作为并列资金来源（§9.3）。

**[68]** Chen, B., Wu, S., Song, Y., Webster, C., Xu, B., & Gong, P. (2022b). Contrasting inequality in human exposure to greenspace between cities of Global North and Global South. *Nature Communications*, *13*. https://doi.org/10.1038/s41467-022-32258-4

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 用精细人口网格和绿地制图构建人口加权绿地暴露框架（population-weighted greenspace exposure），测算2020年全球城市。全球南方城市的绿地暴露只有北方城市的约1/3，暴露不平等（Gini 0.47）约为北方（0.27）的两倍。空间差异中约22%与绿地供给量相关，53%与供给量和空间配置的共同作用相关。
- **证据摘录** Global South cities experience only one third of the greenspace exposure level of Global North cities. Greenspace exposure inequality (Gini: 0.47) in Global South cities is nearly twice that of Global North cities (Gini: 0.27).
- **补充证据**（Scite 全文摘录（结果与方法节））Thus, in addition to the 500-m catchment buffer—widely used for measuring nearby greenspace exposure—used for our primary analysis (Fig. 1a–c), we also changed the buffer distance to 100, 1000, and 1500 m (Fig. 1d–f). ... We applied the population-weighted exposure model to quantify the spatial interaction between population and greenspace.
- **本研究中的用途** 本项目比较县城与大城市的核心指标来源：以县城城区、大城市市辖区为单元，计算人口加权绿地暴露和城内Gini，替代只看人均绿地面积的做法。沿用其500 m缓冲作为主设定，另做100–1500 m敏感性分析。
- **设计采用情况** 已采用，§8.2 的人口加权树木暴露，500 m 为主设定，100、1 000、1 500 m 作敏感性检验；城内基尼系数不采用。
- **备注** Scite 将 Bin Chen 音译为西里尔字母

**[69]** Chen, B., Tu, Y., Wu, S., Song, Y., Jin, Y., Webster, C., Xu, B., & Gong, P. (2022a). Beyond green environments: Multi-scale difference in human exposure to greenspace in China. *Environment International*, *166*, 107348. https://doi.org/10.1016/j.envint.2022.107348

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata; OA, no abstract returned) + Consensus abstract
- **核心发现** 用Sentinel-2 10 m全国绿地覆盖分数和人口加权暴露，在省、市、县、镇、地块五个尺度上评估中国的绿地暴露。暴露存在明显的尺度效应（scaling effect）。以胡焕庸线为界，绿地覆盖率在东部高估、在西部低估实际暴露。新城区的暴露明显好于老城区。
- **证据摘录** In general, the greenspace coverage rate will overestimate more realistic human exposure to greenspace in East China while underestimating in West China. We further found that, in China, more recently urbanized areas have much better greenspace exposure than older urban areas.
- **本研究中的用途** 目前唯一细到县级的全国绿地暴露研究，可作为本项目县级指标的基准和外部验证。覆盖率≠暴露直接说明官方建成区绿化覆盖率不能替代暴露指标。新区优于老城提示需要把县城新区扩张（常与土地、转移支付驱动的建设相关）和老城区分开分析。
- **设计采用情况** 已采用，§2.5 与 §7，跨组比较以占比与暴露指标为主；新老城区分开分析待 v1.x。

**[70]** Chung, C. K. L., Zhang, F., & Wu, F. (2018). Negotiating green space with landed interests: The urban political ecology of greenway in the Pearl River Delta, China. *Antipode*, *50*(4), 891–909. https://doi.org/10.1111/anti.12384

- **依据类别** Scite 摘要
- **核验途径** Scite title lookup (metadata + abstract + in-text snippets); no editorial notice
- **核心发现** 从城市政治生态学（urban political ecology）视角分析珠三角绿道：绿道是在迁就而非挑战强势土地利益的前提下缓解绿地短缺的务实安排。市级用地指标、农村用地权属主张和房地产开发三个相互交织的土地维度，决定了绿道为何建、建在哪、怎么建。
- **证据摘录** Three interlocking dimensions about land-municipal land quota, rural land use claims, and real estate development-have influenced why, where and how greenways have been created.
- **本研究中的用途** 解释用遥感或OSM测得的绿道空间分布时，应把它看作土地政治的结果，而不只是需求响应。文中援引的“green growth machines”和绿色绅士化（green gentrification）概念，可用于大城市绿道、公园与房价资本化的检验。
- **设计采用情况** 已采用，§2.4；绿道一词只用于矢量数据（§8.3）。

**[71]** Elvidge, C. D., Zhizhin, M., Ghosh, T., Hsu, F.-C., & Taneja, J. (2021). Annual time series of global VIIRS nighttime lights derived from monthly averages: 2012 to 2019. *Remote Sensing*, *13*(5), 922. https://doi.org/10.3390/rs13050922

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 由月度无云平均辐亮度生成一致处理的2012至2019年全球VIIRS年度夜光（V.2），用12个月中值去除火点、极光等异常值，并以3×3极差（DR）滤除背景噪声。各年处理方法和阈值一致，适合做变化检测。
- **证据摘录** The key advantages of the V.2 time series include consistent processing and threshold levels across all years, thus optimizing the set for change detection analyses.
- **本研究中的用途** 2020 年用 NOAA/VIIRS/DNB/ANNUAL_V21（2012 至 2021 年）计算县、区的夜光总量、单位建成面积与单位建筑体量夜光；ANNUAL_V22 的实际覆盖年份在 STAC 中说明不一，使用前须核实（见附录D）。
- **设计采用情况** 已采用，§8.4，VIIRS 夜光只作辅助指标，使用不足的主指标改为住房余量比。

**[72]** Gong, P., Li, X., Wang, J., Bai, Y., Chen, B., Hu, T., Liu, X., Xu, B., Yang, J., Zhang, W., & Zhou, Y. (2020b). Annual maps of global artificial impervious area (GAIA) between 1985 and 2018. *Remote Sensing of Environment*, *236*, 111510. https://doi.org/10.1016/j.rse.2019.111510

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata only) + Consensus abstract
- **核心发现** 用Landsat全档案、夜光和Sentinel-1辅助数据，在GEE上生成1985至2018年逐年30 m全球人工不透水面（GAIA），平均总体精度超过90%。2018年全球总量797,076 km²；中国的不透水面积在2015年超过美国。
- **证据摘录** In this paper, we mapped annual GAIA from 1985 to 2018 using the full archive of 30-m resolution Landsat images on the Google Earth Engine platform. [...] the mean overall accuracy is higher than 90%.
- **本研究中的用途** GEE资产Tsinghua/FROM-GLC/GAIA/v10（已经STAC确认）可以直接计算县、区的不透水面扩张年份。这一扩张量作为基建投入的物理代理和SDG 11.3.1的土地消耗项，与财政支出时序对照。数据止于2018年，之后需用GHSL或Dynamic World衔接。
- **设计采用情况** 已采用，§8.1 与 §9.4，固定中心建成区内 2000、2010、2018 年不透水面；年度序列由 --annual 模式输出（§9.5）。

**[73]** Gong, P., Chen, B., Li, X., Liu, H., Wang, J., Bai, Y., Chen, J., Chen, X., Fang, L., Feng, S., Feng, Y., Gong, Y., Gu, H., Huang, H., Huang, X., Jiao, H., Kang, Y., Lei, G., Li, A., … Xu, B. (2020a). Mapping essential urban land use categories in China (EULUC-China): Preliminary results for 2018. *Science Bulletin*, *65*(3), 182–187. https://doi.org/10.1016/j.scib.2019.12.007

- **依据类别** 仅引文片段（他文）
- **核验途径** Scite DOI lookup (metadata only; Consensus returned author list only); limitation grounded via Consensus abstract of citing paper Li X. et al. 2021 Remote Sensing
- **核心发现** Scite和Consensus都没有返回本文摘要，以下只陈述事实：本文发布2018年中国首套按地块划分的城市基本土地利用类别图（EULUC-China）。据引用文献（Li X. et al. 2021）的摘要，这一全国产品在北京、成都、郑州等平原城市的总体精度低于50%。
- **证据摘录** [Citing paper Li X. et al. 2021, Remote Sensing, abstract via Consensus] The first national mapping result of essential urban land use categories of China (EULUC-China) was released in 2019. However, the overall accuracies in some of the plain cities such as Beijing, Chengdu, and Zhengzhou were lower than 50%
- **本研究中的用途** 用其公园与绿地地块类别区分公园绿地（public park）和一般植被，是计算公园可达性的候选供给面。由于地块精度有限，只作为2018年截面使用，并须与OSM leisure=park及POI交叉校验。
- **设计采用情况** 待 v1.1，§8.3，作为矢量公园的交叉核对。
- **备注** 作者超过 20 位，按 APA 列前 19 位与末位

**[74]** Han, C., Lu, B., Zheng, J., Yu, D., & Zheng, S. (2025). Research on multiscale OpenStreetMap in China: Data quality assessment with EWM-TOPSIS and GDP modeling. *Geo-Spatial Information Science*, *28*(3), 1316–1340. https://doi.org/10.1080/10095020.2024.2356238

- **依据类别** Consensus 摘要
- **核验途径** Scite title lookup (metadata) + Consensus abstract; no editorial notice
- **核心发现** 用熵权法和TOPSIS构建2014至2020年中国多尺度OSM质量指数。全国质量先升、后降、再趋稳；省级和市级质量差异显著，并受人口和地理环境影响，空间聚类以高-高、低-低为主。
- **证据摘录** From 2014 to 2020, the quality of national-scale OSM data first increased, then decreased and then gradually stabilized. In addition, the quality of OSM data at the provincial and municipal scales is significantly different, and the distribution is affected by the population and geographical environment.
- **本研究中的用途** 把市级OSM质量指数作为协变量或样本权重，避免把数据质量差异误读为县城与大城市之间的公园、绿道、道路供给差异。
- **设计采用情况** 待 v1.1，§8.3，市级 OSM 质量指数作矢量指标的控制变量。
- **备注** Scite 记录年份为 2024（在线）

**[75]** Hansen, M. C., Potapov, P. V., Moore, R., Hancher, M., Turubanova, S. A., Tyukavina, A., Thau, D., Stehman, S. V., Goetz, S. J., Loveland, T. R., Kommareddy, A., Egorov, A., Chini, L., Justice, C. O., & Townshend, J. R. G. (2013). High-resolution global maps of 21st-century forest cover change. *Science*, *342*(6160), 850–853. https://doi.org/10.1126/science.1244693

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据与摘要（Scite 只列前 3 位作者，2026-09-26 核验）；完整作者表取自 GEE STAC 目录 sci:citation；Scite 未返回编辑通知
- **核心发现** 用 Landsat 观测绘制 2000 至 2012 年 30 m 分辨率的全球森林损失（230 万 km²）与增加（80 万 km²）；热带是唯一呈现趋势的气候带，森林损失每年增加 2 101 km²；亚热带集约林业的森林变化率全球最高。
- **证据摘录** Earth observation satellite data were used to map global forest loss (2.3 million square kilometers) and gain (0.8 million square kilometers) from 2000 to 2012 at a spatial resolution of 30 meters.
- **本研究中的用途** 取 GEE 资产 UMD/hansen/global_forest_change 的 treecover2000 波段（2000 年树冠覆盖度）作基期，把 2020 年 WorldCover 树木像元按覆盖度是否不低于 30% 分为存量树木与新增树木。treecover2000 波段的含义取自 GEE STAC 目录，摘要中没有这一信息。
- **设计采用情况** 已采用，§8.2，2000 年树冠覆盖度作存量与新增树木的基期。
- **备注** Scite 只返回前 3 位作者，完整作者表取自 GEE STAC 目录 UMD/hansen/global_forest_change 的 sci:citation

**[76]** Kuang, W., & Dou, Y. (2020). Investigating the patterns and dynamics of urban green space in China's 70 major cities using satellite remote sensing. *Remote Sensing*, *12*(12), 1929. https://doi.org/10.3390/rs12121929

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 用Landsat混合像元分解得到城市绿地分数（UGSF），测算70个大城市2000至2018年的变化：城市绿地面积从2780.66 km²增至6764.75 km²，人均从15.01 m²升至18.09 m²。沿海新扩张区的绿地比例上升，西部城市则下降。
- **证据摘录** the total area of UGS in these cities grew from 2780.66 km2 in 2000 to 6764.75 km2 in 2018, which more than doubled its area. As a result, the UGS area per inhabitant rose from 15.01 m2 in 2000 to 18.09 m2 in 2018.
- **本研究中的用途** 提供遥感口径人均绿地的大城市基线，量纲接近官方人均公园绿地面积，便于对照；其新扩张区与原建成区分解方法可移植到县城。
- **设计采用情况** 已采用，§8.6 的遥感口径基线。

**[77]** Li, X., Gong, P., Zhou, Y., Wang, J., Bai, Y., Chen, B., Hu, T., Xiao, Y., Xu, B., Yang, J., Liu, X., Cai, W., Huang, H., Wu, T., Wang, X., Lin, P., Li, X., Chen, J., He, C., … Zhu, Z. (2020). Mapping global urban boundaries from the global artificial impervious area (GAIA) data. *Environmental Research Letters*, *15*(9), 094044. https://doi.org/10.1088/1748-9326/ab9be3

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 在GAIA基础上，用核密度估计、元胞自动机和形态学膨胀/腐蚀方法，在GEE上生成1990至2018年7个年份的30 m全球城市边界（GUB）。2018年共有65,582个大于1 km²的GUB，总面积809,664 km²，其中约60%为不透水面。
- **证据摘录** We implemented this delineation on the Google Earth Engine platform and generated a 30 m resolution global urban boundary dataset in seven representative years (i.e. 1990, 1995, 2000, 2005, 2010, 2015, and 2018).
- **本研究中的用途** 为县城城关和大城市建成区提供统一的物理边界，替代口径不一的统计建成区面积，用于在城区内部汇总绿地、道路和人口。2000/2010年份可与普查对接；2020年需要用GHSL SMOD补足。
- **设计采用情况** 已采用，§8.1 作为替代边界（需自行上传资产）；主边界用 GHSL 闭运算结果，并以 GHS-SMOD 对照。
- **备注** 共 23 位作者，按 APA 列前 19 位与末位

**[78]** Liu, Z., Tang, H., Feng, L., & Lyu, S. (2023). China Building Rooftop Area: The first multi-annual (2016–2021) and high-resolution (2.5 m) building rooftop area dataset in China derived with super-resolution segmentation from Sentinel-2 imagery. *Earth System Science Data*, *15*(8), 3547–3572. https://doi.org/10.5194/essd-15-3547-2023

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 用超分辨率分割框架STSR-Seg从Sentinel-2生成2016至2021年逐年2.5 m中国建筑屋顶面积（CBRA），这是首套全国全覆盖的多年屋顶数据。城区F1为62.55%，农村召回率为78.94%。作者指出微软、谷歌的大尺度建筑数据不含中国。
- **证据摘录** Then, we produce the multi-annual China Building Rooftop Area (CBRA) dataset with 2.5 m resolution from 2016–2021 Sentinel-2 images. CBRA is the first full-coverage and multi-annual BRA dataset in China.
- **本研究中的用途** 用2016至2021年屋顶面积变化识别县城新增住宅和公共建筑，并与普查住房指标对照。经GEE STAC确认，Google Open Buildings v3只覆盖非洲、拉美、南亚和东南亚，不含中国，因此CBRA、CNBH和GHSL是中国建筑存量的主要来源。
- **设计采用情况** 不采用，CBRA 需自行上传资产，本版用 GHSL 体量估算住宅建筑面积（§8.4）。

**[79]** Pesaresi, M., Schiavina, M., Politis, P., Freire, S., Goch, K., Uhl, J., Carioli, A., Corbane, C., Dijkstra, L., Florio, P., Friedrich, H. K., Gao, J., Leyk, S., Lu, L., Maffenini, L., Mari-Rivero, I., Melchiorri, M., Syrris, V., Van Den Hoek, J., & Kemper, T. (2024). Advances on the Global Human Settlement Layer by joint assessment of Earth Observation and population survey data. *International Journal of Digital Earth*, *17*(1). https://doi.org/10.1080/17538947.2024.2390454

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata) + Consensus abstract; editorial notice = correction (10.1080/17538947.2024.2404284), not retraction
- **核心发现** GHSL 2023版新增10 m亚像元建成面、全球建筑高度与体积、居住/非居住分类，并据此改进人口网格。在100 m分辨率下，建成面MAE约为网格面积的6%，建筑高度MAE为2.27 m，常住人口的总分配精度为83%。
- **证据摘录** It introduces new elements like 10-m-resolution, sub-pixel estimation of built-up surfaces, global building height and volume estimates, and a classification of residential and non-residential areas, improving population density grids.
- **本研究中的用途** GEE中的JRC/GHSL/P2023A（GHS_BUILT_S、GHS_BUILT_H、GHS_BUILT_V、GHS_POP、GHS_SMOD，均已经STAC确认）提供1975至2030年每5年一版的一致序列，是对接2000/2010/2020普查的首选底图。SMOD的城镇化度（Degree of Urbanisation）可以客观划分县城与大城市。居住建筑体积可作为住房存量代理。
- **设计采用情况** 已采用，§8.1 的中心建成区、§8.4 的住宅体量与 GHS-SMOD 质控。

**[80]** Stevens, F. R., Gaughan, A. E., Linard, C., & Tatem, A. J. (2015). Disaggregating census data for population mapping using random forests with remotely-sensed and ancillary data. *PLOS ONE*, *10*(2), e0107042. https://doi.org/10.1371/journal.pone.0107042

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 提出以随机森林估计权重、再做分区密度制图（dasymetric mapping）的半自动方法，把普查人口分配到约100 m网格。这是WorldPop产品的方法基础。
- **证据摘录** We present a new semi-automated dasymetric modeling approach that incorporates detailed census and ancillary data in a flexible, “Random Forest” estimation technique.
- **本研究中的用途** WorldPop/GP/100m/pop（2000至2020）作为人口加权暴露和可达性的分母。本项目掌握分县普查数据，应以普查县级、乡镇街道常住人口对网格做自上而下重标定（top-down rescaling），使网格人口与财政人均口径一致。
- **设计采用情况** 已采用，§7，GHS-POP 普查重标定值作稳健性分母；WorldPop 格网稳健性待 v1.1（§9.6 表 2）。

**[81]** Venter, Z. S., Barton, D. N., Chakraborty, T., Simensen, T., & Singh, G. (2022). Global 10 m land use land cover datasets: A comparison of Dynamic World, World Cover and Esri Land Cover. *Remote Sensing*, *14*(16), 4101. https://doi.org/10.3390/rs14164101

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract + in-text snippets); no editorial notice
- **核心发现** 三套10 m产品在水体、建成区、树木、农田上的面积高度一致，但WorldCover系统性高估草地。以全球样本计，总体精度为Esri 75%、DW 72%、WC 65%；草地类精度只有34%。作者建议用基于设计的面积估计（design-based inference），不要直接数像元。
- **证据摘录** However, relative to one another, WC is biased towards over-estimating grass cover, Esri towards shrub and scrub cover and DW towards snow and ice. Using global ground truth data with a minimum mapping unit of 250 m2, we found that Esri had the highest overall accuracy (75%) compared to DW (72%) and WC (65%).
- **补充证据**（Scite 全文摘录（结果节））Across all the LULC products, water was consistently the most accurately mapped class (balanced accuracy 92%; mean of precision and recall Figure 5), followed by built area (83%), trees (81%) and crops (78%). ... In contrast, bare ground (57%), grass (34%), shrub and scrub (47%) and flooded vegetation (53%) were mapped with the lowest accuracies (Figure 5). ... We also emphasize the importance of not estimating areas from pixel-counting alone but adopting best practices in design-based inference and area estimation
- **本研究中的用途** 本项目的绿地测度应以树木类为主，草地类必须用多产品一致性掩膜。县城城区外围农田、荒草混杂，更容易把草地误计为绿地，从而虚增县城绿地更多的结论。须做分层随机抽样验证。
- **设计采用情况** 已采用，§8.2 以树木为主口径；§8.6 的分层抽样核验与面积校正在 v1.1 广东试点实施。

**[82]** Wang, Y., Huang, C., Feng, Y., Zhao, M., & Gu, J. (2020). Using earth observation for monitoring SDG 11.3.1-ratio of land consumption rate to population growth rate in mainland China. *Remote Sensing*, *12*(3), 357. https://doi.org/10.3390/rs12030357

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 结合CLUD土地利用数据、DMSP/OLS夜光和普查（人口用GWR分解到1 km网格），测算1990至2010年中国SDG 11.3.1。全国LCRPGR从1.69升至1.78，土地消耗率是人口增长率的1.8倍；不协调发展城市从93个（27%）增至186个（54%）。
- **证据摘录** China’s LCRPGR value increased from 1.69 in 1990–2000 to 1.78 in 2000–2010, and the land consumption rate was 1.8 times higher than the population growth rate from 1990 to 2010
- **本研究中的用途** 用SDG 11.3.1（LCRPGR）标准化检验县城建设用地扩张快于常住人口增长。可用GAIA或GHSL加2000/2010/2020普查在县级计算。常住人口负增长时该比值的符号会失真，需单列类别或改用人均建成区面积的变化。
- **设计采用情况** 已采用，§7 表 1 的扩张效率；人口负增长时不计算 SDG 11.3.1。

**[83]** Wu, S., Chen, B., Webster, C., Xu, B., & Gong, P. (2023). Improved human greenspace exposure equality during 21st century urbanization. *Nature Communications*, *14*. https://doi.org/10.1038/s41467-023-41620-z

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract + in-text snippets); no editorial notice
- **核心发现** 用Landsat 30 m绿地时序和人口加权暴露框架，测算全球1028个城市2000至2018年的变化。结果是绿地覆盖和暴露普遍上升、暴露不平等下降，南方城市不平等的下降速度约为北方的4倍。作者在正文中把绿地看作需求随收入上升的优等品（superior economic good）。
- **证据摘录** Results show a substantial increase in physical greenspace coverage and an improvement in human exposure to urban greenspace, leading to a reduction in greenspace exposure inequality over the past two decades.
- **本研究中的用途** 提供2000至2018年时序方法，可与2000/2010/2020三次普查对齐，检验县城在转移支付支持下的绿化增速是否快于大城市。优等品的说法可以作为财政能力与绿化供给之间的理论桥梁。
- **设计采用情况** 已采用，§2.5；绿地时序待 CLCD 接入后实现（§8.2）。

**[84]** Wu, W., Ma, J., Banzhaf, E., Meadows, M. E., Yu, Z., Guo, F., Sengupta, D., Cai, X.-X., & Zhao, B. (2023). A first Chinese building height estimate at 10 m resolution (CNBH-10 m) using multi-source earth observations and machine learning. *Remote Sensing of Environment*, *291*, 113578. https://doi.org/10.1016/j.rse.2023.113578

- **依据类别** Consensus 摘要
- **核验途径** Scite DOI lookup (metadata only) + Consensus abstract (truncated)
- **核心发现** 用雷达、光学等全天候对地观测数据和机器学习，估算2020年中国10 m分辨率建筑高度（CNBH-10 m）。Consensus返回的摘要被截断，精度数值未取得。
- **证据摘录** We describe an approach to estimate 2020 building height for China at 10 m spatial resolution based on all-weather earth observations (radar, optical [Consensus abstract truncated here]
- **本研究中的用途** 与CBRA屋顶面积相乘得到县、区建筑体积和容积率代理，再与2020普查的人均住房面积对照，检验县城住房过度供给、大城市住房紧张。该数据需自行上传为GEE资产。
- **设计采用情况** 不采用，CNBH-10 m 需自行上传资产，本版用 GHSL 体量（§8.4）。

**[85]** Yang, J., & Huang, X. (2021). The 30 m annual land cover dataset and its dynamics in China from 1990 to 2019. *Earth System Science Data*, *13*(8), 3907–3925. https://doi.org/10.5194/essd-13-3907-2021

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 元数据与摘要（2026-09-26 核验）；Scite 未返回编辑通知
- **核心发现** 基于 GEE 上 335 709 景 Landsat 影像与随机森林分类，生成中国首套 Landsat 30 m 年度土地覆盖数据集 CLCD（1990 至 2019 年）；5 463 个目视解译样本的总体精度为 79.31%，5 131 个第三方样本的检验优于 MCD12Q1、ESACCI_LC、FROM_GLC 与 GlobeLand30；与全球森林变化、全球地表水和三套不透水面产品一致性良好。1985 至 2019 年不透水面增加 148.71%，森林增加 4.34%，耕地与草地减少。
- **证据摘录** we produced the first Landsat-derived annual China land cover dataset (CLCD) on the Google Earth Engine (GEE) platform, which contains 30 m annual LC and its dynamics in China from 1990 to 2019 ... Finally, the overall accuracy of CLCD reached 79.31 % based on 5463 visually interpreted samples.
- **本研究中的用途** 在固定的 2020 年中心建成区内计算历年森林、灌木、草地与不透水面，识别由耕地、裸地或不透水面转来的新增绿地，使绿地也能做长差分。论文版止于 2019 年；GEE 社区目录路径与更新版年份需核验后在 config 的 gee.clcd_asset_template 中启用。
- **设计采用情况** 已采用，§2.5 与 §8.2，可选接入；GEE 社区目录路径核验前不启用。
- **备注** 数据集本身存于 Zenodo（10.5281/zenodo.4417810）；GEE 社区目录路径未核验

**[86]** Zhao, J., Chen, S., Jiang, B., Ren, Y., Wang, H., Vause, J., & Yu, H. (2013). Temporal trend of green space coverage in China and its relationship with urbanization over the last two decades. *Science of the Total Environment*, *442*, 455–465. https://doi.org/10.1016/j.scitotenv.2012.10.014

- **依据类别** Scite 摘要
- **核验途径** Scite DOI lookup (metadata + abstract); no editorial notice
- **核心发现** 基于286个城市1989至2009年的城市层面数据，建成区绿地覆盖率平均从17.0%稳步升至37.3%。刻画城市化的9个变量中有8个与覆盖率显著正相关，人均GDP的独立贡献最大（24.2%）；绿地覆盖更多反映城市化效应，而非气候或地理因素。
- **证据摘录** average green space coverage of cities investigated increased steadily from 17.0% in 1989 to 37.3% in 2009 [...] with 'per capita GDP' having the highest independent contribution (24.2%)
- **本研究中的用途** 作为官方统计口径建成区绿化覆盖率的历史基准，用来和遥感口径（树木覆盖、人口加权暴露）对照，量化统计口径偏差。统计口径以建成区为分母并包含附属绿地，其趋势可能与遥感结果背离。
- **设计采用情况** 已采用，§8.6 的统计口径基准。

## A.5 识别策略与空间方法

**[87]** Anselin, L. (1995). Local indicators of spatial association—LISA. *Geographical Analysis*, *27*(2), 93–115. https://doi.org/10.1111/j.1538-4632.1995.tb00338.x

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 查询（元数据与摘要）
- **核心发现** 提出局部空间关联指标（LISA）这一类统计量，可把全局 Moran's I 分解为各观测的贡献，用于识别局部集聚（hot spots）和空间异常值（outliers），并采用条件置换（conditional permutation）推断。
- **证据摘录** I outline a new general class of local indicators of spatial association (LISA) and show how they allow for the decomposition of global indicators, such as Moran's I, into the contribution of each observation.
- **本研究中的用途** 对县级转移支付依赖度 × 人均公共品做双变量 LISA，识别 HH/LL/HL/LH 集聚（例如西部生态功能区的高转移–高绿地），据此设定空间分区（spatial regimes）和回归残差诊断；多重检验用 FDR 校正。
- **设计采用情况** 待 v2.0 之后，双变量 LISA 与 1 km 格网尺度检验一起实现（§9.1）。

**[88]** Callaway, B., & Sant’Anna, P. H. C. (2021). Difference-in-differences with multiple time periods. *Journal of Econometrics*, *225*(2), 200–230. https://doi.org/10.1016/j.jeconom.2020.12.001

- **依据类别** 仅引文片段（他文）
- **核验途径** Scite DOI 查询（元数据；无摘要）。依据取自 Gil-Ocana et al. 2026 预印本中的 Scite Smart Citation 与全文摘录（doi:10.21203/rs.3.rs-9498631/v1）
- **核心发现** 提出组别-时期平均处理效应 ATT(g,t) 估计框架：按首次处理时点分组（cohort），只与干净对照（如从未处理组 never-treated）比较，从而处理时点异质与效应异质问题。另提供双重稳健（doubly robust）估计量。
- **证据摘录** Callaway and Sant'Anna (2021) propose a grouptime estimator that explicitly accounts for treatment timing heterogeneity and restricts comparisons to never-treated firms, providing a more credible identification strategy in exactly these settings.
- **本研究中的用途** 作为撤县设区准实验的主估计量。面板单元为按 2020 年边界固定的县级单元，cohort 为撤县设区批复年份；对照组为同省（或同一地级市外圈）从未或尚未撤县设区的县；协变量取 2000 年普查基期特征，采用 DR 估计。
- **设计采用情况** 已采用，§9.5 省直管县主设计的估计量（v1.1）；撤县设区不再作为首选设计。

**[89]** de Chaisemartin, C., & D’Haultfœuille, X. (2020). Two-way fixed effects estimators with heterogeneous treatment effects. *American Economic Review*, *110*(9), 2964–2996. https://doi.org/10.1257/aer.20181169

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 查询（元数据与摘要）
- **核心发现** TWFE 回归估计的是各组-时期平均处理效应的加权和，权重可能为负。因此即便所有组-时期效应都为正，回归系数仍可能为负。作者提出了替代估计量。
- **证据摘录** We show that they estimate weighted sums of the average treatment effects (ATE ) in each group and period, with weights that may be negative. Due to the negative weights, the linear regression coefficient may for instance be negative while all the ATEs are positive.
- **本研究中的用途** 适用于非吸收型处理（贫困县名单可进可出，如 2011 年名单调整）以及连续型转移支付依赖度面板回归。报告负权重份额，并用 DID_M 类估计量作稳健性检验。
- **设计采用情况** 已采用，§9.5 的负权重诊断（v1.1）。

**[90]** Fotheringham, A. S., & Wong, D. W. S. (1991). The modifiable areal unit problem in multivariate statistical analysis. *Environment and Planning A*, *23*(7), 1025–1044. https://doi.org/10.1068/a231025

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 查询（元数据与摘要；作者姓名按 Scite 返回原样照录）
- **核心发现** 可变面积单元问题（MAUP）在多元线性回归和 logit 模型中同样存在：参数估计随尺度（scale）和分区（zoning）变化，且变化强度与方向不可预测，比单变量或双变量分析中更严重。
- **证据摘录** The modifiable areal unit problem is shown to be essentially unpredictable in its intensity and effects in multivariate statistical analysis and is therefore a much greater problem than in univariate or bivariate analysis.
- **本研究中的用途** 县级单元面积差异极大（西部大县对东部市辖区），全县人均公共品会被农村腹地稀释。主回归须在全县、城区建成区、1 km 格网、15 分钟生活圈四个尺度重复，并报告系数的稳定性。
- **设计采用情况** 已采用，单元全域与中心建成区两个尺度；1 km 格网与生活圈尺度待 v2.0 之后（§9.6 表 2）。

**[91]** Goodman-Bacon, A. (2021). Difference-in-differences with variation in treatment timing. *Journal of Econometrics*, *225*(2), 254–277. https://doi.org/10.1016/j.jeconom.2021.03.014

- **依据类别** 仅引文片段（他文）
- **核验途径** Scite DOI 查询（元数据；无摘要或全文）。依据取自 Araújo, Bayma & Melo 2021 中的 Scite Smart Citation（doi:10.12660/bre.v40n22020.81749），其引用的是该文 2018 年 NBER 工作论文版本 (w25018)
- **核心发现** 处理时点交错（staggered adoption）时，双向固定效应（TWFE）DiD 估计量等于数据中所有 2×2 DiD 比较的加权平均。已处理组会在部分比较中充当对照组，因此处理效应随时间变化时估计有偏。
- **证据摘录** In this environment, the DD estimator represents a weighted average of all 2 × 2 estimators in the data, and thus all groups can be control units in some of the weighted estimates, and not just the group never treated.
- **本研究中的用途** 撤县设区、省直管县（PMC）、贫困县摘帽都是交错处理。先用 Goodman-Bacon 分解（bacon decomposition）诊断 TWFE 权重中早处理对晚处理比较（forbidden comparisons）所占份额，以此说明主估计为何不用 TWFE。
- **设计采用情况** 已采用，§9.5 的分解诊断（v1.1）。

**[92]** Huang, K., & You, Y. (2025). Evaluating the impact of the fourth round of China's poverty alleviation program. *American Journal of Agricultural Economics*, *107*(2), 583–610. https://doi.org/10.1111/ajae.12495

- **依据类别** Scite 摘要
- **核验途径** Scite 按主题检索后读取记录（元数据、摘要与全文摘录）
- **核心发现** 第四轮扶贫覆盖 14 个连片特困区（contiguous destitute areas）、680 个县，2012至2019 年投入 8136 亿元。DiD 与断点差分（difference-in-discontinuities）估计显示，项目使片区人均 GDP 提高 45% 以上。片区依据 2008至2010 年人均 GDP、人均一般预算收入和农民人均纯收入三项指标划定。
- **证据摘录** Using county‐level data from 2006 to 2019, our difference‐in‐differences and difference‐in‐discontinuities estimates suggest that the program increased GDP per capita in the 14 areas by over 45% from 2012 to 2019, with substantial gains observed in both the agricultural and nonagricultural sectors.
- **本研究中的用途** 这是与本项目最接近的准实验模板：片区边界构成转移支付强度的空间断点。复制其 difference-in-discontinuities 设定，把结果变量换成遥感公园、绿道、道路密度与普查常住人口变化，检验转移支付→公共品更多、人口仍流失。
- **设计采用情况** 已采用，§9.5，沿用片区边界，改为相邻县对双重差分（v2.0）。
- **备注** Scite 记录年份为 2024（在线）

**[93]** Keele, L. J., & Titiunik, R. (2015). Geographic boundaries as regression discontinuities. *Political Analysis*, *23*(1), 127–155. https://doi.org/10.1093/pan/mpu014

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 查询（元数据、摘要与 Smart Citations）
- **核心发现** 提出地理断点设计（geographic regression discontinuity, GRD）：行政或地理边界把单元分成处理区和对照区，等价于有两个运行变量（running variables）的 RD。作者给出基于到边界距离的局部多项式估计，并用处理前协变量平衡检验识别假设；推断须考虑空间相关。
- **证据摘录** In this design, which we call the Geographic Regression Discontinuity (GRD) design, a geographic or administrative boundary splits units into treated and control areas... We show how this design is equivalent to a standard RD with two running variables
- **本研究中的用途** 在新市辖区–相邻未撤县边界和连片特困区边界两侧，用 100 m–1 km 栅格遥感指标（公园绿地、绿道、道路密度、建成区）做 GRD。县界上多种政策同时跳变（复合处理，compound treatment），因此只采用撤县设区前后差分的 difference-in-discontinuities 形式。
- **设计采用情况** 待 v2.0，撤县设区边界的地理断点保留为补充设计（§9.5）；连片特困地区改用边界县对。

**[94]** Li, J., Yang, B., & Quan, T. (2026). Administrative-led urbanisation and migrants' settlement intention: Evidence from the city–county merger policy in China. *Population, Space and Place*, *32*(5). https://doi.org/10.1002/psp.70326

- **依据类别** Scite 摘要
- **核验途径** Scite 检索后读取记录（元数据与摘要；Scite 只列出前 3 位作者；未返回页码）
- **核心发现** 利用 2010至2018 年流动人口动态监测调查（CMDS）并匹配县级统计，准实验发现撤县设区（city–county merger）显著提高流动人口定居意愿和身份认同。渠道有三：扩大住房供给、改善可负担性；提供更高质量就业；提升教育、交通等公共服务的可达性与质量。
- **证据摘录** Our mechanism analyses reveal that the policy operates through three channels: by expanding housing supply and improving affordability, by creating higher‐quality employment opportunities, and by enhancing the accessibility and quality of public services, especially in education and transportation.
- **本研究中的用途** 与住房、社会基础设施议题直接相关：县从转移支付型财政并入城市整合型财政后，人口流入与住房压力如何变化。本项目用 2010至2020 普查常住人口和住房变量（人均住房面积、租赁比例）检验同一机制。
- **设计采用情况** 已采用，§9.5 撤县设区住房与公共服务机制的先验。

**[95]** Meng, L. (2013). Evaluating China's poverty alleviation program: A regression discontinuity approach. *Journal of Public Economics*, *101*, 1–11. https://doi.org/10.1016/j.jpubeco.2013.02.004

- **依据类别** 仅引文片段（他文）
- **核验途径** Scite DOI 查询（仅元数据，无摘要）。依据取自 Niu, Lugo & Yemtsov 2021（世界银行政策研究工作论文，doi:10.1596/1813-9450-9849）中的 Scite Smart Citation 与全文摘录，并由 Huang & You 2024 的全文摘录佐证。注意：简报中“2001–2010 年项目”的描述有误
- **核心发现** 用断点回归（RD）评估八七扶贫攻坚计划（1994至2000 年，592 个贫困县），结果是受益县农村收入约提高 38%。
- **证据摘录** Meng (2013), using regression discontinuity design, finds that the 8-7 National Plan for Poverty Reduction (1994Reduction ( -2000 resulted in an approximately 38 percent increase in rural income for counties that were treated between 1994 and 2000.
- **本研究中的用途** 贫困县身份是转移支付依赖最经典的规则性来源。沿用其以认定门槛处基期收入为运行变量的模糊 RD（fuzzy RD）思路，检验历史认定对 2010、2020 年普查人口和遥感公共品存量的长期效应（persistence）。
- **设计采用情况** 已采用，§9.5 的参照；模糊断点不采用，县级运行变量过粗，改用边界县对。
- **备注** 评估对象为 1994 至 2000 年八七扶贫攻坚计划

**[96]** Mennis, J. (2003). Generating surface models of population using dasymetric mapping. *The Professional Geographer*, *55*(1), 31–42. https://doi.org/10.1111/0033-0124.10042

- **依据类别** 仅引文片段（他文）
- **核验途径** Scite DOI 查询（元数据；摘要为空）。依据取自 Maantay & Maroko 2009 中的 Scite Smart Citation 与全文摘录（doi:10.1016/j.apgeog.2008.08.002）
- **核心发现** 用分区密度制图（dasymetric mapping）生成人口表面模型：借助辅助数据（如遥感土地覆被）把普查汇总人口分解到更细的空间单元。具体算法细节未能从 Scite 获取。
- **证据摘录** The underlying concept of dasymetric mapping involves the process of disaggregating spatial data to a finer unit of analysis, using additional (or “ancillary”) data to help refine locations of population or other phenomena being mapped (Mennis, 2003).
- **本研究中的用途** 把 2010/2020 普查的县级（或乡镇街道级）常住人口按建成区、不透水面等辅助权重分配到格网，总量约束回普查值，得到城区人口分母。用它计算人均公园面积和绿道 500 m 覆盖人口比例，并与 WorldPop、GHS-POP 做敏感性对照。
- **设计采用情况** 已采用，§7，GHS-POP 普查重标定值作稳健性分母；主分母改为官方中心建成区人口。

**[97]** Park, A., Wang, S., & Wu, G. (2002). Regional poverty targeting in China. *Journal of Public Economics*, *86*(1), 123–153. https://doi.org/10.1016/s0047-2727(01)00108-6

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 查询（元数据与摘要）
- **核心发现** 基于 1981至1995 年全国县级面板：贫困县认定和扶贫资金分配受政治因素影响，漏出（leakage）增加，同时覆盖面改善。认定使人均收入在 1985至1992 年每年提高 2.28%，1992至1995 年每年提高 0.91%。
- **证据摘录** Estimates of models of poor county designation and poverty fund allocation and newly defined targeting gap and targeting error measures show that political factors have affected targeting and that leakage has increased while coverage has improved.
- **本研究中的用途** 这是贫困县 RD 的核心威胁证据：认定并非纯按规则进行。因此必须按模糊 RD 处理，并做密度（操纵）检验和门槛处协变量平衡检验；同时提示应把政治联系类变量作为控制或异质性维度。
- **设计采用情况** 已采用，§9.5，边界两侧的基期平衡检验（v2.0）。

**[98]** Rambachan, A., & Roth, J. (2023). A more credible approach to parallel trends. *The Review of Economic Studies*, *90*(5), 2555–2591. https://doi.org/10.1093/restud/rdad018

- **依据类别** Scite 摘要
- **核验途径** Scite DOI 查询（元数据与摘要）
- **核心发现** 不要求平行趋势严格成立，而是限制处理后偏离可比处理前趋势（pre-trends）大多少。在此约束下因果参数为部分识别（partial identification），并可给出一致有效的推断和敏感性分析。
- **证据摘录** Instead of requiring that parallel trends holds exactly, we impose restrictions on how different the post-treatment violations of parallel trends can be from the pre-treatment differences in trends (“pre-trends”). The causal parameter of interest is partially identified under these restrictions.
- **本研究中的用途** 2010至2020 长差分只有一个前期差分（2000至2010 普查），用相对幅度（relative magnitudes）约束报告：平行趋势偏离达到多大时结论仍然成立。撤县设区事件研究同样附 HonestDiD 敏感性区间。
- **设计采用情况** 待 v1.1，§9.4 的相对幅度约束需要处理前的差分期，1990 至 2000 年 GAIA 与 1990 年普查人口接入后实施。

**[99]** Sun, L., & Abraham, S. (2021). Estimating dynamic treatment effects in event studies with heterogeneous treatment effects. *Journal of Econometrics*, *225*(2), 175–199. https://doi.org/10.1016/j.jeconom.2020.09.006

- **依据类别** 仅引文片段（他文）
- **核验途径** Scite DOI 查询（元数据；无摘要）。依据取自 Scite 在 doi:10.1257/aer.20181169 名下索引、指向 10.1016/j.jeconom.2020.09.006 的 Smart Citation
- **核心发现** 在含多个相对期虚拟变量的事件研究（event-study）TWFE 回归中，其他相对期的处理效应会污染（contaminate）某一相对期的系数，预趋势检验和动态效应的解读因此失真。
- **证据摘录** The contamination phenomenon in Theorem 1 is similar to the one first discovered by Sun and Abraham (2020) in the context of event-study regressions, where effects of being treated for ℓ ′ periods may contaminate the coefficient supposed to measure the effect of ℓ periods of treatment
- **补充证据**（他文全文摘录（Dahl & Hernaes, 2022, SSRN 10.2139/ssrn.4114730，经 Scite 取回））In our case, with staggered, absorbing adoption of a binary treatment, no control variables and a never-treated control group, the "interaction-weighted" estimator proposed by Sun & Abraham (2021) gives the same post-treatment estimates as the estimator in Callaway & Sant'Anna (2021).
- **本研究中的用途** 撤县设区和贫困县摘帽的动态效应图不用普通 TWFE 事件研究，改用按 cohort 交互加权的估计（interaction-weighted），并与 Callaway–Sant'Anna 的事件研究聚合结果并列报告。
- **设计采用情况** 已采用，§9.5 的动态效应与附录F 的撤县设区事件研究（v1.1）。

## A.6 数据集引文

以下数据集引文取自 GEE 官方 STAC 目录的 sci:citation 字段。

- Zanaga, D., Van De Kerchove, R., De Keersmaecker, W., Souverijns, N., Brockmann, C., Quast, R., Wevers, J., Grosu, A., Paccini, A., Vergnaud, S., Cartus, O., Santoro, M., Fritz, S., Georgieva, I., Lesiv, M., Carter, S., Herold, M., Li, L., Tsendbazar, N.-E., … Arino, O. (2021). *ESA WorldCover 10 m 2020 v100* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.5571936
- Zhao, C., Cao, X., Chen, X., & Cui, X. (2020). *A consistent and corrected nighttime light dataset (CCNL 1992–2013) from DMSP-OLS data* (Version 1.0) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.6644980

## A.7 已检索但未收录的文献

各主题代理检索到但未能完成核验（DOI 与记录不符、无摘要可依据、仅见于工作论文或只见于 Consensus 而 Scite 无记录）的候选文献，列在 `附录/附录A_未收录候选文献.md`，供后续迭代补核。
