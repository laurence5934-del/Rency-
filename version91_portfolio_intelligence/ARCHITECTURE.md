# Version 9.1 Architecture

```text
IBKR account summary + positions
                |
                v
PortfolioSnapshotAdapter
                |
                v
PortfolioIntelligence
       |                |
       v                v
Portfolio Dashboard   Rule-based Advisor
       |
       v
Human review / existing risk workflow
```

The intelligence layer adds dashboard percentages, health scoring, largest
position analysis, and capacity recommendations without changing order logic.
