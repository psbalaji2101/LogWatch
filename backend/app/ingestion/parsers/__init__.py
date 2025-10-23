# """Parser module"""

# from app.ingestion.parsers.base import BaseParser
# from app.ingestion.parsers.json_parser import JSONParser
# from app.ingestion.parsers.csv_parser import CSVParser
# from app.ingestion.parsers.regex_parser import RegexParser
# from app.ingestion.parsers.heuristic_parser import HeuristicParser

# __all__ = [
#     "BaseParser",
#     "JSONParser",
#     "CSVParser",
#     "RegexParser",
#     "HeuristicParser"
# ]


from .base import BaseParser
from .json_parser import JSONParser
from .csv_parser import CSVParser
from .regex_parser import RegexParser
from .heuristic_parser import HeuristicParser

__all__ = [
    "BaseParser",
    "JSONParser",
    "CSVParser",
    "RegexParser",
    "HeuristicParser"
]

