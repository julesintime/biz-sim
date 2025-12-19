"""
Accounting Module MCP Tools
Wraps ERPNext Accounting module functionality for AI agents.
"""

import frappe
from frappe import _
from typing import Dict, Any, List, Optional
from frappe_assistant_core.core.base_tool import BaseTool


class CreateJournalEntry(BaseTool):
    """Create a Journal Entry in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_journal_entry"
        self.description = """Create a Journal Entry for accounting adjustments.

Use this for manual accounting entries, adjustments, and corrections.
Entries must balance (total debits = total credits)."""
        self.category = "Accounting"
        self.source_app = "business_simulation"
        self.requires_permission = "Journal Entry"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "voucher_type": {
                    "type": "string",
                    "enum": ["Journal Entry", "Bank Entry", "Cash Entry", "Credit Card Entry", "Debit Note", "Credit Note"],
                    "default": "Journal Entry",
                    "description": "Type of journal voucher"
                },
                "accounts": {
                    "type": "array",
                    "description": "Account entries (must balance)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account": {"type": "string", "description": "Account name"},
                            "debit_in_account_currency": {"type": "number", "default": 0},
                            "credit_in_account_currency": {"type": "number", "default": 0},
                            "party_type": {"type": "string", "description": "Optional: Customer, Supplier, etc."},
                            "party": {"type": "string", "description": "Optional: Party name"}
                        },
                        "required": ["account"]
                    }
                },
                "posting_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Posting date"
                },
                "user_remark": {
                    "type": "string",
                    "description": "Description/reason for the entry"
                },
                "submit": {
                    "type": "boolean",
                    "default": False,
                    "description": "Submit the entry after creation"
                }
            },
            "required": ["accounts"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            je = frappe.get_doc({
                "doctype": "Journal Entry",
                "voucher_type": arguments.get("voucher_type", "Journal Entry"),
                "posting_date": arguments.get("posting_date", frappe.utils.today()),
                "user_remark": arguments.get("user_remark"),
                "accounts": []
            })

            for account in arguments["accounts"]:
                je.append("accounts", {
                    "account": account["account"],
                    "debit_in_account_currency": account.get("debit_in_account_currency", 0),
                    "credit_in_account_currency": account.get("credit_in_account_currency", 0),
                    "party_type": account.get("party_type"),
                    "party": account.get("party")
                })

            je.insert()

            if arguments.get("submit", False):
                je.submit()

            return {
                "success": True,
                "journal_entry": je.name,
                "voucher_type": je.voucher_type,
                "total_debit": je.total_debit,
                "total_credit": je.total_credit,
                "docstatus": je.docstatus,
                "message": f"Journal Entry {je.name} created"
            }
        except Exception as e:
            frappe.log_error(title="Create Journal Entry Error", message=str(e))
            return {"success": False, "error": str(e)}


class GetBalanceSheet(BaseTool):
    """Get Balance Sheet report data."""

    def __init__(self):
        super().__init__()
        self.name = "get_balance_sheet"
        self.description = """Retrieve Balance Sheet report data.

Returns assets, liabilities, and equity totals for the specified period."""
        self.category = "Accounting"
        self.source_app = "business_simulation"
        self.requires_permission = "GL Entry"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name"
                },
                "to_date": {
                    "type": "string",
                    "format": "date",
                    "description": "As of date"
                },
                "periodicity": {
                    "type": "string",
                    "enum": ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
                    "default": "Yearly"
                }
            },
            "required": ["company"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from erpnext.accounts.report.balance_sheet.balance_sheet import execute

            filters = frappe._dict({
                "company": arguments["company"],
                "period_end_date": arguments.get("to_date", frappe.utils.today()),
                "periodicity": arguments.get("periodicity", "Yearly"),
                "report_date": arguments.get("to_date", frappe.utils.today())
            })

            columns, data, message, chart = execute(filters)

            # Extract key totals
            totals = {}
            for row in data:
                if row.get("account_name") in ["Total Asset", "Total Liability", "Total Equity"]:
                    totals[row["account_name"]] = row.get("total", 0)

            return {
                "success": True,
                "company": arguments["company"],
                "as_of_date": arguments.get("to_date", frappe.utils.today()),
                "totals": totals,
                "data": data[:50],  # Limit data returned
                "message": message
            }
        except Exception as e:
            frappe.log_error(title="Get Balance Sheet Error", message=str(e))
            return {"success": False, "error": str(e)}


class GetProfitLoss(BaseTool):
    """Get Profit and Loss report data."""

    def __init__(self):
        super().__init__()
        self.name = "get_profit_loss"
        self.description = """Retrieve Profit and Loss (Income Statement) report data.

Returns income, expenses, and net profit/loss for the specified period."""
        self.category = "Accounting"
        self.source_app = "business_simulation"
        self.requires_permission = "GL Entry"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name"
                },
                "from_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Period start date"
                },
                "to_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Period end date"
                },
                "periodicity": {
                    "type": "string",
                    "enum": ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
                    "default": "Yearly"
                }
            },
            "required": ["company"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from erpnext.accounts.report.profit_and_loss_statement.profit_and_loss_statement import execute

            # Get fiscal year dates if not provided
            if not arguments.get("from_date") or not arguments.get("to_date"):
                fiscal_year = frappe.db.get_value(
                    "Fiscal Year",
                    {"disabled": 0},
                    ["year_start_date", "year_end_date"],
                    as_dict=True,
                    order_by="year_start_date desc"
                )
                from_date = arguments.get("from_date") or str(fiscal_year.year_start_date)
                to_date = arguments.get("to_date") or str(fiscal_year.year_end_date)
            else:
                from_date = arguments["from_date"]
                to_date = arguments["to_date"]

            filters = frappe._dict({
                "company": arguments["company"],
                "from_fiscal_year": frappe.db.get_value("Fiscal Year", {"year_start_date": ("<=", from_date)}, "name"),
                "to_fiscal_year": frappe.db.get_value("Fiscal Year", {"year_end_date": (">=", to_date)}, "name"),
                "periodicity": arguments.get("periodicity", "Yearly"),
                "period_start_date": from_date,
                "period_end_date": to_date
            })

            columns, data, message, chart = execute(filters)

            # Extract key totals
            totals = {}
            for row in data:
                if row.get("account_name") in ["Total Income", "Total Expense", "Net Profit"]:
                    totals[row["account_name"]] = row.get("total", 0)

            return {
                "success": True,
                "company": arguments["company"],
                "from_date": from_date,
                "to_date": to_date,
                "totals": totals,
                "data": data[:50],  # Limit data returned
                "message": message
            }
        except Exception as e:
            frappe.log_error(title="Get Profit Loss Error", message=str(e))
            return {"success": False, "error": str(e)}


class CreatePaymentEntry(BaseTool):
    """Create a Payment Entry in ERPNext."""

    def __init__(self):
        super().__init__()
        self.name = "create_payment_entry"
        self.description = """Create a Payment Entry for receiving or making payments.

Use this for recording customer payments received or supplier payments made."""
        self.category = "Accounting"
        self.source_app = "business_simulation"
        self.requires_permission = "Payment Entry"

        self.inputSchema = {
            "type": "object",
            "properties": {
                "payment_type": {
                    "type": "string",
                    "enum": ["Receive", "Pay", "Internal Transfer"],
                    "description": "Type of payment"
                },
                "party_type": {
                    "type": "string",
                    "enum": ["Customer", "Supplier", "Employee"],
                    "description": "Party type"
                },
                "party": {
                    "type": "string",
                    "description": "Party name (customer/supplier/employee)"
                },
                "paid_amount": {
                    "type": "number",
                    "description": "Amount paid"
                },
                "mode_of_payment": {
                    "type": "string",
                    "description": "Payment mode (e.g., 'Cash', 'Bank Transfer')"
                },
                "reference_no": {
                    "type": "string",
                    "description": "Payment reference number"
                },
                "reference_date": {
                    "type": "string",
                    "format": "date",
                    "description": "Reference date"
                },
                "submit": {
                    "type": "boolean",
                    "default": False,
                    "description": "Submit the entry after creation"
                }
            },
            "required": ["payment_type", "party_type", "party", "paid_amount"]
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Get company
            company = frappe.defaults.get_user_default("Company")
            if not company:
                company = frappe.db.get_single_value("Global Defaults", "default_company")

            # Get accounts based on payment type and party type
            if arguments["payment_type"] == "Receive":
                paid_from_account_type = "Receivable"
                paid_to_account_type = "Bank" if arguments.get("mode_of_payment") != "Cash" else "Cash"
            else:
                paid_from_account_type = "Bank" if arguments.get("mode_of_payment") != "Cash" else "Cash"
                paid_to_account_type = "Payable"

            pe = frappe.get_doc({
                "doctype": "Payment Entry",
                "payment_type": arguments["payment_type"],
                "party_type": arguments["party_type"],
                "party": arguments["party"],
                "company": company,
                "paid_amount": arguments["paid_amount"],
                "received_amount": arguments["paid_amount"],
                "mode_of_payment": arguments.get("mode_of_payment"),
                "reference_no": arguments.get("reference_no"),
                "reference_date": arguments.get("reference_date", frappe.utils.today())
            })

            pe.insert()

            if arguments.get("submit", False):
                pe.submit()

            return {
                "success": True,
                "payment_entry": pe.name,
                "payment_type": pe.payment_type,
                "party": pe.party,
                "paid_amount": pe.paid_amount,
                "docstatus": pe.docstatus,
                "message": f"Payment Entry {pe.name} created for {pe.party}"
            }
        except Exception as e:
            frappe.log_error(title="Create Payment Entry Error", message=str(e))
            return {"success": False, "error": str(e)}


__all__ = [
    "CreateJournalEntry",
    "GetBalanceSheet",
    "GetProfitLoss",
    "CreatePaymentEntry",
]
