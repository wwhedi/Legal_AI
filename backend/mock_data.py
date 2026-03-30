from datetime import datetime


MOCK_REGULATIONS = [
    {
        "law_id": "civil_code_585",
        "law_name": "民法典",
        "article": "第585条第2款",
        "law_level": "法律",
        "status": "现行有效",
        "effective_date": "2021-01-01",
        "content": "约定的违约金过分高于造成的损失的，当事人可以请求人民法院或者仲裁机构予以适当减少。",
        "keywords": ["违约金", "损失", "调整"],
    },
    {
        "law_id": "civil_code_497",
        "law_name": "民法典",
        "article": "第497条",
        "law_level": "法律",
        "status": "现行有效",
        "effective_date": "2021-01-01",
        "content": "提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利的，该条款无效。",
        "keywords": ["格式条款", "免责", "无效"],
    },
    {
        "law_id": "contract_interp_65",
        "law_name": "合同编通则解释",
        "article": "第65条",
        "law_level": "司法解释",
        "status": "现行有效",
        "effective_date": "2021-01-01",
        "content": "关于违约金调整，应综合合同履行情况、当事人过错程度和预期利益等因素认定。",
        "keywords": ["违约金", "司法解释", "调整"],
    },
    {
        "law_id": "uav_temp_18",
        "law_name": "无人驾驶航空器飞行管理暂行条例",
        "article": "第18条",
        "law_level": "行政法规",
        "status": "现行有效",
        "effective_date": "2024-01-01",
        "content": "在管制空域内飞行应当依法申请批准。",
        "keywords": ["无人机", "审批", "空域"],
    },
]


MOCK_CHANGE_RECORDS = [
    {
        "change_id": "chg_001",
        "detected_at": datetime.now().isoformat(),
        "source": "national_law_db",
        "law_id": "civil_code_585",
        "law_name": "民法典",
        "change_type": "amended",
        "change_summary_ai": "违约金调整条款解释增加了审查因素说明。",
        "impact_analysis": {"citing_articles_count": 23, "severity": "high"},
        "review_status": "pending_review",
    },
    {
        "change_id": "chg_002",
        "detected_at": datetime.now().isoformat(),
        "source": "pkulaw_mcp",
        "law_id": "uav_temp_18",
        "law_name": "无人驾驶航空器飞行管理暂行条例",
        "change_type": "new",
        "change_summary_ai": "新增城市上空飞行审批要求细则。",
        "impact_analysis": {"citing_articles_count": 4, "severity": "medium"},
        "review_status": "pending_review",
    },
]
