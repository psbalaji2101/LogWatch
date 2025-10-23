# #!/usr/bin/env python3
# """Setup OpenSearch indices"""

# import asyncio
# from backend.app.search.client import get_opensearch_client
# from backend.app.search.mappings import create_index_template

# async def main():
#     client = await get_opensearch_client()
#     await create_index_template(client)
#     print("OpenSearch setup complete")

# if __name__ == "__main__":
#     asyncio.run(main())

#----chatGPT---------

# #!/usr/bin/env python3
# """Setup OpenSearch indices"""

# import sys, os
# # 🔧 Add the project root (LogIngestion/) to Python's module search path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# import asyncio
# from backend.app.search.client import get_opensearch_client
# from backend.app.search.mappings import create_index_template

# async def main():
#     client = await get_opensearch_client()
#     await create_index_template(client)
#     print("OpenSearch setup complete")

# if __name__ == "__main__":
#     asyncio.run(main())

import sys
import os

# 🔧 Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.search.client import get_opensearch_client
from backend.app.search.mappings import create_index_template

def main():
    # Use the synchronous client
    client = get_opensearch_client()
    # Run the setup synchronously
    create_index_template(client)
    print("OpenSearch setup complete")

if __name__ == "__main__":
    main()