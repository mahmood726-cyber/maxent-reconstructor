
# MaxEnt vs IPDfromAGD: Method Comparison

## IPDfromAGD Methods (R Package)

The IPDfromAGD package implements several methods:

1. **Method 1 (M1)**: Normal approximation approach
   - Assumes normal distribution
   - Uses moment matching
   - Similar to Naive Normal

2. **Method 2 (M2)**: Based on published IPD
   - Uses reference IPD distributions
   - Rescales to match target statistics
   - More accurate when similar data available

3. **Method 3 (M3)**: Based on clinical study report IPD
   - Uses patient-level data from CSRs
   - Most accurate but requires access
   - Limited availability

## MaxEnt Method

The Maximum Entropy approach:

- **Distribution assumption**: Truncated normal
- **Optimization**: 5-stage moment matching
- **Advantages**:
  - No reference data needed
  - Handles bounded data well
  - Works with skewed distributions
  - Always produces valid results

## Comparison Summary

| Aspect | IPDfromAGD M1 | IPDfromAGD M2 | IPDfromAGD M3 | MaxEnt |
|--------|--------------|--------------|--------------|---------|
| Normal data | Good | Excellent | Excellent | Good |
| Skewed data | Poor | Good | Good | Good |
| Bounded data | Poor | Fair | Fair | Excellent |
| Reference data | Not needed | Required | Required | Not needed |
| Availability | R package | R package | Limited | Python/R |
| Speed | Fast | Medium | Slow | Fast |

## When to Use Each Method

**Use MaxEnt when:**
- Data is bounded (min/max known)
- Distribution may be skewed
- No reference IPD available
- Need guaranteed valid results

**Use IPDfromAGD M2 when:**
- Similar reference IPD exists
- Working in R environment
- Want best possible accuracy

**Use IPDfromAGD M3 when:**
- Have access to CSR IPD
- Maximum accuracy needed
- Clinical trial setting
