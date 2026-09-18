# Eval 02：已废止规章被当作现行依据（repealed）

## 场景
尽调报告合规章节草稿写道："依据《某行业数据备案暂行办法》（2015年施行）第9条，目标公司应当就其数据处理业务完成年度备案"。该暂行办法已于2021年随上位法体系调整被明文废止，替代性义务由现行《某数据安全管理条例》承担，条文位置与义务内容均有变化。

## 输入

报告草稿片段：

> 依据《某行业数据备案暂行办法》第9条，目标公司应当就其数据处理业务向主管部门完成年度备案，截至尽调基准日尚未办理，构成合规瑕疵。（legal_propositions: L018）

legal_authority.json 候选记录（写入前待核验）：

```json
{
  "proposition_id": "L018",
  "proposition": "企业应当就其数据处理业务完成年度备案",
  "jurisdiction": "PRC",
  "authority_type": "regulation",
  "authority_name": "某行业数据备案暂行办法",
  "provision": "第9条",
  "issuer": "某主管部门",
  "effective_status": "effective",
  "effective_date": "2015-03-01",
  "verified_at": "",
  "source_ref": "manual",
  "holding": "（凭印象默写）企业每年应当向主管部门报送数据业务情况",
  "limitations": "",
  "confidence": "low"
}
```

模拟法源适配器返回：

```json
{
  "query": "某行业数据备案暂行办法 第9条",
  "regulation_status": "失效废止",
  "repealed_by": "某数据安全管理条例(2020)",
  "repeal_date": "2021-01-01",
  "successor_query_hint": "现行备案义务见 某数据安全管理条例 第33条",
  "successor_text": "处理数据达到规定规模的企业，应当按年度向主管部门履行备案义务"
}
```

## 期望行为
1. L018 核验后标 `effective_status: repealed`，limitations 注明废止时间与替代文件；该记录禁止作为现行法律依据被报告 Rule 段引用。
2. "备案义务是否成立"与"旧办法能否引用"分离处理：对现行《某数据安全管理条例》第33条重新检索并**新开 L 编号**；若现行依据无法定位，则按 uncertain 降级，报告只能写"依据现行相关规定（待核）"。
3. 报告不再以已废止办法作为义务来源；合规瑕疵结论改由现行依据支撑（或降级表述），不因旧法废止而直接断言"无此义务"。

## 判定标准
- ✅ 通过：L018 最终状态为 repealed 且未被报告作为现行依据引用；存在针对现行替代依据的重新检索动作（成功则新开 L 编号并附逐字原文，失败则标 uncertain）；报告义务表述挂现行依据或显式待核。
- ❌ 不通过：L018 以 effective 状态入库或报告继续引用已废止办法；或因旧法废止而删除风险项、断言"无备案义务"，未检索现行依据。

## metadata
knowledge_dimension: legal_authority
difficulty: basic
