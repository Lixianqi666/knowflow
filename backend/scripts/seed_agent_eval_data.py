"""写入 Agent 评估场景种子数据。"""

import asyncio
from datetime import datetime

from sqlalchemy import select

from app.database import async_session
from app.models.reimbursement import EmployeeProfile, TravelReceipt


async def seed():
    async with async_session() as db:
        existing = await db.scalar(select(EmployeeProfile).where(EmployeeProfile.employee_no == "E1001"))
        if existing:
            return

        db.add_all(
            [
                EmployeeProfile(name="张三", employee_no="E1001", department="销售部", level="P6", manager_name="李经理"),
                EmployeeProfile(name="李四", employee_no="E1002", department="研发部", level="P7", manager_name="王经理"),
            ]
        )
        db.add_all(
            [
                TravelReceipt(employee_name="张三", receipt_type="交通", amount=560, city="上海", occurred_at=datetime(2026, 4, 10)),
                TravelReceipt(employee_name="张三", receipt_type="住宿", amount=880, city="上海", occurred_at=datetime(2026, 4, 11)),
                TravelReceipt(employee_name="李四", receipt_type="交通", amount=420, city="深圳", occurred_at=datetime(2026, 4, 12)),
            ]
        )
        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
