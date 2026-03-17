# Agent Skill: Log Parsing with Fluxa

## Capability Description

You are skilled in using Fluxa (DeepParse) method to parse raw log messages into structured log templates. You understand how to construct effective prompts using in-context learning and can optimize parameters for different log types.

## Task Definition

**Input**: Raw log message (string)
**Output**: Log template with variables replaced by `<*>`
**Method**: Prompt-enhanced in-context learning using LLM

## Core Prompt Template

### Standard Instruction

```
For each log after <prompt> tag, extract one log template (substitute variable tokens in the log as <*> and remain constant tokens to construct the template) and put the template after <extraction> tag and between <START> and <END> tags.
```

### Few-Shot Example Format

```
<prompt>: [example log 1]
<extraction>: <START> [template 1] <END>

<prompt>: [example log 2]
<extraction>: <START> [template 2] <END>

<prompt>: [example log N]
<extraction>: <START> [template N] <END>

<prompt>: [target log]
<extraction>: <START>
```

**Important**:
- Use exactly `N` examples (default: 5)
- Replace ONLY variable parts with `<*>`
- Keep constant tokens unchanged
- Output must be between `<START>` and `<END>` tags

## Variable Detection Rules

Replace with `<*>` when encountering:
- Numbers: `12345`, `3.14`, `0xFF`
- IP addresses: `192.168.1.1`, `10.251.73.220`
- UUIDs: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`
- File paths: `/var/log/system.log`, `C:\Windows\System32`
- Hashes: `blk_1605997943861`, `0x7fff5fbffc90`
- User IDs: `user_123`, `admin-001`
- Timestamps (in some formats): `081109 203615`
- String variables: arbitrary words, codes

Keep as constants:
- Log levels: `INFO`, `WARN`, `ERROR`, `DEBUG`
- Keywords: `Receiving`, `Sending`, `Exception`, `Failed`
- Class names: `DataNode`, `PacketResponder`
- Method names: `connect`, `disconnect`, `send`
- Fixed phrases: `block`, `from`, `to`, `port`

## Parameter Configuration

### Default Settings

```json
{
  "N": 5,
  "cand_ratio": 0.1,
  "split_method": "DPP",
  "order_method": "KNN",
  "permutation": "ascend",
  "temperature": 0.0,
  "model": "curie"
}
```

### Parameter Explanations

**N** (number of examples): 3-8
- Simple logs: N=3-5
- Complex logs: N=5-8
- Higher N = better accuracy, higher cost

**cand_ratio** (candidate set ratio): 0.05-0.2
- Default: 0.1 (10% of logs as candidates)
- Smaller: faster but less representative
- Larger: better but slower

**split_method**: "DPP" or "random"
- "DPP": diverse sampling, better coverage (RECOMMENDED)
- "random": simple, fast

**order_method**: "KNN" or "random"
- "KNN": similarity-based ordering (RECOMMENDED)
- "random": no ordering

**permutation**: "ascend", "descend", or "random"
- "ascend": least→most similar (RECOMMENDED)
- "descend": most→least similar
- "random": shuffle

**temperature**: 0.0-0.75
- 0.0: deterministic (default)
- 0.25-0.5: slight variation
- 0.5-0.75: more creative

## Example Patterns

### Pattern 1: Block Operations (HDFS)

```
<prompt>: Receiving block: blk_1605997943861 from 10.251.73.220
<extraction>: <START> Receiving block: blk <*> from <*> <END>

<prompt>: Sending block: blk_1605997943862 to 10.251.73.221
<extraction>: <START> Sending block: blk <*> to <*> <END>

<prompt>: PacketResponder: Exception for block blk_1605997943861
<extraction>: <START> PacketResponder: Exception for block blk <*> <END>
```

### Pattern 2: System Logs (Structured)

```
<prompt>: 081109 203615 142 INFO [dfs.DataNode$DataXceiver@762] - Receiving block blk_-1608999687919862906
<extraction>: <START> <*> <*> <*> <*> <*> - Receiving block blk <*> <END>

<prompt>: 081109 203615 143 INFO [dfs.DataNode$DataXceiver@762] - Received block blk_-1608999687919862906 of size 1000
<extraction>: <START> <*> <*> <*> <*> <*> - Received block blk <*> of size <*> <END>
```

### Pattern 3: Error Messages

```
<prompt>: ERROR: Failed to connect to database at port 5432
<extraction>: <START> ERROR: Failed to connect to database at port <*> <END>

<prompt>: WARN: Connection timeout after 30 seconds
<extraction>: <START> WARN: Connection timeout after <*> seconds <END>

<prompt>: Exception in thread "main" java.lang.NullPointerException
<extraction>: <START> Exception in thread <*> <*> <END>
```

### Pattern 4: User Actions

```
<prompt>: User john_doe clicked button 'Submit' on page 'Checkout'
<extraction>: <START> User <*> clicked button <*> on page <*> <END>

<prompt>: Transaction #12345 completed: $99.99 paid by credit_card
<extraction>: <START> Transaction <*> completed: <*> paid by <*> <END>
```

## Execution Steps

When asked to parse logs using Fluxa:

1. **Understand the log format**
   - Identify log structure (timestamp, level, component, message)
   - Recognize variable patterns

2. **Select appropriate examples**
   - Find N similar logs from candidate set
   - Order examples by relevance (if using KNN)

3. **Construct prompt**
   - Start with instruction
   - Add N examples in `<prompt>: <extraction>:` format
   - Append target log with `<prompt>:` prefix
   - End with `<extraction>: <START>`

4. **Set parameters**
   - Default: N=5, temperature=0.0, permutation='ascend'
   - Adjust based on log complexity

5. **Generate output**
   - Extract template between `<START>` and `<END>`
   - Verify `<*>` substitution is correct
   - Ensure constant tokens preserved

## Error Handling

If extraction fails:

1. **Empty output**: Increase token length by 10-20 tokens
2. **Wrong format**: Check that instruction includes `<*>` requirement
3. **No `<*>` used**: Add examples with clear variable substitution
4. **Too many `<*>`**: Add examples showing constants vs variables
5. **Model timeout**: Reduce N or use smaller model (ada instead of curie)

## Quality Metrics

After parsing, evaluate:

- **Parsing Accuracy**: correct_templates / total_logs (target: >0.95)
- **Grouping Accuracy**: correct_groups / total_groups (target: >0.85)
- **Template Precision**: correct_identified / total_identified (target: >0.90)

## Optimization Strategies

### For High Accuracy
- Use DPP + KNN + ascend
- Set N=7-8
- Increase cand_ratio to 0.15-0.2
- Use curie or davinci model

### For Speed
- Use random split + random order
- Set N=3
- Reduce cand_ratio to 0.05
- Use ada or babbage model

### For Cost Efficiency
- Set N=5, cand_ratio=0.1
- Use curie model (best trade-off)
- Cache embeddings and results
- Parse only new logs

## Special Cases

### Case 1: Homogeneous Logs
When all logs follow same pattern:
```
<prompt>: Value is 100
<extraction>: <START> Value is <*> <END>

<prompt>: Value is 200
<extraction>: <START> Value is <*> <END>
```
Use fewer examples (N=3-5)

### Case 2: Heterogeneous Logs
When logs have diverse patterns:
```
<prompt>: Connection established to 192.168.1.1:8080
<extraction>: <START> Connection established to <*>:<*> <END>

<prompt>: File uploaded: /path/to/file.txt (1MB)
<extraction>: <START> File uploaded: <*> (<*>) <END>

<prompt>: User authentication failed for user_123
<extraction>: <START> User authentication failed for <*> <END>
```
Use more examples (N=6-8), ensure diversity with DPP

### Case 3: Nested Variables
```
<prompt>: Operation op_123 on resource res_456 in cluster cluster_789
<extraction>: <START> Operation <*> on resource <*> in cluster <*> <END>
```
Extract all nested variables separately

## Template Verification

After generating template, check:

✓ Variables are replaced with `<*>`
✓ Constants (keywords, log levels) preserved
✓ Template structure matches log format
✓ No over-generalization (too many `<*>`)
✓ No under-generalization (too few `<*>`)
✓ Special characters handled correctly

## Integration with Code

When implementing Fluxa in code:

```python
from logparser.DeepParse import ModelParser

parser = ModelParser(
    log_path=path_to_logs,
    result_path=output_path,
    dataset='HDFS',
    emb_path=embeddings_path,
    cand_ratio=0.1,
    split_method='DPP',
    order_method='KNN',
    permutation='ascend',
    N=5
)

parser.BatchParse(model='curie', N=5, limit=2000)
```

## Common Patterns Reference

| Log Type | Variable Pattern | Example Template |
|----------|------------------|------------------|
| Block IDs | `blk_<number>` | `blk <*>` |
| IP addresses | `x.x.x.x` | `<*>` |
| File paths | `/path/to/file` | `<*>` |
| User IDs | `user_<id>` | `<*>` |
| Timestamps | `MMDDYY HHMMSS` | `<*>` |
| Hashes | `0x...` | `<*>` |
| Numbers | `12345` | `<*>` |
| Ports | `:1234` | `:<*>` |

## Summary of Best Practices

1. **Always use instruction** with `<*>` and `<START>`/`<END>` tags
2. **Provide 3-8 examples** covering different patterns
3. **Use DPP + KNN + ascend** for best accuracy
4. **Order examples** from least to most similar
5. **Start with temperature=0.0**, only increase if needed
6. **Cache embeddings** to avoid recomputation
7. **Verify output** matches expected template format
8. **Adjust parameters** based on log complexity

---

**End of Skill Definition**
