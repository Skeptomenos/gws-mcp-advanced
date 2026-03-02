import asyncio

from auth.google_auth import get_authenticated_google_service
from gdocs.docs_helpers import create_insert_table_request

# Hardcoded scope for debug
DOCS_SCOPE = ["https://www.googleapis.com/auth/documents"]


async def debug_table_math():
    user_email = "david.helmus@hellofresh.com"

    print(f"Authenticating for {user_email}...")
    service, _ = await get_authenticated_google_service(
        service_name="docs",
        version="v1",
        tool_name="debug_script",
        user_google_email=user_email,
        required_scopes=DOCS_SCOPE,
    )

    print("Creating table doc...")
    # We can't use create_doc for this specific low-level debug,
    # we need to inject a raw table request without text

    doc = await asyncio.to_thread(service.documents().create(body={"title": "DEBUG_TABLE_INDICES"}).execute)
    doc_id = doc["documentId"]
    print(f"Created {doc_id}")

    # Insert 2x2 Table at index 1
    requests = [create_insert_table_request(index=1, rows=2, columns=2)]
    await asyncio.to_thread(service.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute)

    # 2. Fetch Structure
    print("Fetching structure...")
    doc = await asyncio.to_thread(service.documents().get(documentId=doc_id).execute)

    # 3. Analyze Indices
    body_content = doc.get("body", {}).get("content", [])

    for element in body_content:
        if "table" in element:
            print(f"Table found at {element['startIndex']}")
            table = element["table"]
            print(f"Rows: {table['rows']}")

            for r_idx, row in enumerate(table["tableRows"]):
                print(f"  Row {r_idx} Start: {row['startIndex']} End: {row['endIndex']}")
                for c_idx, cell in enumerate(row["tableCells"]):
                    # content is a list of structural elements
                    cell_content = cell.get("content", [])
                    # Usually the first element in a cell is a Paragraph
                    first_elem = cell_content[0] if cell_content else {}

                    print(f"    Cell ({r_idx},{c_idx}):")
                    print(f"      Cell Range: {cell['startIndex']} - {cell['endIndex']}")
                    print(f"      First Para Start: {first_elem.get('startIndex')}")

                    # Calculate what our formula WOULD have guessed
                    # Formula: start + 4 + ...
                    # Let's see the delta


if __name__ == "__main__":
    asyncio.run(debug_table_math())
