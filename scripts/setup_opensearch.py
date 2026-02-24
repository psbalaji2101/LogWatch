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

# import sys
# import os

# # 🔧 Add project root to Python path
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from backend.app.search.client import get_opensearch_client
# from backend.app.search.mappings import create_index_template

# def main():
#     # Use the synchronous client
#     client = get_opensearch_client()
#     # Run the setup synchronously
#     create_index_template(client)
#     print("OpenSearch setup complete")

# if __name__ == "__main__":
#     main()

#-------------------------
#!/usr/bin/env python3
"""Setup OpenSearch indices"""

import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))

from app.search.client import get_opensearch_client
from app.search.mappings import create_index_template

def main():
    """Main setup function"""
    print("Setting up OpenSearch indices...")
    
    try:
        client = get_opensearch_client()
        success = create_index_template(client)
        
        if success:
            print("✅ OpenSearch setup complete!")
        else:
            print("❌ Setup failed")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
