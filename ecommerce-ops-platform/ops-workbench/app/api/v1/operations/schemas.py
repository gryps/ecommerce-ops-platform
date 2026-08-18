from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OpsProductPayload(BaseModel):
    product_code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="", max_length=80)
    style_tags: list[str] = Field(default_factory=list, max_length=30)
    supplier_name: str = Field(default="", max_length=160)
    supplier_link: str = Field(default="", max_length=2000)
    purchase_cost_yuan: float = Field(default=40.0, ge=0)
    target_sale_price_yuan: float = Field(default=160.0, ge=0)
    actual_sale_price_yuan: float = Field(default=160.0, ge=0)
    stock_qty: int = Field(default=0, ge=0)
    inbound_qty: int = Field(default=0, ge=0)
    procurement_cycle_days: int = Field(default=7, ge=0, le=365)
    status: str = Field(default="candidate", max_length=30)
    selection_grade: str = Field(default="", max_length=20)
    owner: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=2000)


class OpsProductResponse(OpsProductPayload):
    id: str
    estimated_gross_profit_yuan: float
    estimated_gross_margin: float
    stock_warning: str
    created_at: datetime
    updated_at: datetime


class OpsOverviewMetric(BaseModel):
    key: str
    label: str
    value: float | int | str
    unit: str = ""


class OpsRiskItem(BaseModel):
    product_id: str
    product_code: str
    name: str
    risk: str
    detail: str


class OpsOverviewResponse(BaseModel):
    metrics: list[OpsOverviewMetric]
    risks: list[OpsRiskItem]
    product_status_counts: dict[str, int]
    next_actions: list[str]
