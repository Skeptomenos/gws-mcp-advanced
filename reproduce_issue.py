import json

from gdocs.markdown_parser import MarkdownToDocsConverter

markdown_text = """## 1. HIGH PRIORITY / URGENT

### Andrew Holmes (Personal)
- Returned from sabbatical early (Dec 29) due to a family health emergency (father diagnosed with cancer).
- Fully active as L2 Lead but requires continued flexibility to travel between UK and Berlin.

### Golden Ticket Technical Implementation & Readiness
- **Timeline:** Technical implementation is imminent; completion targeted for the **end of next week**.
"""

converter = MarkdownToDocsConverter()
requests = converter.convert(markdown_text)

print(json.dumps(requests, indent=2))
