# Kitchen Sink: Google Docs Formatting Test

## 1. Typography
This text is **bold**.
This text is *italic*.
This text is ***bold and italic***.
This is a [link to Google](https://google.com).
This is `inline code` for variable names.

## 2. Headings (Hierarchy)
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6

## 3. Lists
### Unordered
- Level 1 Item A
- Level 1 Item B
  - Level 2 Nested Item
  - Level 2 Nested Item
    - Level 3 Deep Nesting
- Level 1 Item C

### Ordered
1. Step One
2. Step Two
   1. Sub-step A
   2. Sub-step B
3. Step Three

## 4. Code Blocks
```python
def hello_world():
    print("This should be monospaced with gray background")
    return True
```

## 5. Blockquotes
> This is a blockquote.
> It should be indented and italicized.

## 6. Tables
| Feature | Status | Priority |
| :--- | :--- | :--- |
| Formatting | ✅ Beta | High |
| Tables | ⚠️ Complex | Medium |
| Lists | ✅ Stable | Low |

## 7. Edge Cases
### Mixed Content
**Bold Header** with *italic* text inside.

- List item with **bold** text
- List item with `code` inside

### Empty Lines Below (Spacing Test)

(There should be spacing above this line)

## 8. Horizontal Rules

Above the line.

---

Below the line.

## 9. Strikethrough

This text is ~~crossed out~~ and this is normal.

## 10. Task Lists

- [ ] Unchecked task
- [x] Completed task
- [ ] Another pending task

## 11. Images

![Google Logo](https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png)
