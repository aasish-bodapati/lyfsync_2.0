# LyfSync Benchmark Assumptions

This document outlines the standard portion priors used to compute gold-standard macros for ambiguous or culturally-specific inputs in the SOTA benchmark.

## Indian Portions
- **1 Katori (Bowl)** = 180ml volume.
  - Dal: ~180g
  - Rice: ~150g
  - Curry (meat): ~200g
- **1 Roti/Chapati** = 50g (standard size).
- **1 Idli** = 50g.
- **1 Dosa** = 120g (plain) / 150g (masala).
- **1 Plate Biryani (Restaurant)** = ~400g total (approx. 200g rice, 150g meat, 50g fat/spices/gravy).

## Ambiguous Western Portions
- **"A bowl"** (e.g., of oats) = 1 cup / ~240ml volume.
- **"Half a pizza"** = Depends on the pizza type, but generally assume 1 standard 12-inch medium pizza = ~800g, so half = 400g.
- **"A little oil" / "A splash"** = 1 teaspoon (5ml / 4.5g).
- **"A handful"** (e.g., peanuts) = 30g.
- **"A generous amount"** = 1.5x to 2x the standard serving size.

## Cooking Losses
- **Yogurt Marinade**: If grilled/air-fried/baked, assume 80% of the yogurt marinade weight is discarded.
- **Deep Frying**: Assume oil absorption equal to 10% of the raw food's weight.

*Note: These assumptions are codified to create deterministic ground truth for the benchmark. The LLM's outputs will be judged against these specific assumptions.*
