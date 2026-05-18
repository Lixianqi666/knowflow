from sqlalchemy import select

from app.agent_runtime.tools import ToolContext, ToolRegistry, ToolResult
from app.models.reimbursement import EmployeeProfile, ReimbursementRequest, TravelReceipt


async def search_policy(ctx: ToolContext, query: str) -> ToolResult:
    """查询政策知识库。"""
    return ToolResult(status="ok", content="差旅报销需提供有效交通和住宿票据，金额需符合员工级别标准。")


async def get_employee(ctx: ToolContext, name: str) -> ToolResult:
    if not ctx.db:
        return ToolResult(status="error", content="数据库不可用", error="missing_db")
    result = await ctx.db.execute(select(EmployeeProfile).where(EmployeeProfile.name == name))
    employee = result.scalar_one_or_none()
    if not employee:
        return ToolResult(status="not_found", content=f"未找到员工 {name}", error="employee_not_found")
    return ToolResult(
        status="ok",
        content=f"员工{name}属于{employee.department}，级别{employee.level}，审批人为{employee.manager_name}",
        data={
            "name": employee.name,
            "employee_no": employee.employee_no,
            "department": employee.department,
            "level": employee.level,
            "manager_name": employee.manager_name,
        },
    )


async def list_receipts(ctx: ToolContext, employee_name: str) -> ToolResult:
    if not ctx.db:
        return ToolResult(status="error", content="数据库不可用", error="missing_db")
    result = await ctx.db.execute(select(TravelReceipt).where(TravelReceipt.employee_name == employee_name))
    receipts = list(result.scalars().all())
    if not receipts:
        return ToolResult(status="not_found", content=f"未找到 {employee_name} 的票据", error="receipt_not_found")
    data = [
        {
            "id": str(r.id),
            "type": r.receipt_type,
            "amount": r.amount,
            "city": r.city,
            "is_valid": r.is_valid,
        }
        for r in receipts
    ]
    transport_types = {"交通", "高铁", "火车", "飞机", "汽车"}
    has_transport = any(t in transport_types for t in {r.receipt_type for r in receipts})
    has_hotel = "住宿" in {r.receipt_type for r in receipts}
    if not has_transport or not has_hotel:
        return ToolResult(status="ok", content="票据不完整，缺少交通或住宿票据", data={"receipts": data})
    return ToolResult(status="ok", content=f"找到 {len(receipts)} 张票据", data={"receipts": data})


async def validate_invoice(ctx: ToolContext, receipt_ids: list[str]) -> ToolResult:
    if not receipt_ids:
        return ToolResult(status="error", content="缺少票据 ID", error="missing_receipt_ids")
    if not ctx.db:
        return ToolResult(status="error", content="数据库不可用", error="missing_db")
    result = await ctx.db.execute(select(TravelReceipt).where(TravelReceipt.id.in_(receipt_ids)))
    receipts = list(result.scalars().all())
    if not receipts:
        return ToolResult(status="error", content="未找到指定票据", error="receipt_not_found")

    issues = []
    dates = set()
    for r in receipts:
        dates.add(str(r.occurred_at.date()) if r.occurred_at else None)
        if r.is_valid != "true":
            issues.append(f"{r.receipt_type}票据({r.amount}元)无效")

    if len(dates) > 1:
        issues.append(f"票据日期不一致：{', '.join(sorted(filter(None, dates)))}")

    if issues:
        return ToolResult(
            status="ok",
            content=f"校验未通过：{'; '.join(issues)}",
            data={"valid": False, "issues": issues, "receipt_count": len(receipts)},
        )
    return ToolResult(
        status="ok",
        content=f"票据校验通过，共 {len(receipts)} 张",
        data={"valid": True, "receipt_count": len(receipts)},
    )


async def submit_reimbursement(ctx: ToolContext, employee_name: str, trip_city: str | None = None) -> ToolResult:
    if not ctx.db:
        return ToolResult(status="error", content="数据库不可用", error="missing_db")
    result = await ctx.db.execute(select(TravelReceipt).where(TravelReceipt.employee_name == employee_name))
    receipts = list(result.scalars().all())
    transport_types = {"交通", "高铁", "火车", "飞机", "汽车"}
    has_transport = any(t in transport_types for t in {r.receipt_type for r in receipts})
    has_hotel = "住宿" in {r.receipt_type for r in receipts}
    if not has_transport or not has_hotel:
        return ToolResult(status="error", content="提交失败：缺少交通或住宿票据", error="missing_receipts")
    amount = sum(r.amount for r in receipts)
    req = ReimbursementRequest(
        employee_name=employee_name,
        trip_city=trip_city,
        amount=amount,
        status="submitted",
        detail="Agent 自动提交差旅报销申请",
        receipt_ids=[str(r.id) for r in receipts],
    )
    ctx.db.add(req)
    await ctx.db.flush()
    return ToolResult(
        status="ok",
        content=f"报销申请已提交，申请 ID：{req.id}，金额：{amount}",
        data={"request_id": str(req.id), "amount": amount},
    )


def build_business_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("search_policy", search_policy, "查询差旅和报销政策", ["query"])
    registry.register("get_employee", get_employee, "查询员工信息", ["name"])
    registry.register("list_receipts", list_receipts, "查询员工票据", ["employee_name"])
    registry.register("validate_invoice", validate_invoice, "校验票据", ["receipt_ids"])
    registry.register("submit_reimbursement", submit_reimbursement, "提交报销申请", ["employee_name"])
    return registry
