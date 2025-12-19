# Business Simulation

MCP tools for ERPNext business simulation and AI-powered operations.

## Overview

This Frappe app provides MCP (Model Context Protocol) tools that wrap existing ERPNext functionality, enabling AI agents to interact with business operations through Frappe Assistant Core.

## Requirements

- Frappe Framework v16+
- ERPNext (for business module tools)
- Frappe Assistant Core v2.2+

## Installation

```bash
# Get the app
bench get-app business_simulation https://github.com/your-org/business_simulation.git

# Install on your site
bench --site your-site install-app business_simulation
```

## Available Tools

### Sales Module
| Tool | Description |
|------|-------------|
| `create_customer` | Create a new Customer |
| `get_customer` | Get customer details |
| `list_customers` | List customers with filters |
| `create_quotation` | Create Sales Quotation |
| `create_sales_order` | Create Sales Order |
| `get_sales_order` | Get Sales Order details |

### Stock/Inventory Module
| Tool | Description |
|------|-------------|
| `create_item` | Create a new Item |
| `get_item` | Get item details |
| `get_stock_balance` | Get stock balance |
| `list_warehouses` | List warehouses |
| `create_stock_entry` | Create stock movements |

### Accounting Module
| Tool | Description |
|------|-------------|
| `create_journal_entry` | Create Journal Entry |
| `get_balance_sheet` | Get Balance Sheet data |
| `get_profit_loss` | Get P&L Statement data |
| `create_payment_entry` | Create Payment Entry |

## Tool Registration

Tools are registered via `hooks.py`:

```python
assistant_tools = [
    "business_simulation.assistant_tools.sales_tools.CreateCustomer",
    "business_simulation.assistant_tools.sales_tools.GetCustomer",
    # ... more tools
]
```

## Adding New Tools

1. Create a new tool file in `business_simulation/assistant_tools/`
2. Extend `BaseTool` from Frappe Assistant Core
3. Define `name`, `description`, `inputSchema`, and `execute()` method
4. Register in `hooks.py`

Example:

```python
from frappe_assistant_core.core.base_tool import BaseTool

class MyNewTool(BaseTool):
    def __init__(self):
        super().__init__()
        self.name = "my_new_tool"
        self.description = "Description of what this tool does"
        self.requires_permission = "DocType Name"
        self.inputSchema = {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param1"]
        }

    def execute(self, arguments):
        # Your tool logic here
        return {"success": True, "result": "..."}
```

## Architecture

This app follows the external app development pattern from Frappe Assistant Core:

```
business_simulation/
├── business_simulation/
│   ├── hooks.py              # Tool registration
│   ├── assistant_tools/      # MCP tools
│   │   ├── sales_tools.py
│   │   ├── stock_tools.py
│   │   └── accounting_tools.py
│   └── ...
└── pyproject.toml
```

## Use Cases

### Business Education AI
Simulate business scenarios using real ERPNext data and operations.

### Family Office
Use ERPNext modules (Asset, CRM, Wiki) for distributed family management.

### Decision Support
AI agents can analyze data and execute business operations through MCP tools.

## Testing

```bash
bench run-tests --app business_simulation
```

## License

MIT
