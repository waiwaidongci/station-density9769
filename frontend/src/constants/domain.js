export const domain = {
  "id": "gb-0042",
  "direction": "聚类分析",
  "title": "河砾微站密度巡检图",
  "slug": "station-density",
  "algorithm": "density",
  "entities": "Survey / StationReading / DensityRun / VisitPlan",
  "scenario": "微站环境特征→密度聚类→复访计划；DBSCAN不是地理热点显著性",
  "visual": "地形勘测图、苔绿",
  "oracle": "手工核心/边界/噪声例；对sklearn标签等价；eps与min_samples验证",
  "frontend": 18246,
  "backend": 19246,
  "db_port": 17746,
  "database": "PostgreSQL16",
  "batch": 1,
  "code": "HL",
  "source": "巡测专题",
  "record": "微站观测",
  "note": "复访计划",
  "source_table": "surveys",
  "record_table": "station_readings",
  "run_table": "density_runs",
  "note_table": "visit_plans",
  "eyebrow": "FIELD CONTOURS / 42",
  "headline": "让相似微站，自然连成一片。",
  "subtitle": "河砾微站协作组 · 环境特征密度分区与噪声复访",
  "fields": [
    [
      "temperature",
      "温度 ℃",
      "number"
    ],
    [
      "humidity",
      "相对湿度 %",
      "number"
    ],
    [
      "particles",
      "颗粒浓度 μg/m³",
      "number"
    ]
  ],
  "params": [
    [
      "eps",
      "标准化邻域半径 ε",
      0.55
    ],
    [
      "min_samples",
      "核心点最少邻居数",
      5
    ]
  ],
  "sample": {
    "temperature": 23.2,
    "humidity": 56,
    "particles": 32
  },
  "seed_count": 240,
  "ink": "oklch(29% .05 140)",
  "accent": "oklch(53% .11 120)",
  "paper": "oklch(94% .026 95)",
  "principle": "每个特征先标准化，再按密度连通分区；噪声标签表示稀疏样本，不等同污染或地理热点显著性。",
  "default_parameters": {
    "eps": 0.55,
    "min_samples": 5
  },
  "method_label": "标准化DBSCAN、噪声比例与邻域连通簇解释",
  "result_headline": "读懂密度分区，也看到稀疏微站。",
  "column_labels": {
    "reference": "样本编号",
    "actual": "实际类型",
    "predicted": "预测类型",
    "posterior": "最高类后验",
    "cluster": "分区编号",
    "kind": "微站类型",
    "temperature": "温度 ℃",
    "humidity": "湿度 %",
    "particles": "颗粒浓度",
    "from": "当前章节",
    "to": "下一章节",
    "count": "接续次数",
    "conditional_probability": "条件概率",
    "target_base_rate": "目标章节基率",
    "lift": "提升度",
    "support": "边支持度",
    "actual_minutes": "实测时长 min",
    "predicted_minutes": "预测时长 min",
    "error_minutes": "预测误差 min",
    "visitor": "匿名访客",
    "exhibit": "展品编号",
    "prediction": "预计评分",
    "method": "计算依据",
    "neighbor_count": "参与邻居数"
  }
};
