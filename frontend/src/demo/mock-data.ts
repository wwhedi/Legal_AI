import type { Citation, PendingRegulationViewItem, RiskAssessment } from "@/types";
import { sanitizeAssistantAnswerText } from "@/lib/assistant-text";

/** Demo 对话场景：每条提问对应独立回答与引用（用于 /chat?demo=true 测试） */
export type DemoChatCitationDetail = {
  law_name: string;
  article: string;
  status: "Verified" | "Unverified";
  evidence_status_display?: string;
  excerpt: string;
};

export type DemoChatScenario = {
  id: string;
  question: string;
  answer: string;
  citations: Citation[];
  citationDetails: Record<string, DemoChatCitationDetail>;
};

export const DEMO_CHAT_SCENARIOS: DemoChatScenario[] = [
  {
    id: "auto-renewal",
    question: "自动续约条款在企业服务合同中如何满足合规要求？",
    answer:
      "自动续约条款并非当然无效，但需要满足显著提示、续约前提醒与退出机制等合规要求。" +
      "建议在合同中明确续约触发条件、续约通知时间窗口、费用变更提示机制，并保留无责退出路径。[1]" +
      "若涉及单方解除或格式条款限制，还应核对解除条件与公平原则，避免条款失衡引发争议。[2]",
    citations: [
      {
        ref_id: "[1]",
        law_name: "民法典",
        article: "496",
        status: "valid",
        status_display: "【有效】",
        score: 0.93,
        verified: true,
        verify_source: "retrieved_context",
      },
      {
        ref_id: "[2]",
        law_name: "民法典",
        article: "563",
        status: "revised",
        status_display: "【已修改】",
        score: 0.88,
        verified: true,
        verify_source: "retrieved_context",
      },
    ],
    citationDetails: {
      "[1]": {
        law_name: "《民法典》",
        article: "第496条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt:
          "提供格式条款的一方应当遵循公平原则确定当事人之间的权利和义务，并采取合理方式提示对方注意与其有重大利害关系的条款。",
      },
      "[2]": {
        law_name: "《民法典》",
        article: "第563条",
        status: "Verified",
        evidence_status_display: "【已修改】",
        excerpt:
          "当事人可以在法定或约定解除条件成就时解除合同。建议在合同中明确解除触发条件及通知机制，防止单方任意解除。",
      },
    },
  },
  {
    id: "labor-compensation",
    question: "用人单位解除劳动合同的经济补偿金如何计算？",
    answer:
      "经济补偿按劳动者在本单位工作的年限计算：每满一年支付一个月工资；六个月以上不满一年的按一年计；不满六个月的支付半个月工资。[1]" +
      "月工资指解除或终止前十二个月的平均工资；若高于当地社平工资三倍的，补偿年限最高不超过十二年。[2]",
    citations: [
      {
        ref_id: "[1]",
        law_name: "劳动合同法",
        article: "47",
        status: "valid",
        status_display: "【有效】",
        score: 0.91,
        verified: true,
        verify_source: "retrieved_context",
      },
      {
        ref_id: "[2]",
        law_name: "劳动合同法",
        article: "47",
        status: "valid",
        status_display: "【有效】",
        score: 0.87,
        verified: true,
        verify_source: "retrieved_context",
      },
    ],
    citationDetails: {
      "[1]": {
        law_name: "《劳动合同法》",
        article: "第47条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt: "经济补偿按劳动者在本单位工作的年限，每满一年支付一个月工资的标准向劳动者支付。",
      },
      "[2]": {
        law_name: "《劳动合同法》",
        article: "第47条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt:
          "劳动者月工资高于用人单位所在直辖市、设区的市级人民政府公布的本地区上年度职工月平均工资三倍的，向其支付经济补偿的标准按职工月平均工资三倍的数额支付，向其支付经济补偿的年限最高不超过十二年。",
      },
    },
  },
  {
    id: "pipd-lawful-basis",
    question: "处理个人信息需要具备哪些合法性基础？",
    answer:
      "处理个人信息应当具有明确、合理的目的，并遵循合法、正当、必要和诚信原则。[1]" +
      "合法性基础包括取得个人同意、为订立或履行合同所必需、履行法定职责或法定义务、应对突发公共卫生事件等法律列举情形。[2]",
    citations: [
      {
        ref_id: "[1]",
        law_name: "个人信息保护法",
        article: "6",
        status: "valid",
        status_display: "【有效】",
        score: 0.9,
        verified: true,
        verify_source: "retrieved_context",
      },
      {
        ref_id: "[2]",
        law_name: "个人信息保护法",
        article: "13",
        status: "valid",
        status_display: "【有效】",
        score: 0.89,
        verified: true,
        verify_source: "retrieved_context",
      },
    ],
    citationDetails: {
      "[1]": {
        law_name: "《个人信息保护法》",
        article: "第6条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt: "处理个人信息应当具有明确、合理的目的，并应当与处理目的直接相关，采取对个人权益影响最小的方式。",
      },
      "[2]": {
        law_name: "《个人信息保护法》",
        article: "第13条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt:
          "符合下列情形之一的，个人信息处理者方可处理个人信息：（一）取得个人的同意；（二）为订立、履行个人作为一方当事人的合同所必需……",
      },
    },
  },
  {
    id: "non-compete",
    question: "竞业限制的最长期限和适用范围在法律上如何把握？",
    answer:
      "对负有保密义务的劳动者，用人单位可在劳动合同或保密协议中约定竞业限制条款，并约定在限制期内按月给予经济补偿。[1]" +
      "竞业限制期限不得超过二年；范围应限于用人单位的商业秘密和与知识产权相关的保密事项，避免明显扩大化。[2]",
    citations: [
      {
        ref_id: "[1]",
        law_name: "劳动合同法",
        article: "23",
        status: "valid",
        status_display: "【有效】",
        score: 0.92,
        verified: true,
        verify_source: "retrieved_context",
      },
      {
        ref_id: "[2]",
        law_name: "劳动合同法",
        article: "24",
        status: "valid",
        status_display: "【有效】",
        score: 0.9,
        verified: true,
        verify_source: "retrieved_context",
      },
    ],
    citationDetails: {
      "[1]": {
        law_name: "《劳动合同法》",
        article: "第23条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt:
          "对负有保密义务的劳动者，用人单位可以在劳动合同或者保密协议中与劳动者约定竞业限制条款，并约定在解除或者终止劳动合同后，在竞业限制期限内按月给予劳动者经济补偿。",
      },
      "[2]": {
        law_name: "《劳动合同法》",
        article: "第24条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt:
          "在解除或者终止劳动合同后，前款规定的人员到与本单位生产或者经营同类产品、从事同类业务的有竞争关系的其他用人单位，或者自己开业生产或者经营同类产品、从事同类业务的竞业限制期限，不得超过二年。",
      },
    },
  },
  {
    id: "social-insurance",
    question: "用人单位未依法足额缴纳社会保险费，劳动者可以主张哪些救济？",
    answer:
      "用人单位未按时足额缴纳社会保险费的，由社会保险费征收机构责令限期缴纳或者补足。[1]" +
      "劳动者亦可依法解除劳动合同并主张经济补偿；具体程序宜结合当地征缴规则与争议处理渠道一并评估。[2]",
    citations: [
      {
        ref_id: "[1]",
        law_name: "社会保险法",
        article: "63",
        status: "valid",
        status_display: "【有效】",
        score: 0.88,
        verified: true,
        verify_source: "retrieved_context",
      },
      {
        ref_id: "[2]",
        law_name: "劳动合同法",
        article: "38",
        status: "revised",
        status_display: "【已修改】",
        score: 0.72,
        verified: false,
        verify_source: "unverified",
      },
    ],
    citationDetails: {
      "[1]": {
        law_name: "《社会保险法》",
        article: "第63条",
        status: "Verified",
        evidence_status_display: "【有效】",
        excerpt:
          "用人单位未按时足额缴纳社会保险费的，由社会保险费征收机构责令其限期缴纳或者补足。",
      },
      "[2]": {
        law_name: "《劳动合同法》",
        article: "第38条",
        status: "Unverified",
        evidence_status_display: "【已修改】",
        excerpt:
          "用人单位有未依法为劳动者缴纳社会保险费等情形的，劳动者可以解除劳动合同。本条引用需结合地方细则人工复核。",
      },
    },
  },
];

/** 按提问匹配场景；未命中时使用首条（与初始种子对话一致） */
export function resolveDemoChatScenario(question: string): DemoChatScenario {
  const q = question.trim();
  const hit = DEMO_CHAT_SCENARIOS.find((s) => s.question === q);
  return hit ?? DEMO_CHAT_SCENARIOS[0];
}

export type DemoAssistantPayload = {
  content: string;
  citations: Citation[];
  details: Array<{
    ref_id: string;
    law_name: string;
    article: string;
    status: "Verified" | "Unverified";
    evidence_status_display?: string;
    excerpt: string;
  }>;
  answerNeedsHumanReview: boolean;
};

export function buildDemoAssistantPayload(scenario: DemoChatScenario): DemoAssistantPayload {
  const details = Object.entries(scenario.citationDetails).map(([ref_id, detail]) => ({
    ref_id,
    ...detail,
  }));
  return {
    content: sanitizeAssistantAnswerText(scenario.answer),
    citations: scenario.citations,
    details,
    answerNeedsHumanReview: scenario.citations.some((c) => c.verified === false),
  };
}

export const DEMO_QA_QUESTION = DEMO_CHAT_SCENARIOS[0].question;
export const DEMO_QA_ANSWER = DEMO_CHAT_SCENARIOS[0].answer;
export const DEMO_QA_CITATIONS = DEMO_CHAT_SCENARIOS[0].citations;
export const DEMO_QA_CITATION_DETAILS = DEMO_CHAT_SCENARIOS[0].citationDetails;

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
  {
    id: "demo-reg-2026-pipl-regulation-draft",
    regulation_id: "pipl_impl_reg_2026_draft",
    regulation_title: "个人信息保护条例（征求意见稿）",
    summary:
      "细化敏感个人信息处理场景、单独同意形式与跨境传输标准合同备案衔接规则。",
    status: "pending_review",
    created_at: "2026-03-22T09:15:00Z",
    updated_at: "2026-03-29T14:00:00Z",
    uiStatus: "pending_review",
    diff: {
      oldText:
        "第9条：个人信息处理者向境外提供个人信息，应当按照国家网信部门的规定进行安全评估。\n" +
        "第12条：处理敏感个人信息应当取得个人的单独同意。",
      newText:
        "第9条：向境外提供个人信息的，应依法完成个人信息保护认证、标准合同备案或安全评估之一，并留存证明材料。\n" +
        "第12条：处理敏感个人信息应当取得个人的单独同意；单独同意应以明示方式作出，不得以捆绑授权替代。",
      aiSummary:
        "突出“出境三路径”与单独同意的可证明性，企业需同步更新隐私政策、同意弹窗与跨境传输台账。",
    },
  },
  {
    id: "demo-reg-2026-csl-revision-consult",
    regulation_id: "csl_2026_revision_consult",
    regulation_title: "网络安全法修订草案（公开征求意见）",
    summary:
      "强化关键信息基础设施运营者供应链安全审查与漏洞披露协同义务。",
    status: "pending_review",
    created_at: "2026-03-25T11:20:00Z",
    updated_at: "2026-03-30T09:45:00Z",
    uiStatus: "pending_review",
    diff: {
      oldText:
        "第22条：网络产品、服务的提供者应当为其产品、服务持续提供安全维护。\n" +
        "第34条：关键信息基础设施的运营者采购网络产品和服务，可能影响国家安全的，应当通过国家网信部门会同国务院有关部门组织的国家安全审查。",
      newText:
        "第22条：网络产品、服务的提供者应当为其产品、服务持续提供安全维护；对已知漏洞应及时修复并按规定报告。\n" +
        "第34条：关键信息基础设施运营者采购网络产品和服务，应开展供应链安全风险评估；可能影响国家安全的，依法申报网络安全审查。",
      aiSummary:
        "将漏洞管理与供应链风险评估写入法定义务，与数据安全法、关基保护条例形成衔接。",
    },
  },
  {
    id: "demo-reg-2026-ecommerce-guideline-internal",
    regulation_id: "ecommerce_sector_guideline_2026",
    regulation_title: "电子商务平台责任指引（内部研讨稿）",
    summary:
      "明确平台对入驻经营者资质核验、促销规则公示与消费者争议先行赔付的最低要求。",
    status: "pending_review",
    created_at: "2026-03-26T07:50:00Z",
    updated_at: "2026-03-31T16:10:00Z",
    uiStatus: "pending_review",
    diff: {
      oldText:
        "第5条：电子商务平台经营者应当要求申请进入平台销售商品或者提供服务的经营者提交其身份、地址、联系方式、行政许可等真实信息。\n" +
        "第10条：平台内经营者损害消费者合法权益的，平台应当承担连带责任。",
      newText:
        "第5条：电子商务平台经营者应当建立经营者身份与行政许可核验机制，并定期抽查更新；对高风险类目应提高核验频次。\n" +
        "第10条：平台内经营者损害消费者合法权益的，消费者可要求平台先行赔付；平台赔偿后可依法向经营者追偿。",
      aiSummary:
        "从“形式登记”转向“持续核验”，并引入先行赔付与追偿机制，平台合规与客服流程需联动改造。",
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
