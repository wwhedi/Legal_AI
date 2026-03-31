import type { Citation, PendingRegulationViewItem, RiskAssessment } from "@/types";

export const DEMO_QA_QUESTION = "自动续约条款在企业服务合同中如何满足合规要求？";

export const DEMO_QA_ANSWER =
  "自动续约条款并非当然无效，但需要满足显著提示、续约前提醒与退出机制等合规要求。" +
  "建议在合同中明确续约触发条件、续约通知时间窗口、费用变更提示机制，并保留无责退出路径[1]。" +
  "若涉及单方解除或格式条款限制，还应核对解除条件与公平原则，避免条款失衡引发争议[2]。";

export const DEMO_QA_CITATIONS: Citation[] = [
  {
    ref_id: "[1]",
    law_name: "民法典",
    article: "496",
    status: "effective",
    score: 0.93,
  },
  {
    ref_id: "[2]",
    law_name: "民法典",
    article: "563",
    status: "effective",
    score: 0.88,
  },
];

export const DEMO_QA_CITATION_DETAILS: Record<
  string,
  { law_name: string; article: string; status: "Verified" | "Unverified"; excerpt: string }
> = {
  "[1]": {
    law_name: "《民法典》",
    article: "第496条",
    status: "Verified",
    excerpt:
      "提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理方式提示对方注意与其有重大利害关系的条款。",
  },
  "[2]": {
    law_name: "《民法典》",
    article: "第563条",
    status: "Verified",
    excerpt:
      "当事人可以在法定或约定解除条件成就时解除合同。建议在合同中明确解除触发条件及通知机制，防止单方任意解除。",
  },
};

export const DEMO_REGULATION_ROWS: PendingRegulationViewItem[] = [
  {
    id: "demo-reg-2026-dsl-amendment",
    regulation_id: "dsl_2026_amendment_draft",
    regulation_title: "2026年数据安全法修正案（示范稿）",
    summary:
      "新增“高敏数据分级分类”和“跨境传输场景化评估”要求，强化企业数据处理审计留痕。",
    status: "pending_review",
    created_at: "2026-03-20T08:00:00Z",
    updated_at: "2026-03-28T10:30:00Z",
    uiStatus: "pending_review",
    diff: {
      oldText:
        "第28条：数据处理者开展跨境数据传输，应按照有关规定进行备案。\n" +
        "第31条：数据安全管理制度由企业根据业务需要自行制定。",
      newText:
        "第28条：高敏数据跨境传输应进行场景化合规评估，并保留完整审计记录。\n" +
        "第31条：数据处理者应建立分级分类管理制度，明确最小必要、访问控制与责任追溯机制。",
      aiSummary:
        "修订重点为“备案制”升级为“评估+审计留痕”，并引入分级分类治理要求。企业需补齐跨境传输评估流程、权限矩阵和审计证据链。",
    },
  },
];

export const DEMO_REVIEW_CONTRACT_TEXT =
  "第1条 自动续约\n本合同到期后自动续约一年，乙方未在到期前30日提出异议视为同意。\n\n" +
  "第2条 单方解除\n甲方可在认为乙方服务质量不达标时立即解除合同且无需承担任何责任。\n\n" +
  "第3条 免责条款\n甲方对于系统故障、数据丢失及由此产生的全部损失不承担任何责任。\n\n" +
  "第4条 通知\n双方通知可采用电子邮件，但送达生效时间由甲方单方认定。";

export const DEMO_REVIEW_RISK: RiskAssessment = {
  summary: "高风险合同案例（Demo）",
  high_risks: [
    {
      risk_id: "HR-001",
      clause_id: "C2",
      title: "单方解除权过宽",
      reason: "甲方可在主观判断条件下即时解除且免责，存在明显权利义务失衡。",
      suggestion: "补充客观触发条件、整改期限、提前通知和违约责任分配。",
    },
  ],
  medium_risks: [
    {
      risk_id: "MR-001",
      clause_id: "C4",
      title: "通知送达条款不清晰",
      reason: "送达生效由一方单方认定，存在争议风险。",
      suggestion: "明确送达方式、回执规则与生效时间点。",
    },
  ],
  low_risks: [],
};

