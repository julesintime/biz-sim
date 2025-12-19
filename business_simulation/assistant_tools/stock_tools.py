"""
Stock/Inventory Module MCP Tools
Wraps ERPNext Stock module functionality for AI agents.
"""

import frappe
from frappe import _
from typing import Dict, Any, List, Optional
from frappe_assistant_core.core.base_tool import BaseTool


class CreateItem(BaseTool):
    """Create a new Item in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_item"
        self.description = """Create a new Item (product/service) in ERPNext.

Use this to add new products, services, or raw materials to the system."""
        self.category = "Stock"
        self.source_app = "business_simulation"
        self.requires_permission = "Item"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "item_code": {
                    "type": "string",
                    "description": "Unique item code/SKU"
                },
                "item_name": {
                    "type": "string",
                    "description": "Item display name"
                },
                "item_group": {
                    "type": "string",
                    "description": "Item group (e.g., 'Products', 'Raw Material')"
                },
                "stock_uom": {
                    "type": "string",
                    "default": "Nos",
                    "description": "Unit of measure (e.g., 'Nos', 'Kg', 'Litre')"
                },
                "is_stock_item": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether item maintains stock"
                },
                "standard_rate": {
                    "type": "number",
                    "description": "Standard selling rate"
                },
                "description": {
                    "type": "string",
                    "description": "Item description"
                }
            },
            "required": ["item_code", "item_name", "item_group"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            item = frappe.get_doc({
                "doctype": "Item",
                "item_code": arguments["item_code"],
                "item_name": arguments["item_name"],
                "item_group": arguments["item_group"],
                "stock_uom": arguments.get("stock_uom", "Nos"),
                "is_stock_item": arguments.get("is_stock_item", 1),
                "standard_rate": arguments.get("standard_rate", 0),
                "description": arguments.get("description", arguments["item_name"])
            })

            item.insert()

            return {
                "success": True,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "message": f"Item '{item.item_code}' created successfully"
            }
        except Exception as e:
            frappe.log_error(title="Create Item Error", message=str(e))
            return {"success": False, "error": str(e)}


class GetItem(BaseTool):
    """Get item details from ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "get_item"
        self.description = """Retrieve item details by item code.

Returns comprehensive item information including pricing and stock settings."""
        self.category = "Stock"
        self.source_app = "business_simulation"
        self.requires_permission = "Item"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "item_code": {
                    "type": "string",
                    "description": "Item code"
                }
            },
            "required": ["item_code"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            item = frappe.get_doc("Item", arguments["item_code"])

            return {
                "success": True,
                "item": {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "item_group": item.item_group,
                    "stock_uom": item.stock_uom,
                    "is_stock_item": item.is_stock_item,
                    "standard_rate": item.standard_rate,
                    "description": item.description,
                    "disabled": item.disabled
                }
            }
        except frappe.DoesNotExistError:
            return {"success": False, "error": f"Item '{arguments['item_code']}' not found"}
        except Exception as e:
            frappe.log_error(title="Get Item Error", message=str(e))
            return {"success": False, "error": str(e)}


class GetStockBalance(BaseTool):
    """Get stock balance for an item."""

    def __init__(self):
        super().__init__()
        self.name = "get_stock_balance"
        self.description = """Get current stock balance for an item.

Returns stock levels across warehouses or for a specific warehouse."""
        self.category = "Stock"
        self.source_app = "business_simulation"
        self.requires_permission = "Stock Ledger Entry"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "item_code": {
                    "type": "string",
                    "description": "Item code"
                },
                "warehouse": {
                    "type": "string",
                    "description": "Optional - specific warehouse. Returns all warehouses if not specified."
                }
            },
            "required": ["item_code"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from erpnext.stock.utils import get_stock_balance

            item_code = arguments["item_code"]
            warehouse = arguments.get("warehouse")

            if warehouse:
                # Get balance for specific warehouse
                balance = get_stock_balance(item_code, warehouse)
                return {
                    "success": True,
                    "item_code": item_code,
                    "warehouse": warehouse,
                    "balance": balance
                }
            else:
                # Get balance for all warehouses
                bins = frappe.get_all(
                    "Bin",
                    filters={"item_code": item_code},
                    fields=["warehouse", "actual_qty", "reserved_qty", "ordered_qty", "projected_qty"]
                )

                total_qty = sum(b["actual_qty"] for b in bins)

                return {
                    "success": True,
                    "item_code": item_code,
                    "total_qty": total_qty,
                    "by_warehouse": bins
                }
        except Exception as e:
            frappe.log_error(title="Get Stock Balance Error", message=str(e))
            return {"success": False, "error": str(e)}


class ListWarehouses(BaseTool):
    """List all warehouses in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "list_warehouses"
        self.description = """List all warehouses in the system.

Returns active warehouses with their parent hierarchy."""
        self.category = "Stock"
        self.source_app = "business_simulation"
        self.requires_permission = "Warehouse"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Filter by company"
                },
                "is_group": {
                    "type": "boolean",
                    "description": "Filter by group/non-group warehouses"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            filters = {"disabled": 0}

            if arguments.get("company"):
                filters["company"] = arguments["company"]
            if "is_group" in arguments:
                filters["is_group"] = arguments["is_group"]

            warehouses = frappe.get_all(
                "Warehouse",
                filters=filters,
                fields=["name", "warehouse_name", "company", "is_group", "parent_warehouse"],
                order_by="lft"
            )

            return {
                "success": True,
                "warehouses": warehouses,
                "count": len(warehouses)
            }
        except Exception as e:
            frappe.log_error(title="List Warehouses Error", message=str(e))
            return {"success": False, "error": str(e)}


class CreateStockEntry(BaseTool):
    """Create a Stock Entry in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_stock_entry"
        self.description = """Create a Stock Entry for material movements.

Supports Material Receipt, Material Issue, Material Transfer, and other stock entry types."""
        self.category = "Stock"
        self.source_app = "business_simulation"
        self.requires_permission = "Stock Entry"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "stock_entry_type": {
                    "type": "string",
                    "enum": ["Material Receipt", "Material Issue", "Material Transfer", "Repack", "Manufacture"],
                    "description": "Type of stock entry"
                },
                "items": {
                    "type": "array",
                    "description": "Items to move",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_code": {"type": "string"},
                            "qty": {"type": "number"},
                            "s_warehouse": {"type": "string", "description": "Source warehouse"},
                            "t_warehouse": {"type": "string", "description": "Target warehouse"},
                            "basic_rate": {"type": "number", "description": "Rate per unit"}
                        },
                        "required": ["item_code", "qty"]
                    }
                },
                "submit": {
                    "type": "boolean",
                    "default": False,
                    "description": "Submit the entry after creation"
                }
            },
            "required": ["stock_entry_type", "items"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            se = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": arguments["stock_entry_type"],
                "items": []
            })

            for item in arguments["items"]:
                se.append("items", {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "s_warehouse": item.get("s_warehouse"),
                    "t_warehouse": item.get("t_warehouse"),
                    "basic_rate": item.get("basic_rate")
                })

            se.insert()

            if arguments.get("submit", False):
                se.submit()

            return {
                "success": True,
                "stock_entry": se.name,
                "stock_entry_type": se.stock_entry_type,
                "total_value": se.total_value,
                "docstatus": se.docstatus,
                "message": f"Stock Entry {se.name} created"
            }
        except Exception as e:
            frappe.log_error(title="Create Stock Entry Error", message=str(e))
            return {"success": False, "error": str(e)}


__all__ = [
    "CreateItem",
    "GetItem",
    "GetStockBalance",
    "ListWarehouses",
    "CreateStockEntry",
]
