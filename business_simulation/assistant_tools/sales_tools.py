"""
Sales Module MCP Tools
Wraps ERPNext Sales module functionality for AI agents.
"""

import frappe
from frappe import _
from typing import Dict, Any, List, Optional
from frappe_assistant_core.core.base_tool import BaseTool


class CreateCustomer(BaseTool):
    """Create a new Customer in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_customer"
        self.description = """Create a new Customer record in ERPNext.

Use this tool to add new customers to the system with their basic details.
Returns the customer name/ID upon successful creation."""
        self.category = "Sales"
        self.source_app = "business_simulation"
        self.requires_permission = "Customer"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "customer_name": {
                    "type": "string",
                    "description": "Name of the customer (company or individual)"
                },
                "customer_type": {
                    "type": "string",
                    "enum": ["Company", "Individual"],
                    "default": "Company",
                    "description": "Type of customer"
                },
                "customer_group": {
                    "type": "string",
                    "description": "Customer group (e.g., 'Commercial', 'Individual')"
                },
                "territory": {
                    "type": "string",
                    "description": "Sales territory"
                },
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "Primary email address"
                },
                "phone": {
                    "type": "string",
                    "description": "Primary phone number"
                }
            },
            "required": ["customer_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            customer = frappe.get_doc({
                "doctype": "Customer",
                "customer_name": arguments["customer_name"],
                "customer_type": arguments.get("customer_type", "Company"),
                "customer_group": arguments.get("customer_group", "All Customer Groups"),
                "territory": arguments.get("territory", "All Territories"),
            })

            # Add contact details if provided
            if arguments.get("email"):
                customer.append("email_ids", {"email_id": arguments["email"], "is_primary": 1})
            if arguments.get("phone"):
                customer.append("phone_nos", {"phone": arguments["phone"], "is_primary_phone": 1})

            customer.insert()

            return {
                "success": True,
                "customer": customer.name,
                "customer_name": customer.customer_name,
                "message": f"Customer '{customer.customer_name}' created successfully"
            }
        except Exception as e:
            frappe.log_error(title="Create Customer Error", message=str(e))
            return {"success": False, "error": str(e)}


class GetCustomer(BaseTool):
    """Get customer details from ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "get_customer"
        self.description = """Retrieve customer details by name or ID.

Returns comprehensive customer information including contact details,
outstanding amounts, and recent transactions."""
        self.category = "Sales"
        self.source_app = "business_simulation"
        self.requires_permission = "Customer"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name or ID"
                },
                "include_outstanding": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include outstanding balance information"
                }
            },
            "required": ["customer"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            customer_name = arguments["customer"]
            customer = frappe.get_doc("Customer", customer_name)

            result = {
                "success": True,
                "customer": {
                    "name": customer.name,
                    "customer_name": customer.customer_name,
                    "customer_type": customer.customer_type,
                    "customer_group": customer.customer_group,
                    "territory": customer.territory,
                    "disabled": customer.disabled,
                }
            }

            if arguments.get("include_outstanding", True):
                # Get outstanding amount
                from erpnext.selling.doctype.customer.customer import get_customer_outstanding
                outstanding = get_customer_outstanding(
                    customer_name,
                    frappe.defaults.get_user_default("Company")
                )
                result["customer"]["outstanding_amount"] = outstanding

            return result
        except frappe.DoesNotExistError:
            return {"success": False, "error": f"Customer '{arguments['customer']}' not found"}
        except Exception as e:
            frappe.log_error(title="Get Customer Error", message=str(e))
            return {"success": False, "error": str(e)}


class ListCustomers(BaseTool):
    """List customers with optional filters."""

    def __init__(self):
        super().__init__()
        self.name = "list_customers"
        self.description = """List customers with optional filters.

Returns a list of customers matching the specified criteria.
Supports pagination and filtering by customer group, territory, etc."""
        self.category = "Sales"
        self.source_app = "business_simulation"
        self.requires_permission = "Customer"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "customer_group": {
                    "type": "string",
                    "description": "Filter by customer group"
                },
                "territory": {
                    "type": "string",
                    "description": "Filter by territory"
                },
                "customer_type": {
                    "type": "string",
                    "enum": ["Company", "Individual"],
                    "description": "Filter by customer type"
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Maximum number of results"
                },
                "offset": {
                    "type": "integer",
                    "default": 0,
                    "description": "Pagination offset"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            filters = {"disabled": 0}

            if arguments.get("customer_group"):
                filters["customer_group"] = arguments["customer_group"]
            if arguments.get("territory"):
                filters["territory"] = arguments["territory"]
            if arguments.get("customer_type"):
                filters["customer_type"] = arguments["customer_type"]

            customers = frappe.get_list(
                "Customer",
                filters=filters,
                fields=["name", "customer_name", "customer_type", "customer_group", "territory"],
                limit_page_length=arguments.get("limit", 20),
                limit_start=arguments.get("offset", 0),
                order_by="creation desc"
            )

            total = frappe.db.count("Customer", filters=filters)

            return {
                "success": True,
                "customers": customers,
                "total": total,
                "limit": arguments.get("limit", 20),
                "offset": arguments.get("offset", 0)
            }
        except Exception as e:
            frappe.log_error(title="List Customers Error", message=str(e))
            return {"success": False, "error": str(e)}


class CreateQuotation(BaseTool):
    """Create a Sales Quotation in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_quotation"
        self.description = """Create a Sales Quotation for a customer.

Creates a quotation with specified items and pricing.
Returns the quotation name and total amount."""
        self.category = "Sales"
        self.source_app = "business_simulation"
        self.requires_permission = "Quotation"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "party_name": {
                    "type": "string",
                    "description": "Customer name"
                },
                "items": {
                    "type": "array",
                    "description": "List of items with qty and rate",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_code": {"type": "string"},
                            "qty": {"type": "number"},
                            "rate": {"type": "number", "description": "Optional - uses item price if not provided"}
                        },
                        "required": ["item_code", "qty"]
                    }
                },
                "valid_till": {
                    "type": "string",
                    "format": "date",
                    "description": "Quotation validity date"
                }
            },
            "required": ["party_name", "items"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            quotation = frappe.get_doc({
                "doctype": "Quotation",
                "quotation_to": "Customer",
                "party_name": arguments["party_name"],
                "valid_till": arguments.get("valid_till"),
                "items": []
            })

            for item in arguments["items"]:
                quotation.append("items", {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "rate": item.get("rate")  # Will use item price if not provided
                })

            quotation.insert()

            return {
                "success": True,
                "quotation": quotation.name,
                "customer": arguments["party_name"],
                "grand_total": quotation.grand_total,
                "status": quotation.status,
                "message": f"Quotation {quotation.name} created for {arguments['party_name']}"
            }
        except Exception as e:
            frappe.log_error(title="Create Quotation Error", message=str(e))
            return {"success": False, "error": str(e)}


class CreateSalesOrder(BaseTool):
    """Create a Sales Order in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_sales_order"
        self.description = """Create a Sales Order for a customer.

Creates a sales order with specified items. Can optionally submit the order.
Returns the sales order name and total amount."""
        self.category = "Sales"
        self.source_app = "business_simulation"
        self.requires_permission = "Sales Order"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "customer": {
                    "type": "string",
                    "description": "Customer name"
                },
                "items": {
                    "type": "array",
                    "description": "List of items with qty",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_code": {"type": "string"},
                            "qty": {"type": "number"},
                            "rate": {"type": "number", "description": "Optional - uses item price if not provided"}
                        },
                        "required": ["item_code", "qty"]
                    }
                },
                "delivery_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Expected delivery date"
                },
                "submit": {
                    "type": "boolean",
                    "default": False,
                    "description": "Submit the order after creation"
                }
            },
            "required": ["customer", "items"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            so = frappe.get_doc({
                "doctype": "Sales Order",
                "customer": arguments["customer"],
                "delivery_date": arguments.get("delivery_date"),
                "items": []
            })

            for item in arguments["items"]:
                so.append("items", {
                    "item_code": item["item_code"],
                    "qty": item["qty"],
                    "rate": item.get("rate"),
                    "delivery_date": arguments.get("delivery_date")
                })

            so.insert()

            if arguments.get("submit", False):
                so.submit()

            return {
                "success": True,
                "sales_order": so.name,
                "customer": arguments["customer"],
                "grand_total": so.grand_total,
                "status": so.status,
                "docstatus": so.docstatus,
                "message": f"Sales Order {so.name} created for {arguments['customer']}"
            }
        except Exception as e:
            frappe.log_error(title="Create Sales Order Error", message=str(e))
            return {"success": False, "error": str(e)}


class GetSalesOrder(BaseTool):
    """Get Sales Order details from ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "get_sales_order"
        self.description = """Retrieve Sales Order details by name.

Returns comprehensive order information including items,
status, and delivery schedule."""
        self.category = "Sales"
        self.source_app = "business_simulation"
        self.requires_permission = "Sales Order"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "sales_order": {
                    "type": "string",
                    "description": "Sales Order name/ID"
                }
            },
            "required": ["sales_order"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            so = frappe.get_doc("Sales Order", arguments["sales_order"])

            items = [{
                "item_code": item.item_code,
                "item_name": item.item_name,
                "qty": item.qty,
                "rate": item.rate,
                "amount": item.amount,
                "delivered_qty": item.delivered_qty
            } for item in so.items]

            return {
                "success": True,
                "sales_order": {
                    "name": so.name,
                    "customer": so.customer,
                    "customer_name": so.customer_name,
                    "transaction_date": str(so.transaction_date),
                    "delivery_date": str(so.delivery_date) if so.delivery_date else None,
                    "status": so.status,
                    "grand_total": so.grand_total,
                    "per_delivered": so.per_delivered,
                    "per_billed": so.per_billed,
                    "items": items
                }
            }
        except frappe.DoesNotExistError:
            return {"success": False, "error": f"Sales Order '{arguments['sales_order']}' not found"}
        except Exception as e:
            frappe.log_error(title="Get Sales Order Error", message=str(e))
            return {"success": False, "error": str(e)}


__all__ = [
    "CreateCustomer",
    "GetCustomer",
    "ListCustomers",
    "CreateQuotation",
    "CreateSalesOrder",
    "GetSalesOrder",
]
