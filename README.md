# get-data-from-gee

## HKU Library 论文抓取脚本（上海风貌别墅）

仓库里新增了一个基于 Playwright 的脚本，用于从 HKU Library（Primo 检索页）抓取关键词检索结果。

### 1) 安装依赖

```bash
pip install playwright
python -m playwright install chromium
```

### 2) 运行抓取

```bash
python scripts/scrape_hku_library.py \
  --query "上海 风貌 别墅" \
  --pages 3 \
  --output data/hku_shanghai_villa.csv
```

参数说明：
- `--query`: 检索词
- `--pages`: 抓取页数（每页约 10 条）
- `--output`: 输出文件，支持 `.csv` 或 `.json`
- `--headed`: 打开有头浏览器（调试用）

### 3) 输出字段

- `query`
- `title`
- `creators`
- `year`
- `material_type`
- `link`
- `offset`

> 说明：HKU Library 页面是前端动态渲染，直接 `curl` 往往拿不到结果列表，因此脚本采用浏览器自动化方式。
